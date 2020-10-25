# -*- coding: utf-8 -*-
#########################################################
# SERVICE : nfs.py                                      #
#           remotemount nfs specific operations         #
#           for xnas                                    #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
from common.shell import shell
#########################################################

####################### GLOBALS #########################
INSTALL   = "nfs-common"
NFSDEFOPT = ["rsize=8192","wsize=8192","timeo=14","intr","nofail"]
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : nfs                                           #
#########################################################
class nfs(object):
    def __init__(self, logger):
        self.hasFs = False
        try:
            self.hasFs = self.checkInstalled()
        except Exception as e:
            logger.error("Error reading nfs information")
            logger.error(e)
            exit(1)

    def __del__(self):
        pass

    def available(self):
        return self.hasFs

    def installName(self):
        return INSTALL

    def getLabel(self, url):
        retval = ""
        try:
            val = ping().getBaseUrl(url)
            retval = val.split(':')[1]
        except:
            pass
        return retval

    # No options for NFS
    def setOptions(self, options, url, guest, access = "0777"):
        for opt in NFSDEFOPT:
            if not opt in options:
                options.append(opt)
        return options

    def buildURL(self, https, server, sharename):
        url = "{}:{}".format(self.fixServer(server), self.fixSharename(sharename))
        return url.replace(" ","$20")

    def parseURL(self, url):
        https = True
        server = ""
        sharename = ""
        try:
            server = url.split(":")[0].strip()
        except:
            pass
        try:
            sharename = url.split(":")[1].strip()
        except:
            pass
        return https, self.fixServer(server), self.fixSharename(sharename)

    def fixServer(self, server):
        if server.startswith('/'):
            sserv = server.lstrip('/')
        else:
            sserv = server
        return sserv

    def fixSharename(self, sharename):
        if sharename.startswith('/'):
            sname = sharename
        else:
            sname = '/' + sharename
        return sname

    # No credentials for NFS
    def addCredentials(self, url, username, password):
        return True

    # No credentials for NFS
    def delCredentials(self, url):
        return True

    ################## INTERNAL FUNCTIONS ###################

    def checkInstalled(self):
        return shell().commandExists("mount.nfs")

######################### MAIN ##########################
if __name__ == "__main__":
    pass
