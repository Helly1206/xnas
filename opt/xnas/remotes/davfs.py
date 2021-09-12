# -*- coding: utf-8 -*-
#########################################################
# SERVICE : davfs.py                                    #
#           remotemount davfs specific operations       #
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
INSTALL        = "davfs2"
SECRETSFILE    = "/etc/davfs2/secrets"
SECRETSBAKFILE = "/etc/davfs2/secrets.bak"
SECRETSMODE    = 0o600
DAVFSDEFOPT    = ["nofail"]
DAVFSFILEOPT   = "file_mode="
DAVFSDIROPT    = "dir_mode="

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : davfs                                         #
#########################################################
class davfs(object):
    def __init__(self, logger):
        self.hasFs = False
        try:
            self.hasFs = self.checkInstalled()
        except Exception as e:
            logger.error("Error reading davfs information")
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
            retval = val.split('.')[0]
        except:
            pass
        return retval

    def setOptions(self, options, url, guest, access = "0777"):
        for opt in DAVFSDEFOPT:
            if not opt in options:
                options.append(opt)

        for opt in options:
            if opt.startswith(DAVFSFILEOPT):
                options.remove(opt)
                break
        for opt in options:
            if opt.startswith(DAVFSDIROPT):
                options.remove(opt)
                break
        options.append("{}{}".format(DAVFSFILEOPT, access))
        options.append("{}{}".format(DAVFSDIROPT, access))

        if guest:
            if not "guest" in options:
                options.append("guest")
        else:
            if "guest" in options:
                options.remove("guest")
        return options

    def buildURL(self, https, server, sharename):
        if https:
            prefix = "https:"
        else:
            prefix = "http:"
        url = "{}//{}.{}".format(prefix, self.fixSharename(sharename), self.fixServer(server))
        return url.replace(" ","$20")

    def parseURL(self, url):
        https = True
        server = ""
        sharename = ""
        try:
            prefix = url.split("//")[0].lower().strip()
            https = prefix == "https:"
        except:
            pass
        try:
            server = ".".join(url.split("//")[1].split(".")[1:]).strip()
        except:
            pass
        try:
            sharename = url.split("//")[1].split(".")[0].strip()
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
        retval = True
        self.checkSecrets()
        self.copySecrets()
        cred = self.findCred(url)
        if cred:
            self.removeCred(cred['line'])
        self.addCred(url, username, password)
        return retval

    def delCredentials(self, url):
        retval = False
        self.checkSecrets()
        cred = self.findCred(url)
        if cred:
            self.copySecrets()
            self.removeCred(cred['line'])
            retval = True
        return retval

    def hasCredentials(self, url):
        return self.findCred(url) != {}

    def getCredentials(self, url):
        username = ""
        cred = self.findCred(url)
        if cred:
            username = cred["user"]
        return username

    ################## INTERNAL FUNCTIONS ###################

    def checkInstalled(self):
        return shell().commandExists("mount.davfs")

    def checkSecrets(self):
        if not os.path.isfile(SECRETSFILE):
            with open(SECRETSFILE, "wt") as fp:
                fp.writelines(["# davfs2 secrets file created by xnas\n","# davfs2 secrets file was non existent\n\n"])
            os.chown(SECRETSFILE, pwd.getpwnam('root').pw_uid, pwd.getpwnam('root').pw_gid) # set user:group as root:root
            os.chmod(SECRETSFILE, SECRETSMODE)

    def copySecrets(self):
        shutil.copy2(SECRETSFILE, SECRETSBAKFILE)

    def findCred(self, url):
        cred = {}
        linenr = 0
        with open(SECRETSFILE, "rt") as fp:
            for line in fp:
                if len(line.strip()) > 0:
                    if line.strip()[0] != "#":
                        line = line.replace("\t", " ")
                        line = " ".join(line.split())
                        linelist = line.split()
                        try:
                            if linelist[0].lower().strip() == url.lower().strip():
                                cred['url'] = linelist[0].strip()
                                cred['user'] = linelist[1].strip()
                                cred['password'] = linelist[2].strip()
                                cred['line'] = linenr
                                break
                        except:
                            cred = {}
                linenr += 1
        return cred

    def removeCred(self, line):
        with open(SECRETSFILE, "rt") as fp:
            lines = fp.readlines()

        lines.pop(line)

        with open(SECRETSFILE, "wt") as fp:
            fp.writelines(lines)

    def addCred(self, url, username, password):
        with open(SECRETSFILE, "rt") as fp:
            filetext = str(fp.read())
        newline = "\n"
        if filetext[-1] == newline:
            newline = ""

        with open(SECRETSFILE, "at") as fp:
            fp.writelines(["{}{} {} {}".format(newline, url, username, password)])



######################### MAIN ##########################
if __name__ == "__main__":
    pass
