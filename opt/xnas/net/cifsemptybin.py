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
CIFSEMPTYTIMESOD = 0
SECONDSINDAY     = 24*60*60
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : cifsemptybin                                  #
#########################################################
class cifsemptybin(object):
    def __init__(self, engine, verbose = False):
        self.engine    = engine
        self.verbose   = verbose
        self.logger    = logging.getLogger('xnas.cifsemptybin')
        self.timer     = None
        self.isRunning = False
        self.first     = True
        self.start()

    def __del__(self):
        pass

    def terminate(self):
        self.stop()
        self.timer.join(5)
        del self.timer

    ################## INTERNAL FUNCTIONS ###################

    def start(self):
        if not self.isRunning:
            if self.first:
                self.first = False
                interval = 1
                if self.verbose:
                    self.logger.info("Check now")
            else:
                interval = SECONDSINDAY - self.getNowSod()
                if self.verbose:
                    self.logger.info("Check in {} seconds".format(interval))
            self.timer = Timer(interval, self.run)
            self.timer.start()
            self.isRunning = True

    def stop(self):
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
            del cifsShare

        return bins

    def checkAndEmpty(self, bins):
        for recbin in bins:
            self.loopFolderRemove(recbin['location'], recbin['maxage'])
            self.loopFolderEmpty(recbin['location'])
        return

    def loopFolderRemove(self, location, maxage):
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
                        if self.verbose:
                            age = self.getAge(info.st_atime)
                            self.logger.info("File '{}' has age of {} days".format(entry.name, age))
                        if age > maxage:
                            try:
                                os.remove(newlocation)
                                self.logger.info("Recycle bin file '{}' exceeded max age of {} days and is removed".format(newlocation, maxage))
                            except:
                                self.logger.error("Error removing recycle bin file: '{}' exceeded max age of {} days".format(newlocation, maxage))
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
                                self.logger.info("Empty recycle bin folder '{}' removed".format(newlocation))
                            except:
                                self.logger.error("Error removing empty recycle bin folder '{}'".format(newlocation))
                except:
                    self.logger.error("Error scanning empty recycle bin folders")
        return

    def getAge(self, time):
        times = datetime.now().timestamp() - time
        return int(times/(60*60*24))

######################### MAIN ##########################
if __name__ == "__main__":
    pass
