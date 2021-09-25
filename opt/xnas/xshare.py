#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : xshare.py                                    #
#          Xnas manage shares                           #
#                                                       #
#          I. Helwegen 2020                             #
#########################################################

####################### IMPORTS #########################
import sys
from common.xnas_engine import xnas_engine
from common.xnas_check import xnas_check
from shares.share import share
#########################################################

####################### GLOBALS #########################
NAMELIST = ["add", "del", "bnd", "ubnd", "ena", "dis", "shw"]
NAMECHECK = ["del", "shw", "bnd", "dis", "add"]
#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : xshare                                        #
#########################################################
class xshare(xnas_engine):
    def __init__(self):
        xnas_engine.__init__(self, "xshare")
        self.settings = {}

    def __del__(self):
        xnas_engine.__del__(self)

    def run(self, argv):
        self.handleArgs(argv)
        Share = share(self)
        xcheck = xnas_check(self, Share = Share, lightCheck = True, json = self.settings['json'])
        if xcheck.ErrorExit(xcheck.check(), self.settings, NAMECHECK):
            if self.settings["json"]:
                self.printJsonResult(False)
            exit(1)
        del xcheck
        if not self.hasSetting(self.settings,"command"):
            shares = Share.getShares()
            if self.settings["json"]:
                self.printJson(shares)
            else:
                self.prettyPrintTable(shares)
        elif self.settings["command"] == "add":
            self.needSudo()
            result = Share.addSh(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated with new share entries")
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "del":
            self.needSudo()
            result = Share.delSh(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated")
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "bnd":
            self.needSudo()
            result = Share.bnd(self.settings["name"])
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "ubnd":
            self.needSudo()
            result = Share.ubnd(self.settings["name"])
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "ena":
            self.needSudo()
            result = Share.ena(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated")
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "dis":
            self.needSudo()
            result = Share.dis(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated")
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "shw":
            shareData = Share.shw(self.settings["name"])
            if self.settings["json"]:
                self.printJson(shareData)
            else:
                self.prettyPrintTable(self.settings2Table(shareData))
        elif self.settings["command"] == "lst":
            listData = Share.lst()
            if self.settings["json"]:
                self.printJson(listData)
            else:
                self.prettyPrintTable(listData)
        else:
            self.parseError("Unknown command argument")
            if self.settings["json"]:
                self.printJsonResult(False)

    def nameRequired(self):
        if self.hasSetting(self.settings,"command"):
            if self.settings["command"] in NAMELIST and not "name" in self.settings:
                self.parseError("The option {} requires a <name> as argument".format(self.settings["command"]))

    def handleArgs(self, argv):
        xargs = {"add": "adds or edits a share [add <name>]",
                 "del": "deletes a share [del <name>]",
                 "ena": "enables a share [ena <name>]",
                 "dis": "disables a share [dis <name>]",
                 "shw": "shows current share settings [shw <name>]",
                 "bnd": "binds a share [bnd <name>]",
                 "ubnd": "unbinds a share [ubd <name>]",
                 "lst": "lists xmounts and xremotemounts to share [lst]",
                 "-": "show shares and their status"}
        xopts = {"xmount": "xmount name to share <string> (add)",
                 "remotemount": "xmount is of remotemount type <boolean> (add)",
                 "folder": "relative folder in xmount to share <string> (add)",
                 "uacc": "users access level (,r,w) (default = rw) (add)",
                 "sacc": "superuser access level (,r,w) (default = rw) (add)"}
        extra = ('Options may be entered as single JSON string using full name, e.g.\n'
        'xshare add test \'{"xmount": "TEST", "folder": "/music"}\'\n'
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
    xshare().run(sys.argv)
