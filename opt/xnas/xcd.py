#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : xcd.py                                       #
#          Xnas change directory                        #
#                                                       #
#          I. Helwegen 2020                             #
#########################################################

####################### IMPORTS #########################
import sys
import os
from common.xnas_engine import xnas_engine
from common.xnas_check import xnas_check
from common.xnas_dir import xnas_dir
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : xcd                                           #
#########################################################
class xcd(xnas_engine):
    def __init__(self):
        xnas_engine.__init__(self, "xcd")
        self.settings = {}
        self.dir = xnas_dir(self)

    def __del__(self):
        del self.dir
        xnas_engine.__del__(self)

    def run(self, argv):
        checkResults = []
        result = ""
        self.handleArgs(argv)
        name, type = self.dir.parseName(self.settings)
        db, obj = self.findName(name, type)
        xcheck = xnas_check(self, lightCheck = True, json = True)
        if xcheck.ErrorExitCmd(xcheck.check(), self.settings, obj):
            if self.settings["json"]:
                self.printJsonResult(False)
            else:
                self.printMarked("Unable to change to folder")
            exit(1)
        del xcheck

        folder, filter = self.dir.pd(name, type, self.settings["loc"])
        if not folder:
            if self.settings['json']:
                printJson(folder)
            else:
                self.printMarked("Folder not found")
            exit(1)
        else:
            print(folder)
            exit(255)

    def handleArgs(self, argv):
        xargs = {"<name>": "Name of the folder to lookup",
                 "<loc>": "(Optional) Relative location from the name folder",
                 "<type>": "(Optional) Type of object to look at"}
        xopts = {}
        extra = ('Changes to folder location\n'
                 'When type is not defined, first shares is checked, then mounts and remote mounts\n'
                 'Types: mount, remotemount, share, netshare')
        self.fillSettings(self.parseOpts(argv, xopts, xargs, extra), xopts)

    def fillSettings(self, optsnargs, xopts):
        self.settings["loc"] = ""
        if len(optsnargs[1]) > 0:
            self.settings["name"]=optsnargs[1][0]
        if len(optsnargs[1]) > 1:
            for i in range(1, len(optsnargs[1])-1):
                self.settings["loc"] = os.path.join(self.settings["loc"],optsnargs[1][i])
            i = len(optsnargs[1]) - 1
            if self.dir.inTypeList(optsnargs[1][i]):
                self.settings["type"]=optsnargs[1][i]
            else:
                self.settings["loc"] = os.path.join(self.settings["loc"],optsnargs[1][i])

        if len(optsnargs[1]) < 1:
            self.parseError("Not enough arguments, no name defined")

        self.settings.update(optsnargs[0])
        self.settingsBool(self.settings, 'json')
        if self.settings['json']:
            self.StdoutLogging(False)
        else:
            self.StdoutLogging(True)
#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    xcd().run(sys.argv)
