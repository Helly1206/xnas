# -*- coding: utf-8 -*-
#########################################################
# SERVICE : dynmount.py                                 #
#           Handles dynamic mounts for standard mounts  #
#           Part of xservices                           #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import logging
from common.xnas_engine import groups
from mounts.mountfs import mountfs
from common.xnas_wd import device_wd, zfs_wd
from common.dynmountdata import dynmountdata
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : dynmount                                      #
#########################################################
class dynmount(mountfs, dynmountdata):
    def __init__(self, engine, verbose = False, zfshealth = False, removable = False):
        self.engine    = engine
        self.verbose   = verbose
        self.zfshealth = zfshealth
        self.removable = removable
        self.logger    = logging.getLogger('xnas.dynmount')
        self.device_wd = device_wd(self.onAdded, self.onDeleted)
        self.zfs_wd = zfs_wd(self.getZfsList(), self.zfshealth, self.onZfsAdded, self.onZfsDeleted)
        mountfs.__init__(self, self.logger)
        dynmountdata.__init__(self, self.logger)
        self.device_wd.start()
        self.zfs_wd.start()

    def __del__(self):
        dynmountdata.__del__(self)
        mountfs.__del__(self)

    def terminate(self):
        if self.device_wd:
            self.device_wd.stop()
            del self.device_wd
        if self.zfs_wd:
            self.zfs_wd.stop()
            del self.zfs_wd

    def update(self, zfshealth = False, removable = False):
        self.zfshealth = zfshealth
        self.removable = removable

    def updateZfsList(self):
        self.zfs_wd.updateList(self.getZfsList(), self.zfshealth)

    ####################### CALLBACKS #######################

    def onAdded(self, fsname):
        self.engine.mutex.acquire()
        #available
        mountpoint, uuid = self.findMountpoint(fsname)
        xmount = None
        zfs = False
        if uuid:
            xmount, zfs = self.findMount(uuid)
        if xmount:
            self.logger.info("{} mount device available".format(xmount))
            mounted = False
            if zfs:
                self.logger.info("{} device is an zfs device, not mounting".format(xmount))
            elif mountpoint:
                refs = []
                refsena = []
                if self.mounted(mountpoint): #mountfs.isMounted(self, mountpoint)
                    mounted = True
                    self.logger.info("{} already mounted".format(xmount))
                else:
                    mounted = mountfs.mount(self, mountpoint)
                    if mounted: # check reference
                        self.logger.info("{} mounted".format(xmount))
                    else:
                        self.logger.error("{} mounting failed".format(xmount))
                if mounted: # check reference
                    refdata = self.enableReferences(self.engine, xmount, True, self.verbose)
                    if refdata:
                        for refdatum in refdata:
                            refs.append(refdatum['key'])
                            refsena.append(refdatum['enabled'])
                            if refdatum['enabled'] and refdatum['changed']:
                                self.logger.info("{} reference found and enabled: {}".format(xmount, refdatum['key']))
                            elif refdatum['enabled']:
                                self.logger.info("{} reference found, already enabled: {}".format(xmount, refdatum['key']))
                            else:
                                self.logger.info("{} reference found, enabling failed: {}".format(xmount, refdatum['key']))
                    elif self.verbose:
                        self.logger.info("{} no reference found".format(xmount))
                else:
                    self.logger.warning("{} mount device available but no available mountpoint found, not mounting".format(xmount))
                dynmountdata.addDynmount(xmount, mounted, mountpoint, refs, refsena)
        else:
            if self.removable:
                mountpoint, uuid = self.findInFstab(fsname, fstabOnly = True)
                if not mountpoint: # if in fstab, don't dyn mount
                    type = self.getFsType(fsname)
                    if type:
                        if type == "zfs":
                            if self.verbose:
                                self.logger.info("removable mount device of type zfs, not mounting: {}".format(fsname))
                        else:
                            mounted = False
                            mountpoint, uuid = self.makeNewMountpoint(fsname)
                            if mountpoint:
                                retval = self.addMountpoint(fsname)
                                if retval:
                                    mounted = mountfs.mountTemp(self, fsname, mountpoint, type)
                                if mounted: # check reference
                                    self.logger.info("removable mount device mounted: {}, type {} on {}".format(fsname, type, mountpoint))
                                else:
                                    self.logger.error("removable mount device mounting failed: {}".format(fsname))
                            else:
                                self.logger.error("removable mount device mounting failed: {}".format(fsname))
                            dynmountdata.addDynmount("removable:{}".format(fsname), mounted, mountpoint)
                    elif self.verbose:
                        self.logger.info("removable mount device available but no type detected, not mounting: {}".format(fsname))
                elif self.verbose:
                    self.logger.info("removable mount device available but found in fstab, not mounting: {}".format(fsname))
            elif self.verbose:
                self.logger.info("mount device available but not found in database, not mounting: {}".format(fsname))
        self.engine.mutex.release()

    def onDeleted(self, fsname):
        self.engine.mutex.acquire()
        #not available
        mountpoint, uuid = self.findMountpoint(fsname)
        xmount = None
        zfs = False
        if uuid:
            xmount, zfs = self.findMount(uuid)
        if xmount:
            self.logger.info("{} mount device unavailable".format(xmount))
            mounted = True
            if zfs:
                self.logger.info("{} device is an zfs device, not unmounting".format(xmount))
            elif mountpoint:
                refs = []
                refsena = []
                if not self.mounted(mountpoint):
                    mounted = False
                    self.logger.info("{} already unmounted".format(xmount))
                else:
                    refdata = self.enableReferences(self.engine, xmount, False, self.verbose)
                    if refdata:
                        for refdatum in refdata:
                            refs.append(refdatum['key'])
                            refsena.append(refdatum['enabled'])
                            if not refdatum['enabled'] and refdatum['changed']:
                                self.logger.info("{} reference found and disabled: {}".format(xmount, refdatum['key']))
                            elif not refdatum['enabled']:
                                self.logger.info("{} reference found, already disabled: {}".format(xmount, refdatum['key']))
                            else:
                                self.logger.info("{} reference found, disabling failed: {}".format(xmount, refdatum['key']))
                    elif self.verbose:
                        self.logger.info("{} no reference found".format(xmount))
                    mounted = not mountfs.unmount(self, mountpoint)
                    if not mounted: # check reference
                        self.logger.info("{} unmounted".format(xmount))
                    else:
                        self.logger.error("{} unmounting failed".format(xmount))
                if not mounted: # check reference
                    refdata = self.enableReferences(self.engine, xmount, False, self.verbose)
                    if self.verbose and not refdata:
                        self.logger.info("{} no reference found".format(xmount))
                    self.delMountpoint(fsname)
                else:
                    self.logger.warning("{} mount device unavailable but no available mountpoint found, not unmounting".format(xmount))
                dynmountdata.addDynmount(xmount, mounted, mountpoint, refs, refsena)
        else:
            if self.removable:
                mountpoint, uuid = self.findMountpoint(fsname)
                if mountpoint:
                    retval = mountfs.unmount(self, mountpoint)
                    if retval: # check reference
                        self.logger.info("removable mount device unmounted: {}, on {}".format(fsname, mountpoint))
                        retval = self.delMountpoint(fsname)
                        if not retval:
                            self.logger.error("Error removing mountpoint: {}".format(mountpoint))
                    else:
                        self.logger.error("removable mount device unmounting failed: {}".format(fsname))
                    dynmountdata.delDynmount("removable:{}".format(fsname))
                elif self.verbose:
                    self.logger.info("removable mount device available but no mountpoint found, not unmounting: {}".format(fsname))
            elif self.verbose:
                self.logger.info("mount device unavailable but not found in database, not unmounting: {}".format(fsname))
        self.engine.mutex.release()

    def onZfsAdded(self, poolHealth):
        self.engine.mutex.acquire()
        #available
        if poolHealth:
            uuid = list(poolHealth.keys())[0]
            xmount, zfs = self.findMount(uuid)
            if xmount:
                if zfs:
                    if poolHealth[uuid] != "UNMOUNTED":
                        self.logger.info("{}: ZFS mount device is {}, enabling".format(xmount, poolHealth[uuid]))
                        refs = []
                        refsena = []
                        refdata = self.enableReferences(self.engine, xmount, True, self.verbose)
                        if refdata:
                            for refdatum in refdata:
                                refs.append(refdatum['key'])
                                refsena.append(refdatum['enabled'])
                                if refdatum['enabled'] and refdatum['changed']:
                                    self.logger.info("{} reference found and enabled: {}".format(xmount, refdatum['key']))
                                elif refdatum['enabled']:
                                    self.logger.info("{} reference found, already enabled: {}".format(xmount, refdatum['key']))
                                else:
                                    self.logger.info("{} reference found, enabling failed: {}".format(xmount, refdatum['key']))
                        elif self.verbose:
                            self.logger.info("{} no reference found".format(xmount))
                        dynmountdata.addDynmount(xmount, True, self.getMountPoint(uuid, True), refs, refsena, poolHealth[uuid])
                    else:
                        if self.verbose:
                            self.logger.info("{}: ZFS mount device is not mounted, not enabling".format(xmount))
                        dynmountdata.addDynmount(xmount)
                else:
                    if self.verbose:
                        self.logger.warning("{}: ZFS mount device is not a ZFS device".format(xmount))
                    dynmountdata.addDynmount(xmount)
            elif self.verbose:
                self.logger.info("ZFS mount device available but not found in database, not enabling: {}".format(uuid))
        elif self.verbose:
            self.logger.warning("ZFS mount device added without data")
        self.engine.mutex.release()

    def onZfsDeleted(self, poolHealth):
        self.engine.mutex.acquire()
        #not available
        if poolHealth:
            uuid = list(poolHealth.keys())[0]
            xmount, zfs = self.findMount(uuid)
            if xmount:
                if zfs:
                    if True:
                        self.logger.info("{}: ZFS mount device is {}, disabling".format(xmount, poolHealth[uuid]))
                        # I don't care whether the device is mounted for disabling
                        refs = []
                        refsena = []
                        refdata = self.enableReferences(self.engine, xmount, False, self.verbose)
                        if refdata:
                            for refdatum in refdata:
                                refs.append(refdatum['key'])
                                refsena.append(refdatum['enabled'])
                                if not refdatum['enabled'] and refdatum['changed']:
                                    self.logger.info("{} reference found and disabled: {}".format(xmount, refdatum['key']))
                                elif not refdatum['enabled']:
                                    self.logger.info("{} reference found, already disabled: {}".format(xmount, refdatum['key']))
                                else:
                                    self.logger.info("{} reference found, disabling failed: {}".format(xmount, refdatum['key']))
                        elif self.verbose:
                            self.logger.info("{} no reference found".format(xmount))
                        dynmountdata.addDynmount(xmount, False, "", refs, refsena, poolHealth[uuid])
                else:
                    if self.verbose:
                        self.logger.warning("{}: ZFS mount device is not a ZFS device".format(xmount))
                    dynmountdata.addDynmount(xmount)
            elif self.verbose:
                self.logger.info("ZFS mount device unavailable but not found in database, not disabling: {}".format(uuid))
        elif self.verbose:
            self.logger.warning("ZFS mount device added without data")
        self.engine.mutex.release()

    ################## INTERNAL FUNCTIONS ###################

    def getZfsList(self):
        zfsList = []

        mounts = self.engine.checkGroup(groups.MOUNTS)
        if mounts:
            for key, mount in mounts.items():
                if mount['dyn'] and mount['zfs']:
                    zfsList.append(mount['uuid'])
        return zfsList

    def findMount(self, uuid):
        xmount = ""
        zfs = False
        mounts = self.engine.checkGroup(groups.MOUNTS)
        if mounts:
            for key, mount in mounts.items():
                if mount['dyn']:
                    if mount['uuid'] == uuid:
                        xmount = key
                        zfs = mount['zfs']
                        break
        return xmount, zfs

######################### MAIN ##########################
if __name__ == "__main__":
    pass
