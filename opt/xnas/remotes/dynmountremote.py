# -*- coding: utf-8 -*-
#########################################################
# SERVICE : dynmountremote.py                           #
#           Handles dynamic mounts for remote mounts    #
#           Part of xservices                           #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import logging
from common.xnas_engine import groups
from mounts.mountfs import mountfs
from remotes.davfs import davfs
from remotes.cifs import cifs
from remotes.nfs import nfs
from common.xnas_wd import remote_wd
from common.dynmountdata import dynmountdata
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : dynmountremote                                #
#########################################################
class dynmountremote(mountfs, dynmountdata):
    def __init__(self, engine, verbose = False):
        self.engine    = engine
        self.verbose   = verbose
        self.logger    = logging.getLogger('xnas.dynmountremote')
        self.xmounts   = []
        self.remote_wd = remote_wd(self.getUrlList(), self.onAdded, self.onDeleted)
        mountfs.__init__(self, self.logger)
        dynmountdata.__init__(self, self.logger)
        self.remote_wd.start()

    def __del__(self):
        dynmountdata.__del__(self)
        mountfs.__del__(self)

    def terminate(self):
        if self.remote_wd:
            self.remote_wd.stop()
            del self.remote_wd

    def updateUrlList(self):
        self.remote_wd.updateList(self.getUrlList())

    ####################### CALLBACKS #######################

    def onAdded(self, url):
        self.engine.mutex.acquire()
        #available
        mountpoint, uuid = self.findMountpoint(url, True)
        xmount = self.findRemoteMount(url)
        if xmount:
            self.logger.info("{} remotemount online".format(xmount))
            if mountpoint:
                refs = []
                refsena = []
                if self.isMounted(mountpoint):
                    mounted = True
                    self.logger.info("{} already mounted".format(xmount))
                else:
                    mounted = mountfs.mount(self, mountpoint)
                    if mounted:
                        self.logger.info("{} mounted as {}".format(xmount, self.getMethod(xmount)))
                    else:
                        self.logger.error("{} mounting failed".format(xmount))
                if mounted: # check reference
                    refs, refsena = self.checkReferences(self.engine, xmount, self.verbose)
                    if self.verbose:
                        for ref,refena in zip(refs, refsena):
                            if not refena:
                                self.logger.info("{} reference found, but not enabled: {}".format(xmount, ref))
                        if not refs:
                            self.logger.info("{} no reference found".format(xmount))
                dynmountdata.addDynmount(xmount, mounted, mountpoint, refs, refsena)
            else:
                self.logger.warning("{} remotemount online but no available mountpoint found, not mounting".format(xmount))
                dynmountdata.addDynmount(xmount)
        elif self.verbose:
            self.logger.error("remotemount online but not found in database, not mounting: {}".format(url))
        self.engine.mutex.release()

    def onDeleted(self, url):
        self.engine.mutex.acquire()
        #not available
        mountpoint, uuid = self.findMountpoint(url, True)
        xmount = self.findRemoteMount(url)
        if xmount:
            self.logger.info("{} remotemount offline".format(xmount))
            if mountpoint:
                if not self.isMounted(mountpoint):
                    mounted = False
                    self.logger.info("{} already unmounted".format(xmount))
                else:
                    # leave references as they are
                    mounted = not mountfs.unmount(self, mountpoint, internal = True, force = True)
                    if not mounted:
                        self.logger.info("{} unmounted".format(xmount))
                    else:
                        self.logger.error("{} unmounting failed".format(xmount))
                if not mounted:
                    self.delMountpoint(url)
                dynmountdata.addDynmount(xmount, mounted, mountpoint)
            else:
                self.logger.warning("{} remotemount offline but no available mountpoint found, not unmounting".format(xmount))
                dynmountdata.addDynmount(xmount)
        elif self.verbose:
            self.logger.error("remotemount offline but not found in database, not unmounting: {}".format(url))
        self.engine.mutex.release()

    ################## INTERNAL FUNCTIONS ###################

    def getUrlList(self):
        newxmounts = []
        urlList = []
        mounts = self.engine.checkGroup(groups.REMOTEMOUNTS)
        if mounts:
            for key, mount in mounts.items():
                if mount['method'] == "dynmount":
                    url = self.getURL(mount)
                    if url:
                        urlList.append(url)
                    refs, refsena = self.getReferences(self.engine, key)
                    mounted = self.isMounted(mount['mountpoint'])
                    dynmountdata.addDynmount(key, mounted, mount['mountpoint'], refs, refsena)
                    newxmounts.append(key)
                elif mount['method'] == "auto":
                    refs, refsena = self.getReferences(self.engine, key)
                    dynmountdata.addDynmount(key, False, mount['mountpoint'], refs, refsena, health = "AUTO")
                    newxmounts.append(key)
        for newxmount in newxmounts:
            if not newxmount in self.xmounts:
                self.xmounts.append(newxmount)
        for xmount in self.xmounts:
            if not xmount in newxmounts:
                self.xmounts.remove(xmount)
                dynmountdata.delDynmount(xmount)
        return urlList

    def getURL(self, db):
        url = ""
        if db['type'] == 'davfs':
            url = davfs(self.logger).buildURL(db['https'], db['server'], db['sharename'])
        elif db['type'] == 'cifs':
            url = cifs(self.logger).buildURL(db['https'], db['server'], db['sharename'])
        elif db['type'] == 'nfs' or db['type'] == 'nfs4':
            url = nfs(self.logger).buildURL(db['https'], db['server'], db['sharename'])
        return url

    def findRemoteMount(self, url):
        xmount = ""
        mounts = self.engine.checkGroup(groups.REMOTEMOUNTS)
        if mounts:
            for key, mount in mounts.items():
                if mount['method'] == "dynmount":
                    mnturl = self.getURL(mount)
                    if mnturl == url:
                        xmount = key
                        break
        return xmount

    def getMethod(self, xmount):
        method = "dynmount"
        mount = self.engine.checkKey(groups.REMOTEMOUNTS, xmount)
        if mount:
            method = mount['method']
        return method

######################### MAIN ##########################
if __name__ == "__main__":
    pass
