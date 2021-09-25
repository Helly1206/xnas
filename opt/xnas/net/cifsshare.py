# -*- coding: utf-8 -*-
#########################################################
# SERVICE : cifsshare.py                                #
#           netshare cifs specific implementation       #
#           for xnas                                    #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
from common.shell import shell
from common.params import param,params
from common.systemdctl import systemdctl
from common.ini import ini
from common.stdin import stdin
from net.cifsusrmgt import cifsusrmgt
from common.xnas_engine import groups
#########################################################

####################### GLOBALS #########################
DAEMONEXEC   = "smbd"
DAEMONEXEC2  = "nmbd"
RELOADCONFIG = "smbcontrol all reload-config"
INSTALL      = "samba"
CONFIGFILE   = "/etc/samba/smb.conf"
HOMESSECT    = "homes"
GLOBALSECT   = "global"

#########################################################

###################### FUNCTIONS ########################

class CfgCifs(params):
    workgroup             = param('workgroup','WORKGROUP') # Cfg
    server_string         = param('server string','%h server') # Cfg
    dns_proxy             = param('dns proxy','no')
    log_level             = param('log level','0') # Cfg
    logging               = param('logging', 'file')
    #syslog                = param('syslog','0') # Cfg log_level
    log_file              = param('log file','/var/log/samba/log.%m')
    max_log_size          = param('max log size','1000')
    #syslog_only           = param('syslog only','yes')
    panic_action          = param('panic action','/usr/share/samba/panic-action %d')
    #encrypt_passwords     = param('encrypt passwords','true')
    passdb_backend        = param('passdb backend','tdbsam')
    obey_pam_restrictions = param('obey pam restrictions','no')
    unix_password_sync    = param('unix password sync','no')
    passwd_program        = param('passwd program','/usr/bin/passwd %u')
    passwd_chat           = param('passwd chat','*Enter\snew\s*\spassword:* %n\\n *Retype\snew\s*\spassword:* %n\\n *password\supdated\ssuccessfully* .')
    pam_password_change   = param('pam password change','yes')
    socket_options        = param('socket options','TCP_NODELAY IPTOS_LOWDELAY')
    guest_account         = param('guest account','nobody')
    load_printers         = param('load printers','no')
    disable_spoolss       = param('disable spoolss','yes')
    printing              = param('printing','bsd')
    printcap_name         = param('printcap name','/dev/null')
    unix_extensions       = param('unix extensions','yes')
    wide_links            = param('wide links','no')
    create_mask           = param('create mask','0777')
    directory_mask        = param('directory mask','0777')
    map_to_guest          = param('map to guest','Bad User') # Cfg check shares guest allowed, if it is, remove
    use_sendfile          = param('use sendfile','yes') # Cfg
    aio_read_size         = param('aio read size','16384') # Cfg aio, otherwise remove
    aio_write_size        = param('aio write size','16384') # Cfg aio, otherwise remove
    local_master          = param('local master','yes') # Cfg
    time_server           = param('time server','no') # Cfg
    wins_support          = param('wins support','no') # Cfg
    wins_server           = param('wins server',None) #"" # Cfg, if not set, remove
    extraoptions          = param('extraoptions',None) #"" # Cfg, if extra options, add

class HomesCifs(params):
    comment              = param('comment','Home directories')
    browseable           = param('browseable','yes') # Cfg
    writable             = param('writable','yes') # Cfg
    create_mask          = param('create mask','0600')
    force_create_mode    = param('force create mode','0600')
    directory_mask       = param('directory mask','0700')
    force_directory_mode = param('force directory mode','0700')
    valid_users          = param('valid users','%S')
    hide_special_files   = param('hide special files','yes')
    follow_symlinks      = param('follow symlinks','yes')
    vfs_objects          = param('vfs objects','')
    extraoptions         = param('extraoptions',None) #Cfg

class ShareCifs(params):
    comment              = param('comment',None) # Cfg
    path                 = param('path','') #Cfg
    available            = param('available','yes') #Cfg for disable
    guest_ok             = param('guest ok','no') #Cfg
    guest_only           = param('guest only','no') #Cfg
    read_only            = param('read only','no') #Cfg
    browseable           = param('browseable','yes') #Cfg
    inherit_acls         = param('inherit acls','yes') #Cfg
    inherit_permissions  = param('inherit permissions','no') #Cfg
    ea_support           = param('ea support','no') #Cfg
    store_dos_attributes = param('store dos attributes','no') #Cfg
    vfs_objects          = param('vfs objects','') #Cfg (see vfs objects)
    printable            = param('printable','no')
    create_mask          = param('create mask','0664')
    force_create_mode    = param('force create mode','0664')
    directory_mask       = param('directory mask','0775')
    force_directory_mode = param('force directory mode','0775')
    hide_special_files   = param('hide special files','yes')
    follow_symlinks      = param('follow symlinks','yes')
    hosts_allow          = param('hosts allow',None) #Cfg
    hosts_deny           = param('hosts deny',None) #Cfg
    hide_dot_files       = param('hide dot files','yes') #Cfg
    valid_users          = param('valid users',None) #Cfg
    invalid_users        = param('invalid users',None) #Cfg
    read_list            = param('read list',None) #Cfg
    write_list           = param('write list',None) #Cfg
    extraoptions         = param('extraoptions',None) #Cfg

