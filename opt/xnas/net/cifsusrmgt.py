# -*- coding: utf-8 -*-
#########################################################
# SERVICE : cifsusrmgt.py                               #
#           User management for cifs shares in          #
#           netshare for xnas                           #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
from common.shell import shell
#########################################################

####################### GLOBALS #########################
PDBEDITEXEC  = "pdbedit"
SMBPASSEXEC  = "smbpasswd"
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : cifsusrmgt                                    #
#########################################################
class cifsusrmgt(object):
    def __init__(self, logger):
        self.logger = logger
        self.usrLst = []
        try:
            self.usrmgt = self.checkInstalled()
        except Exception as e:
            logger.error("Error reading cifs information")
            logger.error(e)
            exit(1)
        self.usrLst = self.userList()

    def __del__(self):
        del self.usrLst

    def available(self):
        return self.usrmgt

    def list(self):
        return self.usrLst

    def exists(self, user):
        retval = False

        if user:
            for usr in self.usrLst:
                if usr['user'] == user:
                    retval = True
                    break

        return retval

    def add(self, user, password, fullname, comment):
        retval = False

        if user and password:
            if self.exists(user):
                self.logger.error("Trying to add an existing user")
            else:
                pwdstr = "{}\n{}\n".format(password, password)
                if fullname:
                    fnstr = ' -f "{}"'.format(fullname)
                else:
                    fnstr = ""
                if comment:
                    cmtstr = ' -N "{}"'.format(comment)
                else:
                    cmtstr = ""
                cmd = "{} -a -t{}{} -u {}".format(PDBEDITEXEC, fnstr, cmtstr, user)
                print(cmd)
                try:
                    shell().command(cmd, input = pwdstr)
                    retval = True
                except:
                    pass
                print(retval)
        return retval

    def modify(self, user, password, fullname, comment):
        retval = False

        if user:
            if not self.exists(user):
                self.logger.error("Trying to modify an unexisting user")
            else:
                pwdstr = "{}\n{}\n".format(password, password)
                if fullname:
                    fnstr = ' -f "{}"'.format(fullname)
                else:
                    fnstr = ""
                if comment:
                    cmtstr = ' -N "{}"'.format(comment)
                else:
                    cmtstr = ""
                cmd = "{} -r{}{} -u {}".format(PDBEDITEXEC, fnstr, cmtstr, user)
                cmd2 = "{} -s {}".format(SMBPASSEXEC, user)
                try:
                    shell().command(cmd)
                    if password:
                        shell().command(cmd2, input = pwdstr)
                    retval = True
                except:
                    pass

        return retval

    def delete(self, user):
        retval = False

        if user:
            if not self.exists(user):
                self.logger.error("Trying to delete an unexisting user")
            else:
                cmd = "{} -x -u {}".format(PDBEDITEXEC, user)
                try:
                    shell().command(cmd)
                    retval = True
                except:
                    pass

        return retval

################## INTERNAL FUNCTIONS ###################

    def checkInstalled(self):
        smbPassCmd = "{} -h".format(SMBPASSEXEC)
        return shell().commandExists(PDBEDITEXEC) and shell().commandExists(smbPassCmd)

    def userList(self):
        userlst = []

        cmd = "{} -L".format(PDBEDITEXEC)
        try:
            lines = shell().command(cmd).splitlines()
            for line in lines:
                usrItem = {}
                parts = line.split(":")
                if len(parts) > 1:
                    usrItem['user'] = parts[0]
                    usrItem['id'] = parts[1]
                    if len(parts) > 2:
                        usrItem['fullname'] = parts[2]
                    else:
                        usrItem['fullname'] = ""
                    userlst.append(usrItem)
        except:
            pass

        return userlst

######################### MAIN ##########################
if __name__ == "__main__":
    pass
