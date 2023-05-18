# -*- coding: utf-8 -*-
#########################################################
# SERVICE : xnas_check.py                               #
#           Checks for broken mounts and shares         #
#           when running xnas related command           #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import logging
from mounts.mount import mount
from mounts.fstab import fstab
from mounts.zfs import zfs
from remotes.remotemount import remotemount
from remotes.davfs import davfs
from common.xnas_engine import groups
from common.xnas_engine import errors
from common.xnas_engine import objects
from shares.share import share
from net.netshare import netshare
from remotes.ping import ping
#########################################################

####################### GLOBALS #########################
# {"obj": OBJECT, "name": NAME, "check": CHECK}

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : xnas_check                                    #
#########################################################
class xnas_check(object):
    def __init__(self, engine, Mount = None, Remotemount = None, Share = None, Net = None, noMsg = False, level = -1, json = False):
        #self.engine = engine
        self.logger = logging.getLogger('xnas.check')
        self.engine = engine
        self.noMsg = noMsg
        self.level = level
        self.json = json
        self.msgLst = []
        self.msgCnt = 0
        self.selfMount = False
        self.object = objects.NONE
        if Mount:
            self.Mount = Mount
            self.object = objects.MOUNT
        else:
            self.Mount = mount(engine)
            self.selfMount = True
        self.selfRemotemount = False
        if Remotemount:
            self.Remotemount = Remotemount
            self.object = objects.REMOTEMOUNT
        else:
            self.Remotemount = remotemount(engine)
            self.selfRemotemount = True
        self.selfShare = False
        if Share:
            self.Share = Share
            self.object = objects.SHARE
        else:
            self.Share = share(engine)
            self.selfShare = True
        self.selfNet = False
        if Net:
            self.Net = Net
            self.object = objects.NETSHARE
        else:
            self.Net = netshare(engine)
            self.selfNet = True

    def __del__(self):
        if self.selfNet:
            del self.Net
        if self.selfShare:
            del self.Share
        if self.selfRemotemount:
            del self.Remotemount
        if self.selfMount:
            del self.Mount
        del self.msgLst

    def check(self):
        self.msgLst = []
        self.msgCnt = 0
        Errors = []
        Errors.extend(self.checkMounts())
        Errors.extend(self.checkRemoteMounts())
        Errors.extend(self.checkShares())
        Errors.extend(self.checkNets())

        Errors = [Error for Error in Errors if not Error['warning']]

        if Errors and not self.json:
            print("Xnas reported one or more errors ...")
            if not self.noMsg:
                print("Please run 'xnas fix' to fix these errors")
        return Errors

    def GetList(self):
        return self.msgLst

    def ErrorExit(self, Errors, settings, cmdNames):
        retval = False
        if self.ErrorExitCmd(Errors, settings, self.object):
            if "command" in settings:
                if not settings['command'] in cmdNames:
                    retval = True

        return retval

    def ErrorExitCmd(self, Errors, settings, obj):
        retval = False
        if Errors:
            if "name" in settings:
                for Error in Errors:
                    if Error['obj'] == obj:
                        if Error['name'] == settings['name']:
                            retval = True
                            break

        return retval

    ################## INTERNAL FUNCTIONS ###################

    def checkMounts(self):
        Errors = []
        mounts = self.engine.checkGroup(groups.MOUNTS)
        if mounts:
            for key, mount in mounts.items():
                device = self.Mount.getDevices(mount['uuid'])
                if device:
                    if mount['zfs']:
                        health = zfs.getHealth(self.Mount, mount['uuid'], device[0]['mounted'])
                        available = health == "ONLINE" or health == "DEGRADED"
                    else:
                        available = True
                else:
                    available = False
                if not available:
                    if mount['method'] == "startup" and self.level < 1:
                        self.printError(objects.MOUNT, key, errors.UNAVAILABLE)
                        Errors.append(self.makeError(objects.MOUNT, key, errors.UNAVAILABLE, self.level2warningRpt(self.level)))
                else:
                    if mount['method'] == "dynmount":
                        if not device[0]['mounted']:
                            self.printError(objects.MOUNT, key, errors.DYNNOTMOUNTED)
                            Errors.append(self.makeError(objects.MOUNT, key, errors.DYNNOTMOUNTED, self.level2warning(self.level)))
                    if device[0]['mounted']:
                        if mount['zfs']:
                            health = zfs.getHealth(self.Mount, mount['uuid'], device[0]['mounted'])
                        else:
                            health = fstab.getHealth(self.Mount, mount['uuid'], device[0]['fsname'], device[0]['label'], device[0]['mounted'])
                        if health != "ONLINE":
                            self.printError(objects.MOUNT, key, errors.UNHEALTHY, health)
                            Errors.append(self.makeError(objects.MOUNT, key, errors.UNHEALTHY, self.level2warning(self.level)))
                    else:
                        if self.Mount.isReferenced(key, True) and mount['method'] == "startup" and self.level >= 0:
                            self.printError(objects.MOUNT, key, errors.REFNOTMOUNTED)
                            Errors.append(self.makeError(objects.MOUNT, key, errors.REFNOTMOUNTED, self.level2warning(self.level)))

        return Errors

    def checkRemoteMounts(self):
        Errors = []

        remotemounts = self.engine.checkGroup(groups.REMOTEMOUNTS)
        if remotemounts:
            for key, mount in remotemounts.items():
                url = self.Remotemount.buildDbURL(mount)
                entry = self.Remotemount.getEntry(fsname=url)
                netdev = False
                mounted = False
                Guest = False
                Creds = False
                if entry:
                    if '_netdev' in entry['options']:
                        netdev = True
                    if 'guest' in entry['options']:
                        Guest = True
                    for opt in entry['options']:
                        if 'credentials' in opt:
                            Creds = True
                            break
                    mounted = self.Remotemount.isMounted(entry['mountpoint'])

                    if mount['method'] == "dynmount" and self.level >= 0:
                        if not mounted:
                            if ping().ping(url):
                                self.printError(objects.REMOTEMOUNT, key, errors.DYNNOTMOUNTED)
                                Errors.append(self.makeError(objects.REMOTEMOUNT, key, errors.DYNNOTMOUNTED, self.level2warning(self.level)))
                            else:
                                self.printError(objects.REMOTEMOUNT, key, errors.HOSTFAILED)
                                Errors.append(self.makeError(objects.REMOTEMOUNT, key, errors.HOSTFAILED, self.level2warningRpt(self.level)))

                    if not netdev:
                        self.printError(objects.REMOTEMOUNT, key, errors.NONETDEV)
                        Errors.append(self.makeError(objects.REMOTEMOUNT, key, errors.NONETDEV, self.level2warning(self.level)))

                    if mount['type'] == 'cifs' and self.engine.isSudo():
                        if not (Guest ^ Creds):
                            self.printError(objects.REMOTEMOUNT, key, errors.NOCREDENTIALS)
                            Errors.append(self.makeError(objects.REMOTEMOUNT, key, errors.NOCREDENTIALS, self.level2warning(self.level)))
                    elif mount['type'] == 'davfs' and self.engine.isSudo():
                        Creds = davfs(self.logger).hasCredentials(url)
                        if not (Guest ^ Creds):
                            self.printError(objects.REMOTEMOUNT, key, errors.NOCREDENTIALS)
                            Errors.append(self.makeError(objects.REMOTEMOUNT, key, errors.NOCREDENTIALS, self.level2warning(self.level)))

                    if mounted:
                        health = self.Remotemount.getHealth(fsname = entry['fsname'], isMounted = mounted, hasHost = ping().ping(url))
                        if health != "ONLINE":
                            self.printError(objects.REMOTEMOUNT, key, errors.UNHEALTHY, health)
                            Errors.append(self.makeError(objects.REMOTEMOUNT, key, errors.UNHEALTHY, self.level2warning(self.level)))
                    else:
                        if self.Remotemount.isReferenced(key, True) and mount['method'] == "startup" and self.level >= 0:
                            if ping().ping(url):
                                self.printError(objects.REMOTEMOUNT, key, errors.REFNOTMOUNTED)
                                Errors.append(self.makeError(objects.REMOTEMOUNT, key, errors.REFNOTMOUNTED, self.level2warning(self.level)))
                            else:
                                self.printError(objects.REMOTEMOUNT, key, errors.HOSTFAILED)
                                Errors.append(self.makeError(objects.REMOTEMOUNT, key, errors.HOSTFAILED, self.level2warningRpt(self.level)))
                else: # No entry available
                    if mount['method'] == "startup":
                        self.printError(objects.REMOTEMOUNT, key, errors.UNAVAILABLE)
                        Errors.append(self.makeError(objects.REMOTEMOUNT, key, errors.UNAVAILABLE, self.level2warningRpt(self.level)))
        return Errors

    def checkShares(self):
        Errors = []
        shares = self.engine.checkGroup(groups.SHARES)
        if shares:
            for key, share in shares.items():
                if share['enabled']:
                    if not self.Share.getlink(self.engine.shareDir(key)):
                        self.printError(objects.SHARE, key, errors.ENABLEDNOTLINKED)
                        Errors.append(self.makeError(objects.SHARE, key, errors.ENABLEDNOTLINKED, self.level2warning(self.level)))
                else: #disabled
                    if self.Share.isReferenced(key, True):
                        self.printError(objects.SHARE, key, errors.DISABLEDREFERENCED)
                        Errors.append(self.makeError(objects.SHARE, key, errors.DISABLEDREFERENCED, self.level2warning(self.level)))
                    elif self.Share.getlink(self.engine.shareDir(key)):
                        self.printError(objects.SHARE, key, errors.DISABLEDLINKED)
                        Errors.append(self.makeError(objects.SHARE, key, errors.DISABLEDLINKED, self.level2warning(self.level)))
        return Errors

    def checkNets(self):
        Errors = []

        netshares = self.engine.checkGroup(groups.NETSHARES)
        if netshares:
            for key, netshare in netshares.items():
                if not self.Net.isSourced(key, True) and netshare['enabled']:
                    self.printError(objects.NETSHARE, key, errors.UNAVAILABLE, key)
                    Errors.append(self.makeError(objects.NETSHARE, key, errors.UNAVAILABLE, self.level2warning(self.level)))

        return Errors

    def level2warningRpt(self, level):
        return level != 0

    def level2warning(self, level):
        return level < 0

    def makeError(self, obj, name, check, warning = False):
        #{"obj": OBJECT, "name": NAME, "check": CHECK}
        Error = {}
        Error['obj'] = obj
        Error['name'] = name
        Error['check'] = check
        Error['warning'] = warning
        return(Error)

    def printError(self, obj, name, check, text = ""):
        if obj == objects.MOUNT:
            if check == errors.UNAVAILABLE:
                self.logError("{}: [Mount] Device is unavailable".format(name))
            elif check == errors.DYNNOTMOUNTED:
                self.logError("{}: [Mount] Device is not mounted but should be dynmounted".format(name))
            elif check == errors.UNHEALTHY:
                self.logError("{}: [Mount] Device is mounted but not healthy: {}".format(name, text))
            elif check == errors.REFNOTMOUNTED:
                self.logError("{}: [Mount] Device is referenced but not mounted and should be startup mounted".format(name))
        elif obj == objects.REMOTEMOUNT:
            if check == errors.UNAVAILABLE:
                self.logError("{}: [Remotemount] Device is unavailable".format(name))
            elif check == errors.HOSTFAILED:
                self.logError("{}: [Remotemount] Device host unreachable".format(name))
            elif check == errors.DYNNOTMOUNTED:
                self.logError("{}: [Remotemount] Device is not mounted but should be dynmounted".format(name))
            elif check == errors.UNHEALTHY:
                self.logError("{}: [Remotemount] Device is mounted but not healthy: {}".format(name, text))
            elif check == errors.REFNOTMOUNTED:
                self.logError("{}: [Remotemount] Device is referenced but not mounted and should be startup mounted".format(name))
            elif check == errors.NONETDEV:
                self.logError("{}: [Remotemount] Device doesn't have '_netdev' option".format(name))
            elif check == errors.NOCREDENTIALS:
                self.logError("{}: [Remotemount] Device doesn't have credentials and doesn't have 'guest' option".format(name))
        elif obj == objects.SHARE:
            if check == errors.UNAVAILABLE:
                self.logError("{}: [Share] Source device '{}' is unavailable".format(name, text))
            elif check == errors.ENABLEDNOTLINKED:
                self.logError("{}: [Share] Device is enabled but not linked".format(name))
            elif check == errors.DISABLEDLINKED:
                self.logError("{}: [Share] Device is disabled but link exists".format(name))
            elif check == errors.DISABLEDREFERENCED:
                self.logError("{}: [Share] Device is disabled but referenced".format(name))
        elif obj == objects.NETSHARE:
            if check == errors.UNAVAILABLE:
                self.logError("{}: [Netshare] Source device '{}' is unavailable".format(name, text))

    def logError(self, message):
        msg = {}
        self.msgCnt += 1
        msg['#'] = self.msgCnt
        msg['level'] = "ERROR"
        msg['message'] = message
        self.msgLst.append(msg)
        self.logger.error(message)

######################### MAIN ##########################
if __name__ == "__main__":
    pass
