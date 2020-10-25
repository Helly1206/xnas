# -*- coding: utf-8 -*-
#########################################################
# SERVICE : xnas_wd.py                                  #
#           Handles watchdog funtions for dynmount      #
#           and other services, requiring watchdog pkg  #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
from remotes.ping import ping
from mounts.zfs import zfs
from threading import Lock
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileDeletedEvent, EVENT_TYPE_CREATED, EVENT_TYPE_DELETED
    from watchdog.observers.api import EventEmitter, BaseObserver
except:
    try:
        import pip
        try:
            package="watchdog"
            if hasattr(pip, 'main'):
                pip.main(['install', package])
            else:
                pip._internal.main(['install', package])
        except:
            print("Unable to install required packages")
            print("watchdog not installed")
            exit(1)
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileDeletedEvent, EVENT_TYPE_CREATED, EVENT_TYPE_DELETED
        from watchdog.observers.api import EventEmitter, BaseObserver
    except:
        print("Pip not installed, please install pip to continue")
        print("Unable to install the required packages")
        exit(1)
#########################################################

####################### GLOBALS #########################
DEVICE_LOC = "/dev/disk/by-path"
OBSERVER_TIMEOUT = 5
EMITTER_TIMEOUT  = 5
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : deviceHandler                                 #
#########################################################
class deviceHandler(FileSystemEventHandler):
    def __init__(self, onAdded = None, onDeleted = None):
        self.onAdded = onAdded
        self.onDeleted = onDeleted
        self.data = {}
        self.on_any_event(None)

    def __del__(self):
        pass

    def on_any_event(self, event):
        if not event:
            # initial sync
            self.initial()
        else:
            if not event.is_directory:
                if event.event_type == EVENT_TYPE_DELETED:
                    fsname = self.findInList(event.src_path)
                    if self.onDeleted:
                        self.onDeleted(fsname)
                    self.delFromList(event.src_path)
                elif event.event_type == EVENT_TYPE_CREATED:
                    fsname = self.addToList(event.src_path)
                    if self.onAdded and fsname:
                        self.onAdded(fsname)

    def initial(self):
        with os.scandir(DEVICE_LOC) as entries:
            for entry in entries:
                fsname = self.addToList(os.path.join(DEVICE_LOC,entry.name))
                if self.onAdded:
                    self.onAdded(fsname)

    def addToList(self, path):
        fsname = ""
        try:
            fsname = os.path.realpath(os.path.join(DEVICE_LOC,os.readlink(path)))
            self.data[path] = fsname
        except:
            pass
        return fsname

    def delFromList(self, path):
        try:
            self.data.pop(path)
        except:
            pass

    def findInList(self, path):
        fsname = ""
        if self.data:
            for key, value in self.data.items():
                if key == path:
                    fsname = value
                    break
        return fsname
#########################################################
# Class : device_wd                                     #
#########################################################
class device_wd(object):
    def __init__(self, onAdded = None, onDeleted = None):
        self.onAdded = onAdded
        self.onDeleted = onDeleted
        self.observer = None

    def __del__(self):
        if self.observer:
            self.stop()

    def start(self):
        if self.observer:
            self.stop()
        event_handler = deviceHandler(self.onAdded, self.onDeleted)
        self.observer = Observer()
        self.observer.schedule(event_handler, path = DEVICE_LOC, recursive = False)
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            #self.observer.join()
            del self.observer
            self.observer = None

#########################################################
# Class : simpleHandler                                 #
#########################################################
class simpleHandler(FileSystemEventHandler):
    def __init__(self, onAdded = None, onDeleted = None):
        self.onAdded = onAdded
        self.onDeleted = onDeleted
        self.on_any_event(None)

    def __del__(self):
        pass

    def on_any_event(self, event):
        if not event:
            pass
        else:
            if event.event_type == EVENT_TYPE_DELETED:
                if self.onDeleted:
                    self.onDeleted(event.src_path)
            elif event.event_type == EVENT_TYPE_CREATED:
                if self.onAdded:
                    self.onAdded(event.src_path)

#########################################################
# Class : RemoteEmitter                                 #
#########################################################
class RemoteEmitter(EventEmitter):
    urlList = []
    onlineList = []
    offlineList = []
    _lock = Lock()

    def __init__(self, event_queue, watch, timeout = EMITTER_TIMEOUT):
        EventEmitter.__init__(self, event_queue, watch, timeout)
        self.ping = ping()

    def on_thread_start(self):
        pass

    @classmethod
    def update(cls, urlList = []):
        with cls._lock:
            cls.urlList = urlList
            for item in cls.onlineList:
                if not item in cls.urlList:
                    cls.onlineList.remove(item)
            for item in cls.offlineList:
                if not item in cls.urlList:
                    cls.offlineList.remove(item)

    def queue_events(self, timeout):
        if self.stopped_event.wait(timeout):
            return

        with self._lock:
            if not self.should_keep_running():
                return

            try:
                for url in self.urlList:
                    available = self.ping.ping(url)

                    if available:
                        if not url in self.onlineList:
                            self.onlineList.append(url)
                            self.queue_event(FileCreatedEvent(url))
                        if url in self.offlineList:
                            self.offlineList.remove(url)
                    else:
                        if not url in self.offlineList:
                            self.offlineList.append(url)
                            self.queue_event(FileDeletedEvent(url))
                        if url in self.onlineList:
                            self.onlineList.remove(url)
            except:
                self.stop()
                return

