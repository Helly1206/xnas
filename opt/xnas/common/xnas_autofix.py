# -*- coding: utf-8 -*-
#########################################################
# SERVICE : xnas_fix.py                                 #
#           Fixes broken mounts and shares              #
#           (if possible)                               #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import logging
from threading import Timer
from common.xnas_check import xnas_check
from common.xnas_fix import xnas_fix
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : xnas_autofix                                  #
#########################################################
class xnas_autofix(object):
    def __init__(self, engine, verbose = False, enable = True, retries = 3, interval = 60):
        self.engine = engine
        self.verbose = verbose
        self.logger = logging.getLogger('xnas.autofix')
        self.enable = True
        self.retries = 0
        self.interval = 0
        self.update(enable, retries, interval)
        self.timer     = None
        self.isRunning = False
        self.counter   = 0
        self.start()

    def __del__(self):
        pass

    def terminate(self):
        self.stop()
        if self.timer:
            self.timer.join(5)
        del self.timer

    def update(self, enable, retries, interval):
        dostart = enable and not self.enable
        self.enable = enable
        self.retries = retries
        self.interval = interval
        if self.interval == 0:
            self.interval = 1
        if dostart:
            self.start()

    ################## INTERNAL FUNCTIONS ###################

    def start(self):
        if not self.enable:
            self.checkOnce()
        elif not self.isRunning:
            if self.counter == 0:
                interval = 1
                if self.verbose:
                    self.logger.info("Check and fix now")
            else:
                interval = self.interval
                if self.verbose:
                    self.logger.info("Check and fix in {} seconds".format(interval))
            self.timer = Timer(interval, self.run)
            self.counter += 1
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
            self.logger.info("Checking and fixing errors")
        self.checkAndFix()
        if (self.retries == 0) or (self.counter < self.retries):
            self.start()
        self.engine.mutex.release()

    def checkOnce(self):
        if xnas_check(self).check():
            self.logger.warning("Running xservices with errors, service may have limited performance")

    def checkAndFix(self):
        checkResults = xnas_check(self.engine, noMsg = True, level = self.counter-1, json = True).check()
        if not checkResults:
            if self.retries == 0:
                self.retries = 1
            self.counter = self.retries # do not check anymore
        else:
            xnas_fix(self.engine).fix(checkResults)
            checkResults = xnas_check(self.engine, noMsg = True, level = self.counter-1, json = True).check()
            if not checkResults:
                if self.retries == 0:
                    self.retries = 1
                self.counter = self.retries # do not check anymore

######################### MAIN ##########################
if __name__ == "__main__":
    pass
