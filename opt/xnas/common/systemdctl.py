# -*- coding: utf-8 -*-
#########################################################
# SERVICE : systemdctl.py                               #
#           systemd systemctl wrapper to start/ stop    #
#           services                                    #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
from common.shell import shell
#########################################################

####################### GLOBALS #########################
SYSTEMCTL = "systemctl"
CTLSTART     = SYSTEMCTL + " start"
CTLSTOP      = SYSTEMCTL + " stop"
CTLRELOAD    = SYSTEMCTL + " reload"
CTLRESTART   = SYSTEMCTL + " restart"
CTLENABLE    = SYSTEMCTL + " enable"
CTLDISABLE   = SYSTEMCTL + " disable"
CTLSTATUS    = SYSTEMCTL + " status"
CTLISACTIVE  = SYSTEMCTL + " is-active"
CTLISENABLED = SYSTEMCTL + " is-enabled"
CTLDAEMONRLD = SYSTEMCTL + " daemon-reload"

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : systemdctl                                    #
#########################################################
class systemdctl(object):
    def __init__(self, logger):
        self.hasSystemd = False
        try:
            self.hasSystemd = self.checkInstalled()
        except Exception as e:
            logger.error("Error reading systemd information")
            logger.error(e)
            exit(1)

    def __del__(self):
        pass

    def available(self):
        return self.hasSystemd

    def start(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLSTART, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def stop(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLSTOP, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def reload(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLRELOAD, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def restart(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLRESTART, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def enable(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLENABLE, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def disable(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLDISABLE, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def status(self, service):
        retval = []
        if self.available():
            cmd = "{} {}".format(CTLSTATUS, service)
            try:
                retcode, stdout, stderr = shell().runCommand(cmd)
                retval = stdout.splitlines()
            except:
                pass
        return retval

    def isActive(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLISACTIVE, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def isEnabled(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLISENABLED, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def daemonReload(self):
        retval = False
        if self.available():
            cmd = "{}".format(CTLDAEMONRLD)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

################## INTERNAL FUNCTIONS ###################

    def checkInstalled(self):
        return shell().commandExists(SYSTEMCTL)

######################### MAIN ##########################
if __name__ == "__main__":
    pass
