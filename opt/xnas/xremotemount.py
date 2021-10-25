#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : xremotemount.py                              #
#          Xnas manage remote mounts                    #
#                                                       #
#          I. Helwegen 2020                             #
#########################################################

####################### IMPORTS #########################
import sys
from common.xnas_engine import xnas_engine
from common.xnas_check import xnas_check
from remotes.remotemount import remotemount
#########################################################

####################### GLOBALS #########################
NAMELIST = ["add", "del", "mnt", "umnt", "clr", "ena", "dis", "shw"]
NAMECHECK = ["del", "clr", "mnt", "dis", "shw"]
#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : xremotemount                                  #
#########################################################
class xremotemount(xnas_engine):
    def __init__(self):
        xnas_engine.__init__(self, "xremotemount")
        self.settings = {}

    def __del__(self):
        xnas_engine.__del__(self)

    def run(self, argv):
        result = True
        self.handleArgs(argv)
        Remotemount = remotemount(self, self.settings['human'])
        xcheck = xnas_check(self, Remotemount = Remotemount, json = self.settings['json'])
        if xcheck.ErrorExit(xcheck.check(), self.settings, NAMECHECK):
            if self.settings["json"]:
                self.printJsonResult(False)
            exit(1)
        del xcheck
        if not self.hasSetting(self.settings,"command"):
            remotemounts = Remotemount.getRemotemounts()
            if self.settings["json"]:
                self.printJson(remotemounts)
            else:
                self.prettyPrintTable(remotemounts)
        elif self.settings["command"] == "add":
            self.needSudo()
            result = Remotemount.addRm(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated with new remotemount entries")
            if self.settings["json"]:
                self.printJsonResult(result)
            # zfs do not create or destroy, use ZFS for that!
        elif self.settings["command"] == "del":
            self.needSudo()
            result = Remotemount.delRm(self.settings["name"])
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
            addedRemotemounts = Remotemount.pop(self.settings['interactive'], self.settings['pop'])
            if addedRemotemounts:
                if doUpdate:
                    self.update()
                    self.logger.info("Database updated with new remotemount entries")
            if self.settings["json"]:
                self.printJson(addedRemotemounts)
            else:
                self.prettyPrintTable(addedRemotemounts)
        elif self.settings["command"] == "mnt":
            self.needSudo()
            result = Remotemount.mnt(self.settings["name"])
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "umnt":
            self.needSudo()
            result = Remotemount.umnt(self.settings["name"])
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "clr":
            self.needSudo()
            result = Remotemount.clr(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated")
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "ena":
            self.needSudo()
            #result = Remotemount.ena(self.settings["name"])
            self.parseError("Command deprecated, use --method option instead")
            result = False
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "dis":
            self.needSudo()
            #result = Remotemount.dis(self.settings["name"])
            self.parseError("Command deprecated, use --method option instead")
            result = False
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "shw":
            self.needSudo()
            remotemountData = Remotemount.shw(self.settings["name"])
            if self.settings["json"]:
                self.printJson(remotemountData)
            else:
                self.prettyPrintTable(self.settings2Table(remotemountData))
        elif self.settings["command"] == "lst":
            entries = Remotemount.inDB()
            if self.settings["json"]:
                self.printJson(entries)
            else:
                self.prettyPrintTable(entries)
        elif self.settings["command"] == "url":
            url = Remotemount.findUrl()
            if self.settings["json"]:
                self.printJson(url)
            else:
                self.printValues(url)
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
        xargs = {"add": "adds or edits a remotemount [add <name>]",
                 "del": "deletes a remotemount [del <name>]",
                 "pop": "populates from fstab [pop]",
                 "mnt": "mounts a remotemount [mnt <name>]",
                 "umnt": "unmounts a remotemount if not referenced [umnt <name>]",
                 "clr": "removes a remotemount, but leaves fstab [clr <name>]",
                 "shw": "shows current remotemount settings [shw <name>]",
                 "lst": "lists xremotemount compatible fstab entries [lst]",
                 "url": "prints url of a <name> or <server>, <sharename> [url]",
                 "-": "show remotemounts and their status"}
        xopts = {"interactive": "ask before adding or changing mounts",
                 "human": "show sizes in human readable format",
                 "https": "davfs use https <boolean> (default = True) (add)",
                 "server": "server for remote mount <string> (add)",
                 "sharename": "sharename for remote mount <string> (add)",
                 "mountpoint": "mountpoint <string> (add)",
                 "type": "type <string> (davfs, cifs, nfs or nfs4) (add)",
                 "options": "extra options, besides _netdev <string> (add)",
                 "rw": "mount rw <boolean> (add)",
                 "freq": "dump value <value> (add)",
                 "pass": "mount order <value> (add)",
                 "uacc": "users access level (,r,w) (default = rw) (add)",
                 "sacc": "superuser access level (,r,w) (default = rw) (add)",
                 "username": "remote mount access username (guest if omitted) (add)",
                 "password": "remote mount access password (add)",
                 "method": "mount method <string> (see below) (add)",
                 "idletimeout": "unmount when idle timeout <int> (default = 30) (add)",
                 "timeout": "mounting timeout <int> (default = 10) (add)"}
        extra = ('URL generation from settings:\n'
        'davfs: <https>://<sharename>.<server>, e.g. https://test.myserver.com/dav.php/\n'
        'cifs : //<server>/<sharename>        , e.g. //192.168.1.1/test\n'
        'nfs  : server:<sharename>            , e.g. 192.168.1.1:/test\n'
        '"nfs4" is prefered as type for nfs, "nfs" as type refers to nfs3\n'
        'Mount methods:\n'
        'disabled: do not mount\n'
        'startup : mount from fstab during startup\n'
        'auto    : auto mount from fstab when accessed (default)\n'
        'dynmount: dynamically mount when available\n'
        'Options may be entered as single JSON string using full name, e.g.\n'
        'xremotemount add test \'{"server": "192.168.1.1", "sharename": "test", \n'
        '                   "mountpoint": "/mnt/test", "type": "cifs", \n'
        '                   "username": "userme", "password": "secret"}\'\n'
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
        #self.settingsBool(self.settings, 'auto', False)
        self.settingsBool(self.settings, 'rw', False)
        self.settingsBool(self.settings, 'https', False)
        self.settingsInt(self.settings, 'freq', False)
        self.settingsInt(self.settings, 'pass', False)
        self.settingsStr(self.settings, 'uacc', False)
        self.settingsStr(self.settings, 'sacc', False)
        self.settingsStr(self.settings, 'username', False)
        self.settingsStr(self.settings, 'password', False)

        self.nameRequired()

        if self.settings['json']:
            self.StdoutLogging(False)
        else:
            self.StdoutLogging(True)

#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    xremotemount().run(sys.argv)
