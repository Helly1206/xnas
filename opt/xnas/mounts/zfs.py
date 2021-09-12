# -*- coding: utf-8 -*-
#########################################################
# SERVICE : zfs.py                                      #
#           zfs operations for xnas                     #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import logging
from common.shell import shell
#########################################################

####################### GLOBALS #########################
INSTALL = "zfsutils-linux"
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : zfs                                           #
#########################################################
class zfs(object):
    def __init__(self, logger, light = True):
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger('xnas.zfs')
        self.zentries = []
        self.hasZfs = False
        self.light = light
        try:
            if not self.light:
                self.tune("Whatever")
        except Exception as e:
            self.logger.error("devices must be loaded in parent")
            exit(1)
        try:
            self.hasZfs = self.checkZfsInstalled()
            if not self.light:
                self.getPools()
        except Exception as e:
            self.logger.error("Error reading ZFS information")
            self.logger.error(e)
            exit(1)

    def __del__(self):
        self.zentries = []

    def available(self):
        return self.hasZfs

    def installName(self):
        return INSTALL

    def getEntries(self):
        return self.zentries

    def addPool(self, pool):
        # never add pool in Zfs
        return True

    def deletePool(self, pool):
        # never delete pool in Zfs
        return True

    def getHealth(self, pool, isMounted = True):
        retval = "UNEXIST"
        if self.hasZfs:
            if self.poolExists(pool):
                cmd = "zpool list -H -o health " + pool
                outp = shell().command(cmd)
                if outp:
                    retval = outp.upper().strip()
        return retval

    def mount(self, pool):
        retval = True
        cmd = "zfs mount " + pool
        try:
            shell().command(cmd)
        except Exception as e:
            self.logger.error("Error mounting ZFS: {}".format(pool))
            self.logger.error(e)
            retval = False
        return retval

    def unmount(self, pool):
        retval = True
        cmd = "zfs unmount " + pool
        try:
            shell().command(cmd)
        except Exception as e:
            self.logger.error("Error unmounting ZFS: {}".format(pool))
            self.logger.error(e)
            retval = False
        return retval

    def getAvailable(self, pool):
        avl = False
        degr = False
        health = "UNEXIST"
        if self.hasZfs:
            cmd = "zpool list -H -o health " + pool
            outp = shell().command(cmd)
            if outp:
                health = outp.upper().strip()
            degr = health.upper() == "DEGRADED"
            avl = health.upper() == "ONLINE" or degr

        return avl, degr

    def isMounted(self, pool):
        retval = False
        cmd = "zfs get mounted -H -o value " + pool
        try:
            lines = shell().command(cmd)
            if lines:
                retval = lines.lower().strip() == "yes"
        except Exception as e:
            retval = False
        return retval

    def isEna(self, pool):
        retval = False
        cmd = "zfs get canmount -H -o value " + pool
        try:
            lines = shell().command(cmd)
            if lines:
                retval = lines.lower().strip() == "on"
        except Exception as e:
            retval = False
        return retval

    def ena(self, pool):
        retval = True
        cmd = "zfs set canmount=on " + pool
        try:
            shell().command(cmd)
        except Exception as e:
            self.logger.error("Error enabling ZFS: {}".format(pool))
            self.logger.error(e)
            retval = False
        return retval

    def dis(self, pool):
        retval = True
        cmd = "zfs set canmount=off " + pool
        try:
            shell().command(cmd)
        except Exception as e:
            self.logger.error("Error disabling ZFS: {}".format(pool))
            self.logger.error(e)
            retval = False
        return retval

    def makeEntry(self, entry, settings, name):
        changed = False

        if self.light:
            self.logger.error("No ZFS entry handling in light zfs allowed")
            return changed

        if "options" in entry:
            options = entry["options"]
        else:
            changed = True
            options = []

        if "fsname" in settings:
            self.logger.info("fsname is not used on ZFS")
        entry['fsname'] = ""
        if "uuid" in settings:
            self.logger.info("uuid is not used on ZFS")
        entry['uuid'] = ""
        if not "label" in entry:
            entry['label'] = name
            changed = True
        if "mountpoint" in settings:
            if "mountpoint" in entry:
                echanged =  entry['mountpoint'] != settings['mountpoint']
            else:
                echanged = True
            changed = changed or echanged
            entry['mountpoint'] = settings['mountpoint']
        elif not "mountpoint" in entry:
            changed = True
            entry['mountpoint'] = "/dev/null"
        if "type" in settings:
            if "type" in entry:
                echanged =  entry['type'] != self.tune(settings['type'])
            else:
                echanged = True
            changed = changed or echanged
            entry['type'] = self.tune(settings['type'])
        elif not "type" in entry:
            changed = True
            entry['type'] = "none"
        if "options" in settings:
            doptions = list(map(str.strip, settings['options'].split(","))).remove("");
            if not doptions:
                doptions = []
            soptions = self.getExtraOptions(doptions)
            eoptions = self.getExtraOptions(options)
            ochanged = False
            if len(soptions) != len(eoptions):
                ochanged = True
            else:
                for item in soptions:
                    if item not in eoptions:
                        ochanged = True
                        break
            if ochanged:
                options = soptions.extend(self.getExtraOptions(options, True))
                changed = True
        if "auto" in settings:
            if settings['auto']:
                if "noauto" in options:
                    changed = True
                    options.remove("noauto")
            elif not "noauto" in options:
                    changed = True
                    options.append("noauto")
        if "rw" in settings:
            if settings['rw']:
                if "ro" in options:
                    changed = True
                    options.remove("ro")
            elif not "ro" in options:
                changed = True
                options.append("ro")
        if "ssd" in settings:
            if settings['ssd']:
                if not "noatime" in options:
                    changed = True
                    options.append("noatime")
            # If no ssd, don't care about noatime or nodiratime settings
        entry['options'] = options
        if "freq" in settings:
            if settings['freq'] != 0:
                self.logger.info("freq is not used on ZFS")
        entry['dump'] = str(0)
        if "pass" in settings:
            if settings['pass'] != 0:
                self.logger.info("pass is not used on ZFS")
        entry['pass'] = str(0)

        return changed

    def checkEntry(self, entry, new = True, changed = True, checkMnt = False):
        retval = True

        if self.light:
            self.logger.error("No ZFS entry handling in light zfs allowed")
            return False

        if new:
            self.logger.info("Adding a new ZFS entry not supported")
        else:
            if entry["label"]:
                if not zfs.getEntry(self, entry["label"]):
                    self.logger.info("Pool {} does not exist, item not created".format(entry["label"]))
                    retval = False
            else:
                self.logger.info("Item doesn't contain a pool, item not created")
                retval = False

            if retval:
                device = self.findDevices(uuid = entry["uuid"], fsname = entry["fsname"], label = entry["label"])
                if device:
                    if self.tune(entry["type"], True) != str(device[0]["type"]):
                        self.logger.info("Incorrect type {}, {} expected, item not created".format(self.tune(entry["type"], True), device[0]["type"]))
                        retval = False
                    if checkMnt and changed and device[0]["mounted"]:
                        self.logger.info("Physical device is mounted as a different entry, item not created")
                        retval = False
                else:
                    self.logger.info("Physical device not found, item not created")
                    retval = False

        return retval

    def updateEntry(self, entry, new = True):
        retval = False

        if self.light:
            self.logger.error("No ZFS entry handling in light zfs allowed")
            return retval

        if new:
            self.logger.info("Adding a new ZFS entry not supported")
        else:
            curentry = zfs.getEntry(self, entry["label"])
            retval = True
            if entry['mountpoint'] != curentry['mountpoint']:
                self.setOpt(entry['label'], "mountpoint", entry['mountpoint'])
            if retval and (entry['options'] != curentry['options']):
                retval = self.setOpts(entry['label'], entry['options'], curentry['options'])
            # updating the entries themself is not required as they will be reloaded next time
        return retval

    def getEntry(self, pool):
        entry = {}
        for entr in self.zentries:
            if entr['label'] == pool:
                entry = entr
                break
        return entry

    ################## INTERNAL FUNCTIONS ###################

    def getExtraOptions(self, options, default = False):
        defOpt = ["auto","noauto","rw","ro","atime","noatime","diratime","nodiratime"]
        extraOpt = []
        for opt in options:
            if not default and not opt in defOpt:
                extraOpt.append(opt)
            elif default and opt in defOpt:
                extraOpt.append(opt)
        return extraOpt

    def checkZfsInstalled(self):
        return shell().commandExists("zfs") and shell().commandExists("zpool")

    def getPools(self):
        if self.hasZfs:
            # get pools
            # zpool list (-H to remove headers and tabs)
            # zpool list -o name
            pools = shell().command("zpool list -H -o name").splitlines()
            for pool in pools:
                entry = self.getEntryFromPool(pool)
                if entry:
                    self.zentries.append(entry)
        return

    def getEntryFromPool(self, pool):
        entry = {}

        if self.poolExists(pool):
            entry['uuid'] = ""
            entry['fsname'] = ""
            entry['label'] = pool
            cmd = "zfs get -H -o value mountpoint " + pool
            outp = shell().command(cmd)
            entry['mountpoint'] = outp.strip()
            entry['type'] = "zfs"
            entry['options'] = self.getOpts(pool)
            entry['dump'] = str(0)
            entry['pass'] = str(0)
        return entry

    def poolExists(self, pool):
        retval = False
        cmd = "zfs list -H -o name " + pool
        try:
            outp = shell().command(cmd)
            if outp:
                retval = True
        except:
            pass
        return retval

    def getOpts(self, pool):
        opts = []
        if self.getOpt(pool, "atime") != "on":
            opts.append('noatime')
        if self.getOpt(pool, "readonly") == "on":
            opts.append('ro')
        if self.getOpt(pool, "exec") != "on":
            opts.append('noexec')
        if self.getOpt(pool, "devices") != "on":
            opts.append('nodevices')
        if self.getOpt(pool, "setuid") != "on":
            opts.append('nosetuid')
        if self.getOpt(pool, "xattr") != "on":
            opts.append('noxattr')
        if self.getOpt(pool, "canmount") != "on":
            opts.append('noauto')
        return opts

    """
    PROPERTY                MOUNT OPTION
    devices                 devices/nodevices
    exec                    exec/noexec
    readonly                ro/rw
    setuid                  setuid/nosetuid
    xattr                   xattr/noxattr
    atime                   atime/noatime
    canmount                auto/noauto
    """
    def setOpts(self, pool, opts, curopts):
        if "nodevices" in opts and not "nodevices" in curopts:
            self.setOpt(pool, "devices", "off")
        elif not "nodevices" in opts and "nodevices" in curopts:
            self.setOpt(pool, "devices", "on")
        if "noexec" in opts and not "noexec" in curopts:
            self.setOpt(pool, "exec", "off")
        elif not "noexec" in opts and "noexec" in curopts:
            self.setOpt(pool, "exec", "on")
        if "ro" in opts and not "ro" in curopts:
            self.setOpt(pool, "readonly", "on")
        elif not "ro" in opts and "ro" in curopts:
            self.setOpt(pool, "readonly", "off")
        if "nosetuid" in opts and not "nosetuid" in curopts:
            self.setOpt(pool, "setuid", "off")
        elif not "nosetuid" in opts and "nosetuid" in curopts:
            self.setOpt(pool, "setuid", "on")
        if "noxattr" in opts and not "noxattr" in curopts:
            self.setOpt(pool, "xattr", "off")
        elif not "noxattr" in opts and "noxattr" in curopts:
            self.setOpt(pool, "xattr", "on")
        if "noatime" in opts and not "noatime" in curopts:
            self.setOpt(pool, "atime", "off")
        elif not "noatime" in opts and "noatime" in curopts:
            self.setOpt(pool, "atime", "on")
        if "noauto" in opts and not "noauto" in curopts:
            self.setOpt(pool, "canmount", "off")
        elif not "noauto" in opts and "noauto" in curopts:
            self.setOpt(pool, "canmount", "on")
        return True

    def getOpt(self, pool, opt):
        cmd = "zfs get -H -o value {} {}".format(opt, pool)
        return shell().command(cmd).strip()

    def setOpt(self, pool, opt, value):
        cmd = "zfs set {}={} {}".format(opt.lower(), value, pool)
        return shell().command(cmd).lower().strip()
