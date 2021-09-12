# -*- coding: utf-8 -*-
#########################################################
# SERVICE : remotemount.py                              #
#           remotemount and database operations         #
#           for xnas                                    #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import logging
from copy import deepcopy
from mounts.fstab import fstab
from mounts.mountfs import mountfs
from mounts.mountpoint import mountpoint
from common.stdin import stdin
from common.xnas_engine import groups
from common.shell import shell
from remotes.davfs import davfs
from remotes.cifs import cifs
from remotes.nfs import nfs
from remotes.ping import ping
#########################################################

## Indeed fsname is used
"""
{'line': 24,
'content': {'fsname': 'https://Helly1206.stackstorage.com/remote.php/webdav/',
'label': '', 'uuid': '', 'mountpoint': '/mnt/test', 'type': 'davfs',
'options': ['_netdev', 'user'], 'dump': '0', 'pass': '0'}}]
"""
## Change uuid based functions to be able to be used with fsname (or mountpoint)
## fsname works. This is the only thing in the db, maybe add some user management information later

## Mounting this to remote-fs.target just works
## see: /run/systemd/generator
# systemd-analyze plot > plot.svg

# it looks like the mounts are done before remote-fs.target, so this one can be used for the bounds later
# df shows contents of remotemounts df --output=source,size,pcent,target -h /mnt/OS

