# -*- coding: utf-8 -*-
#########################################################
# SERVICE : dynmountdata.py                             #
#           Handles dynmount data and mountpoints       #
#           and finds mountpoints if required           #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import logging
import time
import json
from common.xnas_engine import groups
from mounts.mountpoint import mountpoint
from mounts.devices import devices
from mounts.fstab import fstab
from shares.share import share
#########################################################

####################### GLOBALS #########################
MEDIAFOLDER      = "/media"
MAXENABLERETRIES = 10
ENABLEDELAY      = 0.5
RUNFILE          = "/run/dynmount"
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : dynmountdata                                  #
#########################################################
class dynmountdata(mountpoint, devices):
    dynmounts = []
    def __init__(self, logger):
        self.logger = logger
        mountpoint.__init__(self, self.logger)
        self.data = {}
        dynmountdata.monUpdate()

    def __del__(self):
        dynmountdata.monDel()
        mountpoint.__del__(self)

    def findMountpoint(self, fsname, remote = False):
        item = self.findInList(fsname)
        if item:
            mountpoint = item['mountpoint']
            uuid = item['uuid']
        else:
            mountpoint, uuid = self.findInFstab(fsname, remote)
            if mountpoint:
                self.addToList(fsname, uuid, mountpoint)
        return mountpoint, uuid

    def makeNewMountpoint(self, fsname): #doesn't work for remote!!!
        mountpoint = ""
        uuid = ""
        label = ""
        device = devices(self.logger, False).getDevices(fsname)
        if device:
            label = device[0]['label']
            uuid = device[0]['uuid'].upper()
            if label:
                mountpoint = self.make(label, MEDIAFOLDER, uuid)
            else:
                mountpoint = self.make(uuid, MEDIAFOLDER)
            if mountpoint:
                self.addToList(fsname, uuid, mountpoint)
        return mountpoint, uuid

    def addMountpoint(self, fsname):
        retval = False
        item = self.findInList(fsname)
        if item:
            retval = self.create(item['mountpoint'])
        return retval

    def delMountpoint(self, fsname):
        retval = False
        item = self.findInList(fsname)
        if item:
            retval = True
            self.delFromList(fsname)
            if item['mountpoint'].startswith(MEDIAFOLDER): # removable device, so not in fstab
                retval = self.delete(item['mountpoint'])
        return retval

    def enableReferences(self, engine, name, enable, verbose = True):
        refdata = []
        retry = 0
        refshares = engine.findAllInGroup(groups.SHARES, 'xmount', name)
        for key, refshare in refshares.items():
            refdatum = {}
            refdatum['key'] = key
            if enable:
                if not refshare['enabled']:
                    # it may be the case that the system is enabled before the mount gets online
                    # therefore give it some retries
                    retval = False
                    while not retval and retry < MAXENABLERETRIES:
                        retval = share(engine).ena(key, verbose=verbose)
                        if not retval:
                            time.sleep(ENABLEDELAY)
                        retry += 1
                    refdatum['enabled'] = retval
                    refdatum['changed'] = True
                    engine.update()
                else:
                    refdatum['enabled'] = True
                    refdatum['changed'] = False
            else: # disable
                if refshare['enabled']:
                    retval = False
                    while not retval and retry < MAXENABLERETRIES:
                        retval = share(engine).dis(key, force=True, verbose=verbose)
                        if not retval:
                            time.sleep(ENABLEDELAY)
                        retry += 1
                    refdatum['enabled'] = not retval
                    refdatum['changed'] = True
                    engine.update()
                else:
                    refdatum['enabled'] = False
                    refdatum['changed'] = False
            refdata.append(refdatum)
        return refdata

    def findInFstab(self, fsname, remote = False, fstabOnly = False):
        mountpoint = ""
        uuid = ""
        if remote: # find mountpoint in fstab based on url
            entry = fstab(self.logger, True).getEntry(fsname=fsname) # fname = url
            if entry:
                mountpoint = entry['mountpoint']
        else:
            device = devices(self.logger, False).findDevices(fsname=fsname)
            if device:
                if device[0]['mountpoint'] and not fstabOnly: # mountpoint is not "", so we don't have to lookup from fstab
                    mountpoint = device[0]['mountpoint']
                else: # find mountpoint in fstab also searching fsname and label
                    # mountpoint cannot be found for zfs on fstab, but is not relevant either
                    if device[0]['type'] != 'zfs':
                        entry = fstab(self.logger, True).getEntry(uuid=device[0]['uuid'], fsname=device[0]['fsname'], label=device[0]['label'])
                        if entry:
                            mountpoint = entry['mountpoint']
                if device[0]['type'] == 'zfs':
                    uuid = device[0]['label']
                else:
                    uuid = device[0]['uuid']
            else: #try fstab on fsname only, wild guess, no uuid
                entry = fstab(self.logger, True).getEntry(fsname=fsname)
                if entry:
                    mountpoint = entry['mountpoint']

        return mountpoint, uuid

    def getFsType(self, fsname):
        fstype = ""
        device = devices(self.logger, False).findDevices(fsname=fsname)
        if device:
            fstype = device[0]['type']
        return fstype

    @classmethod
    def addDynmount(cls, xmount, mounted = False, mountpoint = "", references = [], refsenabled = [], health = None, healthOnly = False):
        itemFound = False
        if not health:
            health = "ONLINE" if mounted else "OFFLINE"
        if not mounted:
            mountpoint = ""
        for item in cls.dynmounts:
            if item['xmount'] == xmount:
                itemFound = True
                item['health'] = health
                if not healthOnly:
                    item['mountpoint'] = mountpoint
                    item['references'] = references
                    item['enabled'] = refsenabled
                break
        if not itemFound:
            item = {}
            item['xmount'] = xmount
            item['mountpoint'] = mountpoint
            item['health'] = health
            item['references'] = references
            item['enabled'] = refsenabled
            cls.dynmounts.append(item)
        cls.monUpdate()

    @classmethod
    def delDynmount(cls, xmount):
        for item in cls.dynmounts:
            if item['xmount'] == xmount:
                cls.dynmounts.remove(item)
                break
        cls.monUpdate()


    ################## INTERNAL FUNCTIONS ###################

    def findInList(self, fsname):
        listitem = {}
        if self.data:
            for key, value in self.data.items():
                if key == fsname:
                    listitem = value
        return listitem

    def addToList(self, fsname, uuid, mountpoint):
        listitem = {}
        listitem['uuid'] = uuid
        listitem['mountpoint'] = mountpoint
        self.data[fsname] = listitem

    def delFromList(self, fsname):
        try:
            self.data.pop(fsname)
        except:
            pass

    @classmethod
    def monCheck(cls):
        return os.access(os.path.dirname(RUNFILE), os.W_OK)

    @classmethod
    def monUpdate(cls):
        if cls.monCheck():
            with open(RUNFILE, 'w') as monfile:
                monfile.write(json.dumps(cls.dynmounts))

    @classmethod
    def monDel(cls):
        if cls.monCheck() and os.path.exists(RUNFILE):
            os.remove(RUNFILE)
######################### MAIN ##########################
if __name__ == "__main__":
    pass

"""
Options:

list contains: uuid, (label, id,) mountpoint, or url, mountpoint
always get mp from list, if not, try fstab or get mountmount

Available:
Not mounted:
no mountpoint -> From fstab or make one
To get mountpoint from fstab --> get label and id from devices
mount
store mountpoint in dict uuid: mountpoint
If not in fstab, generate mountpoint and store in dict
Mounted:
store mountpoint in dict

Not available:
get mountpoint from dict (if not available, check fstab or generated mountpoints)
Mounted:
unmount
remove media mountpoint

mounted or not mounted:
remove mountpoint from dict
"""
