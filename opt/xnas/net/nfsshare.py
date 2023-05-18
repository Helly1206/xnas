# -*- coding: utf-8 -*-
#########################################################
# SERVICE : nfsshare.py                                 #
#           netshare nfs specific implementation        #
#           for xnas                                    #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import shutil
from copy import deepcopy
from common.shell import shell
from common.params import param,params
from common.systemdctl import systemdctl
from common.ini import ini
from common.ip import ip
#########################################################

####################### GLOBALS #########################
NFSEXEC      = "rpc.nfsd"
RELOADCONFIG = "exportfs -ra"
INSTALL      = "nfs-kernel-server"
DAEMONEXEC   = INSTALL
DEFAULTSFILE = "/etc/default/" + INSTALL
CONFIGFILE   = "/etc/exports"
CONFIGFILEBU = CONFIGFILE + ".bak"
COMMENT      = '#'
OPTIONSTART  = '('
OPTIONEND    = ')'
LINENOEXIST  = -1
DEFAULTOPTIONS = ["rw","fsid=0","root_squash","no_subtree_check","hide"]
#########################################################

###################### FUNCTIONS ########################

class CfgNfs(params):
    RPCNFSDCOUNT    = param('RPCNFSDCOUNT','8') # Cfg
    RPCNFSDPRIORITY = param('RPCNFSDPRIORITY','0')
    RPCMOUNTDOPTS   = param('RPCMOUNTDOPTS','"--manage-gids"')
    NEED_SVCGSSD    = param('NEED_SVCGSSD','')
    RPCSVCGSSDOPTS  = param('RPCSVCGSSDOPTS','')

#########################################################