class VfsRecycleCifs(params):
    vfs_object     = param('vfs objects','recycle')
    repository     = param('repository','.recycle/%U')
    keeptree       = param('keeptree','yes')
    versions       = param('versions','yes')
    touch          = param('touch','yes')
    directory_mode = param('directory_mode','0777')
    subdir_mode    = param('subdir_mode','0700')
    exclude        = param('exclude','')
    exclude_dir    = param('exclude_dir','')
    maxsize        = param('maxsize','0') #Cfg

class VfsFullAuditCifs(params):
    vfs_object = param('vfs objects','full_audit')
    prefix     = param('prefix','%u|%I|%m|%P|%S')
    success    = param('success','mkdir rename unlink rmdir pwrite')
    failure    = param('failure','none')
    facility   = param('facility','local7')
    priority   = param('priority','NOTICE')

#########################################################

#########################################################
# Class : cifsshare                                     #
#########################################################
class cifsshare(object):
    def __init__(self, logger, engine, backup = True):
        self.logger = logger
        self.engine = engine
        self.backup = backup
        self.cifsShare = False
        self.cfg = {}
        try:
            self.cifsShare = self.checkInstalled()
        except Exception as e:
            logger.error("Error reading cifs information")
            logger.error(e)
            exit(1)
        try:
            if self.cifsShare:
                self.cfg = ini(self.logger, CONFIGFILE)
        except Exception as e:
            self.logger.error("Error reading config file: {}".format(CONFIGFILE))
            self.logger.error(e)
            exit(1)

    def __del__(self):
        del self.cfg

    def available(self):
        return self.cifsShare

    def installName(self):
        return INSTALL

    def restart(self):
        retval = False
        if self.available():
            ctl = systemdctl(self.logger)
            if ctl.available():
                retval = ctl.restart(DAEMONEXEC)
                if retval:
                    retval = ctl.restart(DAEMONEXEC2)
            else:
                self.logger.error("Error restarting cifs service")
                self.logger.info("Reason: systemd unavailable on your distro")
                self.logger.info("xnas cannot automatically restart the cifs service")
                self.logger.info("You can try it yourself using a command like 'service {} restart'".format(DAEMONEXEC))
                self.logger.info("and 'service {} restart'".format(DAEMONEXEC2))
            del ctl
        return retval

    def config(self):
        retval = False
        if self.engine.hasSetting(self.engine.settings, 'settings'):
            retval = self.settingsConfig()
        elif self.available():
            if self.engine.hasSetting(self.engine.settings, 'enable'):
                self.enable(self.engine.toBool(self.engine.settings['enable']))

            if self.engine.hasSetting(self.engine.settings, 'clear'):
                if self.engine.toBool(self.engine.settings['clear']):
                    self.cfg.clearIni()

            self.cfg.setDefaultSection(GLOBALSECT, CfgCifs.todict())

            if self.engine.hasSetting(self.engine.settings, 'workgroup'):
                self.cfg.set(GLOBALSECT, CfgCifs.workgroup.key, self.engine.settings['workgroup'])

            if self.engine.hasSetting(self.engine.settings, 'serverstring'):
                self.cfg.set(GLOBALSECT, CfgCifs.server_string.key, self.engine.settings['serverstring'])

            if self.engine.hasSetting(self.engine.settings, 'loglevel'):
                self.cfg.set(GLOBALSECT, CfgCifs.log_level.key, str(self.engine.toInt(self.engine.settings['loglevel'])))
            #    self.cfg.set(GLOBALSECT, CfgCifs.syslog.key, str(self.engine.toInt(self.engine.settings['loglevel'])))

            self.cfgMapToGuest()

            if self.engine.hasSetting(self.engine.settings, 'sendfile'):
                self.cfg.set(GLOBALSECT, CfgCifs.use_sendfile.key, CfgCifs.yn(self.engine.toBool(self.engine.settings['sendfile'])))

            if self.engine.hasSetting(self.engine.settings, 'aio'):
                if self.engine.toBool(self.engine.settings['aio']):
                    self.cfg.setDefault(GLOBALSECT, CfgCifs.aio_read_size.key, CfgCifs.aio_read_size.value)
                    self.cfg.setDefault(GLOBALSECT, CfgCifs.aio_write_size.key, CfgCifs.aio_write_size.value)
                else:
                    self.cfg.remove(GLOBALSECT, CfgCifs.aio_read_size.key)
                    self.cfg.remove(GLOBALSECT, CfgCifs.aio_write_size.key)

            if self.engine.hasSetting(self.engine.settings, 'localmaster'):
                self.cfg.set(GLOBALSECT, CfgCifs.local_master.key, CfgCifs.yn(self.engine.toBool(self.engine.settings['localmaster'])))

            if self.engine.hasSetting(self.engine.settings, 'timeserver'):
                self.cfg.set(GLOBALSECT, CfgCifs.time_server.key, CfgCifs.yn(self.engine.toBool(self.engine.settings['timeserver'])))

            if self.engine.hasSetting(self.engine.settings, 'winssupport'):
                self.cfg.set(GLOBALSECT, CfgCifs.wins_support.key, CfgCifs.yn(self.engine.toBool(self.engine.settings['winssupport'])))

            if self.engine.hasSetting(self.engine.settings, 'winsserver'):
                if self.engine.settings['winsserver']:
                    self.cfg.set(GLOBALSECT, CfgCifs.wins_server.key, self.engine.settings['winsserver'])
                else:
                    self.cfg.remove(GLOBALSECT, CfgCifs.wins_server.key)

            if self.engine.hasSetting(self.engine.settings, 'extraoptions'):
                opt = self.engine.parseJSONStr(self.engine.settings['extraoptions'])
                if opt and isinstance(opt, dict):
                    for key, val in opt:
                        self.cfg.set(GLOBALSECT, key, CfgCifs.anyyn(val))

            retval = self.cfg.update()

            if retval:
                self.reloadConfig()
        return retval

    def homes(self):
        retval = False
        if self.engine.hasSetting(self.engine.settings, 'settings'):
            retval = self.settingsHomes()
        elif self.available():
            if not self.engine.hasSetting(self.engine.settings, 'enable'):
                # always enable if not disabled
                self.cfg.setDefaultSection(HOMESSECT, HomesCifs.todict())
            else:
                if self.engine.toBool(self.engine.settings['enable']):
                    self.cfg.setDefaultSection(HOMESSECT, HomesCifs.todict())
                else:
                    self.cfg.removeSection(HOMESSECT)

            if self.cfg.getSection(HOMESSECT): #Only update settings when enabled
                if self.engine.hasSetting(self.engine.settings, 'browseable'):
                    self.cfg.set(HOMESSECT, HomesCifs.browseable.key, HomesCifs.yn(self.engine.toBool(self.engine.settings['browseable'])))

                if self.engine.hasSetting(self.engine.settings, 'writable'):
                    self.cfg.set(HOMESSECT, HomesCifs.writable.key, HomesCifs.yn(self.engine.toBool(self.engine.settings['writable'])))

                if self.engine.hasSetting(self.engine.settings, 'extraoptions'):
                    opt = self.engine.parseJSONStr(self.engine.settings['extraoptions'])
                    if opt and isinstance(opt, dict):
                        for key, val in opt:
                            self.cfg.set(HOMESSECT, key, HomesCifs.anyyn(val))

            retval = self.cfg.update()

            if retval:
                self.reloadConfig()

        return retval

    def users(self, cmd):
        retval = False
        user = ""
        fullname = ""
        comment = ""
        password = ""
        usrmgt = cifsusrmgt(self.logger)

        if usrmgt.available():
            if self.engine.hasSetting(self.engine.settings, 'username'):
                user = self.engine.settings['username']
            if self.engine.hasSetting(self.engine.settings, 'fullname'):
                fullname = self.engine.settings['fullname']
            if self.engine.hasSetting(self.engine.settings, 'comment'):
                comment = self.engine.settings['comment']

            if cmd.lower() == "list":
                retval = usrmgt.list()
            elif cmd.lower() == "avl":
                retval = usrmgt.avl()
            elif user:
                if cmd.lower() == "exists":
                    retval = usrmgt.exists(user)
                elif cmd.lower() == "add":
                    if not usrmgt.exists(user):
                        self.logger.info("{}: User does not exist, add user".format(user))
                        if self.engine.hasSetting(self.engine.settings, 'password'):
                            if self.engine.settings['password']:
                                password = self.engine.settings['password']
                            else:
                                password = self.setPassword()
                        else:
                            password = self.setPassword()
                        retval = usrmgt.add(user, password, fullname, comment)
                    else:
                        self.logger.info("{}: User already exists, modifying user".format(user))
                        if self.engine.hasSetting(self.engine.settings, 'password'):
                            if self.engine.settings['password']:
                                password = self.engine.settings['password']
                            else:
                                password = self.setPassword()
                        retval = usrmgt.modify(user, password, fullname, comment)
                elif cmd.lower() == "del":
                    retval = usrmgt.delete(user)
                else:
                    self.engine.parseError("Incorrect argument entered for usr command")
        else:
            self.logger.error("Netshare is of type cifs, but this type is not correctly installed")
            self.logger.error("User management cannot be executed")
            self.logger.info("Please re-install cifs on your distro (if available) and try again")
            self.logger.info("Common package to install on most distros: '{}'".format(self.installName()))
            exit(1)

        del usrmgt

        if not retval and (cmd.lower() == "add" or cmd.lower() == "del"):
            self.logger.error("Error managing users")

        return retval

    def privileges(self, name):
        retval = False
        privList = self.getPriv(name)
        if self.engine.hasSetting(self.engine.settings, 'list'):
            retval = privList
        else:
            if self.engine.hasSetting(self.engine.settings, 'username'):
                user = self.engine.settings['username']
            else:
                user = "guest"
            invalid = self.engine.hasSetting(self.engine.settings, 'invalid')
            if invalid:
                invalid = self.engine.toBool(self.engine.settings['invalid'])
            readonly = self.engine.hasSetting(self.engine.settings, 'readonly')
            if readonly:
                readonly = self.engine.toBool(self.engine.settings['readonly'])
            delete = self.engine.hasSetting(self.engine.settings, 'delete')
            if delete:
                delete = self.engine.toBool(self.engine.settings['delete'])

            self.updatePriv(name, privList, user, invalid, readonly, delete)
            retval = self.setPriv(name, privList)

            if not retval:
                self.logger.error("Error setting privileges")

        return retval

    def addfss(self, name):
        retval = False
        if self.engine.hasSetting(self.engine.settings, 'settings'):
            retval = self.settingsShare(name)
        elif self.available():
            # Don't care if share already exists, always add default and then check for specific options
            self.cfg.setDefaultSection(name, ShareCifs.todict())
            self.cfg.set(name, ShareCifs.path.key, self.engine.shareDir(name))

            # Always enable
            enabled = ShareCifs.bl(self.cfg.get(name, ShareCifs.available.key))
            if enabled and not ShareCifs.bl(enabled):
                self.cfg.set(name, ShareCifs.available.key, ShareCifs.yn(True))

            if self.engine.hasSetting(self.engine.settings, 'comment'):
                if self.engine.settings['comment']:
                    self.cfg.set(name, ShareCifs.comment.key, self.engine.settings['comment'])
                else:
                    self.cfg.remove(name, ShareCifs.comment.key)

            if self.engine.hasSetting(self.engine.settings, 'guest'):
                if self.engine.settings['guest'].lower().strip() == "no":
                    self.cfg.set(name, ShareCifs.guest_ok.key, ShareCifs.yn(False))
                    self.cfg.set(name, ShareCifs.guest_only.key, ShareCifs.yn(False))
                elif self.engine.settings['guest'].lower().strip() == "only":
                    self.cfg.set(name, ShareCifs.guest_ok.key, ShareCifs.yn(True))
                    self.cfg.set(name, ShareCifs.guest_only.key, ShareCifs.yn(True))
                else: #allow
                    self.cfg.set(name, ShareCifs.guest_ok.key, ShareCifs.yn(True))
                    self.cfg.set(name, ShareCifs.guest_only.key, ShareCifs.yn(False))

            if self.engine.hasSetting(self.engine.settings, 'readonly'):
                self.cfg.set(name, ShareCifs.read_only.key, HomesCifs.yn(self.engine.toBool(self.engine.settings['readonly'])))

            if self.engine.hasSetting(self.engine.settings, 'browseable'):
                self.cfg.set(name, ShareCifs.browseable.key, HomesCifs.yn(self.engine.toBool(self.engine.settings['browseable'])))

            if self.engine.hasSetting(self.engine.settings, 'hidedotfiles'):
                self.cfg.set(name, ShareCifs.hide_dot_files.key, HomesCifs.yn(self.engine.toBool(self.engine.settings['hidedotfiles'])))

            if self.engine.hasSetting(self.engine.settings, 'inheritacls'):
                self.cfg.set(name, ShareCifs.inherit_acls.key, HomesCifs.yn(self.engine.toBool(self.engine.settings['inheritacls'])))

            if self.engine.hasSetting(self.engine.settings, 'inheritpermissions'):
                self.cfg.set(name, ShareCifs.inherit_permissions.key, HomesCifs.yn(self.engine.toBool(self.engine.settings['inheritpermissions'])))

            if self.engine.hasSetting(self.engine.settings, 'easupport'):
                self.cfg.set(name, ShareCifs.ea_support.key, HomesCifs.yn(self.engine.toBool(self.engine.settings['easupport'])))

            if self.engine.hasSetting(self.engine.settings, 'storedosattr'):
                self.cfg.set(name, ShareCifs.store_dos_attributes.key, HomesCifs.yn(self.engine.toBool(self.engine.settings['storedosattr'])))

            if self.engine.hasSetting(self.engine.settings, 'hostsallow'):
                if self.engine.settings['hostsallow']:
                    self.cfg.set(name, ShareCifs.hosts_allow.key, self.engine.settings['hostsallow'])
                else:
                    self.cfg.remove(name, ShareCifs.hosts_allow.key)

            if self.engine.hasSetting(self.engine.settings, 'hostsdeny'):
                if self.engine.settings['hostsdeny']:
                    self.cfg.set(name, ShareCifs.hosts_deny.key, self.engine.settings['hostsdeny'])
                else:
                    self.cfg.remove(name, ShareCifs.hosts_deny.key)

            if self.engine.hasSetting(self.engine.settings, 'extraoptions'):
                opt = self.engine.parseJSONStr(self.engine.settings['extraoptions'])
                if opt and isinstance(opt, dict):
                    for key, val in opt:
                        self.cfg.set(name, key, ShareCifs.anyyn(val))

            #    valid_users          = param('valid users',None) #Cfg
            #    invalid_users        = param('invalid users',None) #Cfg
            #    write_list           = param('write list',None) #Cfg, implemented in users/ priv

            vfs_objects = self.getVfsObjects(name)
            if self.engine.hasSetting(self.engine.settings, 'recyclebin'):
                if self.engine.toBool(self.engine.settings['recyclebin']):
                    vfsdict = VfsRecycleCifs.todict()
                    vfsdict.pop(VfsRecycleCifs.vfs_object.key)
                    self.cfg.setDefaultObject(name, VfsRecycleCifs.vfs_object.value, vfsdict)

                    if self.engine.hasSetting(self.engine.settings, 'recyclemaxsize'):
                        self.cfg.set(name, VfsRecycleCifs.maxsize.key, str(self.engine.toInt(self.engine.settings['recyclemaxsize'])), VfsRecycleCifs.vfs_object.value)
                    # "recyclemaxage": "maximum bin age (0 = no max) (default = 0)", Implemented in xservices

                    vfs_objects.append(VfsRecycleCifs.vfs_object.value)
                else:
                    self.cfg.removeObject(name, VfsRecycleCifs.vfs_object.value)
                    try:
                        vfs_objects.remove(VfsRecycleCifs.vfs_object.value)
                    except:
                        pass

            if self.engine.hasSetting(self.engine.settings, 'audit'):
                if self.engine.toBool(self.engine.settings['audit']):
                    vfsdict = VfsFullAuditCifs.todict()
                    vfsdict.pop(VfsFullAuditCifs.vfs_object.key)
                    self.cfg.setDefaultObject(name, VfsFullAuditCifs.vfs_object.value, vfsdict)
                    vfs_objects.append(VfsFullAuditCifs.vfs_object.value)
                else:
                    self.cfg.removeObject(name, VfsFullAuditCifs.vfs_object.value)
                    try:
                        vfs_objects.remove(VfsFullAuditCifs.vfs_object.value)
                    except:
                        pass

            self.cfg.set(name, ShareCifs.vfs_objects.key, ' '.join(vfs_objects))

            self.cfgMapToGuest()
            retval = self.cfg.update()
            if retval:
                self.reloadConfig()

        return retval

    def delfss(self, name):
        retval = False

        if self.available():
            self.cfg.removeSection(name)
            self.cfgMapToGuest()
            retval = self.cfg.update()
            if retval:
                self.reloadConfig()

        return retval

    def ena(self, name):
        retval = False

        if self.available():
            enabled = ShareCifs.bl(self.cfg.get(name, ShareCifs.available.key))
            if enabled and not ShareCifs.bl(enabled):
                self.cfg.set(name, ShareCifs.available.key, ShareCifs.yn(True))

            retval = self.cfg.update()
            if retval:
                self.reloadConfig()

        return retval

    def dis(self, name):
        retval = False

        if self.available():
            enabled = ShareCifs.bl(self.cfg.get(name, ShareCifs.available.key))
            if enabled and ShareCifs.bl(enabled):
                self.cfg.set(name, ShareCifs.available.key, ShareCifs.yn(False))

            retval = self.cfg.update()
            if retval:
                self.reloadConfig()

        return retval

    def getAccess(self, name):
        access = []

        if self.available():
            guest_ok = ShareCifs.bl(self.cfg.get(name, ShareCifs.guest_ok.key))
            guest_only = ShareCifs.bl(self.cfg.get(name, ShareCifs.guest_only.key))
            read_only = ShareCifs.bl(self.cfg.get(name, ShareCifs.read_only.key))
            browseable = ShareCifs.bl(self.cfg.get(name, ShareCifs.browseable.key))

            if guest_only:
                access.append('guest only')
            elif guest_ok:
                access.append('guest ok')
            else:
                access.append('no guest')

            if read_only:
                access.append('readonly')
            else:
                access.append('read/write')

            if browseable:
                access.append('browseable')

        return ','.join(access)

    def findShare(self, name):
        retval = False

        if self.available():
            retval = True if self.cfg.getSection(name) else False

        return retval

    def getHomes(self):
        myHomes =[]
        if self.available():
            if self.cfg.getSection(HOMESSECT): # only if home section
                access = []
                read_only = not HomesCifs.bl(self.cfg.get(HOMESSECT, HomesCifs.writable.key))
                browseable = HomesCifs.bl(self.cfg.get(HOMESSECT, HomesCifs.browseable.key))
                if read_only:
                    access.append('readonly')
                else:
                    access.append('read/write')

                if browseable:
                    access.append('browseable')
                accessstr = ','.join(access)

                usrmgt = cifsusrmgt(self.logger)
                if usrmgt.available():
                    usrLst = usrmgt.list()
                    for usr in usrLst:
                        myHome = {}
                        myHome['xnetshare'] = "(home){}".format(usr['user'])
                        myHome['type'] = "cifs"
                        myHome['access'] = accessstr
                        myHome['enabled'] = True
                        myHome['sourced'] = "N/A"
                        if myHome:
                            myHomes.append(myHome)
                del usrmgt

        return myHomes

    def getRecycleBin(self, name):
        binLoc = ""

        if self.findShare(name):
            vfs_objects = self.getVfsObjects(name)
            if VfsRecycleCifs.vfs_object.value in vfs_objects:
                obj = self.cfg.getObject(name, VfsRecycleCifs.vfs_object.value)
                if obj:
                    relBinLoc = obj[VfsRecycleCifs.repository.key]
                    shareLoc = self.cfg.get(name, ShareCifs.path.key)
                    binLoc = os.path.join(shareLoc, relBinLoc)
                    while '%' in binLoc:
                        binLoc = os.path.split(binLoc)[0]

        return binLoc

