# -*- coding: utf-8 -*-
#########################################################
# SERVICE : mount.py                                    #
#           mount and database operations for xnas      #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import logging
from copy import deepcopy
from mounts.devices import devices
from mounts.fstab import fstab
from mounts.mountfs import mountfs
from mounts.zfs import zfs
from mounts.mountpoint import mountpoint
from common.stdin import stdin
from common.xnas_engine import groups
#########################################################

####################### GLOBALS #########################
FSTYPES = ["ext2", "ext3", "ext4", "ntfs", "ntfs-3g", "fat", "vfat", "btrfs", "jfs", "xfs", "iso9660", "udf"]
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : mount                                         #
#########################################################
class mount(devices, fstab, mountfs, zfs, mountpoint):
    def __init__(self, engine, human = False):
        self.engine = engine
        self.logger = logging.getLogger('xnas.xmount')
        devices.__init__(self, self.logger, human)
        fstab.__init__(self, self.logger)
        mountfs.__init__(self, self.logger)
        zfs.__init__(self, self.logger, False)
        mountpoint.__init__(self, self.logger)

    def __del__(self):
        mountpoint.__del__(self)
        zfs.__del__(self)
        mountfs.__del__(self)
        fstab.__del__(self)
        devices.__del__(self)

    def inDB(self):
        listentries = []
        # First for generic mounts
        entries = fstab.getEntries(self, FSTYPES)
        for entry in entries:
            listentry = {}
            #Shrink I
            if entry["uuid"]:
                listentry["uuid/ fsname/ label"] = entry["uuid"]
            elif entry["fsname"]:
                listentry["uuid/ fsname/ label"] = entry["fsname"]
            else:
                listentry["uuid/ fsname/ label"] = entry["label"]
            #copy
            for key, value in entry.items():
                if key == "options":
                    listentry[key] = ",".join(value)
                elif key != "fsname" and key != "uuid" and key != "label":
                    listentry[key] = value
            dbkey, dbval = self.engine.findInGroup(groups.MOUNTS, 'uuid', self.getUuid(entry))
            if dbkey:
                listentry['xmount'] = dbkey
            else:
                listentry['xmount'] = "-"
            listentries.append(listentry)
        # Then for ZFS mounts
        entries = zfs.getEntries(self)
        for entry in entries:
            listentry = {}
            listentry["uuid/ fsname/ label"] = entry["label"]
            #copy
            for key, value in entry.items():
                if key == "options":
                    listentry[key] = ",".join(value)
                elif key != "fsname" and key != "uuid" and key != "label":
                    listentry[key] = value
            dbkey, dbval = self.engine.findInGroup(groups.MOUNTS, 'uuid', entry["label"])
            if dbkey:
                listentry['xmount'] = dbkey
            else:
                listentry['xmount'] = "-"
            listentries.append(listentry)
        return listentries

    def getMounts(self):
        mymounts = []
        mounts = self.engine.checkGroup(groups.MOUNTS)
        if mounts:
            for key, mount in mounts.items():
                mymount = {}
                # Check but same for zfs and regular fs-es
                device = self.getDevices(mount['uuid'])
                if device:
                    mymount['xmount'] = key
                    fsnames = []
                    for mydevice in device:
                        fsnames.append(mydevice['fsname'])
                    mymount['device'] = fsnames
                    mymount['mountpoint'] = device[0]['mountpoint']
                    mymount['type'] = device[0]['type']
                    mymount['size'] = device[0]['size']
                    mymount['used'] = device[0]['used']
                    mymount['mounted'] = device[0]['mounted']
                    if mount['zfs']:
                        mymount['health'] = zfs.getHealth(self, mount['uuid'], device[0]['mounted'])
                    else:
                        mymount['health'] = fstab.getHealth(self, mount['uuid'], device[0]['fsname'], device[0]['label'], device[0]['mounted'])
                    mymount['referenced'] = self.isReferenced(key, True)
                    mymount['dynmount'] = mount['dyn']
                if mymount:
                    mymounts.append(mymount)

        return mymounts

    def getAvailable(self):
        blkdevices = self.getBlockList(FSTYPES)
        newdevices = []
        for blkdevice in blkdevices:
            if not fstab.findEntry(self, blkdevice):
                newdevices.append(blkdevice)
        # Exclude zfs devices from this list. if they exist, they are in the zpool list
        return newdevices

    def pop(self, interactive, popArgs):
        addedMounts = []
        # First for generic mounts
        entries = fstab.getEntries(self, FSTYPES)
        for entry in entries:
            uuid = self.getUuid(entry)
            if uuid: # Don't add if uuid cannot be found
                dbkey, dbval = self.engine.findInGroup(groups.MOUNTS, 'uuid', uuid)
                popArg = {}
                if not dbkey:
                    if popArgs:
                        for arg in popArgs:
                            if 'device' in arg:
                                if arg['device'] == self.getFsname(uuid):
                                    popArg = arg
                                    break
                    newMount = self.addToDB(entry, uuid, interactive, popArg)
                    if newMount:
                        addedMounts.append(newMount)
        # Then for ZFS mounts
        entries = zfs.getEntries(self)
        for entry in entries:
            pool = entry['label']
            if pool: # Don't add if pool cannot be found
                dbkey, dbval = self.engine.findInGroup(groups.MOUNTS, 'uuid', pool)
                popArg = {}
                if not dbkey:
                    if popArgs:
                        for arg in popArgs:
                            if arg['device'] == pool:
                                popArg = arg
                                break
                    newMount = self.addToDB(entry, "", interactive, popArg)
                    if newMount:
                        addedMounts.append(newMount)
        return addedMounts

    def getReferenced(self, name):
        # Mounts can only be referenced to shares, so check shares for references
        dbkeys = []
        refs = self.engine.findAllInGroup(groups.SHARES, 'xmount', name)
        for dbkey, dbval in refs.items():
            if 'remotemount' in dbval and 'enabled' in dbval:
                if not dbval['remotemount'] and dbval['enabled']:
                    dbkeys.append(dbkey)
        return dbkeys

    def isReferenced(self, name, silent = False):
        # Mounts can only be referenced to shares, so check shares for references
        ref = self.getReferenced(name)
        if ref and not silent:
            self.logger.warning("{} is referenced by {}".format(name, ref))
        return ref != []

    def mnt(self, name, dbItem = True, Zfs = False, mpoint = ""):
        retval = False
        isMounted = False
        uuid = name
        isZfs = Zfs
        if dbItem:
            db = self.engine.checkKey(groups.MOUNTS, name)
            if db:
                isZfs = db['zfs']
                uuid =  db['uuid']
                retval = True
        else:
            retval = True

        if retval:
            retval = False
            if isZfs:
                entry = zfs.getEntry(self, uuid)
            else:
                entry = fstab.getEntry(self, uuid)
            device = self.getDevices(uuid)
            if entry and device:
                isMounted = device[0]['mounted']
                if not isMounted:
                    if isZfs:
                        if zfs.available(self):
                            retval = zfs.mount(self, uuid)
                        else:
                            self.logger.error("{} is of type zfs, but zfs is not installed".format(name))
                    else:
                        if mpoint:
                            mp = mpoint
                        else:
                            mp = entry['mountpoint']
                        retval = mountfs.mount(self, mp)
                elif dbItem:
                    self.logger.warning("{} already mounted".format(name))

        if retval:
            self.logger.info("{} mounted".format(name))
        elif not isMounted:
            self.logger.warning("{} not mounted".format(name))
        else: # Already mounted
            retval = True
        return retval

    def umnt(self, name, dbItem = True, Zfs = False, mpoint = ""):
        retval = False
        isMounted = False
        uuid = name
        isZfs = Zfs
        if dbItem:
            db = self.engine.checkKey(groups.MOUNTS, name)
            if db:
                isZfs = db['zfs']
                uuid =  db['uuid']
                retval = True
        else:
            retval = True

        if retval:
            retval = False
            if isZfs:
                entry = zfs.getEntry(self, uuid)
                if not entry:
                    entry = {}
                    entry['mountpoint'] = mountpoint.getMountPoint(self, uuid, True)
            else:
                entry = fstab.getEntry(self, uuid)
                if not entry:
                    entry = {}
                    entry['mountpoint'] = mountpoint.getMountPoint(self, uuid)
            device = self.getDevices(uuid)
            if 'mountpoint' in entry and device:
                isMounted = device[0]['mounted']
                if isMounted:
                    if not self.isReferenced(name):
                        if isZfs:
                            if zfs.available(self):
                                retval = zfs.unmount(self, uuid)
                            else:
                                self.logger.error("{} is of type zfs, but zfs is not installed".format(name))
                        else:
                            if mpoint:
                                mp = mpoint
                            else:
                                mp = entry['mountpoint']
                            retval = mountfs.unmount(self, mp)
                elif dbItem:
                    self.logger.warning("{} is not mounted".format(name))

        if retval:
            self.logger.info("{} unmounted".format(name))
        elif isMounted:
            self.logger.warning("{} not unmounted".format(name))
        else:
            retval = True
        return retval

    def getMountpoint(self, name):
        retval = ""

        db = self.engine.checkKey(groups.MOUNTS, name)
        if db:
            if db['zfs']:
                entry = zfs.getEntry(self, db['uuid'])
            else:
                entry = fstab.getEntry(self, db['uuid'])
            if entry:
                retval = entry['mountpoint']
        return retval

    def clr(self, name):
        retval = False
        db = self.engine.checkKey(groups.MOUNTS, name)
        if db:
            if not self.isReferenced(name):
                retval = self.engine.removeFromGroup(groups.MOUNTS, name)
        if retval:
            self.logger.info("{} removed from database".format(name))
        else:
            self.logger.warning("{} removed from database".format(name))
        return retval

    def ena(self, name):
        retval = False
        db = self.engine.checkKey(groups.MOUNTS, name)
        if db:
            if db['zfs']:
                retval = zfs.ena(self, db['uuid'])
            else:
                retval = fstab.ena(self, db['uuid'])
        if retval:
            self.logger.info("{} enabled".format(name))
        else:
            self.logger.warning("{} not enabled".format(name))
        return retval

    def dis(self, name):
        retval = False
        db = self.engine.checkKey(groups.MOUNTS, name)
        if db:
            if db['zfs']:
                if not self.isReferenced(name):
                    retval = zfs.dis(self, db['uuid'])
            else:
                if not self.isReferenced(name):
                    retval = fstab.dis(self, db['uuid'])
        if retval:
            self.logger.info("{} disabled".format(name))
        else:
            self.logger.warning("{} not disabled".format(name))
        return retval

    def addFs(self, name):
        retval = True
        isZfs = False
        entry = {}
        entryNew = {}
        newEntry = False
        uuid = ""
        db = self.engine.checkKey(groups.MOUNTS, name)
        changed = False
        currentMountpoint = ""
        currentLabel = ""
        deleteCurrentMountpoint = False
        # Check existence of entry
        if db: # in db
            if self.isReferenced(name):
                self.logger.info("{} found in database, but is referenced. Remove reference first".format(name))
                retval = False
            else:
                self.logger.info("{} found in database, editing content".format(name))
                if db['zfs']:
                    isZfs = True
                    entry = zfs.getEntry(self, db['uuid'])
                else:
                    entry = fstab.getEntry(self, db['uuid'])
        else: # not in db, check uuid, name or label in pool
            # allow usage of name as label if no label set
            if 'label' in self.engine.settings:
                label = self.engine.settings['label']
            else:
                label = name
            if 'uuid' in self.engine.settings: # check in fstab
                entry = fstab.getEntry(self, uuid = self.engine.settings['uuid'])
                if entry:
                    self.logger.info("{} not in database, but uuid found, editing content".format(name))
            elif 'fsname' in self.engine.settings: # check in fstab
                entry, uuid = fstab.getEntry2(self, fsname = self.engine.settings['fsname'])
                if entry:
                    self.logger.info("{} not in database, but fsname found, editing content".format(name))
            elif label: # check in fstab
                entry, uuid = fstab.getEntry2(self, label = label)
                if entry:
                    self.logger.info("{} not in database, but label found, editing content".format(name))
                else: # Check in zfs pool
                    entry = zfs.getEntry(self, label)
                    if entry:
                        self.logger.info("{} not in database, but found in ZFS pool, editing content".format(name))
                        isZfs = True

            # check entry is somewhere else is DB or create new entry
            if entry:
                # Check DB
                if not uuid:
                    if isZfs:
                        uuid = entry['label']
                    else:
                        uuid = self.getUuid(entry)
                dbkey, dbval = self.engine.findInGroup(groups.MOUNTS, 'uuid', uuid)
                if dbkey:
                    self.logger.warning("{} found in database under different mount: {}".format(name, dbkey))
                    retval = False
                if retval:
                    newEntry = False
            else:
                if retval:
                    if "type" in self.engine.settings:
                        if self.engine.settings["type"].lower().find("zfs") >= 0:
                            isZfs = True
                    if isZfs:
                        self.logger.info("{} not found, creating new ZFS pool item not allowed".format(name))
                        self.logger.info("This must be done via ZFS: e.g. 'zpool create {}'".format(name))
                        retval = False
                    else:
                        self.logger.info("{} not found, creating new item".format(name))
                    newEntry = True

        if isZfs and not zfs.available(self):
            self.logger.error("{} is of type zfs, but zfs is not installed".format(name))
            self.logger.info("Please install zfs no your distro (if available) and try again")
            self.logger.info("Common package to install on most distros: '{}'".format(zfs.installName()))
            retval = False

        # Make Mountpoint
        if retval:
            MPvalid = True
            MPnew = ""
            if not newEntry:
                currentMountpoint = entry['mountpoint']

            if 'mountpoint' in self.engine.settings:
                MPnew = self.engine.settings['mountpoint']
                MPvalid = not mountpoint.exists(self, MPnew)
                if not MPvalid:
                    if mountpoint.mounted(self, MPnew):
                        # Check mountpoint is linked to current url
                        mp = ""
                        if isZfs:
                            if 'label' in self.engine.settings:
                                mp = mountpoint.getMountPoint(self, self.engine.settings['label'], True)
                        else:
                            tempUuid = self.deviceUuid(self.engine.settings)
                            if tempUuid:
                                mp = mountpoint.getMountPoint(self, tempUuid, False)
                            url = self.buildDbURL(self.engine.settings, typeObj)
                        MPvalid = mp == MPnew
                    else:
                        MPvalid = True
            elif newEntry: # New entry and no mountpoint
                MPValid = False

            if currentMountpoint and MPnew:
                if currentMountpoint != MPnew:
                    if MPvalid:
                        deleteCurrentMountpoint = True
                    else:
                        self.logger.info("New mountpoint invalid, keep current: {}".format(currentMountpoint))
                        MPnew = currentMountpoint
                        MPvalid = True
                else:
                    MPvalid = True # current mountpoint is unmounted later

            if not MPnew:
                MPnew = currentMountpoint
            if not MPnew: # no mountpoint at all
                MPvalid = False

            if not MPvalid:
                label = ""
                if 'label' in entry:
                    label = entry['label']
                MPnew = mountpoint.make(self, name, backupmountpoint = label)

            retval = MPnew != None
            self.engine.settings['mountpoint'] = MPnew

        # Create, check and update entry
        if retval:
            entryNew = deepcopy(entry)
            if isZfs:
                currentLabel = entry['label']
                changed = zfs.makeEntry(self, entryNew, self.engine.settings, name)
                retval = zfs.checkEntry(self, entryNew, newEntry, changed)
            else:
                changed = fstab.makeEntry(self, entryNew, self.engine.settings)
                retval = fstab.checkEntry(self, entryNew, newEntry, changed)

        # If changed, unmount and update
        if changed and retval:
            if isZfs:
                if currentLabel:
                    retval = self.umnt(currentLabel, dbItem = False, Zfs = isZfs, mpoint = "")
            else:
                if currentMountpoint:
                    retval = self.umnt(self.getUuid(entryNew), dbItem = False, Zfs = isZfs, mpoint = currentMountpoint)
            if not retval:
                self.logger.warning("Unable to unmount {}".format(name))
            else:
                if isZfs:
                    retval = zfs.updateEntry(self, entryNew, newEntry)
                else:
                    retval = fstab.updateEntry(self, entryNew, newEntry)

        # Mount if not noauto option
        if retval:
            if 'dyn' in self.engine.settings:
                dyn = self.engine.settings['dyn']
            else:
                dyn = False
            if deleteCurrentMountpoint:
                retval = mountpoint.delete(self, currentMountpoint)
                if retval:
                    self.logger.info("Removed old mountpoint: {}".format(currentMountpoint))
            if retval and not mountpoint.exists(self, entryNew['mountpoint']):
                retval = mountpoint.create(self, entryNew['mountpoint'])
                if retval:
                    self.logger.info("Created new mountpoint: {}".format(entryNew['mountpoint']))
            if retval:
                mode = self.setMode(self.engine.settings['uacc'], self.engine.settings['sacc'])
                if mode != self.getMode(entryNew['mountpoint']):
                    self.chMode(entryNew['mountpoint'], mode)
                    self.logger.info("Changed mountpoint mode: user {}, superuser {}".format(self.engine.settings['uacc'], self.engine.settings['sacc']))
            if retval:
                noauto = False
                if 'options' in entryNew:
                    noauto = 'noauto' in entryNew['options']
                    if not noauto:
                        if isZfs:
                            uuid = entryNew['label']
                        else:
                            uuid = self.getUuid(entryNew)
                        retval = self.mnt(uuid, dbItem = False, Zfs = isZfs, mpoint = entryNew['mountpoint'])
                        if dyn: # Do not blame mounting failed if dynmount device
                            retval = True

        # Add to DB or edit DB
        if retval:
            if db:
                # remove old item from db
                if not self.isReferenced(name):
                    retval = self.engine.removeFromGroup(groups.MOUNTS, name)
            #add new item to db
            dbMount = {}
            dbMountItems = {}
            if isZfs:
                dbMountItems['uuid'] = entryNew['label']
                dbMountItems['zfs'] = True

            else:
                dbMountItems['uuid'] = self.getUuid(entryNew)
                dbMountItems['zfs'] = False
            dbMountItems['dyn'] = dyn
            dbMount[name] = dbMountItems
            self.engine.addToGroup(groups.MOUNTS, dbMount)
            self.logger.info("{} added/ edited".format(name))
        else:
            self.logger.warning("{} not added/ edited".format(name))

        return retval

    def delFs(self, name):
        retval = False
        db = self.engine.checkKey(groups.MOUNTS, name)
        if db:
            if db['zfs']:
                if not self.isReferenced(name):
                    retval = self.umnt(name)
                    if retval:
                        retval = zfs.deletePool(self, db['uuid'])
                        self.logger.info("As {} is a ZFS pool, it will not be deleted, only removed from database".format(name))
            else:
                if not self.isReferenced(name):
                    retval = self.umnt(name)
                    if retval:
                        mpoint = fstab.getEntry(self, db['uuid'])['mountpoint']
                        retval = fstab.deleteEntry(self, db['uuid'])
                        if retval:
                            mountpoint.delete(self, mpoint)
                            self.logger.info("Removed mountpoint: {}".format(mpoint))
        if retval:
            self.logger.info("{} deleted".format(name))
            self.clr(name) # Remove from DB
        else:
            self.logger.warning("{} not deleted".format(name))
        return retval

    ################## INTERNAL FUNCTIONS ###################

    def addToDB(self, entry, uuid, interactive = False, popArg = {}):
        dbMount = {}
        newMount = {}
        addThis = True
        name = ""

        if popArg:
            if self.engine.checkKey(groups.MOUNTS, popArg['xmount']):
                self.logger.error("Name already exists, not added: {}".format(popArg['xmount']))
                addThis = False
            else:
                name = popArg['xmount']
        elif uuid:
            name = self.engine.generateUniqueName(groups.MOUNTS, entry['mountpoint'], entry['label'], entry['fsname'])
        else:
            name = self.engine.generateUniqueName(groups.MOUNTS, entry['mountpoint'], entry['label'])

        if interactive and not popArg:
            addThis = False
            cont = True
            stdinput = stdin("", exitevent = None, mutex = None, displaylater = False, background = False)

            print("New mount found:")
            if uuid:
                print("    device        : ", self.getFsname(uuid))
            else:
                print("    device        : ", entry['label'])
            print("    mountpoint    : ", entry['mountpoint'])
            print("    type          : ", entry['type'])
            print("    Generated name: ", name)

            while cont:
                res = ""
                while not res:
                    res = stdinput.inputchar("Add this mount (y/n/c)? ")
                    if res:
                        res = res.lower()[0]
                    if res == "y":
                        addThis = True
                        cont = False
                        print("New mount added: {}".format(name))
                    elif res == "n":
                        addThis = False
                        cont = False
                        print("New mount skipped: {}".format(name))
                        # text
                    elif res == "c":
                        newname = stdinput.input("Enter new name for this mount: ")
                        if ord(newname[0]) == 3: # ^C
                            self.engine.exitSignal()
                        else:
                            if not self.engine.valid(newname):
                                print("Name contains special characters, try again")
                            elif self.engine.checkKey(groups.MOUNTS, newname):
                                print("Name already exists, try again")
                            else:
                                name = newname
                                print("New mount added: {}".format(name))
                                addThis = True
                                cont = False
                    elif ord(res) == 3: # ^C
                        self.engine.exitSignal()
                    else:
                        print("Invalid response, y = yes, n = no, c = change name")
                        res = ""
            del stdinput

        if addThis:
            dbMountItems = {}
            if uuid:
                dbMountItems['uuid'] = uuid
                dbMountItems['zfs'] = False
            else:
                dbMountItems['uuid'] = entry['label']
                dbMountItems['zfs'] = True
                if not zfs.available(self):
                    self.logger.error("{} is of type zfs, but zfs is not installed".format(name))
                    self.logger.info("Please install zfs no your distro (if available) and try again")
                    addThis = False
            if addThis:
                if 'dyn' in self.engine.settings:
                    dbMountItems['dyn'] = self.engine.settings['dyn']
                else:
                    dbMountItems['dyn'] = False
                dbMount[name] = dbMountItems
                self.engine.addToGroup(groups.MOUNTS, dbMount)
                newMount['xmount'] = name
                if uuid:
                    newMount["device"] = self.getFsname(uuid)
                else:
                    newMount["device"] = entry['label']
                newMount['mountpoint'] = entry['mountpoint']
                newMount['type'] = entry['type']
                newMount['dynmount'] = dbMountItems['dyn']
                self.logger.info("New mount entry: {}".format(name))

        return newMount

    def deviceUuid(self, settings):
        devUuid = ""
        if 'uuid' in settings:
            devUuid = settings['uuid']
        else:
            dev = {}
            if 'fsname' in settings:
                dev = self.getDevices(settings['fsname'])
            elif 'label' in settings:
                dev = self.getDevices(settings['label'])
            if dev:
                devUuid = dev[0]['uuid']
        return devUuid

######################### MAIN ##########################
if __name__ == "__main__":
    pass