#########################################################
# Class : nfsshare                                      #
#########################################################
class nfsshare(object):
    def __init__(self, logger, engine, backup = True):
        self.logger = logger
        self.engine = engine
        self.backup = backup
        self.nfsShare = False
        self.exports = {}
        try:
            self.nfsShare = self.checkInstalled()
        except Exception as e:
            logger.error("Error reading nfs information")
            logger.error(e)
            exit(1)
        try:
            self.readExports()
        except Exception as e:
            self.logger.error("Error reading config file: {}".format(CONFIGFILE))
            self.logger.error(e)
            exit(1)

    def __del__(self):
        del self.exports

    def available(self):
        return self.nfsShare

    def installName(self):
        return INSTALL

    def restart(self):
        retval = False
        if self.available():
            ctl = systemdctl(self.logger)
            if ctl.available():
                retval = ctl.restart(DAEMONEXEC)
            else:
                self.logger.error("Error restarting nfs service")
                self.logger.info("Reason: systemd unavailable on your distro")
                self.logger.info("xnas cannot automatically restart the nfs service")
                self.logger.info("You can try it yourself using a command like 'service {} restart'".format(DAEMONEXEC))
            del ctl
        return retval

    def config(self):
        retval = False

        if self.engine.hasSetting(self.engine.settings, 'settings'):
            retval = self.settingsConfig()
        else:
            if self.engine.hasSetting(self.engine.settings, 'enable'):
                self.enable(self.engine.toBool(self.engine.settings['enable']))

            cfg = ini(self.logger, DEFAULTSFILE, backup = self.backup, shellStyle = True)

            if self.engine.hasSetting(self.engine.settings, 'clear'):
                if self.engine.toBool(self.engine.settings['clear']):
                    cfg.clearIni()

            cfg.setDefaultSection("", CfgNfs.todict())

            if self.engine.hasSetting(self.engine.settings, 'servers'):
                cfg.set("", CfgNfs.RPCNFSDCOUNT.key, self.engine.settings['servers'])

            retval = cfg.update()
            del cfg

            if retval:
                self.reloadConfig()

        return retval

    def homes(self):
        # homes not applicable for nfs
        return True

    def users(self, cmd):
        # users not applicable for nfs
        return True

    def privileges(self, name):
        # privileges not applicable for nfs
        return True

    def addfss(self, name):
        retval = False
        if self.engine.hasSetting(self.engine.settings, 'settings'):
            retval = self.settingsShare(name)
        elif self.available():
            newExport = False
            export = self.getExportsLine(self.engine.shareDir(name))
            if not export: #new export
                self.exports.update(self.addExport(self.engine.shareDir(name), "", DEFAULTOPTIONS, enabled = True, line = LINENOEXIST, changed = True))
                export = self.getExportsLine(self.engine.shareDir(name))
                newExport = True

            if export:
                if self.engine.hasSetting(self.engine.settings, 'client'):
                    if ip().isIpMask(self.engine.settings['client']):
                        export['client'] = ip().ipMask(self.engine.settings['client'])
                        export['changed'] = True
                    elif ip().isIp(self.engine.settings['client']):
                        export['client'] = ip().mask(24, self.engine.settings['client'])
                        export['changed'] = True
                    elif ip().isMaskOnly(self.engine.settings['client']):
                        export['client'] = ip().mask(ip().getMask(self.engine.settings['client']))
                        export['changed'] = True
                    elif newExport:
                        self.logger.error("Incorrect IP format, default IP used")
                        export['client'] = ip().mask(24)
                        export['changed'] = True
                    else:
                        self.logger.error("Incorrect IP format, IP not changed")
                elif newExport:
                    export['client'] = ip().mask(24)
                    export['changed'] = True

                if self.engine.hasSetting(self.engine.settings, 'readonly'):
                    if self.engine.toBool(self.engine.settings['readonly']) and not 'ro' in export['options']:
                        try:
                            export['options'].remove("rw")
                        except:
                            pass
                        export['options'].insert(0,"ro")
                        export['changed'] = True
                    if not self.engine.toBool(self.engine.settings['readonly']) and not 'rw' in export['options']:
                        try:
                            export['options'].remove("ro")
                        except:
                            pass
                        export['options'].insert(0,"rw")
                        export['changed'] = True

                if self.engine.hasSetting(self.engine.settings, 'extraoptions'):
                    if self.engine.settings['extraoptions']:
                        export['options'].extend(self.engine.settings['extraoptions'].split(','))
                        export['changed'] = True

            retval = self.writeExports()

        if retval:
            self.reloadConfig()

        return retval

    def delfss(self, name):
        retval = False

        export = self.getExportsLine(self.engine.shareDir(name))
        if export:
            export['removed'] = True
            export['changed'] = True
            retval = self.writeExports()

        if retval:
            self.reloadConfig()

        return retval

    def ena(self, name):
        retval = False

        export = self.getExportsLine(self.engine.shareDir(name))
        if export:
            if not export['enabled']:
                export['enabled'] = True
                export['changed'] = True
                retval = self.writeExports()

        if retval:
            self.reloadConfig()

        return retval

    def dis(self, name):
        retval = False

        export = self.getExportsLine(self.engine.shareDir(name))
        if export:
            if export['enabled']:
                export['enabled'] = False
                export['changed'] = True
                retval = self.writeExports()

        if retval:
            self.reloadConfig()

        return retval

    def getAccess(self, name):
        access = []

        export = self.getExportsLine(self.engine.shareDir(name))
        if export:
            read_only = "ro" in export["options"]

        if read_only:
            access.append('readonly')
        else:
            access.append('read/write')

        return ','.join(access)

    def findShare(self, name):
        retval = True if self.getExportsLine(self.engine.shareDir(name)) else False

        return retval

    def getHomes(self):
        return []