#########################################################
# Class : RemoteObserver                                #
#########################################################
class RemoteObserver(BaseObserver):
    def __init__(self, urlList = [], timeout = OBSERVER_TIMEOUT):
        RemoteEmitter.update(urlList)
        BaseObserver.__init__(self, emitter_class = RemoteEmitter, timeout = timeout)

    def updateList(self, urlList = []):
        RemoteEmitter.update(urlList)

#########################################################
# Class : remote_wd                                     #
#########################################################
class remote_wd(object):
    def __init__(self, urlList = [], onAdded = None, onDeleted = None):
        self.urlList = urlList
        self.onAdded = onAdded
        self.onDeleted = onDeleted
        self.observer = None

    def __del__(self):
        if self.observer:
            self.stop()

    def start(self):
        if self.observer:
            self.stop()
        event_handler = simpleHandler(self.onAdded, self.onDeleted)
        self.observer = RemoteObserver(self.urlList)
        self.observer.schedule(event_handler, path = "", recursive = False)
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            #self.observer.join()
            del self.observer
            self.observer = None

    def updateList(self, urlList = []):
        self.urlList = urlList
        if self.observer:
            self.observer.updateList(urlList)

#########################################################
# Class : ZfsEmitter                                    #
#########################################################
class ZfsEmitter(EventEmitter):
    poolList = []
    deleteDegraded = False
    poolHealth = {}
    _lock = Lock()

    def __init__(self, event_queue, watch, timeout = EMITTER_TIMEOUT):
        EventEmitter.__init__(self, event_queue, watch, timeout)
        self.zfs = zfs(None, True)

    def __del__(self):
        del self.zfs

    def on_thread_start(self):
        pass

    @classmethod
    def update(cls, poolList = [], deleteDegraded = False):
        with cls._lock:
            cls.poolList = poolList
            cls.deleteDegraded = deleteDegraded
            for key, value in cls.poolHealth.items():
                if not key in cls.poolList:
                    cls.poolHealth.pop(key)

    def queue_events(self, timeout):
        if self.stopped_event.wait(timeout):
            return

        with self._lock:
            if not self.should_keep_running():
                return

            try:
                for pool in self.poolList:
                    health = self.zfs.getHealth(pool)

                    if health == "ONLINE" or (health == "DEGRADED" and not self.deleteDegraded):
                        if not self.zfs.isMounted(pool):
                            health = "UNMOUNTED"
                        if pool in self.poolHealth:
                            if self.poolHealth[pool] != health:
                                self.queue_event(FileCreatedEvent({pool: health}))
                                self.poolHealth[pool] = health
                        else:
                            self.queue_event(FileCreatedEvent({pool: health}))
                            self.poolHealth[pool] = health
                    else:
                        if pool in self.poolHealth:
                            if self.poolHealth[pool] != health:
                                self.queue_event(FileDeletedEvent({pool: health}))
                                self.poolHealth[pool] = health
                        else:
                            self.queue_event(FileDeletedEvent({pool: health}))
                            self.poolHealth[pool] = health
            except:
                self.stop()
                return

#########################################################
# Class : ZfsObserver                                   #
#########################################################
class ZfsObserver(BaseObserver):
    def __init__(self, poolList = [], deleteDegraded = False, timeout = OBSERVER_TIMEOUT):
        ZfsEmitter.update(poolList, deleteDegraded)
        BaseObserver.__init__(self, emitter_class = ZfsEmitter, timeout = timeout)

    def updateList(self, poolList = [], deleteDegraded = False):
        ZfsEmitter.update(poolList, deleteDegraded)

#########################################################
# Class : zfs_wd                                        #
#########################################################
class zfs_wd(object):
    def __init__(self, poolList = [], deleteDegraded = False, onAdded = None, onDeleted = None):
        self.poolList = poolList
        self.deleteDegraded = deleteDegraded
        self.onAdded = onAdded
        self.onDeleted = onDeleted
        self.observer = None

    def __del__(self):
        if self.observer:
            self.stop()

    def start(self):
        if self.observer:
            self.stop()
        event_handler = simpleHandler(self.onAdded, self.onDeleted)
        self.observer = ZfsObserver(self.poolList, self.deleteDegraded)
        self.observer.schedule(event_handler, path = "", recursive = False)
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            #self.observer.join()
            del self.observer
            self.observer = None

    def updateList(self, poolList = [], deleteDegraded = False):
        self.poolList = poolList
        self.deleteDegraded = deleteDegraded
        if self.observer:
            self.observer.updateList(poolList, deleteDegraded)

######################### MAIN ##########################
if __name__ == "__main__":
    pass