"""
#zpool status
# zfs list
NAME     USED  AVAIL  REFER  MOUNTPOINT
intp1    631K  48.0T   219K  /intp1
intp2    631K  48.0T   219K  /intp2
intp3    631K  48.0T   219K  /intp3
jbodp4   631K  48.0T   219K  /jbodp4

# zpool list
NAME     SIZE  ALLOC   FREE  EXPANDSZ   FRAG    CAP  DEDUP  HEALTH  ALTROOT
intp1     65T  1.02M  65.0T         -     0%     0%  1.00x  ONLINE  -
intp2     65T  1020K  65.0T         -     0%     0%  1.00x  ONLINE  -
intp3     65T  1.02M  65.0T         -     0%     0%  1.00x  ONLINE  -
jbodp4    65T  1.02M  65.0T         -     0%     0%  1.00x  ONLINE  -

#### This is device, entry should contain the same fields as fstab entry
entry['label'] ==> name
entry['type'] ==> zfs (filesystem, snapshot ?????)
if self.human:
    entry['size'] = zfs USED as human (used + avail)
    entry['used'] = zfs USED as %
else:
    entry['size'] = zfs (used + avail)
    entry['used'] = zfs USED
entry['mountpoint'] = zfs mountpoint
entry['mounted'] = mountpoint and health == ONLINE (or DEGRADED)

Or USE df
zfs set mountpoint=/ora_vol1 szpool/vol1
bash-3.00# zfs list |grep szpool
szpool                              115K  56.9M    22K  /szpool
szpool/vol1                          21K  56.9M    21K  /ora_vol1
bash-3.00# df -h /ora_vol1
Filesystem             size   used  avail capacity  Mounted on
szpool/vol1             57M    21K    57M     1%    /ora_vol1

df --output=source,size,used,avail, target -h /mnt/OS

# human:
entry['size'] = kid['fssize'].replace(",",".")
entry['used'] = kid['fsuse%'].replace(",",".")

df --output=size,pcent,target -h /dev/sda5

entry['mountpoint'] = kid["mountpoint"]
entry['mounted'] = True if kid["mountpoint"] else False

entry['fsname'] = kid['name']
entry['type'] = self.tune(kid['fstype'], True)
entry['label'] = kid['label']
if kid['uuid']:

# not human:
df --output=size,used,target /dev/sda5
size, used *1024

or try lsblk as it gives all relevant output (even in JSON)
"""
######################### MAIN ##########################
if __name__ == "__main__":
    pass
