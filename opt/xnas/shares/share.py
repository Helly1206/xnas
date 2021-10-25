# -*- coding: utf-8 -*-
#########################################################
# SERVICE : share.py                                    #
#           share and database operations for xnas      #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import logging
from copy import deepcopy
from shares.link import link
from mounts.mountfs import mountfs
from mounts.mountpoint import mountpoint
from common.stdin import stdin
from common.xnas_engine import groups
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : share                                         #
#########################################################
class share(link, mountpoint):
    def __init__(self, engine):
        self.engine = engine
        self.logger = logging.getLogger('xnas.xshare')
        link.__init__(self, self.logger)
        mountpoint.__init__(self, self.logger)

    def __del__(self):
        mountpoint.__del__(self)
        link.__del__(self)

    def getShares(self):
        myshares = []
        shares = self.engine.checkGroup(groups.SHARES)
        if shares:
            for key, share in shares.items():
                myshare = {}
                myshare['xshare'] = key
                myshare['xmount'] = share['xmount']
                myshare['remotemount'] = share['remotemount']
                myshare['folder'] = share['folder']
                myshare['enabled'] = share['enabled']
                myshare['referenced'] = self.isReferenced(key, True)
                myshare['sourced'] = self.isSourced(key, True)
                if myshare:
                    myshares.append(myshare)

        return myshares

    def lst(self):
        mylist = []
        mounts = self.engine.checkGroup(groups.MOUNTS)
        if mounts:
            for key, mount in mounts.items():
                myitem = {}
                myitem['xmount'] = key
                myitem['remotemount'] = False
                myitem['mountpoint'] = self.getSourceMountpoint(key, False)
                myitem['xshares'] = self.findShares(key, False)
                mylist.append(myitem)
        remotemounts = self.engine.checkGroup(groups.REMOTEMOUNTS)
        if remotemounts:
            for key, mount in remotemounts.items():
                myitem = {}
                myitem['xmount'] = key
                myitem['remotemount'] = True
                myitem['mountpoint'] = self.getSourceMountpoint(key, True)
                myitem['xshares'] = self.findShares(key, True)
                mylist.append(myitem)
        return mylist

    def getReferenced(self, name):
        #Shares can only be referenced to netshares, so check netshares for references
        db = self.engine.checkKey(groups.NETSHARES, name)
        return db

    def isReferenced(self, name, silent = False):
        #Shares can only be referenced to netshares, so check netshares for references
        ref = self.getReferenced(name)
        if ref and not silent:
            self.logger.warning("{} is referenced by a {} netshare".format(name, ref['type']))
        return ref != None

    def getSourceMountpoint(self, name, remotemount = False):
        sourceMountpoint = ""
        if remotemount:
            db = self.engine.checkKey(groups.REMOTEMOUNTS, name)
            if db:
                sourceMountpoint = db['mountpoint']
        else:
            db = self.engine.checkKey(groups.MOUNTS, name)
            if db:
                sourceMountpoint = db['mountpoint']
        return sourceMountpoint

    def isSourced(self, name, silent = False):
        # Shares can only be sourced by mounts or remotemounts
        isSrcd = False
        src = ""
        db = self.engine.checkKey(groups.SHARES, name)
        if db:
            src = self.getSourceMountpoint(db['xmount'], db['remotemount'])
        if src:
            #mounted = mountfs(self.logger).isMounted(src)
            #if mounted:
            #    srcdir = self.sourceDir(name, src)
            isSrcd = self.exists(src)
        if isSrcd and not silent:
            self.logger.warning("{} is sourced".format(name))
        return isSrcd

    """
    def isBound(self, name, silent = False):
        isMounted = False
        isMounted = self.isMounted(self.engine.shareDir(name))
        if isMounted and not silent:
            self.logger.warning("{} is bound".format(name))
        return isMounted

    def bnd(self, name, timeout = 5, verbose = True):
        retval = False
        isMounted = False
        isMounted = self.isBound(name, True)

        db = self.engine.checkKey(groups.SHARES, name)
        if db:
            if not isMounted:
                if self.isSourced(name, True):
                    srcdir = self.sourceDir(name)
                    if srcdir:
                        retval = self.bind(srcdir, self.engine.shareDir(name), timeout)
                        self.chMode(self.engine.shareDir(name), self.setMode(db['uacc'], db['sacc']))
            elif verbose:
                self.logger.warning("{} already bound".format(name))
        if retval:
            if verbose:
                self.logger.info("{} bound".format(name))
        elif not isMounted:
            if verbose:
                self.logger.warning("{} not bound".format(name))
        else: # Already bound
            retval = True
        return retval

    def ubnd(self, name, disable = False, force = False, timeout = 5, verbose = True):
        retval = False
        isMounted = self.isBound(name, True)
        if isMounted:
            if not self.isReferenced(name) or disable:
                retval = self.unbind(self.engine.shareDir(name), force, timeout)
        elif verbose:
            self.logger.warning("{} is not bound".format(name))
        if retval:
            if verbose:
                self.logger.info("{} unbound".format(name))
        elif isMounted:
            if verbose:
                self.logger.warning("{} not unbound".format(name))
        else:
            retval = True
        return retval
    """

    def ena(self, name, verbose = True):
        retval = False
        db = self.engine.checkKey(groups.SHARES, name)
        if db:
            retval = self.isSourced(name, True)
        if retval:
            retval = self.linkSingle(name)
        if retval:
            db['enabled'] = True
            if verbose:
                self.logger.info("{} enabled".format(name))
        elif verbose:
                self.logger.warning("{} not enabled".format(name))
        return retval

    def dis(self, name, verbose = True):
        retval = False
        db = self.engine.checkKey(groups.SHARES, name)
        if db:
            if not self.isReferenced(name):
                retval = self.unlink(self.engine.shareDir(name))
        if retval:
            db['enabled'] = False
            if verbose:
                self.logger.info("{} disabled".format(name))
        elif verbose:
            self.logger.warning("{} not disabled".format(name))
        return retval

    def shw(self, name):
        shareData = {}
        db = self.engine.checkKey(groups.SHARES, name)
        if db:
            shareData['xmount'] = db['xmount']
            shareData['remotemount'] = db['remotemount']
            shareData['mountpoint'] = self.getSourceMountpoint(db['xmount'], db['remotemount'])
            shareData['folder'] = db['folder']
        return shareData

    def addSh(self, name):
        entryNew = {}
        newEntry = False
        retval = True

        db = self.engine.checkKey(groups.SHARES, name)
        if retval:
            if db: # in db
                if self.isReferenced(name):
                    self.logger.info("{} found in database, but is referenced. Remove reference first".format(name))
                    retval = False
                elif db['enabled']:
                    self.logger.info("{} found in database, but is enabled. Disable first".format(name))
                    retval = False
                else:
                    self.logger.info("{} found in database, editing content".format(name))
            else: #create new item
                self.logger.info("{} not found, creating new item".format(name))
                db = {}
                newEntry = True

        # Create, check and update entry
        if retval:
            entryNew = deepcopy(db)
            changed = self.makeEntry(entryNew)
            retval = self.checkEntry(entryNew, newEntry, changed)

        """
        if changed and retval and not newEntry:
            if entryNew['enabled']:
                retval = self.ubnd(name)
                if not retval:
                    self.logger.warning("Unable to unbind {}".format(name))

        if retval:
            if not self.exists(self.engine.shareDir(name)):
                self.create(self.engine.shareDir(name))
                if retval:
                    self.logger.info("Created new shared folder: {}".format(self.engine.shareDir(name)))

        if retval:
            if entryNew['enabled']:
                mode = self.setMode(entryNew['uacc'], entryNew['sacc'])
            else:
                mode = self.modeDisabled()
            if mode != self.getMode(self.engine.shareDir(name)):
                self.chMode(self.engine.shareDir(name), mode)
                self.logger.info("Changed mountpoint mode: user {}, superuser {}".format(entryNew['uacc'], entryNew['sacc']))
        """

        if retval:
            if db:
                # remove old item from db
                if not self.isReferenced(name):
                    retval = self.engine.removeFromGroup(groups.SHARES, name)
            #add new item to db
            dbShare = {}
            dbShare[name] = entryNew
            self.engine.addToGroup(groups.SHARES, dbShare)
            self.logger.info("{} added/ edited".format(name))
            if entryNew['enabled']:
                if retval:
                    retval = self.isSourced(name)
                    if not retval:
                        self.logger.error("{} source doesn't exist: {}".format(name, entryNew['xmount']))
                if retval:
                    retval = self.link(self.sourceDir(name), self.engine.shareDir(name))
                    if not retval:
                        self.logger.error("{} Error binding share".format(name))
        else:
            self.logger.warning("{} not added/ edited".format(name))

        return retval

    def delSh(self, name):
        retval = False

        if not self.isReferenced(name):
            retval = self.dis(name, False)
        if retval:
            self.logger.info("{} deleted".format(name))
            self.clr(name) # Remove from DB
        else:
            self.logger.warning("{} not deleted".format(name))
        return retval

    def linkSingle(self, name, verbose = False):
        retval = False
        db = self.engine.checkKey(groups.SHARES, name)
        if db:
            retval = self.link(self.sourceDir(name), self.engine.shareDir(name))
        if verbose and not retval:
            self.logger.warning("{} not linked".format(name))
        return retval

    def linkAll(self, verbose = False):
        bndList = []
        shares = self.engine.checkGroup(groups.SHARES)
        if shares:
            for key, share in shares.items():
                bndItem={}
                bndItem['xhare'] = key
                if share['enabled']:
                    bndItem['linked'] = self.link(self.sourceDir(key), self.engine.shareDir(key))
                else:
                    bndItem['linked'] = False
                    if verbose:
                        if not share['enabled']:
                            self.logger.info("{} not linked, share disabled".format(key))
                        else:
                            self.logger.warning("{} not linked, no valid source found".format(key))
                bndList.append(bndItem)
        return bndList

    def legacyUnbind(self, name):
        retval = True
        mntfs = mountfs(self.logger)
        if mntfs.isMounted(self.engine.shareDir(name)):
            retval = mntfs.unbind(self.engine.shareDir(name), force = True, timeout = 5)
        del mntfs
        if retval and self.exists(self.engine.shareDir(name)):
            retval = self.delete(self.engine.shareDir(name))

        return retval

    ################## INTERNAL FUNCTIONS ###################

    def findShares(self, xmount, remotemount):
        myshares = [];
        shares = self.engine.checkGroup(groups.SHARES)
        if shares:
            for key, share in shares.items():
                if (share['xmount'] == xmount) and (share['remotemount'] == remotemount):
                    myshares.append(key)
        if not myshares:
            myshares.append("-");
        return myshares

    def sourceDir(self, name, src = ""):
        folder = ""
        db = self.engine.checkKey(groups.SHARES, name)
        if db:
            if not src:
                src = self.getSourceMountpoint(db['xmount'], db['remotemount'])
            if src:
                shfolder = ""
                if db['folder']:
                    if db['folder'][0] == "/":
                        shfolder = db['folder'][1:] # something weird in os.path.join
                    else:
                        shfolder = db['folder']
                folder = os.path.join(src, shfolder)
        return folder

    def clr(self, name):
        retval = False
        db = self.engine.checkKey(groups.SHARES, name)
        if db:
            if not self.isReferenced(name):
                retval = self.engine.removeFromGroup(groups.SHARES, name)
        if retval:
            self.logger.info("{} removed from database".format(name))
        else:
            self.logger.warning("{} removed from database".format(name))
        return retval

    def makeEntry(self, entry):
        changed = False

        if "xmount" in self.engine.settings:
            if "xmount" in entry:
                echanged =  entry['xmount'] != self.engine.settings['xmount']
            else:
                echanged = True
            changed = changed or echanged
            entry['xmount'] = self.engine.settings['xmount']
        elif not "xmount" in entry:
            changed = True
            entry['xmount'] = ""
        if "remotemount" in self.engine.settings:
            remotemount = self.engine.settings['remotemount']
            if "remotemount" in entry:
                echanged =  entry['remotemount'] != remotemount
            else:
                echanged = True
            changed = changed or echanged
            entry['remotemount'] = remotemount
        elif not "remotemount" in entry:
            changed = True
            entry['remotemount'] = False
            if entry['xmount']:
                db = self.engine.checkKey(groups.REMOTEMOUNTS, entry['xmount'])
                if db:
                    entry['remotemount'] = True
        if "folder" in self.engine.settings:
            if "folder" in entry:
                echanged =  entry['folder'] != self.engine.settings['folder']
            else:
                echanged = True
            changed = changed or echanged
            entry['folder'] = self.engine.settings['folder']
        elif not "folder" in entry:
            changed = True
            entry['folder'] = ""
        if not "enabled" in entry:
            changed = True
            entry['enabled'] = True
        return changed

    def checkEntry(self, entry, new = True, changed = True):
        retval = True

        if entry["xmount"]:
            if not new:
                if entry['remotemount']:
                    db = self.engine.checkKey(groups.REMOTEMOUNTS, entry['xmount'])
                else:
                    db = self.engine.checkKey(groups.MOUNTS, entry['xmount'])
                if not db:
                    self.logger.info("xmount {} does not exist, item not created".format(entry["xmount"]))
                    retval = False
        else:
            self.logger.info("Item doesn't have xmount, item not created")
            retval = False

        if retval:
            if entry["folder"]:
                exists = False
                src = self.getSourceMountpoint(entry['xmount'], entry['remotemount'])
                if src:
                    folder = os.path.join(src, entry['folder'])
                    exists = self.exists(folder)
                if not exists:
                    self.logger.info("folder {} on xmount {} does not exist, item not created".format(entry['folder'], entry["xmount"]))
                    retval = False

        return retval

######################### MAIN ##########################
if __name__ == "__main__":
    pass
