#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : xdir.py                                      #
#          Xnas list directory                          #
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
# Class : xdir                                          #
#########################################################
class xdir(xnas_engine):
    def __init__(self):
        xnas_engine.__init__(self, "xdir")
        self.settings = {}
        self.dir = xnas_dir(self)

    def __del__(self):
        del self.dir
        xnas_engine.__del__(self)

    def run(self, argv):
        checkResults = []
        result = ""
        self.handleArgs(argv)
        if xnas_check(self, lightCheck = True).check():
            exit(1)

        name, type = self.dir.parseName(self.settings)
        folder, filter = self.dir.pd(name, type, self.settings["loc"])
        if folder:
            contents=self.dir.ls(folder, self.settings['human'],
                    self.settings['short'], self.settings['noroot'],
                    self.settings['nocolor'], self.settings['noclass'], self.settings['nosort'], filter)
        if self.settings["json"]:
            self.printJson(contents)
        else:
            if not folder or not contents:
                self.printMarked("File or folder not found")
            else:
                self.prettyPrintTable(contents)

    def handleArgs(self, argv):
        xargs = {"<name>": "Name of the folder to change to",
                 "<loc>": "(Optional) Relative location from the name folder",
                 "<type>": "(Optional) Type of object to look at"}
        xopts = {"human": "show sizes in human readable format",
                 "short": "show in short format (only names)",
                 "noroot": "don't show root folders (. and ..)",
                 "nocolor": "don't show colors",
                 "noclass": "don't classify",
                 "nosort": "don't soft alphabetically by name"}
        extra = ('Lists folder contents\n'
                 'When type is not defined, first shares is checked, then mounts and remote mounts\n'
                 '<type>: mount, remotemount, share, netshare\n'
                 '<loc>: can also be a file or multiple files with wildcards *? etc.')
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
        self.settingsBool(self.settings, 'human')
        self.settingsBool(self.settings, 'short')
        self.settingsBool(self.settings, 'noroot')
        self.settingsBool(self.settings, 'nocolor')
        self.settingsBool(self.settings, 'noclass')
        self.settingsBool(self.settings, 'nosort')
        if self.settings['json']:
            self.StdoutLogging(False)
            self.settings['nocolor'] = True
            self.settings['noclass'] = True
        else:
            self.StdoutLogging(True)
#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    xdir().run(sys.argv)