################## INTERNAL FUNCTIONS ###################

    def checkInstalled(self):
        return shell().commandExists(NFSEXEC)

    def reloadConfig(self):
        retval = False
        try:
            shell().command(RELOADCONFIG)
            retval = True
        except:
            pass
        return retval

    def enable(self, ena = True):
        retval = False
        if self.available():
            ctl = systemdctl(self.logger)
            if ctl.available():
                if ena:
                    retval = ctl.enable(DAEMONEXEC)
                    if retval:
                        retval = ctl.start(DAEMONEXEC)
                else:
                    retval = ctl.stop(DAEMONEXEC)
                    if retval:
                        retval = ctl.disable(DAEMONEXEC)
            else:
                self.logger.error("Error enabling/ disabling nfs service")
                self.logger.info("Reason: systemd unavailable on your distro")
                self.logger.info("xnas cannot automatically enable/ disable the nfs service")
                self.logger.info("You can try it yourself using a command like 'service {} enable'".format(DAEMONEXEC))
            del ctl
        return retval

    def getExportsLine(self, share):
        export = {}
        for key, val in self.exports.items():
            if key == share:
                export = val
                break
        return export

    def readExports(self):
        self.exports = {}
        linenr = 0
        if self.available():
            with open(CONFIGFILE, "rt") as fp:
                for line in fp:
                    self.exports.update(self.parseExportsLine(line, linenr))
                    linenr += 1

    def writeExports(self, reRead = False):
        retval = False
        if self.changed():
            if self.backup:
                self.backupExports()

            with open(CONFIGFILE, "rt") as fp:
                lines = fp.readlines()
            #cycle through the dict and execute modifications
            offset = 0
            insertline = 0

            for key, val in self.exports.items():
                if val['line'] >= 0:
                    insertline = val['line'] + 1
                if val['changed']: # If not changed, do nothing
                    if val['removed']:
                        lines.pop(val['line'] + offset)
                        offset -= 1
                    elif val['line'] == LINENOEXIST:
                        lines.insert(insertline + offset, self.export2line(key, val))
                        offset += 1
                    else:
                        lines[val['line'] + offset] = self.export2line(key, val)

            with open(CONFIGFILE, "wt") as fp:
                fp.writelines(lines)
                retval = True
            #reread file afterwards if required
            if reRead:
               self.readExports()
        return retval

    def parseExportsLine(self, line, linenr):
        export = {}
        valid = False
        enabled = True
        share = ""
        client = ""
        options = ""
        line = line.strip()

        #/srv/nfs4/homes  gss/krb5i(rw,sync,no_subtree_check)
        if COMMENT in line[0]:
            enabled = False
            line = line[1:].strip()

        line = line.replace('\t', ' ')
        line = ' '.join(line.split())
        linelist = line.split()

        if len(linelist) > 1:
            if os.path.isdir(linelist[0]):
                share = linelist[0]
                osta = linelist[1].find(OPTIONSTART)
                oend = linelist[1].find(OPTIONEND)
                if osta >= 1 and oend > osta:
                    client = linelist[1][0:osta].strip()
                    options = linelist[1][osta+1:oend].replace(' ', '').split(',')
                    valid = True
                else: # no options
                    if len(linelist[1]):
                        client = linelist[1].strip()
                        valid = True

        if valid:
            export = self.addExport(share, client, options, enabled, linenr)

        return export

    def addExport(self, share, client, options, enabled = True, line = LINENOEXIST, changed = False):
        export = {}
        exportcontent = {}
        exportcontent["client"] = client
        exportcontent["options"] = options
        exportcontent["enabled"] = enabled
        exportcontent['line'] = line
        exportcontent['removed'] = False
        exportcontent['changed'] = changed
        export[share] = exportcontent
        return export

    def export2line(self, share, val):
        optstr = ""
        cmtstr = ""
        if not val['enabled']:
            cmtstr=COMMENT
        if val['options']:
            optstr = "{}{}{}".format(OPTIONSTART, ','.join(val['options']), OPTIONEND)
        return "{}{} {}{}\n".format(cmtstr, share, val['client'], optstr)

    def changed(self):
        retval = False
        for key, val in self.exports.items():
            if val['changed']:
                retval = True
                break
        return retval

    def backupExports(self):
        if os.path.isfile(CONFIGFILE):
            shutil.copy2(CONFIGFILE, CONFIGFILEBU)

    def settingsConfig(self):
        settings = {}

        if self.available():
            ctl = systemdctl(self.logger)
            if ctl.available():
                settings['enable'] = ctl.isEnabled(DAEMONEXEC)
            else:
                settings['enable'] = False
            del ctl

            cfg = ini(self.logger, DEFAULTSFILE, backup = self.backup, shellStyle = True)
            settings["servers"] = cfg.get("", CfgNfs.RPCNFSDCOUNT.key)
            del cfg

        return settings

    def settingsShare(self, name):
        settings = {}

        if self.available():
            export = self.getExportsLine(self.engine.shareDir(name))

            if export:
                settings['client'] = export['client']
                settings['readonly'] = "ro" in export['options']
                extraoptions = deepcopy(export['options'])
                try:
                    extraoptions.remove('ro')
                except:
                    pass
                try:
                    extraoptions.remove('rw')
                except:
                    pass
                for opt in DEFAULTOPTIONS:
                    if opt in extraoptions:
                        extraoptions.remove(opt)
                settings['extraoptions'] = ','.join(extraoptions)
        return settings

######################### MAIN ##########################
if __name__ == "__main__":
    pass
