# -*- coding: utf-8 -*-
#########################################################
# SERVICE : mountpoint.py                               #
#           Manages mountpoints                         #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import stat
import pwd
from common.shell import shell
#########################################################

####################### GLOBALS #########################
DEFAULTLOCATION = "/mnt"
MOUNTPOINTMODE = 0o777
SUWURMODE = 0o755
DISABLEDMODE = 0o000
EXECONLYMODE = 0o111
SUWRITEMODE = 0o200
SUREADMODE = 0o400
UWRITEMODE = 0o022
UREADMODE = 0o044
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : mountpoint                                    #
#########################################################
class mountpoint(object):
    def __init__(self, logger):
        self.logger = logger

    def __del__(self):
        pass

    def exists(self, mountpoint):
        return os.path.isdir(mountpoint)

    def mounted(self, mountpoint):
        return os.path.ismount(mountpoint)

    def create(self, mountpoint):
        retval = False
        if self.exists(mountpoint):
            self.logger.warning("Mountpoint not created, folder exists: {}".format(mountpoint))
        else:
            try:
                os.mkdir(mountpoint, MOUNTPOINTMODE)
                retval = True
            except OSError as e:
                self.logger.error("Mountpoint not created, error occured: {}".format(mountpoint))
                self.logger.error(e)
        return retval

    def delete(self, mountpoint):
        retval = False
        if self.exists(mountpoint):
            if self.mounted(mountpoint):
                self.logger.warning("Mountpoint not removed, still mounted: {}".format(mountpoint))
            else:
                try:
                    os.rmdir(mountpoint)
                    retval = True
                except OSError as e:
                    self.logger.error("Mountpoint not removed, error occured: {}".format(mountpoint))
                    self.logger.error(e)
        else:
            self.logger.warning("Mountpoint not removed, doesn't exist: {}".format(mountpoint))
        return retval

    def make(self, mountpoint, location = DEFAULTLOCATION, backupmountpoint = ""):
        madeMountpoint = ""
        IsUnique = False
        usedMountpoint = mountpoint
        usedBackupMountpoint = backupmountpoint
        cnt = 0

        while not IsUnique:
            madeMountpoint = os.path.join(location, usedMountpoint)
            IsUnique = not self.exists(madeMountpoint)

            if not IsUnique:
                if cnt == 0 and usedBackupMountpoint:
                    usedMountpoint = usedBackupMountpoint
                    usedBackupMountpoint = ""
                else:
                    cnt += 1
                    usedMountpoint = mountpoint + str(cnt)
        return madeMountpoint

    def setMode(self, uacc, sacc):
        mode = EXECONLYMODE

        if 'r' in sacc.lower():
            mode = mode | SUREADMODE
        if 'w' in sacc.lower():
            mode = mode | SUWRITEMODE

        if 'r' in uacc.lower():
            mode = mode | UREADMODE
        if 'w' in uacc.lower():
            mode = mode | UWRITEMODE

        return mode

    def chMode(self, mountpoint, mode):
        os.chown(mountpoint, pwd.getpwnam('root').pw_uid, pwd.getpwnam('root').pw_gid) # set user:group as root:root
        os.chmod(mountpoint, mode)

    def getMode(self, mountpoint):
        mode = DISABLEDMODE
        if mountpoint:
            try:
                mode = os.stat(mountpoint).st_mode & MOUNTPOINTMODE
            except:
                pass
        return mode

    def getUacc(self, mode):
        retval = ""
        if mode & UREADMODE:
            retval += "r"
        if mode & UWRITEMODE:
            retval += "w"

        return retval

    def getSacc(self, mode):
        retval = ""
        if mode & SUREADMODE:
            retval += "r"
        if mode & SUWRITEMODE:
            retval += "w"

        return retval

    def modeDisabled(self):
        return DISABLEDMODE

    def strMode(self, mode, leading = True):
        if leading:
            lz = "0"
        else:
            lz = ""
        smode = "{0:03o}".format(mode)

        return "{}{}".format(lz, smode)

    def umask(self, mode):
        return ~mode & 0o0777

    def createDir(self, dir, mode = SUWURMODE):
        retval = False
        if not self.exists(dir):
            try:
                os.mkdir(dir, mode)
                os.chown(dir, pwd.getpwnam('root').pw_uid, pwd.getpwnam('root').pw_gid) # set user:group as root:root
                self.logger.info("Folder created: {}".format(dir))
                retval = True
            except OSError as e:
                self.logger.error("Folder not created, error occured: {}".format(dir))
                self.logger.error(e)
        else:
            retval = True
        return retval

    def getMountPoint(self, uuid, byName = False):
        mpoint = ""
        cmd = ""
        if byName: # e.g. for ZFS
            cmd = "findmnt -rn -S {} -o TARGET".format(uuid)
        else:
            cmd = "findmnt -rn -S UUID={} -o TARGET".format(uuid)
        try:
            lines = shell().command(cmd).splitlines()
            mpoint = lines[0] # assume first mountpoint is of importance
        except:
            pass

        return mpoint

######################### MAIN ##########################
if __name__ == "__main__":
    pass