################## INTERNAL FUNCTIONS ###################

    def checkInstalled(self):
        return shell().commandExists(DAEMONEXEC) and shell().commandExists(DAEMONEXEC2)

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
                    if retval:
                        retval = ctl.enable(DAEMONEXEC2)
                    if retval:
                        retval = ctl.start(DAEMONEXEC2)
                else:
                    retval = ctl.stop(DAEMONEXEC2)
                    if retval:
                        retval = ctl.disable(DAEMONEXEC2)
                    if retval:
                        retval = ctl.stop(DAEMONEXEC)
                    if retval:
                        retval = ctl.disable(DAEMONEXEC)
            else:
                self.logger.error("Error enabling/ disabling cifs service")
                self.logger.info("Reason: systemd unavailable on your distro")
                self.logger.info("xnas cannot automatically enable/ disable the cifs service")
                self.logger.info("You can try it yourself using a command like 'service {} enable'".format(DAEMONEXEC))
                self.logger.info("and 'service {} enable'".format(DAEMONEXEC2))
            del ctl
        return retval

    def cfgMapToGuest(self):
        retval = False

        for section in self.cfg.getSections():
            allowed = ShareCifs.bl(self.cfg.get(section, ShareCifs.guest_ok.key))
            if allowed and not retval:
                retval = ShareCifs.bl(allowed)

        if retval:
            self.cfg.setDefault(GLOBALSECT, CfgCifs.map_to_guest.key, CfgCifs.map_to_guest.value)
        else:
            self.cfg.remove(GLOBALSECT, CfgCifs.map_to_guest.key)

        return retval

    def setPassword(self):
        password = ""

        stdinput = stdin("", exitevent = None, mutex = None, displaylater = False, background = False)
        print("Please enter password for this user")

        pass1 = stdinput.input("Enter new password: ", echo = False).strip()
        if ord(pass1[0]) == 3: # ^C
            print("^C")
            self.engine.exitSignal()
        else:
            print("")
        pass2 = stdinput.input("Retype new password: ", echo = False).strip()
        if ord(pass2[0]) == 3: # ^C
            print("^C")
            self.engine.exitSignal()
        else:
            print("")
        del stdinput

        if pass1 != pass2:
            self.logger.error("Passwords do not match, exiting ...")
            exit(1)
        else:
            password = pass1

        return password

    def getPriv(self, name):
        privList = []
        valid_users = []
        invalid_users = []
        read_list = []
        write_list = []

        # get user lists
        userlist = self.cfg.get(name, ShareCifs.valid_users.key)
        if userlist:
            valid_users = userlist.split(',')
        userlist = self.cfg.get(name, ShareCifs.invalid_users.key)
        if userlist:
            invalid_users = userlist.split(',')
        userlist = self.cfg.get(name, ShareCifs.read_list.key)
        if userlist:
            read_list = userlist.split(',')
        userlist = self.cfg.get(name, ShareCifs.write_list.key)
        if userlist:
            write_list = userlist.split(',')

        users = sorted(list(set(valid_users + invalid_users + read_list + write_list)))

        for user in users:
            priv = {}
            if user == "nobody":
                userprnt = "guest"
            else:
                userprnt = user
            priv['user'] = userprnt
            priv['invalid'] = user in invalid_users
            priv['readonly'] = user in read_list and not user in write_list
            privList.append(priv)

        return privList

    def setPriv(self, name, privList):
        retval = False

        guest_ok = ShareCifs.bl(self.cfg.get(name, ShareCifs.guest_ok.key)) # no valid/ invalid
        guest_only = ShareCifs.bl(self.cfg.get(name, ShareCifs.guest_only.key)) # nothing
        read_only = ShareCifs.bl(self.cfg.get(name, ShareCifs.read_only.key)) # no write

        valid_users = []
        invalid_users = []
        read_list = []
        write_list = []

        usrmgt = cifsusrmgt(self.logger)

        if not guest_only and usrmgt.available():
            for priv in privList:
                if priv['user'] == "guest":
                    user = "nobody"
                    userOk = guest_ok
                else:
                    user = priv['user']
                    userOk = usrmgt.exists(user)
                if userOk:
                    if not guest_ok:
                        if priv['invalid']:
                            invalid_users.append(user)
                        else:
                            valid_users.append(user)
                    if priv['readonly']:
                        read_list.append(user)
                    elif not read_only:
                        write_list.append(user)

        if valid_users:
            self.cfg.set(name, ShareCifs.valid_users.key, ','.join(valid_users))
        else:
            self.cfg.remove(name, ShareCifs.valid_users.key)
        if invalid_users:
            self.cfg.set(name, ShareCifs.invalid_users.key, ','.join(invalid_users))
        else:
            self.cfg.remove(name, ShareCifs.invalid_users.key)
        if read_list:
            self.cfg.set(name, ShareCifs.read_list.key, ','.join(read_list))
        else:
            self.cfg.remove(name, ShareCifs.read_list.key)
        if write_list:
            self.cfg.set(name, ShareCifs.write_list.key, ','.join(write_list))
        else:
            self.cfg.remove(name, ShareCifs.write_list.key)

        del usrmgt

        retval = self.cfg.update()
        if retval:
            self.reloadConfig()

        return retval

    def updatePriv(self, name, privList, user, invalid, readonly, delete):
        newUser = True
        guest_ok = ShareCifs.bl(self.cfg.get(name, ShareCifs.guest_ok.key)) # no valid/ invalid
        guest_only = ShareCifs.bl(self.cfg.get(name, ShareCifs.guest_only.key)) # nothing
        read_only = ShareCifs.bl(self.cfg.get(name, ShareCifs.read_only.key)) # no write

        invalid_guest = user.lower() == "guest" and not guest_ok

        if guest_only:
            self.logger.info("Privileges are not added/ updated as netshare accepts guests only")
        elif invalid_guest:
            self.logger.info("Privileges are not added/ updated for guest user as guests are not allowed")
        else:
            newPriv = {}
            newPriv['user'] = user
            if not guest_ok:
                newPriv['invalid'] = invalid
            else:
                newPriv['invalid'] = False
                if not delete:
                    self.logger.info("User cannot be invalidated as netshare accepts guests")
            newPriv['readonly'] = readonly
            if not delete and read_only and not readonly:
                self.logger.info("User cannot be given write access as netshare is readonly")

            item = 0
            for priv in privList:
                if priv['user'] == user:
                    newUser = False
                    if delete:
                        self.logger.info("User found, user deleted")
                        privList.pop(item)
                    else:
                        self.logger.info("User found, privileges updated")
                        privList[item] = newPriv
                    break
                item += 1

            if newUser:
                self.logger.info("User cannot be found, new user privileges added")
                privList.append(newPriv)

        return privList

    def settingsHomes(self):
        settings = {}

        if self.available():
            if self.cfg.getSection(HOMESSECT):
                settings['enable'] = True
                settings['browseable'] = HomesCifs.bl(self.cfg.get(HOMESSECT, HomesCifs.browseable.key))
                settings['writable'] = HomesCifs.bl(self.cfg.get(HOMESSECT, HomesCifs.writable.key))

                setopts = [HomesCifs.browseable.key, HomesCifs.writable.key, HomesCifs.extraoptions.key]
                defaults = HomesCifs.todict()
                extraoptions = {}
                for key, val in self.cfg.getSection(HOMESSECT).items():
                    if not key in setopts:
                        if not key in defaults:
                            extraoptions[key] = HomesCifs.anybl(val)
                        elif HomesCifs.anybl(val) != HomesCifs.anybl(defaults[key]):
                            extraoptions[key] = HomesCifs.anybl(val)
                settings['extraoptions'] = extraoptions
            else:
                settings['enable'] = False
                settings['browseable'] = HomesCifs.bl(HomesCifs.browseable)
                settings['writable'] = HomesCifs.bl(HomesCifs.writable)
                settings['extraoptions'] = {}

        return settings

    def settingsConfig(self):
        settings = {}

        if self.available():
            ctl = systemdctl(self.logger)
            if ctl.available():
                settings['enable'] = ctl.isEnabled(DAEMONEXEC)
            else:
                settings['enable'] = False
            del ctl

            settings['workgroup'] = self.cfg.get(GLOBALSECT, CfgCifs.workgroup.key)
            settings['serverstring'] = self.cfg.get(GLOBALSECT, CfgCifs.server_string.key)
            settings['loglevel'] = self.cfg.get(GLOBALSECT, CfgCifs.log_level.key)
            settings['sendfile'] = HomesCifs.bl(self.cfg.get(GLOBALSECT, CfgCifs.use_sendfile.key))
            settings['aio'] = int(self.cfg.get(GLOBALSECT, CfgCifs.aio_read_size.key)) > 0 and int(self.cfg.get(GLOBALSECT, CfgCifs.aio_write_size.key)) > 0
            settings['localmaster'] = HomesCifs.bl(self.cfg.get(GLOBALSECT, CfgCifs.local_master.key))
            settings['timeserver'] = HomesCifs.bl(self.cfg.get(GLOBALSECT, CfgCifs.time_server.key))
            settings['winssupport'] = HomesCifs.bl(self.cfg.get(GLOBALSECT, CfgCifs.wins_support.key))
            settings['winsserver'] = self.cfg.get(GLOBALSECT, CfgCifs.wins_server.key)

            setopts = [CfgCifs.workgroup.key, CfgCifs.server_string.key, CfgCifs.log_level.key, CfgCifs.use_sendfile.key,
                      CfgCifs.local_master.key, CfgCifs.time_server.key, CfgCifs.wins_support.key, CfgCifs.wins_server.key,
                      CfgCifs.map_to_guest.key, CfgCifs.extraoptions.key]
            defaults = CfgCifs.todict()
            extraoptions = {}
            for key, val in self.cfg.getSection(GLOBALSECT).items():
                if not key in setopts:
                    if not key in defaults:
                        extraoptions[key] = CfgCifs.anybl(val)
                    elif CfgCifs.anybl(val) != CfgCifs.anybl(defaults[key]):
                        extraoptions[key] = CfgCifs.anybl(val)
            settings['extraoptions'] = extraoptions
        return settings

    def settingsShare(self, name):
        settings = {}

        if self.available():
            settings['comment'] = self.cfg.get(name, ShareCifs.comment.key)

            settings['guest'] = "no"
            if ShareCifs.bl(self.cfg.get(name, ShareCifs.guest_ok.key)) and ShareCifs.bl(self.cfg.get(name, ShareCifs.guest_only.key)):
                settings['guest'] = "only"
            elif ShareCifs.bl(self.cfg.get(name, ShareCifs.guest_ok.key)) and not ShareCifs.bl(self.cfg.get(name, ShareCifs.guest_only.key)):
                settings['guest'] = "allow"

            settings['readonly'] = ShareCifs.bl(self.cfg.get(name, ShareCifs.read_only.key))
            settings['browseable'] = ShareCifs.bl(self.cfg.get(name, ShareCifs.browseable.key))
            settings['recyclebin'] = True if VfsRecycleCifs.vfs_object.value in self.cfg.get(name, ShareCifs.vfs_objects.key) else False
            settings['recyclemaxsize'] = self.cfg.get(name, VfsRecycleCifs.maxsize.key, VfsRecycleCifs.vfs_object.value)
            db = self.engine.checkKey(groups.NETSHARES, name)
            if db:
                settings['recyclemaxage'] = db['recyclemaxage']
            else:
                settings['recyclemaxage'] = 0

            settings['hidedotfiles'] = ShareCifs.bl(self.cfg.get(name, ShareCifs.hide_dot_files.key))
            settings['inheritacls'] = ShareCifs.bl(self.cfg.get(name, ShareCifs.inherit_acls.key))
            settings['inheritpermissions'] = ShareCifs.bl(self.cfg.get(name, ShareCifs.inherit_permissions.key))
            settings['easupport'] = ShareCifs.bl(self.cfg.get(name, ShareCifs.ea_support.key))
            settings['storedosattr'] = ShareCifs.bl(self.cfg.get(name, ShareCifs.store_dos_attributes.key))

            settings['hostsallow'] = self.cfg.get(name, ShareCifs.hosts_allow.key)
            settings['hostsdeny'] = self.cfg.get(name, ShareCifs.hosts_deny.key)
            settings['audit'] =  True if VfsFullAuditCifs.vfs_object.value in self.cfg.get(name, ShareCifs.vfs_objects.key) else False

            setopts = [ShareCifs.comment.key, ShareCifs.path.key, ShareCifs.available.key, ShareCifs.guest_ok.key,
                      ShareCifs.guest_only.key, ShareCifs.read_only.key, ShareCifs.browseable.key, ShareCifs.inherit_acls.key,
                      ShareCifs.inherit_permissions.key, ShareCifs.ea_support.key, ShareCifs.store_dos_attributes.key, ShareCifs.vfs_objects.key,
                      ShareCifs.hosts_allow.key, ShareCifs.hosts_deny.key, ShareCifs.hide_dot_files.key, ShareCifs.valid_users.key,
                      ShareCifs.invalid_users.key, ShareCifs.read_list.key, ShareCifs.write_list.key, ShareCifs.extraoptions.key]
            defaults = ShareCifs.todict()
            extraoptions = {}
            for key, val in self.cfg.getSection(name).items():
                if not key in setopts:
                    if not key in defaults:
                        extraoptions[key] = CfgCifs.anybl(val)
                    elif CfgCifs.anybl(val) != CfgCifs.anybl(defaults[key]):
                        extraoptions[key] = CfgCifs.anybl(val)
            setopts = [VfsRecycleCifs.maxsize.key]
            defaults = VfsRecycleCifs.todict()
            for key, val in self.cfg.getObject(name, VfsRecycleCifs.vfs_object.value).items():
                ekey="{}:{}".format(VfsRecycleCifs.vfs_object.value, key)
                if ekey in extraoptions:
                    if key in setopts:
                        extraoptions.pop(ekey)
                    elif key in defaults:
                        if CfgCifs.anybl(val) == CfgCifs.anybl(defaults[key]):
                            extraoptions.pop(ekey)
            setopts = []
            defaults = VfsFullAuditCifs.todict()
            for key, val in self.cfg.getObject(name, VfsFullAuditCifs.vfs_object.value).items():
                ekey="{}:{}".format(VfsFullAuditCifs.vfs_object.value, key)
                if ekey in extraoptions:
                    if key in setopts:
                        extraoptions.pop(ekey)
                    elif key in defaults:
                        if CfgCifs.anybl(val) == CfgCifs.anybl(defaults[key]):
                            extraoptions.pop(ekey)
            settings['extraoptions'] = extraoptions
        return settings

    def getVfsObjects(self, name):
        vfs_objects = []
        objstring = self.cfg.get(name, ShareCifs.vfs_objects.key)
        if objstring:
            if type(objstring) == str:
                objs = objstring.strip().split(' ')
                for obj in objs:
                    if obj.strip():
                        vfs_objects.append(obj.strip())
        return vfs_objects

######################### MAIN ##########################
if __name__ == "__main__":
    pass
