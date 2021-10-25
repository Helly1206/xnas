#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : xnas.py                                      #
#          Xnas main program                            #
#                                                       #
#          I. Helwegen 2020                             #
#########################################################

####################### IMPORTS #########################
import os
import sys
import logging
import json
from common.xnas_engine import xnas_engine, groups
from common.xnas_check import xnas_check
from common.xnas_fix import xnas_fix
from common.stdin import stdin
from common.systemdctl import systemdctl
from mounts.mount import mount
from remotes.remotemount import remotemount
from shares.share import share
from net.netshare import netshare
from mounts.fstab import fstab
#########################################################

####################### GLOBALS #########################
DAEMONXSERVICES = "xservices"
RUNFILE         = "/run/dynmount"
#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : xnas                                          #
#########################################################
class xnas(xnas_engine):
    def __init__(self):
        xnas_engine.__init__(self, "xnas")
        self.settings = {}

    def __del__(self):
        xnas_engine.__del__(self)

    def run(self, argv):
        result = True
        checkResults = []
        checkList = []
        self.handleArgs(argv)
        if self.hasSetting(self.settings,"command") and (self.settings["command"] == "fix" or self.settings["command"] == "chk"):
            xnasChk = xnas_check(self, noMsg = True, level = 0, json = self.settings['json'])
            checkResults = xnasChk.check()
            checkList = xnasChk.GetList()
            del xnasChk
        elif not self.hasSetting(self.settings,"command") or (self.hasSetting(self.settings,"command") and
                (self.settings["command"] == "shw" or self.settings["command"] == "rst" or self.settings["command"] == "srv")):
            xnasChk = xnas_check(self, json = self.settings['json'])
            checkResults = xnasChk.check()
            checkList = xnasChk.GetList()
            del xnasChk
        elif self.hasSetting(self.settings,"command") and (self.settings["command"] == "upd"):
            pass #don't check on update
        else:
            if xnas_check(self, level = 0).check():
                if self.settings["json"]:
                    self.printJsonResult(False)
                exit(1)
        if not self.hasSetting(self.settings,"command"):
            self.needSudo()
            links = share(self).linkAll()
            if self.settings["json"]:
                self.printJson(links)
            else:
                self.prettyPrintTable(links)
            xnas_check(self, level = 0, json = self.settings['json']).check()
        elif self.settings["command"] == "fix":
            self.needSudo()
            if not checkResults:
                if self.settings["json"]:
                    self.printJson(checkResults)
                else:
                    self.printMarked("No errors reported, nothing to be fixed")
            else:
                xnasFix = xnas_fix(self)
                xnasFix.fix(checkResults)
                if self.settings["json"]:
                    self.printJson(xnasFix.GetList())
                del xnasFix
        elif self.settings["command"] == "chk":
            if self.settings["json"]:
                self.printJson(checkList)
            elif checkResults:
                self.printMarked("Errors reported, please run 'xnas fix' to fix these errors")
            else:
                self.printMarked("No errors reported")
        elif self.settings["command"] == "shw":
            self.showAll()
        elif self.settings["command"] == "rst":
            self.needSudo()
            if not self.hasSetting(self.settings,"type"):
                self.parseError("Command [rst] requires a type argument")
            elif self.settings["type"] == "fstab":
                result = self.restoreFstab()
                if self.settings["json"]:
                    self.printJsonResult(result)
                else:
                    if result:
                        self.printMarked("Restored fstab")
                    else:
                        self.printMarked("Unable to restore fstab")
            else:
                self.parseError("Unknown type entered")
        elif self.settings["command"] == "srv":
            self.needSudo()
            result = self.setServicesOptions()
            if self.settings["json"] and not "show" in self.settings and not "settings" in self.settings:
                self.printJsonResult(result)
        elif self.settings["command"] == "upd":
            self.needSudo()
            result = self.updateDB()
            if self.settings["json"]:
                self.printJsonResult(result)
            else:
                if result:
                    self.printUnmarked("xnas settings updated")
                else:
                    self.printUnmarked("Unable update xnas settings")
        else:
            self.parseError("Unknown command argument")
            result = False
            if self.settings["json"]:
                self.printJsonResult(result)

        exit(0 if result else 1)

    def handleArgs(self, argv):
        xargs = {"fix": "tries to fix reported errors",
                 "chk": "only check for errors",
                 "shw": "shows all mounts, remotemounts, shares and netshares",
                 "rst": "restores backups [rst <type>] (type: fstab)",
                 "srv": "sets xservices options (restarts services)",
                 "upd": "update xnas settings to latest version",
                 "-": "checks all shared folders"}
        xopts = {"backup": "backup id to restore <string> (rst) (auto = empty)",
                 "show": "show current dynmounts and their status (srv)",
                 "interval": "database reloading interval (srv) (default = 60 [s])",
                 "enable": "enables or disables xservices (srv) (default = true)",
                 "zfshealth": "disables degraded zfs pools (srv) (default = false)",
                 "removable": "dynmount devices not in fstab (srv) (default = false)",
                 "afenable": "enables or disables autofix (srv) (default = true)",
                 "afretries": "number of retries during autofix (srv) (default = 3)",
                 "afinterval": "autofix retry interval (srv) (default = 60)",
                 "settings": "lists current settings (srv)"}
        extra = ('xservices run as a service for dynmount, autofix and also handles emptying\n'
        'the cifs recyclebin if required. See "interval", "enable", "removable",\n'
        '"afenable", "afretries" and "afinterval" options.\n'
        'xservices is always restarted after calling the "srv" command.\n'
        'Options may be entered as single JSON string using full name, e.g.\n'
        'xnas rst fstab \'{"backup": "2"}\'\n'
        'Mind the single quotes to bind the JSON string.')
        self.fillSettings(self.parseOpts(argv, xopts, xargs, extra), xopts)

    def fillSettings(self, optsnargs, xopts):
        if len(optsnargs[1]) > 0:
            self.settings["command"]=optsnargs[1][0]
            xopts[self.settings["command"]] = "NA" # Add command for optional JSON input
        if len(optsnargs[1]) > 1:
            if self.settings["command"] == "rst":
                self.settings["type"]=optsnargs[1][1]
            else:
                if self.isJSON(optsnargs[1][1]):
                    self.settings.update(self.parseJSON(optsnargs[1][1], xopts))
                else:
                    self.settings["type"]=optsnargs[1][1]
        if len(optsnargs[1]) > 2:
            self.settings.update(self.parseJSON(optsnargs[1][2], xopts))

        if len(optsnargs[1]) > 3:
            self.parseError("Too many arguments")

        self.settings.update(optsnargs[0])
        self.settingsBool(self.settings, 'json')
        self.settingsStr(self.settings, 'backup', default = "0")
        if self.settings['json']:
            self.StdoutLogging(False)
        else:
            self.StdoutLogging(True)

    def showAll(self):
        all = {}
        mounts = mount(self).getMounts()
        if self.settings["json"]:
            all['xmounts'] = mounts
        else:
            self.printMarked("xmounts:", True)
            self.prettyPrintTable(mounts)
        remotemounts = remotemount(self).getRemotemounts()
        if self.settings["json"]:
            all['xremotemounts'] = remotemounts
        else:
            self.printMarked("xremotemounts:", True)
            self.prettyPrintTable(remotemounts)
        shares = share(self).getShares()
        if self.settings["json"]:
            all['xshares'] = shares
        else:
            self.printMarked("xshares:", True)
            self.prettyPrintTable(shares)
        netshares = netshare(self).getNetshares()
        if self.settings["json"]:
            all['xnetshare'] = netshares
        else:
            self.printMarked("xnetshares:", True)
            self.prettyPrintTable(netshares)

        if self.settings["json"]:
            self.printJson(all)

    def restoreFstab(self):
        retval = 0
        backup = -1
        Fstab = fstab(logging.getLogger('xnas.xnas'), True)
        try:
            backup = int(self.settings["backup"])
        except:
            pass
        if backup == 0 and not self.settings["json"]: #interactive
            backups = Fstab.fstabBackups()
            if backups:
                stdinput = stdin("", exitevent = None, mutex = None, displaylater = False, background = False)
                print("Available backups:")
                self.prettyPrintTable(backups)
                backup = stdinput.inputchar("Enter backup to restore (1-9, 0 to cancel)? ")
                try:
                    backup = int(backup)
                except:
                    backup = 0
                if backup != 0:
                    res = stdinput.inputchar("Restore this file or show differences (y/n/d)? ")
                    if res.lower() == 'd':
                        diff = Fstab.diffFstab(backup)
                        if diff:
                            self.printList(diff)
                        backup = 0
                    elif res.lower() == 'n':
                        backup = 0
                del stdinput
            else:
                print("No backups available")

        retval = Fstab.restoreFstab(backup)
        del Fstab
        return retval

    def setServicesOptions(self):
        retval = True
        enaupd = False
        updated = False
        dorestart = not self.hasSetting(self.settings,"show") and not self.hasSetting(self.settings,"settings")

        settings = self.checkGroup(groups.SETTINGS)
        if not settings:
            settings = {}
            settings["srvenable"] = True
            enaupd = True
            settings["dyninterval"] = 60
            settings["dynzfshealth"] = False
            settings["dynremovable"] = False
            settings["autofixenable"] = True
            settings["autofixretries"] = 3
            settings["autofixinterval"] = 60
            updated = True
            self.addToGroup(groups.SETTINGS, settings)

        if self.hasSetting(self.settings,"enable"):
            if settings["srvenable"] != self.toBool(self.settings["enable"]):
                settings["srvenable"] = self.toBool(self.settings["enable"])
                enaupd = True

        if self.hasSetting(self.settings,"interval"):
            interval = self.toInt(self.settings["interval"])
            if not interval:
                interval = 60
            if settings["dyninterval"] != interval:
                settings["dyninterval"] = interval
                updated = True

        if self.hasSetting(self.settings,"zfshealth"):
            if settings["dynzfshealth"] != self.toBool(self.settings["zfshealth"]):
                settings["dynzfshealth"] = self.toBool(self.settings["zfshealth"])
                updated = True

        if self.hasSetting(self.settings,"removable"):
            if settings["dynremovable"] != self.toBool(self.settings["removable"]):
                settings["dynremovable"] = self.toBool(self.settings["removable"])
                updated = True

        if self.hasSetting(self.settings,"afenable"):
            if settings["autofixenable"] != self.toBool(self.settings["afenable"]):
                settings["autofixenable"] = self.toBool(self.settings["afenable"])
                updated = True

        if self.hasSetting(self.settings,"afretries"):
            retries = self.toInt(self.settings["afretries"])
            if not retries:
                retries = 3
            if settings["autofixretries"] != retries:
                settings["autofixretries"] = retries
                updated = True

        if self.hasSetting(self.settings,"afinterval"):
            afinterval = self.toInt(self.settings["afinterval"])
            if not afinterval:
                afinterval = 60
            if settings["autofixinterval"] != afinterval:
                settings["autofixinterval"] = afinterval
                updated = True

        if updated or enaupd:
            dorestart = True
            self.update()

        # enable or disable !!!
        if enaupd:
            retval = self.enable(settings["srvenable"])
            if not retval:
                self.logger.error("Error enabling or disabling xservices service")

        if settings["srvenable"] and dorestart and retval:
            retval = self.restart()
            if not retval:
                self.logger.error("Error restarting xservices service")

        if self.hasSetting(self.settings,"show"):
            self.showDynmounts()
        elif self.hasSetting(self.settings,"settings"):
            self.showSettings()

        return retval

    def enable(self, ena = True):
        retval = False
        if True: # assuming xservices is always available
            logger = logging.getLogger('xnas.xnas')
            ctl = systemdctl(logger)
            if ctl.available():
                if ena:
                    retval = ctl.enable(DAEMONXSERVICES)
                    if retval:
                        retval = ctl.start(DAEMONXSERVICES)
                else:
                    retval = ctl.stop(DAEMONXSERVICES)
                    if retval:
                        retval = ctl.disable(DAEMONXSERVICES)
            else:
                logger.error("Error enabling/ disabling xservices service")
                logger.info("Reason: systemd unavailable on your distro")
                logger.info("xnas cannot automatically enable/ disable the xservices service")
                logger.info("You can try it yourself using a command like 'service {} enable'".format(DAEMONXSERVICES))
            del ctl
        return retval

    def restart(self):
        retval = False
        if True: # assuming xservices is always available
            logger = logging.getLogger('xnas.xnas')
            ctl = systemdctl(logger)
            if ctl.available():
                retval = ctl.restart(DAEMONXSERVICES)
            else:
                logger.error("Error restarting xservices service")
                logger.info("Reason: systemd unavailable on your distro")
                logger.info("xnas cannot automatically restart the xservices service")
                logger.info("You can try it yourself using a command like 'service {} restart'".format(DAEMONXSERVICES))
            del ctl
        return retval

    def showDynmounts(self):
        mondata = []
        if os.path.exists(RUNFILE):
            with open(RUNFILE, 'rt') as monfile:
                mondata = json.loads(monfile.readlines()[0])
        if self.settings["json"]:
            self.printJson(mondata)
        else:
            self.prettyPrintTable(mondata)

    def showSettings(self):
        settings = self.checkGroup(groups.SETTINGS)
        if self.settings["json"]:
            self.printJson(settings)
        else:
            self.prettyPrintTable(self.settings2Table(settings))

    def updateDB(self):
        retval = True

        retval = self.updateDB1()

        return retval

    def updateDB1(self):
        retval = True

        mounts = self.checkGroup(groups.MOUNTS)
        if mounts:
            for name, mnt in mounts.items():
                if not "mountpoint" in mnt:
                    mnt["mountpoint"] = mount(self).getMountpoint(name)
                if "dyn" in mnt:
                    if mnt["dyn"] and not "method" in mnt:
                        mnt["method"] = "dynmount"
                    del mnt["dyn"]
                if not "method" in mnt:
                    entry = mount(self).getMntEntry(name)
                    if entry:
                        if not 'noauto' in entry['options']:
                            mnt["method"] = "auto"
                        else:
                            mnt["method"] = "disabled"
                    else:
                        mnt["method"] = "disabled"

        mounts = self.checkGroup(groups.REMOTEMOUNTS)
        if mounts:
            for name, mnt in mounts.items():
                if not "mountpoint" in mnt:
                    mnt["mountpoint"] = remotemount(self).getMountpoint(name)
                if "dyn" in mnt:
                    if mnt["dyn"] and not "method" in mnt:
                        mnt["method"] = "dynmount"
                    del mnt["dyn"]
                if not "method" in mnt:
                    entry = remotemount(self).getMntEntry(name)
                    if entry:
                        if not 'noauto' in entry['options']:
                            mnt["method"] = "auto"
                        else:
                            mnt["method"] = "disabled"
                    else:
                        mnt["method"] = "disabled"

        checkLinks = False
        shares = self.checkGroup(groups.SHARES)
        if shares:
            for name, shr in shares.items():
                if "uacc" in shr:
                    # use this as trigger to remove bindings
                    if share(self).legacyUnbind(name):
                        checkLinks = True
                        del shr["uacc"]
                if "sacc" in shr:
                    del shr["sacc"]

        if checkLinks:
            share(self).linkAll()

        settings = self.checkGroup(groups.SETTINGS)
        if settings:
            if not "autofixenable" in settings:
                settings["autofixenable"] = True
            if not "autofixretries" in settings:
                settings["autofixretries"] = 3
            if not "autofixinterval" in settings:
                settings["autofixinterval"] = 60

        self.update()

        return retval
#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    xnas().run(sys.argv)
