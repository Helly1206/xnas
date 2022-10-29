# -*- coding: utf-8 -*-
#########################################################
# SERVICE : link.py                                     #
#           Links or unlinks folders from mounts as     #
#           shares                                      #
#                                                       #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
import os
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : link                                          #
#########################################################
class link(object):
    def __init__(self, logger):
        self.logger = logger

    def __del__(self):
        pass

    def link(self, source, loc):
        retval = False
        current = self.getlink(loc)
        if current:
            if current == source:
                #link exists and is correct, don't do anything
                retval = True
            else:
                #link exists and is not correct, remove old link
                self.unlink(loc)
        if not retval:
            if os.path.exists(loc):
                if os.path.isdir(loc):
                    if not os.listdir(loc):
                        #empty folder, remove
                        os.rmdir(loc)
            if os.path.exists(loc):
                self.logger.error("Non empty file or folder exists at share link")
            else:
                try:
                    self.hasSharesFolder(loc)
                    os.symlink(source, loc)
                    retval = True
                except Exception as e:
                    self.logger.error("Adding share")
                    self.logger.error(e)
        return retval

    def unlink(self, loc):
        retval = False
        if self.getlink(loc):
            os.unlink(loc)
            retval = True
        return retval

    def getlink(self, loc):
        lnk = ""
        if os.path.islink(loc):
            lnk = os.readlink(loc)
        return lnk
    
    def hasSharesFolder(self, loc):
        sharesFolder = os.path.dirname(loc)
        try:
            if not os.path.exists(sharesFolder):
                os.mkdir(sharesFolder)
        except Exception as e:
            self.logger.error("Unable to add shares folder: {}".format(sharesFolder))
            self.logger.error(e)
        return

######################### MAIN ##########################
if __name__ == "__main__":
    pass
