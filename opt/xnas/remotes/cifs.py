# -*- coding: utf-8 -*-
#########################################################
# SERVICE : cifs.py                                     #
#           remotemount cifs specific operations        #
#           for xnas                                    #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import pwd
import shutil
from common.shell import shell
from remotes.ping import ping
#########################################################

####################### GLOBALS #########################
INSTALL      = "cifs-utils"
CIFSCREDS    = "/root/.cifscredentials-"
CIFSCREDOPT  = "credentials="
CIFSDEFOPT   = ["iocharset=utf8","nofail"]
CIFSFILEOPT  = "file_mode="
CIFSDIROPT   = "dir_mode="
CIFSCREDSBAK = ".bak"
CREDSMODE    = 0o600
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : cifs                                          #
#########################################################
class cifs(object):
    def __init__(self, logger):
        self.hasFs = False
        try:
            self.hasFs = self.checkInstalled()
        except Exception as e:
            logger.error("Error reading cifs information")
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
            val = ping().getPath(url)
            retval = val.replace('/','')
        except:
            pass
        return retval

    def setOptions(self, options, url, guest, access = "0777"):
        for opt in CIFSDEFOPT:
            if not opt in options:
                options.append(opt)

        for opt in options:
            if opt.startswith(CIFSFILEOPT):
                options.remove(opt)
                break
        for opt in options:
            if opt.startswith(CIFSDIROPT):
                options.remove(opt)
                break
        options.append("{}{}".format(CIFSFILEOPT, access))
        options.append("{}{}".format(CIFSDIROPT, access))

        if guest:
            if not "guest" in options:
                options.append("guest")
            for opt in options:
                if opt.startswith(CIFSCREDOPT):
                    options.remove(opt)
                    break
        else:
            if "guest" in options:
                options.remove("guest")
            for opt in options:
                if opt.startswith(CIFSCREDOPT):
                    options.remove(opt)
                    break
            options.append("{}{}".format(CIFSCREDOPT, self.getCredsFile(url)))
        return options

    def buildURL(self, https, server, sharename):
        url = "//{}/{}".format(self.fixServer(server), self.fixSharename(sharename))
        return url.replace(" ","$20")

    def parseURL(self, url):
        https = True
        server = ""
        sharename = ""
        try:
            server = url.lstrip("//").split("/")[0].strip()
        except:
            pass
        try:
            sharename = "/".join(url.lstrip("//").split("/")[1:]).strip()
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
            sname = sharename.lstrip('/')
        else:
            sname = sharename
        return sname

    def addCredentials(self, url, username, password):
        self.delCredentials(url)
        return self.addCredsFile(url, username, password)

    def delCredentials(self, url):
        retval = False
        if self.checkCredsFile(url):
            self.copyCredsFile(url)
            os.remove(self.getCredsFile(url))
            retval = True
        return retval

    def getCredentials(self, url):
        username = ""
        cred = self.getCredsContent(url)
        if cred:
            username = cred["user"]
        return username

    ################## INTERNAL FUNCTIONS ###################

    def checkInstalled(self):
        return shell().commandExists("mount.cifs")

    def checkCredsFile(self, url):
        return os.path.isfile(self.getCredsFile(url))

    def copyCredsFile(self, url):
        shutil.copy2(self.getCredsFile(url), "{}{}".format(self.getCredsFile(url), CIFSCREDSBAK))

    def addCredsFile(self, url, username, password):
        retval = False
        try:
            credsFile = self.getCredsFile(url)
            with open(credsFile, "wt") as fp:
                    fp.write("username={}\npassword={}".format(username, password))
            os.chown(credsFile, pwd.getpwnam('root').pw_uid, pwd.getpwnam('root').pw_gid) # set user:group as root:root
            os.chmod(credsFile, CREDSMODE)
            retval = True
        except:
            pass
        return retval

    def getCredsContent(self, url):
        retval = {}
        try:
            credsFile = self.getCredsFile(url)
            with open(credsFile, "rt") as fp:
                for line in fp:
                    if "username=" in line:
                        retval["user"] = line.split('=')[1]
                    if "password=" in line:
                        retval["password"] = line.split('=')[1]
        except:
            pass
        return retval

    def getCredsFile(self, url):
        return "{}{}".format(CIFSCREDS,self.getCredsSuffix(url))

    def getCredsSuffix(self, url):
        https, server, sharename = self.parseURL(url)
        return "{}-{}".format(sharename.strip('/'),server.strip('.'))
######################### MAIN ##########################
if __name__ == "__main__":
    pass