####################### GLOBALS #########################
FSTYPES = ["cifs", "davfs", "nfs", "nfs4"]
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : remotemount                                   #
#########################################################
class remotemount(fstab, mountfs, mountpoint):
    def __init__(self, engine, human = False):
        self.engine = engine
        self.human = human
        self.logger = logging.getLogger('xnas.xremotemount')
        fstab.__init__(self, self.logger, True)
        mountfs.__init__(self, self.logger)
        mountpoint.__init__(self, self.logger)

    def __del__(self):
        mountpoint.__del__(self)
        mountfs.__del__(self)
        fstab.__del__(self)

    def inDB(self):
        listentries = []
        entries = self.getEntries(FSTYPES)
        for entry in entries:
            listentry = {}
            #Shrink I
            https = True
            listentry["server"] = ""
            listentry["sharename"] = ""
            if entry["fsname"]:
                https, listentry["server"], listentry["sharename"] = self.parseEntryURL(entry)
            #copy
            for key, value in entry.items():
                if key == "options":
                    listentry[key] = ",".join(value)
                elif key != "fsname" and key != "uuid" and key != "label":
                    listentry[key] = value
            dbkey = self.findInDb(https, listentry["server"], listentry["sharename"], entry["type"])
            if dbkey:
                listentry['xremotemount'] = dbkey
            else:
                listentry['xremotemount'] = "-"
            listentries.append(listentry)
        return listentries

    def getRemotemounts(self):
        mymounts = []
        mounts = self.engine.checkGroup(groups.REMOTEMOUNTS)
        if mounts:
            for key, mount in mounts.items():
                mymount = {}
                url = self.buildDbURL(mount)
                entry = self.getEntry(fsname=url)
                if entry:
                    mymount['xremotemount'] = key
                    # Don't show https
                    mymount['server'] = mount['server']
                    mymount['sharename'] = mount['sharename']
                    mymount['mountpoint'] = entry['mountpoint']
                    mymount['type'] = entry['type']
                    dfentry = self.dfRemoteDevice(entry['mountpoint'])
                    if dfentry:
                        mymount['size'] = dfentry['size']
                        mymount['used'] = dfentry['used']
                        mymount['mounted'] = True
                    else:
                        mymount['size'] = None
                        mymount['used'] = None
                        mymount['mounted'] = False
                    mymount['enabled'] = fstab.isEna(self, fsname = entry['fsname'])
                    mymount['health'] = self.getHealth(fsname = entry['fsname'], isMounted = mymount['mounted'], hasHost = ping().ping(url))
                    mymount['referenced'] = self.isReferenced(key, True)
                    mymount['dynmount'] = mount['dyn']
                if mymount:
                    mymounts.append(mymount)

        return mymounts

    def pop(self, interactive, popArgs):
        addedMounts = []

        entries = self.getEntries(FSTYPES)
        for entry in entries:
            if entry['fsname']: # Don't add if fsname cannot be found
                https, server, sharename = self.parseEntryURL(entry)
                dbkey = self.findInDb(https, server, sharename, entry["type"])
                popArg = {}
                if not dbkey:
                    if popArgs:
                        for arg in popArgs:
                            if 'server' in arg and 'sharename' in arg:
                                if arg['server'] == server and arg['sharename'] == sharename:
                                    popArg = arg
                                    break
                    newMount = self.addToDB(entry, interactive, popArg)
                    if newMount:
                        addedMounts.append(newMount)
        return addedMounts

    def getReferenced(self, name):
        # Remotemounts can only be referenced to shares, so check shares for references
        dbkeys = []
        refs = self.engine.findAllInGroup(groups.SHARES, 'xmount', name)
        for dbkey, dbval in refs.items():
            if 'remotemount' in dbval and 'enabled' in dbval:
                if dbval['remotemount'] and dbval['enabled']:
                    dbkeys.append(dbkey)
        return dbkeys

    def isReferenced(self, name, silent = False):
        # Remotemounts can only be referenced to shares, so check shares for references
        ref = self.getReferenced(name)
        if ref and not silent:
            self.logger.warning("{} is referenced by {}".format(name, ref))
        return ref != []

    def mnt(self, name, dbItem = True, mpoint = ""):
        retval = False
        isMounted = False
        url = name
        if dbItem:
            db = self.engine.checkKey(groups.REMOTEMOUNTS, name)
            if db:
                url = self.buildDbURL(db)
                retval = True
        else:
            retval = True
        if retval:
            retval = False
            entry = self.getEntry(fsname=url)
            if entry:
                if mpoint:
                    mp = mpoint
                else:
                    mp = entry['mountpoint']
                isMounted = self.mounted(mp)
                if not isMounted:
                    if ping().ping(entry['fsname']):
                        retval = mountfs.mount(self, mp)
                    else:
                        self.logger.warning("{} failed pinging host".format(name))
                        retval = False
                elif dbItem:
                    self.logger.warning("{} already mounted".format(name))
        if retval:
            self.logger.info("{} mounted".format(name))
        elif not isMounted:
            self.logger.warning("{} not mounted".format(name))
        else: # Already mounted
            retval = True
        return retval

    def umnt(self, name, dbItem = True, mpoint = ""):
        retval = False
        isMounted = False
        url = name
        if dbItem:
            db = self.engine.checkKey(groups.REMOTEMOUNTS, name)
            if db:
                url = self.buildDbURL(db)
                retval = True
        else:
            retval = True
        if retval:
            retval = False
            entry = self.getEntry(fsname=url)
            if not entry:
                entry = {}
                entry['mountpoint'] = mountpoint.getMountPoint(self, url, True)
            if 'mountpoint' in entry:
                if mpoint:
                    mp = mpoint
                else:
                    mp = entry['mountpoint']
                isMounted = self.mounted(mp)
                if isMounted:
                    if not self.isReferenced(name):
                        retval = mountfs.unmount(self, mp, internal = True)
                elif dbItem:
                    self.logger.warning("{} is not mounted".format(name))
        if retval:
            self.logger.info("{} unmounted".format(name))
        elif isMounted:
            self.logger.warning("{} not unmounted".format(name))
        else:
            retval = True
        return retval

    def getMountpoint(self, name):
        retval = ""
        db = self.engine.checkKey(groups.REMOTEMOUNTS, name)
        if db:
            entry = self.getEntry(fsname=self.buildDbURL(db))
            retval = entry['mountpoint']
        return retval

    def clr(self, name):
        retval = False
        db = self.engine.checkKey(groups.REMOTEMOUNTS, name)
        if db:
            if not self.isReferenced(name):
                retval = self.engine.removeFromGroup(groups.REMOTEMOUNTS, name)
        if retval:
            self.logger.info("{} removed from database".format(name))
        else:
            self.logger.warning("{} removed from database".format(name))
        return retval

    def ena(self, name):
        retval = False
        db = self.engine.checkKey(groups.REMOTEMOUNTS, name)
        if db:
            retval = fstab.ena(self, fsname=self.buildDbURL(db))
        if retval:
            self.logger.info("{} enabled".format(name))
        else:
            self.logger.warning("{} not enabled".format(name))
        return retval

    def dis(self, name):
        retval = False
        db = self.engine.checkKey(groups.REMOTEMOUNTS, name)
        if db:
            if not self.isReferenced(name):
                retval = fstab.dis(self, fsname=self.buildDbURL(db))
        if retval:
            self.logger.info("{} disabled".format(name))
        else:
            self.logger.warning("{} not disabled".format(name))
        return retval

    def shw(self, name):
        remotemountData = {}
        db = self.engine.checkKey(groups.REMOTEMOUNTS, name)
        if db:
            url = self.buildDbURL(db)
            entry = self.getEntry(fsname=url)
            if entry:
                remotemountData['https'] = db['https']
                remotemountData['server'] = db['server']
                remotemountData['sharename'] = db['sharename']
                remotemountData['mountpoint'] = entry['mountpoint']
                remotemountData['type'] = entry['type']
                remotemountData['options'] = fstab.getExtraOptions(self, entry['options'])
                remotemountData['auto'] = not 'noauto' in entry['options']
                remotemountData['rw'] = not 'ro' in entry['options']
                remotemountData['freq'] = entry['dump']
                remotemountData['pass'] = entry['pass']
                typeObj = self.loadTypeObj(entry['type'])
                if self.hasTypeObj(typeObj):
                    remotemountData['username'] = typeObj.getCredentials(url)
                else:
                    remotemountData['username'] = ""
                self.delTypeObj(typeObj)
                remotemountData['password'] = ""
                mode = self.getMode(remotemountData['mountpoint'])
                remotemountData['uacc'] = self.getUacc(mode)
                remotemountData['sacc'] = self.getSacc(mode)
                remotemountData['dynmount'] = db['dyn']
        return remotemountData

    def addRm(self, name):
        retval = True
        entry = {}
        entryNew = {}
        newEntry = False
        uuid = ""
        db, entry = self.findEntry(self.engine.settings, generate = False)
        changed = False
        currentMountpoint = ""
        currentLabel = ""
        deleteCurrentMountpoint = False
        typeObj = None
        # Check existence of entry
        if db: # in db
            if self.isReferenced(name):
                self.logger.info("{} found in database, but is referenced. Remove reference first".format(name))
                retval = False
            else:
                self.logger.info("{} found in database, editing content".format(name))
                typeObj = self.loadTypeObj(db['type'])
                if self.hasTypeObj(typeObj):
                    entry = self.getEntry(fsname=self.buildDbURL(db, typeObj))
                else:
                    self.logger.error("{} found in database, but invalid type".format(name))
                    retval = False
        elif entry:
            self.logger.info("{} not in database, but entry found, editing content".format(name))
            typeObj = self.loadTypeObj(entry['type'])
            if self.hasTypeObj(typeObj):
                # check entry is somewhere else is DB or create new entry
                dbkey = self.findEntryInDb(entry, typeObj)
                if dbkey:
                    self.logger.warning("{} found in database under different mount: {}".format(name, dbkey))
                    retval = False
                if retval:
                    newEntry = False
            else:
                self.logger.error("{} found, but invalid type".format(name))
                retval = False
        else:
            if retval:
                if 'server' in self.engine.settings and 'sharename' in self.engine.settings and 'type' in self.engine.settings:
                    typeObj = self.loadTypeObj(self.engine.settings['type'])
                    if self.hasTypeObj(typeObj):
                        self.logger.info("{} not found, creating new item".format(name))
                        newEntry = True
                    else:
                        self.logger.error("{} not found, and invalid type entered".format(name))
                        retval = False
                else:
                    self.logger.warning("{} not found, no server, sharename and/ or type entered".format(name))
                    retval = False
        # Make Mountpoint
        if retval:
            MPvalid = True
            MPnew = ""
            if not newEntry:
                currentMountpoint = entry['mountpoint']

            if 'mountpoint' in self.engine.settings:
                MPnew = self.engine.settings['mountpoint']
                MPvalid = not mountpoint.exists(self, MPnew)
                if not MPvalid:
                    if mountpoint.mounted(self, MPnew):
                        # Check mountpoint is linked to current url
                        url = ""
                        if entry:
                            url = entry['fsname']
                        else:
                            url = self.buildDbURL(self.engine.settings, typeObj)
                        MPvalid = mountpoint.getMountPoint(self, url, True) == MPnew
                    else:
                        MPvalid = True
            elif newEntry: # New entry and no mountpoint
                MPValid = False

            if currentMountpoint and MPnew:
                if currentMountpoint != MPnew:
                    if MPvalid:
                        deleteCurrentMountpoint = True
                    else:
                        self.logger.info("New mountpoint invalid, keep current: {}".format(currentMountpoint))
                        MPnew = currentMountpoint
                        MPvalid = True
                else:
                    MPvalid = True # current mountpoint is unmounted later

            if not MPnew:
                MPnew = currentMountpoint
            if not MPnew: # no mountpoint at all
                MPvalid = False

            if not MPvalid:
                url = ""
                if entry:
                    url = entry['fsname']
                else: # check for correct options is done before
                    url = self.buildDbURL(self.engine.settings, typeObj)
                label = typeObj.getLabel(url)
                MPnew = mountpoint.make(self, name, backupmountpoint = label)

            retval = MPnew != None
            self.engine.settings['mountpoint'] = MPnew

        # Create, check and update entry
        if retval:
            url = ""
            if entry:
                url = entry['fsname']
            else: # check for correct options is done before
                url = self.buildDbURL(self.engine.settings, typeObj)
            entryNew = deepcopy(entry)
            changed = self.makeEntry(entryNew, self.engine.settings, url)
            retval = self.checkRemoteEntry(entryNew)

        # Credentials
        if retval:
            if self.hasTypeObj(typeObj) and entryNew['type'] != 'nfs' and entryNew['type'] != 'nfs4':
                if 'username' in self.engine.settings:
                    uspss = self.UserPass(self.engine.settings)
                    guest = not uspss[0]
                    if not guest:
                        if not uspss[1]:
                            if uspss[0] != typeObj.getCredentials(entryNew['fsname']):
                                retval = typeObj.addCredentials(entryNew['fsname'], uspss[0], uspss[1])
                        else:
                            retval = typeObj.addCredentials(entryNew['fsname'], uspss[0], uspss[1])
                else:
                    guest = not typeObj.getCredentials(entryNew['fsname'])
            else:
                guest = False

        if retval:
            oldOptions = deepcopy(entryNew['options'])
            curmode = self.setMode("rw", "rw") # RW mode if new or non existent
            if currentMountpoint:
                curmode = self.getMode(currentMountpoint)
            elif mountpoint.exists(self, entryNew['mountpoint']):
                curmode = self.getMode(entryNew['mountpoint'])
            if 'uacc' in self.engine.settings:
                uacc = self.engine.settings['uacc']
            else:
                uacc = self.getUacc(curmode)
            if 'sacc' in self.engine.settings:
                sacc = self.engine.settings['sacc']
            else:
                sacc = self.getSacc(curmode)
            typeObj.setOptions(entryNew['options'], entryNew['fsname'], guest, self.strMode(self.setMode(uacc, sacc)))
            changed = changed or (oldOptions != entryNew['options'])

        # If changed, unmount and update
        if changed and retval:
            if currentMountpoint:
                # If entry['mountpoint'] exists, then entry['fsname'] must also exist
                retval = self.umnt(entry['fsname'], dbItem = False, mpoint = currentMountpoint)
            if not retval:
                self.logger.warning("Unable to unmount {}".format(name))

        if retval:
            retval = self.updateEntry(entryNew, newEntry)

        # Mount if not noauto option
        if retval:
            if 'dynmount' in self.engine.settings:
                dyn = self.engine.settings['dynmount']
            else:
                dyn = False
            if deleteCurrentMountpoint:
                retval = mountpoint.delete(self, currentMountpoint)
                if retval:
                    self.logger.info("Removed old mountpoint: {}".format(currentMountpoint))
            if retval and not mountpoint.exists(self, entryNew['mountpoint']):
                retval = mountpoint.create(self, entryNew['mountpoint'])
                if retval:
                    self.logger.info("Created new mountpoint: {}".format(entryNew['mountpoint']))
            if retval:
                curmode = self.getMode(entryNew['mountpoint'])
                if 'uacc' in self.engine.settings:
                    uacc = self.engine.settings['uacc']
                elif newEntry:
                    uacc = "rw"
                else:
                    uacc = self.getUacc(curmode)
                if 'sacc' in self.engine.settings:
                    sacc = self.engine.settings['sacc']
                elif newEntry:
                    sacc = "rw"
                else:
                    sacc = self.getSacc(curmode)
                mode = self.setMode(uacc, sacc)
                if mode != curmode:
                    self.chMode(entryNew['mountpoint'], mode)
                    self.logger.info("Changed mountpoint mode: user {}, superuser {}".format(uacc, sacc))
            if retval:
                noauto = False
                if 'options' in entryNew:
                    noauto = 'noauto' in entryNew['options']
                    if not noauto:
                        retval = self.mnt(entryNew['fsname'], dbItem = False, mpoint = entryNew['mountpoint'])
                        if dyn: # Do not blame mounting failed if dynmount device
                            retval = True

        # Add to DB or edit DB
        if retval:
            if db:
                # remove old item from db
                if not self.isReferenced(name):
                    retval = self.engine.removeFromGroup(groups.REMOTEMOUNTS, name)
            #add new item to db
            dbMount = {}
            dbMountItems = {}
            dbMountItems['https'], dbMountItems['server'], dbMountItems['sharename'] = self.parseEntryURL(entryNew, typeObj)
            dbMountItems['type'] = entryNew['type']
            dbMountItems['dyn'] = dyn
            dbMount[name] = dbMountItems
            self.engine.addToGroup(groups.REMOTEMOUNTS, dbMount)
            self.logger.info("{} added/ edited".format(name))
        else:
            self.logger.warning("{} not added/ edited".format(name))

        self.delTypeObj(typeObj)

        return retval

    def delRm(self, name):
        retval = False
        db = self.engine.checkKey(groups.REMOTEMOUNTS, name)
        if db:
            if not self.isReferenced(name):
                retval = self.umnt(name)
                if retval:
                    url = self.buildDbURL(db)
                    entry = self.getEntry(fsname=url)
                    retval = self.deleteEntry(fsname=url)
                    if retval and entry:
                        mountpoint.delete(self, entry['mountpoint'])
                        self.logger.info("Removed mountpoint: {}".format(entry['mountpoint']))
                        #delete credentails if applicable
                        typeObj = self.loadTypeObj(entry['type'])
                        if self.hasTypeObj(typeObj):
                            if typeObj.delCredentials(url):
                                self.logger.info("Removed credentials")
                        self.delTypeObj(typeObj)
        if retval:
            self.logger.info("{} deleted".format(name))
            self.clr(name) # Remove from DB
        else:
            self.logger.warning("{} not deleted".format(name))
        return retval

    def findUrl(self):
        retval = {}
        retval['url'] = ""

        db, entry = self.findEntry(self.engine.settings)

        if entry:
            retval['url'] = entry['fsname']

        return retval

    def buildDbURL(self, db, typeObj = None):
        url = ""
        doDel = False
        if not typeObj:
            typeObj = self.loadTypeObj(db['type'])
            doDel = True
        if self.hasTypeObj(typeObj):
            if not 'https' in db:
                db['https'] = True
            url = typeObj.buildURL(db['https'], db['server'], db['sharename'])
        if doDel:
            self.delTypeObj(typeObj)

        return url

    ################## INTERNAL FUNCTIONS ###################

    def addToDB(self, entry, interactive = False, popArg = {}):
        dbMount = {}
        newMount = {}
        addThis = True
        name = ""
        https = True
        server = ""
        sharename = ""

        typeObj = self.loadTypeObj(entry['type'])

        if popArg:
            if self.engine.checkKey(groups.REMOTEMOUNTS, popArg['xremotemount']):
                self.logger.error("Name already exists, not added: {}".format(popArg['xremotemount']))
                addThis = False
            else:
                name = popArg['xremotemount']
        else:
            label = ""
            if self.hasTypeObj(typeObj):
                label = typeObj.getLabel(entry['fsname'])

            name = self.engine.generateUniqueName(groups.REMOTEMOUNTS, entry['mountpoint'], label)

        if self.hasTypeObj(typeObj):
            https, server, sharename = typeObj.parseURL(entry['fsname'])

        if interactive and not popArg:
            addThis = False
            cont = True
            stdinput = stdin("", exitevent = None, mutex = None, displaylater = False, background = False)

            print("New remotemount found:")
            if entry['type'] == "davfs":
                    print("    https         : ", https)
            print("    server        : ", server)
            print("    sharename     : ", sharename)
            print("    mountpoint    : ", entry['mountpoint'])
            print("    type          : ", entry['type'])
            print("    Generated name: ", name)

            while cont:
                res = ""
                while not res:
                    res = stdinput.inputchar("Add this remotemount (y/n/c)? ")
                    if res:
                        res = res.lower()[0]
                    if res == "y":
                        addThis = True
                        cont = False
                        print("New remotemount added: {}".format(name))
                    elif res == "n":
                        addThis = False
                        cont = False
                        print("New remotemount skipped: {}".format(name))
                        # text
                    elif res == "c":
                        newname = stdinput.input("Enter new name for this remotemount: ")
                        if ord(newname[0]) == 3: # ^C
                            self.engine.exitSignal()
                        else:
                            if not self.engine.valid(newname):
                                print("Name contains special characters, try again")
                            elif self.engine.checkKey(groups.REMOTEMOUNTS, newname):
                                print("Name already exists, try again")
                            else:
                                name = newname
                                print("New remotemount added: {}".format(name))
                                addThis = True
                                cont = False
                    elif ord(res) == 3: # ^C
                        self.engine.exitSignal()
                    else:
                        print("Invalid response, y = yes, n = no, c = change name")
                        res = ""
            del stdinput

        if addThis:
            dbMountItems = {}
            dbMountItems['https'] = https
            dbMountItems['server'] = server
            dbMountItems['sharename'] = sharename
            dbMountItems['type'] = entry['type']
            if 'dynmount' in self.engine.settings:
                dbMountItems['dyn'] = self.engine.settings['dynmount']
            else:
                dbMountItems['dyn'] = False
            dbMount[name] = dbMountItems
            self.engine.addToGroup(groups.REMOTEMOUNTS, dbMount)
            newMount['xremotemount'] = name
            #newMount['https'] = https
            newMount['server'] = server
            newMount['sharename'] = sharename
            newMount['mountpoint'] = entry['mountpoint']
            newMount['type'] = entry['type']
            newMount['dynmount'] = dbMountItems['dyn']
            self.logger.info("New mount entry: {}".format(name))

        self.delTypeObj(typeObj)

        return newMount

    def UserPass(self, settings):
        usernm = ""
        passwd = ""
        if settings['interactive']:
            stdinput = stdin("", exitevent = None, mutex = None, displaylater = False, background = False)
            print("Please enter a username and password for this remote mount (or enter for guest)")
            usernm = stdinput.input("Username: ").strip()
            if ord(usernm[0]) == 3: # ^C
                self.engine.exitSignal()
            if usernm:
                passwd = stdinput.input("Password: ", echo = False).strip()
                if ord(passwd[0]) == 3: # ^C
                    print("^C")
                    self.engine.exitSignal()
                else:
                    print("")
            del stdinput
        else:
            if 'username' in settings:
                usernm = settings['username']
            if 'password' in settings:
                passwd = settings['password']
        return (usernm, passwd)

    # df shows contents of remotemounts df --output=source,size,pcent,target -h /mnt/OS
    def dfRemoteDevice(self, mpoint):
        entry = {}
        cmd = ""
        if self.human:
            cmd = "df --output=source,size,pcent,target -h {}".format(mpoint)
        else:
            cmd = "df --output=source,size,used,target {}".format(mpoint)
        try:
            lines = shell().command(cmd).splitlines()
            if len(lines) > 1:
                for line in lines[1:]:
                    data = line.split()
                    if len(data) == 4:
                        if data[3] == mpoint: # df can give strange output if device not mounted
                            entry['label'] = data[0]
                            entry['size'] = data[1].replace(",",".")
                            entry['used'] = data[2].replace(",",".")
                            break
        except:
            pass
        return entry

    def loadTypeObj(self, type):
        typeObj = None
        if type == 'davfs':
            typeObj = davfs(self.logger)
        elif type == 'cifs':
            typeObj = cifs(self.logger)
        elif type == 'nfs' or type == 'nfs4':
            typeObj = nfs(self.logger)

        if self.hasTypeObj(typeObj):
            if not typeObj.available():
                self.logger.error("Remotemount is of type {}, but this type is not installed".format(type))
                self.logger.info("Please install {} no your distro (if available) and try again".format(type))
                self.logger.info("Common package to install on most distros: '{}'".format(typeObj.installName()))
                del typeObj
                exit(1)

        return typeObj

    def hasTypeObj(self, typeObj):
        return typeObj != None

    def delTypeObj(self, typeObj):
        if self.hasTypeObj(typeObj):
            del typeObj

    def checkRemoteEntry(self, entry, new = True):
        retval = True

        if not new:
            if self.findEntryLine(fsname = entry["fsname"]) < 0:
                self.logger.info("fsname {} does not exist, item not created".format(entry["fsname"]))
                retval = False
        if retval:
            retval = "_netdev" in entry['options']
            if not retval:
                self.logger.info("Entry is not marked as net device, item not created")
        #remotemount may have multiple mounts, so don't check for it.
        #don't ping here, only at mount
        return retval

    def findEntry(self, settings, generate = True):
        entry = {}
        db = {}
        server = ""
        sharename = ""
        if 'name' in settings:
            db = self.engine.checkKey(groups.REMOTEMOUNTS, settings['name'])
        if not db:
            if 'server' in settings and 'sharename' in settings:
                if 'type' in settings:
                    url = self.buildDbURL(settings)
                    fsentries = self.getEntries([settings['type']])
                    for fsentry in fsentries:
                        if fsentry['fsname'] == url:
                            entry = fsentry
                            break
                    if not entry and generate: # else if type build it yourself
                        entry['fsname'] = url
                        entry['label'] = ""
                        entry['uuid'] = ""
                        entry['mountpoint'] = ""
                        entry['type'] = settings['type']
                        entry['options'] = []
                        entry['dump'] = "0"
                        entry['pass'] = "0"
                else:
                    for type in FSTYPES:
                        settings['type'] = type
                        url = self.buildDbURL(settings)
                        fsentries = self.getEntries([settings['type']])
                        for fsentry in fsentries:
                            if fsentry['fsname'] == url:
                                entry = fsentry
                                break
                        else:
                            continue  # only executed if the inner loop did NOT break
                        break  # only executed if the inner loop DID break
                    if not entry:
                        self.logger.warning("Unable to build URL as nothing found in fstab and no type entered")
            else:
                self.logger.warning("Nothing found in database and no server/ sharename entered")
        else:
            entry = self.getEntry(fsname=self.buildDbURL(db))
        return db, entry

    def findInDb(self, https, server, sharename, type):
        dbkey = ""
        items = self.engine.findAllInGroup(groups.REMOTEMOUNTS, 'type', type)
        for ikey, ivalue in items.items():
            httpsok = True
            if type == 'davfs':
                httpsok = ivalue['https'] == https
            if httpsok and ivalue['server'] == server and ivalue['sharename'] == sharename:
                dbkey = ikey
                break
        return dbkey

    def findEntryInDb(self, entry, typeObj = None):
        https, server, sharename = self.parseEntryURL(entry, typeObj)
        return self.findInDb(https, server, sharename, entry['type'])

    def parseEntryURL(self, entry, typeObj = None):
        https = True
        server = ""
        sharename = ""
        doDel = False
        if not typeObj:
            typeObj = self.loadTypeObj(entry['type'])
            doDel = True
        if self.hasTypeObj(typeObj):
            https, server, sharename = typeObj.parseURL(entry['fsname'])
        if doDel:
            self.delTypeObj(typeObj)

        return https, server, sharename

######################### MAIN ##########################
if __name__ == "__main__":
    pass
