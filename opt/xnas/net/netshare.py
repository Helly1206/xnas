# -*- coding: utf-8 -*-
#########################################################
# SERVICE : netshare.py                                 #
#           netshare and database operations for xnas   #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import logging
from copy import deepcopy
from shares.share import share
from net.cifsshare import cifsshare
from net.nfsshare import nfsshare
from common.stdin import stdin
from common.xnas_engine import groups
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : netshare                                      #
#########################################################
class netshare(object):
    def __init__(self, engine):
        self.engine = engine
        self.logger = logging.getLogger('xnas.xnetshare')

    def __del__(self):
        pass

    def getNetshares(self):
        mynetshares = []
        netshares = self.engine.checkGroup(groups.NETSHARES)
        if netshares:
            for key, netshare in netshares.items():
                mynetshare = {}
                mynetshare['xnetshare'] = key
                mynetshare['type'] = netshare['type']
                typeObj = self.loadTypeObj(netshare['type'])
                if self.hasTypeObj(typeObj):
                    mynetshare['access'] = typeObj.getAccess(key)
                else:
                    mynetshare['access'] = "ERROR"
                self.delTypeObj(typeObj)
                mynetshare['enabled'] = netshare['enabled']
                mynetshare['sourced'] = self.isSourced(key, True)
                if mynetshare:
                    mynetshares.append(mynetshare)

        typeObj = self.loadTypeObj('cifs', False)
        if self.hasTypeObj(typeObj):
            mynetshares.extend(typeObj.getHomes())
        self.delTypeObj(typeObj)

        return mynetshares

    def lst(self):
        mylist = []
        shares = self.engine.checkGroup(groups.SHARES)
        if shares:
            for key, share in shares.items():
                myitem = {}
                myitem['xshare'] = key
                myitem['netshare'] = self.isNetshare(key)
                mylist.append(myitem)
        return mylist

    def isSourced(self, name, silent = False):
        # Netshares can only be sourced by shares
        isSrcd = False
        shr = self.engine.checkKey(groups.SHARES, name)
        if shr:
            isSrcd = shr['enabled']
        if isSrcd and not silent:
            self.logger.warning("{} is sourced".format(name))
        return isSrcd

    def ena(self, name):
        retval = False
        db = self.engine.checkKey(groups.NETSHARES, name)
        if db:
            if self.isSourced(name):
                typeObj = self.loadTypeObj(db['type'])
                if self.hasTypeObj(typeObj):
                    retval = typeObj.ena(name)
                self.delTypeObj(typeObj)
        if retval:
            db['enabled'] = True
            self.logger.info("{} enabled".format(name))
        else:
            self.logger.warning("{} not enabled".format(name))
        return retval

    def dis(self, name):
        retval = False
        db = self.engine.checkKey(groups.NETSHARES, name)
        if db:
            typeObj = self.loadTypeObj(db['type'])
            if self.hasTypeObj(typeObj):
                retval = typeObj.dis(name)
            self.delTypeObj(typeObj)
        if retval:
            db['enabled'] = False
            self.logger.info("{} disabled".format(name))
        else:
            self.logger.warning("{} not disabled".format(name))
        return retval

    def shw(self, name):
        netshareData = {}
        db = self.engine.checkKey(groups.NETSHARES, name)
        if db:
            netshareData['type'] = db['type']
        return netshareData

    def addNsh(self, name):
        retval = True
        entryNew = {}
        newEntry = False
        typeObj = None
        hasShare = False
        db = self.engine.checkKey(groups.NETSHARES, name)
        if retval:
            if db: # in db
                if 'type' in self.engine.settings:
                    if self.engine.settings['type'].lower() != db['type']:
                        self.logger.error("{} found in database, but types do not match".format(name))
                        retval = False
                if retval:
                    if not self.engine.hasSetting(self.engine.settings, 'settings'):
                        self.logger.info("{} found in database, editing content".format(name))
                    typeObj = self.loadTypeObj(db['type'])
                    if not self.hasTypeObj(typeObj):
                        self.logger.error("{} found in database, but invalid type".format(name))
                        retval = False
            elif not self.engine.hasSetting(self.engine.settings, 'settings'): #create new item
                self.logger.info("{} not found, creating new item".format(name))
                db = {}
                newEntry = True
            else:
                self.logger.error("{} not found, create item first".format(name))
                retval = False

        # Create, check and update entry
        if retval and newEntry:
            if 'type' in self.engine.settings:
                typeObj = self.loadTypeObj(self.engine.settings['type'])
                if not self.hasTypeObj(typeObj):
                    self.logger.error("{} not found in database, and invalid type".format(name))
                    retval = False
            else:
                self.logger.warning("{} not found, no type entered".format(name))
                retval = False

        if retval and self.hasTypeObj(typeObj):
            hasShare = typeObj.findShare(name)
            if newEntry and hasShare:
                self.logger.info("{} not in database, but entry found, editing content".format(name))
            elif db and not hasShare:
                self.logger.info("{} in database, but no entry found, generating new entry".format(name))

        # Create, check and update entry
        if not self.engine.hasSetting(self.engine.settings, 'settings'):
            if retval:
                entryNew = deepcopy(db)
                changed = self.makeEntry(entryNew)
                retval = self.checkEntry(entryNew, newEntry, changed)

            if retval:
                if not self.isSourced(name, silent = True):
                    self.logger.error("{} is not sourced, has no valid or available xshare".format(name))
                    retval = False

            if retval:
                if changed:
                    if db:
                        retval = self.engine.removeFromGroup(groups.NETSHARES, name)
                        if db['type'] != entryNew['type']: # type changed, remove old type
                            retval = typeObj.delfss(name)
                            self.delTypeObj(typeObj)
                            typeObj = self.loadTypeObj(entryNew['type'])
                            if not self.hasTypeObj(typeObj):
                                self.logger.error("{} invalid type".format(name))
                                retval = False
        else:
            changed = False

        if retval and self.hasTypeObj(typeObj):
            retval = typeObj.addfss(name)
            if retval:
                if not self.engine.hasSetting(self.engine.settings, 'settings'):
                    self.logger.info("{} added/ edited in netshares config".format(name))
            else:
                self.logger.error("{} cannot be added/ edited in netshares config".format(name))

        if retval:
            if changed:
                #add new item to db
                dbNetshare = {}
                dbNetshare[name] = entryNew
                self.engine.addToGroup(groups.NETSHARES, dbNetshare)
            if not self.engine.hasSetting(self.engine.settings, 'settings'):
                self.logger.info("{} added/ edited".format(name))
        else:
            self.logger.warning("{} not added/ edited".format(name))

        self.delTypeObj(typeObj)

        return retval

    def delNsh(self, name):
        retval = False
        db = self.engine.checkKey(groups.NETSHARES, name)
        if db:
            typeObj = self.loadTypeObj(db['type'])
            if self.hasTypeObj(typeObj):
                retval = typeObj.delfss(name)
            self.delTypeObj(typeObj)
        if retval:
            self.logger.info("{} deleted".format(name))
            self.clr(name) # Remove from DB
        else:
            self.logger.warning("{} not deleted".format(name))
        return retval

    def config(self, type = ""):
        retval = True
        if not type:
            if self.engine.hasSetting(self.engine.settings, 'type'):
                type = self.engine.settings['type']

        all = not type

        if (all or type == 'cifs') and retval:
            cifs = self.loadTypeObj('cifs', not all)
            if self.hasTypeObj(cifs):
                if all and not cifs.available():
                    retval = True
                else:
                    retval = cifs.config()
            self.delTypeObj(cifs)

        if (all or type == 'nfs') and retval:
            nfs = self.loadTypeObj('nfs', not all)
            if self.hasTypeObj(nfs):
                if all and not nfs.available():
                    retval = True
                else:
                    retval = nfs.config()
            self.delTypeObj(nfs)

        return retval

    def homes(self, type = ""):
        retval = False
        if not type:
            if self.engine.hasSetting(self.engine.settings, 'type'):
                type = self.engine.settings['type']

        all = not type

        if all or type == 'cifs':
            cifs = self.loadTypeObj('cifs')
            if self.hasTypeObj(cifs):
                if not cifs.available():
                    retval = True
                else:
                    retval = cifs.homes()
            self.delTypeObj(cifs)
        else:
            self.logger.warning("Homes are only available on cifs netshares")

        return retval

    def users(self, cmd, type = ""):
        retval = False
        if not type:
            if self.engine.hasSetting(self.engine.settings, 'type'):
                type = self.engine.settings['type']

        all = not type

        if all or type == 'cifs':
            cifs = self.loadTypeObj('cifs')
            if self.hasTypeObj(cifs):
                if not cifs.available():
                    retval = True
                else:
                    retval = cifs.users(cmd)
            self.delTypeObj(cifs)
        else:
            self.logger.warning("Users are only available on cifs netshares")

        return retval

    def privileges(self, name):
        retval = False
        db = self.engine.checkKey(groups.NETSHARES, name)
        if db:
            if db['type'] == 'cifs':
                typeObj = self.loadTypeObj(db['type'])
                if self.hasTypeObj(typeObj):
                    retval = typeObj.privileges(name)
                    self.delTypeObj(typeObj)
            else:
                self.logger.warning("Privileges are only available on cifs netshares")
        return retval

    def refresh(self, type = ""):
        retval1 = False
        retval2 = False
        if not type:
            if 'type' in self.engine.settings:
                type = self.engine.settings['type']

        all = not type

        if all or type == 'cifs':
            cifs = self.loadTypeObj('cifs', not all)
            if self.hasTypeObj(cifs):
                if all and not cifs.available():
                    retval1 = True
                else:
                    retval1 = cifs.restart()
                if not all:
                    retval2 = True
            self.delTypeObj(cifs)

        if all or type == 'nfs':
            nfs = self.loadTypeObj('nfs', not all)
            if self.hasTypeObj(nfs):
                if all and not nfs.available():
                    retval2 = True
                else:
                    retval2 = nfs.restart()
                if not all:
                    retval1 = True
            self.delTypeObj(nfs)

        return retval1 and retval2

    ################## INTERNAL FUNCTIONS ###################

    def isNetshare(self, xshare):
        netshare = False
        db = self.engine.checkKey(groups.NETSHARES, xshare)
        if db:
            netshare = True
        return netshare

    def clr(self, name):
        retval = False
        db = self.engine.checkKey(groups.NETSHARES, name)
        if db:
            retval = self.engine.removeFromGroup(groups.NETSHARES, name)
        if retval:
            self.logger.info("{} removed from database".format(name))
        else:
            self.logger.warning("{} removed from database".format(name))
        return retval

    def makeEntry(self, entry):
        changed = False
        type = "cifs"

        if "type" in self.engine.settings:
            type = self.engine.settings['type'].lower()
            if "type" in entry:
                echanged =  entry['type'] != type
            else:
                echanged = True
            changed = changed or echanged
            entry['type'] = type
        elif not "type" in entry:
            changed = True
            entry['type'] = type
        if not "enabled" in entry:
            changed = True
            entry['enabled'] = True
        if "recyclemaxage" in self.engine.settings and type == "cifs":
            maxage = self.engine.settings['recyclemaxage']
            if "recyclemaxage" in entry:
                echanged =  entry['recyclemaxage'] != maxage
            else:
                echanged = True
            changed = changed or echanged
            entry['recyclemaxage'] = maxage
        elif not "recyclemaxage" in entry:
            changed = True
            entry['recyclemaxage'] = 0

        return changed

    def checkEntry(self, entry, new = True, changed = True):
        retval = True

        return retval

    def loadTypeObj(self, type, checkAvailable = True):
        typeObj = None
        if type == 'cifs':
            typeObj = cifsshare(self.logger, self.engine)
        elif type == 'nfs':
            typeObj = nfsshare(self.logger, self.engine)

        if self.hasTypeObj(typeObj):
            if checkAvailable and not typeObj.available():
                self.logger.error("Netshare is of type {}, but this type is not installed".format(type))
                self.logger.info("Please install {} on your distro (if available) and try again".format(type))
                self.logger.info("Common package to install on most distros: '{}'".format(typeObj.installName()))
                del typeObj
                exit(1)

        return typeObj

    def hasTypeObj(self, typeObj):
        return typeObj != None

    def delTypeObj(self, typeObj):
        if self.hasTypeObj(typeObj):
            del typeObj

######################### MAIN ##########################
if __name__ == "__main__":
    pass
