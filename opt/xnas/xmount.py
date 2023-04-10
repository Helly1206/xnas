#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : xmount.py                                    #
#          Xnas manage mounts                           #
#                                                       #
#          I. Helwegen 2020                             #
#########################################################

####################### IMPORTS #########################
import sys
from common.xnas_engine import xnas_engine
from common.xnas_check import xnas_check
from mounts.mount import mount
#########################################################

####################### GLOBALS #########################
NAMELIST = ["add", "del", "mnt", "umnt", "clr", "ena", "dis", "shw", "pth"]
NAMECHECK = ["del", "clr", "mnt", "dis", "shw"]
#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : xmount                                        #
#########################################################
class xmount(xnas_engine):
    def __init__(self):
        xnas_engine.__init__(self, "xmount")
        self.settings = {}

    def __del__(self):
        xnas_engine.__del__(self)

    def run(self, argv):
        result = True
        self.handleArgs(argv)
        Mount = mount(self, self.settings['human'])
        xcheck = xnas_check(self, Mount = Mount, json = self.settings['json'])
        if xcheck.ErrorExit(xcheck.check(), self.settings, NAMECHECK):
            if self.settings["json"]:
                self.printJsonResult(False)
            exit(1)
        del xcheck
        if not self.hasSetting(self.settings,"command"):
            mounts = Mount.getMounts()
            if self.settings["json"]:
                self.printJson(mounts)
            else:
                self.prettyPrintTable(mounts)
        elif self.settings["command"] == "add":
            self.needSudo()
            result = Mount.addFs(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated with new mount entries")
            if self.settings["json"]:
                self.printJsonResult(result)
            # zfs do not create or destroy, use ZFS for that!
        elif self.settings["command"] == "del":
            self.needSudo()
            result = Mount.delFs(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated")
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "pop":
            self.needSudo()
            doUpdate = True
            if 'pop' in self.settings:
                if not self.settings['pop']:
                    doUpdate = False
            else:
                self.settings['pop'] = []
            addedMounts = Mount.pop(self.settings['interactive'], self.settings['pop'])
            if addedMounts:
                if doUpdate:
                    self.update()
                    self.logger.info("Database updated with new mount entries")
            if self.settings["json"]:
                self.printJson(addedMounts)
            else:
                self.prettyPrintTable(addedMounts)
        elif self.settings["command"] == "mnt":
            self.needSudo()
            result = Mount.mnt(self.settings["name"])
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "umnt":
            self.needSudo()
            result = Mount.umnt(self.settings["name"])
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "clr":
            self.needSudo()
            result = Mount.clr(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated")
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "ena":
            self.needSudo()
            #result = Mount.ena(self.settings["name"])
            self.parseError("Command obsolete, use --method option instead")
            result = False
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "dis":
            self.needSudo()
            #result = Mount.dis(self.settings["name"])
            self.parseError("Command obsolete, use --method option instead")
            result = False
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "shw":
            mountData = Mount.shw(self.settings["name"])
            if self.settings["json"]:
                self.printJson(mountData)
            else:
                self.prettyPrintTable(self.settings2Table(mountData))
        elif self.settings["command"] == "pth":
            pth = Mount.getDevicePath(self.settings["name"])
            if self.settings["json"]:
                self.printJson(pth)
            else:
                self.printUnmarked(pth)
        elif self.settings["command"] == "lst":
            entries = Mount.inDB()
            if self.settings["json"]:
                self.printJson(entries)
            else:
                self.prettyPrintTable(entries)
        elif self.settings["command"] == "avl":
            newdevices = Mount.getAvailable()
            if self.settings["json"]:
                self.printJson(newdevices)
            else:
                self.prettyPrintTable(newdevices)
        elif self.settings["command"] == "blk":
            blkdevices = Mount.getBlock()
            if self.settings["json"]:
                self.printJson(blkdevices)
            else:
                self.prettyPrintTable(blkdevices)
        else:
            self.parseError("Unknown command argument")
            result = False
            if self.settings["json"]:
                self.printJsonResult(result)
        exit(0 if result else 1)

    def nameRequired(self):
        if self.hasSetting(self.settings,"command"):
            if self.settings["command"] in NAMELIST and not "name" in self.settings:
                self.parseError("The option {} requires a <name> as argument".format(self.settings["command"]))

    def handleArgs(self, argv):
        xargs = {"add": "adds or edits a mount [add <name>]",
                 "del": "deletes a mount [del <name>]",
                 "pop": "populates from fstab [pop]",
                 "mnt": "mounts a mount [mnt <name>]",
                 "umnt": "unmounts a mount if not referenced [umnt <name>]",
                 "clr": "removes a mount, but leaves fstab [clr <name>]",
                 "shw": "shows current mount settings [shw <name>]",
                 "pth": "gets real device path of an fsname [pth <name>]",
                 "lst": "lists xmount compatible fstab entries [lst]",
                 "avl": "show available compatible devices not in fstab [avl]",
                 "blk": "show all compatible block devices [blk]",
                 "-": "show mounts and their status"}
        xopts = {"interactive": "ask before adding or changing mounts",
                 "human": "show sizes in human readable format",
                 "fsname": "filesystem <string> (add)",
                 "uuid": "uuid <string> (add)",
                 "label": "label <string> (also for zfs pool) (add)",
                 "mountpoint": "mountpoint <string> (add)",
                 "type": "type <string> (filesystem) (add)",
                 "options": "extra options, besides default <string> (add)",
                 "rw": "mount rw <boolean> (add)",
                 "ssd": "disk type is ssd <boolean> (add)",
                 "freq": "dump value <value> (add)",
                 "pass": "mount order <value> (add)",
                 "uacc": "users access level (,r,w) (default = rw) (add)",
                 "sacc": "superuser access level (,r,w) (default = rw) (add)",
                 "method": "mount method <string> (see below) (add)",
                 "idletimeout": "unmount when idle timeout <int> (default = 0) (add)",
                 "timeout": "mounting timeout <int> (default = 0) (add)"}
        extra = ('Mount methods:\n'
        'disabled: do not mount\n'
        'startup : mount from fstab during startup (default)\n'
        'auto    : auto mount from fstab when accessed\n'
        'dynmount: dynamically mount when available\n'
        'Options may be entered as single JSON string using full name, e.g.\n'
        'xmount add test \'{"fsname": "/dev/sda1", "mountpoint": "/mnt/test", \n'
        '                   "type": "ext4"}\'\n'
        'Mind the single quotes to bind the JSON string.')
        self.fillSettings(self.parseOpts(argv, xopts, xargs, extra), xopts)

    def fillSettings(self, optsnargs, xopts):
        if len(optsnargs[1]) > 0:
            self.settings["command"]=optsnargs[1][0]
            xopts[self.settings["command"]] = "NA" # Add command for optional JSON input
        if len(optsnargs[1]) > 1:
            if self.settings["command"] in NAMELIST:
                self.settings["name"]=optsnargs[1][1]
            else:
                if self.isJSON(optsnargs[1][1]):
                    self.settings.update(self.parseJSON(optsnargs[1][1], xopts))
                else:
                    self.settings["name"]=optsnargs[1][1]
        if len(optsnargs[1]) > 2:
            self.settings.update(self.parseJSON(optsnargs[1][2], xopts))

        if len(optsnargs[1]) > 3:
            self.parseError("Too many arguments")

        self.settings.update(optsnargs[0])
        self.settingsBool(self.settings, 'json')
        self.settingsBool(self.settings, 'interactive')
        self.settingsBool(self.settings, 'human')
        self.settingsBool(self.settings, 'rw', False)
        self.settingsBool(self.settings, 'ssd', False)
        self.settingsInt(self.settings, 'freq', False)
        self.settingsInt(self.settings, 'pass', False)
        self.settingsStr(self.settings, 'uacc', False)
        self.settingsStr(self.settings, 'sacc', False)

        self.nameRequired()

        if self.settings['json']:
            self.StdoutLogging(False)
        else:
            self.StdoutLogging(True)

#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    xmount().run(sys.argv)
