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

    def avl(self):
        linuxUsers = self.getLinuxUsers()
        for linuxUser in linuxUsers:
            for usr in self.usrLst:
                linuxUser['cifs'] = False
                if (usr['user'] == linuxUser['user']) and (usr['id'] == linuxUser['id']):
                    linuxUser['cifs'] = True
                    break
        return linuxUsers

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
                try:
                    shell().command(cmd, input = pwdstr)
                    retval = True
                except:
                    pass
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

    def getLinuxUsers(self):
        #only lists normal users
        cmd = "grep -E '^UID_MIN|^UID_MAX' /etc/login.defs"
        lines = []
        try:
            lines = shell().command(cmd).splitlines()
        except:
            pass
        uidsel = {}
        for line in lines:
            try:
                l = line.split()
                uidsel[l[0]]=int(l[1])
            except:
                pass
        if not 'UID_MIN' in uidsel:
            uidsel['UID_MIN'] = 1000
        if not 'UID_MAX' in uidsel:
            uidsel['UID_MAX'] = 60000

        cmd = "cat /etc/passwd"
        lines = []
        try:
            lines = shell().command(cmd).splitlines()
        except:
            pass
        users = []
        for line in lines:
            l = line.split(":")
            try:
                uid = int(l[2])
                if (uid >= uidsel['UID_MIN']) and (uid <= uidsel['UID_MAX']):
                    user = {}
                    user['user'] = l[0]
                    user['id'] = l[2]
                    try:
                        user['fullname'] = l[4].replace(",","")
                    except:
                        user['fullname'] = ""
                    users.append(user)
            except:
                pass

        return users

######################### MAIN ##########################
if __name__ == "__main__":
    pass
