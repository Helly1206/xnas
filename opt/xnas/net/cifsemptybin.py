# -*- coding: utf-8 -*-
#########################################################
# SERVICE : cifsemptybin.py                             #
#           Empties the cifs recyclebin on max age      #
#           Part of xservices                           #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import stat
import logging
from threading import Timer
from datetime import datetime
from common.xnas_engine import groups
from net.cifsshare import cifsshare
#########################################################

####################### GLOBALS #########################
SECONDSINDAY     = 24*60*60
DEFAULTINTERVAL  = 7*SECONDSINDAY
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : cifsemptybin                                  #
#########################################################
class cifsemptybin(object):
    def __init__(self, engine, verbose = False, manual = True, autoenable = True):
        self.engine     = engine
        self.autoenable = autoenable
        self.verbose    = verbose
        self.logger     = logging.getLogger('xnas.cifsemptybin')
        self.timer      = None
        self.isRunning  = False
        self.first      = True
        self.interval   = 0
        self.minage     = 0
        if not manual:
            self.start()

    def __del__(self):
        pass

    def terminate(self):
        self.stop()
        if self.timer:
            self.timer.join(5)
        del self.timer

    def update(self, autoenable):
        if autoenable:
            if not self.autoenable:
                if not self.isRunning:
                    self.first = True
                    self.start()
        elif self.autoenable:
            self.stop()
        self.autoenable = autoenable

    def emptyBin(self, key):
        retval = False
        if not key:
            retval = self.forceEmptyAll()
        else:
            retval = self.forceEmpty(key)

        return retval

    ################## INTERNAL FUNCTIONS ###################

    def start(self):
        if not self.isRunning:
            if self.first:
                self.first = False
                interval = 1
                if self.verbose:
                    self.logger.info("Check now")
            else:
                if self.interval == 0:
                    if self.minage > 0:
                        interval = self.minage * SECONDSINDAY
                    else:
                        interval = DEFAULTINTERVAL
                else:
                    interval = self.interval
                interval = SECONDSINDAY - self.getNowSod()
                if self.verbose:
                    self.logger.info("Check in {} seconds".format(interval))
            self.interval = 0
            self.timer = Timer(interval, self.run)
            self.timer.start()
            self.isRunning = True

    def stop(self):
        if self.timer:
            self.timer.cancel()
        self.isRunning = False

    def run(self):
        self.engine.mutex.acquire()
        self.stop()
        if self.verbose:
            self.logger.info("Checking recycle bins for maximum age")
        self.checkAndEmpty(self.getBins())
        self.start()
        self.engine.mutex.release()

    def getNowSod(self):
        now = datetime.now()
        return (now.hour*60 + now.minute)*60 + now.second

    def getBins(self):
        bins = []
        self.minage = 0
        netshares = self.engine.checkGroup(groups.NETSHARES)
        if netshares:
            cifsShare = cifsshare(self.logger, self.engine)
            for key, netshare in netshares.items():
                if netshare['type'] == 'cifs' and netshare['recyclemaxage'] != 0:
                    binloc = cifsShare.getRecycleBin(key)
                    #cifs check recylce bin
                    if binloc:
                        recbin = {}
                        #recbin['name'] = key
                        recbin['maxage'] = netshare['recyclemaxage']
                        recbin['location'] = binloc
                        bins.append(recbin)
                        if self.verbose:
                            self.logger.info("Recycle bin with age limit found for '{}' (maxage = {})".format(key, recbin['maxage']))
                        if (self.minage == 0) or (recbin['maxage'] < self.minage):
                            self.minage = recbin['maxage']
                            if self.verbose:
                                self.logger.info("Recycle bin with minimum age updated (minage = {})".format(self.minage))
            del cifsShare

        return bins

    def checkAndEmpty(self, bins):
        for recbin in bins:
            self.loopFolderRemove(recbin['location'], recbin['maxage'])
            self.loopFolderEmpty(recbin['location'])
        return

    def forceEmptyAll(self):
        retval = True # always return true, even if nothing to be done
        netshares = self.engine.checkGroup(groups.NETSHARES)
        if netshares:
            cifsShare = cifsshare(self.logger, self.engine)
            for key, netshare in netshares.items():
                if netshare['type'] == 'cifs':
                    binloc = cifsShare.getRecycleBin(key)
                    if binloc:
                        self.loopFolderRemove(binloc, force = True)
                        self.loopFolderEmpty(binloc)
                        retval = True
            del cifsShare
        return retval

    def forceEmpty(self, key):
        retval = True # always return true, even if nothing to be done
        netshare = self.engine.checkKey(groups.NETSHARES, key)
        if netshare:
            if netshare['type'] == 'cifs':
                binloc = cifsshare(self.logger, self.engine).getRecycleBin(key)
                if binloc:
                    self.loopFolderRemove(binloc, force = True)
                    self.loopFolderEmpty(binloc)
                    retval = True
        return retval

    def loopFolderRemove(self, location, maxage = 0, force = False):
        if not os.path.isdir(location):
            return
        with os.scandir(location) as entries:
            for entry in entries:
                try:
                    info = entry.stat()
                    newlocation = os.path.join(location, entry.name)
                    if stat.S_ISDIR(info.st_mode):
                        self.loopFolderRemove(newlocation, maxage)
                    else:
                        age = self.getAge(info.st_atime)
                        keeptime = self.keepTime(age, maxage)
                        if self.verbose:
                            self.logger.info("File '{}' has age of {} days".format(entry.name, int(age/SECONDSINDAY)))
                        if force or (keeptime <= 0):
                            try:
                                os.remove(newlocation)
                                if self.verbose:
                                    if force:
                                        self.logger.info("Recycle bin file '{}' is forced removed".format(newlocation))
                                    else:
                                        self.logger.info("Recycle bin file '{}' exceeded max age of {} days and is removed".format(newlocation, maxage))
                            except:
                                if force:
                                    self.logger.error("Error forced removing recycle bin file: '{}'".format(newlocation))
                                else:
                                    self.logger.error("Error removing recycle bin file: '{}' exceeded max age of {} days".format(newlocation, maxage))
                        elif not force:
                            if (self.interval == 0) or (self.interval > keeptime):
                                self.interval = keeptime
                except:
                    self.logger.error("Error scanning recycle bin files for exceeding max age")
        return

    def loopFolderEmpty(self, location):
        if not os.path.isdir(location):
            return
        with os.scandir(location) as entries:
            for entry in entries:
                try:
                    info = entry.stat()
                    if stat.S_ISDIR(info.st_mode):
                        rmFolder = False
                        newlocation = os.path.join(location, entry.name)
                        if any(os.scandir(newlocation)): # folder not empty
                            self.loopFolderEmpty(newlocation)
                            if not any(os.scandir(newlocation)): # folder empty after resursive loop
                                rmFolder = True
                        else:
                            rmFolder = True
                        if rmFolder:
                            try:
                                os.rmdir(newlocation)
                                if self.verbose:
                                    self.logger.info("Empty recycle bin folder '{}' removed".format(newlocation))
                            except:
                                self.logger.error("Error removing empty recycle bin folder '{}'".format(newlocation))
                except:
                    self.logger.error("Error scanning empty recycle bin folders")
        return

    def keepTime(self, age, maxage):
        return (maxage * SECONDSINDAY) - age

    def getAge(self, time):
        return int(datetime.now().timestamp() - time)

######################### MAIN ##########################
if __name__ == "__main__":
    pass
