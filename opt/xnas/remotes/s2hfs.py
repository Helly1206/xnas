# -*- coding: utf-8 -*-
#########################################################
# SERVICE : s2hfs.py                                    #
#           remotemount s2hfs specific operations       #
#           for xnas                                    #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
import os
import pwd
import shutil
from common.shell import shell
#########################################################

####################### GLOBALS #########################
INSTALL        = "s2hfs"
S2HFSDEFOPT    = ["nofail"]
S2HFSUMASK     = "umask="

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : s2hfs                                         #
#########################################################
class s2hfs(object):
    def __init__(self, logger):
        self.logger = logger
        self.hasFs = False
        try:
            self.hasFs = self.checkInstalled()
        except Exception as e:
            logger.error("Error reading s2hfs information")
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
            label = url.split(":")[0].split("@")
            if len(label) > 1:
                retval = "_".join(label[1:])
            else:
                retval = label[0]
        except:
            pass
        return retval

    def setOptions(self, options, url, guest, access = "0777"):
        changed = False
        for opt in S2HFSDEFOPT:
            if not opt in options:
                options.append(opt)
                changed = True

        for opt in options:
            if opt.startswith(S2HFSUMASK):
                try:
                    val = opt.split("=")[1]
                    umask = self.umask(access)
                    if val != umask:
                        options.remove(opt)
                        options.append("{}{}".format(S2HFSUMASK, umask))
                        changed = True
                except:
                    pass
                break
        #guest is not used
        return changed

    def buildURL(self, https, server, sharename, username = ""):
        if username:
            url = "{}@{}".format(username,self.fixServer(server))
        else:
            url = "{}".format(self.fixServer(server))
        if sharename:
            url += ":{}".format(self.fixSharename(sharename))
        return url.replace(" ","$20")

    def parseURL(self, url):
        https = True
        server = ""
        sharename = ""
        try:
            label = url.split(":")
            if len(label) > 1:
                sharename = label[1]
            server = label[0]
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
        retval = False
        if self.available() and password:
            https, server, sharename = self.parseURL(url)
            if not username:
                cmd = "s2hfs " + server + " -c -p " + password
            else:
                cmd = "s2hfs " + server + " -c -u " + username + " -p " + password
            try:
                shell().command(cmd)
                retval = True
            except Exception as e:
                self.logger.error("Error adding credentials")
                self.logger.error(e)
                retval = False
        return retval

    def delCredentials(self, url, username = ""):
        retval = False
        if self.available():
            if self.hasCredentials(url):
                https, server, sharename = self.parseURL(url)
                if not username:
                    cmd = "s2hfs " + server + " -C"
                else:
                    cmd = "s2hfs " + server + " -C -u " + username
                try:
                    shell().command(cmd)
                    retval = True
                except Exception as e:
                    self.logger.error("Error deleting credentials")
                    self.logger.error(e)
                    retval = False
        return retval

    def hasCredentials(self, url):
        return self.getCredentials(url, False) != ""

    def getCredentials(self, url, fromServer = True):
        username = ""
        if self.available():
            https, server, sharename = self.parseURL(url)
            cmd = "s2hfs " + server + " -r"
            try:
                if fromServer:
                    servuserloc = server.split("@")
                    if len(servuserloc) > 1:
                        username = servuserloc[0]
                else:
                    lines = shell().command(cmd)
                    username = lines.splitlines()[0]
            except Exception as e:
                self.logger.error("Error getting credentials")
                self.logger.error(e)
        return username

    def addKeys(self, url, username, password):
        retval = False
        if self.available() and password:
            https, server, sharename = self.parseURL(url)
            if self.hasKeys(url): #delete current keys first
                retval = self.delKeys(url, username, password)
            if retval:
                if not username:
                    cmd = "s2hfs " + server + " -k -p " + password
                else:
                    cmd = "s2hfs " + server + " -k -u " + username + " -p " + password
                try:
                    shell().command(cmd)
                    retval = True
                except Exception as e:
                    self.logger.error("Error adding keys")
                    self.logger.error(e)
                    retval = False
        return retval

    def delKeys(self, url, username = ""):
        retval = False
        if self.available():
            if self.hasKeys(url):
                https, server, sharename = self.parseURL(url)
                if not username:
                    cmd = "s2hfs " + server + " -K"
                else:
                    cmd = "s2hfs " + server + " -K -u " + username
                try:
                    shell().command(cmd)
                    retval = True
                except Exception as e:
                    self.logger.error("Error deleting keys")
                    self.logger.error(e)
                    retval = False
        return retval

    def hasKeys(self, url):
        return self.getKeys(url) != ""

    def getKeys(self, url):
        idFile = ""
        if self.available():
            https, server, sharename = self.parseURL(url)
            cmd = "s2hfs " + server + " -e"
            try:
                lines = shell().command(cmd)
                idFile = lines.splitlines()[0]
            except Exception as e:
                self.logger.error("Error getting credentials")
                self.logger.error(e)
        return idFile

    ################## INTERNAL FUNCTIONS ###################

    def checkInstalled(self):
        return shell().commandExists("mount.s2hfs")

    def umask(self, smode):
        mode = int(smode,8)
        return ~mode & 0o0777

######################### MAIN ##########################
if __name__ == "__main__":
    pass
