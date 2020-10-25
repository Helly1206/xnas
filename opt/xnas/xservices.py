#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : xservices.py                                 #
#          Xnas all in one services                     #
#          Dynmount and auto empty cifs recyclebin      #
#          I. Helwegen 2020                             #
#########################################################

####################### IMPORTS #########################
import sys
import os
import signal
from threading import Timer, Lock
from common.xnas_engine import groups
from common.xnas_engine import xnas_engine
from common.xnas_check import xnas_check
from common.shell import shell
from net.cifsemptybin import cifsemptybin
from mounts.dynmount import dynmount
from remotes.dynmountremote import dynmountremote
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : xservices                                     #
#########################################################
class xservices(xnas_engine):
    def __init__(self):
        xnas_engine.__init__(self, "xservices")
        self.settings = {}
        self.mutex = Lock()
        self.cifsemptybin = None
        self.dynmount = None
        self.dynmountremote = None
        self.srvTimer     = None
        self.srvIsRunning = False
        self.srvInterval = 60
        self.verbose = False

    def __del__(self):
        del self.mutex
        xnas_engine.__del__(self)

    def exitSignal(self, signum = 0, frame = 0):
        self.logger.info("stopping xservices")
        if self.cifsemptybin:
            self.cifsemptybin.terminate()
        if self.dynmount:
            self.dynmount.terminate()
        if self.dynmountremote:
            self.dynmountremote.terminate()
        self.stop()
        if self.srvTimer:
            self.srvTimer.join(5)
            del self.srvTimer
        self.logger.info("stopped xservices")
        exit(0)

    def checkInstanceRunning(self):
        retval = False
        pname = os.path.basename(__file__)

        cmd = "ps -All|grep {}".format(pname)

        try:
            lines = shell().command(cmd).splitlines()
            if len(lines) > 1:
                retval = True
        except:
            pass

        return retval

    def run(self, argv):
        checkResults = []
        result = ""
        self.handleArgs(argv)
        if xnas_check(self, lightCheck = True).check():
            exit(1)

        if self.checkInstanceRunning():
            self.logger.info("Another instance of xservices is already running, exit ...")
            exit(1)

        self.logger.info("starting xservices")
        # 2 loops, one timer at 12am, one timer that runs for every n seconds
        if self.hasSetting(self.settings,"verbose"):
            self.verbose = self.toBool(self.settings["verbose"])

        self.srvInterval = self.checkKey(groups.SETTINGS,"dyninterval")
        if self.srvInterval == None:
            self.srvInterval = 60

        zfshealth = self.checkKey(groups.SETTINGS,"dynzfshealth")
        if zfshealth == None:
            zfshealth = False

        removable = self.checkKey(groups.SETTINGS,"dynremovable")
        if removable == None:
            removable = False

        self.start()

        if self.checkKey(groups.SETTINGS,"srvenable"):
            self.cifsemptybin = cifsemptybin(self, self.verbose)
            self.dynmount = dynmount(self, self.verbose, zfshealth, removable)
            self.dynmountremote = dynmountremote(self, self.verbose)

            self.logger.info("started xservices")
            signal.pause()
        else:
            self.logger.info("xservices is disabled, exiting")

    def handleArgs(self, argv):
        xargs = {}
        xopts = {"verbose": "be verbose in actions (for debugging)"}
        extra = ('xservices needs to preferably run as a service\n'
                 'It takes care of:\n'
                 '    Dynmount:        dynamically mount mounts or remotemounts when they become\n'
                 '                     available. Options can be changed with: "xnas srv ..."\n'
                 '    Emptyrecyclebin: automatically delete old files from cifs recycle bin\n'
                 '                     Maximum age can be changed with: "xnetshare add ..."\n'
                 '                     The recyclebin is emptied every day at midnight\n'
                 'xservices can be enabled or disabled with "xnas srv -e"')
        self.fillSettings(self.parseOpts(argv, xopts, xargs, extra), xopts)

    def fillSettings(self, optsnargs, xopts):
        self.settings.update(optsnargs[0])
        self.settingsBool(self.settings, 'json')
        if self.settings['json']:
            self.StdoutLogging(False)
        else:
            self.StdoutLogging(True)

    def start(self):
        if not self.srvIsRunning:
            if self.verbose:
                self.logger.info("Reload database in {} seconds".format(self.srvInterval))
            self.srvTimer = Timer(self.srvInterval, self.reloadDB)
            self.srvTimer.start()
            self.srvIsRunning = True

    def stop(self):
        self.srvTimer.cancel()
        self.srvIsRunning = False

    def reloadDB(self):
        self.mutex.acquire()
        self.stop()
        self.reload()
        if self.verbose:
            self.logger.info("Reloaded database")

        self.srvInterval = self.checkKey(groups.SETTINGS,"dyninterval")
        if self.srvInterval == None:
            self.srvInterval = 60

        if self.dynmountremote:
            self.dynmountremote.updateUrlList()

        if self.dynmount:
            zfshealth = self.checkKey(groups.SETTINGS,"dynzfshealth")
            if zfshealth == None:
                zfshealth = False

            removable = self.checkKey(groups.SETTINGS,"dynremovable")
            if removable == None:
                removable = False
            self.dynmount.update(zfshealth, removable)
            self.dynmount.updateZfsList()
            
        self.start()
        self.mutex.release()

#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    xservices().run(sys.argv)
