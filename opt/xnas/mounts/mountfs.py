# -*- coding: utf-8 -*-
#########################################################
# SERVICE : mountfs.py                                  #
#           mounts or unmounts devices from filesystem  #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
from common.shell import shell
#########################################################

####################### GLOBALS #########################
EXCLUDEMOUNTEDLIST = ["autofs"]
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : mountfs                                       #
#########################################################
class mountfs(object):
    def __init__(self, logger):
        self.logger = logger

    def __del__(self):
        pass

    def mount(self, mountpoint, timeout = 5):
        retval = True
        cmd = "mount " + mountpoint
        try:
            lines = shell().command(cmd, input = None, timeout = timeout)
        except Exception as e:
            self.logger.error("Error mounting system")
            self.logger.error(e)
            retval = False
        return retval

    def mountTemp(self, fsname, mountpoint, type = None, timeout = 5):
        retval = True
        mtype = ""
        if type:
            mtype = "-t {} ".format(type)
        cmd = "mount {}{} {}".format(mtype, fsname, mountpoint)
        try:
            lines = shell().command(cmd, input = None, timeout = timeout)
        except Exception as e:
            self.logger.error("Error mounting system")
            self.logger.error(e)
            retval = False
        return retval

    def unmount(self, mountpoint, txt = "unmounting", internal = False, force = False, timeout = 5):
        retval = True
        if internal:
            i = "-i "
        else:
            i = ""
        if force:
            i = i + "-l -f "
        cmd = "umount " + i + mountpoint
        try:
            lines = shell().command(cmd, input = None, timeout = timeout)
        except Exception as e:
            self.logger.error("Error {} system".format(txt))
            self.logger.error(e)
            retval = False
        return retval

    def bind(self, source, mountpoint, timeout = None):
        retval = True
        cmd = "mount --bind " + source + " " + mountpoint
        try:
            lines = shell().command(cmd, input = None, timeout = timeout)
        except Exception as e:
            self.logger.error("Error binding system")
            self.logger.error(e)
            retval = False
        return retval

    def unbind(self, mountpoint, force = False, timeout = None):
        return self.unmount(mountpoint, "unbinding", force = force, timeout = timeout)

    def isMounted(self, mountpoint):
        retval = False
        cmd = "cat /proc/mounts|grep " + mountpoint
        try:
            lines = shell().command(cmd).splitlines()
            for line in lines:
                l = line.split(" ")
                if not l[2].strip() in EXCLUDEMOUNTEDLIST:
                    retval = True
        except Exception as e:
            retval = False
        return retval

######################### MAIN ##########################
if __name__ == "__main__":
    pass
