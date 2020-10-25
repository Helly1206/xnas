# -*- coding: utf-8 -*-
#########################################################
# SERVICE : xnas_dir.py                                 #
#           gets xnas folders and its contents          #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import logging
from common.ls import ls
from mounts.mount import mount
from remotes.remotemount import remotemount
from shares.share import share
from net.netshare import netshare
from common.xnas_engine import objects
#########################################################

####################### GLOBALS #########################
WILDCARDS = ['*', '?', '[', ']']

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : xnas_dir                                      #
#########################################################
class xnas_dir(ls):
    def __init__(self, engine):
        self.logger = logging.getLogger('xnas.dir')
        self.engine = engine
        ls.__init__(self)

    def __del__(self):
        ls.__del__(self)

    def parseName(self, settings):
        name = ""
        type = ""
        if self.engine.hasSetting(settings,"name"):
            name = settings["name"]
            if self.engine.hasSetting(settings,"type"):
                type = settings["type"]

        return name, type

    def pd(self, name, type, loc):
        folder = ""
        filter = "*"
        found, obj = self.engine.findName(name, type)
        if found:
            if obj == objects.MOUNT:
                folder = mount(self.engine).getMountpoint(name)
            elif obj == objects.REMOTEMOUNT:
                folder = remotemount(self.engine).getMountpoint(name)
            elif obj == objects.SHARE or obj == objects.NETSHARE:
                folder = self.engine.shareDir(name)
            else:
                self.logger.error("Database object unknown")

        if loc:
            folder = os.path.join(folder,loc)

        if not os.path.isdir(folder):
            folder, filter = os.path.split(folder)
            if not os.path.isdir(folder):
                folder = ""
                filter = "*"
            elif not os.path.isfile(os.path.join(folder,filter)):
                if not any(chr for chr in WILDCARDS if chr in filter):
                    folder = ""
                    filter = "*"

        return folder, filter

    def cd(self, point):
        try:
            os.chdir(point)
        except Exception as e:
            self.logger.error("Error changing directory to {}".format(point))
            self.logger.error(e)

    def inTypeList(self, type):
        return self.engine.findType(type) != None

######################### MAIN ##########################
if __name__ == "__main__":
    pass
