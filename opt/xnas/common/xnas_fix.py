# -*- coding: utf-8 -*-
#########################################################
# SERVICE : xnas_fix.py                                 #
#           Fixes broken mounts and shares              #
#           (if possible)                               #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import logging
from copy import deepcopy
from mounts.mount import mount
from remotes.remotemount import remotemount
from common.xnas_engine import groups
from common.xnas_engine import errors
from common.xnas_engine import objects
from shares.share import share
from net.netshare import netshare
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : xnas_fix                                      #
#########################################################
class xnas_fix(object):
    def __init__(self, engine, Mount = None, Remotemount = None, Share = None, Net = None):
        self.logger = logging.getLogger('xnas.fix')
        self.engine = engine
        self.msgLst = []
        self.msgCnt = 0
        self.selfMount = False
        if Mount:
            self.Mount = Mount
        else:
            self.Mount = mount(engine)
            self.selfMount = True
        self.selfRemotemount = False
        if Remotemount:
            self.Remotemount = Remotemount
        else:
            self.Remotemount = remotemount(engine)
            self.selfRemotemount = True
        self.selfShare = False
        if Share:
            self.Share = Share
        else:
            self.Share = share(engine)
            self.selfShare = True
        self.selfNet = False
        if Net:
            self.Net = Net
        else:
            self.Net = netshare(engine)
            self.selfNet = True

    def __del__(self):
        if self.selfNet:
            del self.Net
        if self.selfShare:
            del self.Share
        if self.selfRemotemount:
            del self.Remotemount
        if self.selfMount:
            del self.Mount
        del self.msgLst

    def fix(self, Errors):
        self.msgLst = []
        self.msgCnt = 0
        for Error in Errors:
            if Error['obj'] == objects.MOUNT:
                self.fixMount(Error)
            elif Error['obj'] == objects.REMOTEMOUNT:
                self.fixRemoteMount(Error)
            elif Error['obj'] == objects.SHARE:
                self.fixShare(Error)
            elif Error['obj'] == objects.NETSHARE:
                self.fixNet(Error)
            else:
                self.logWarning("{}: Unknown error reported, unable to fix {}-{}".format(Error['name'], Error['obj'], Error['check']))
    
    def GetList(self):
        return self.msgLst

    ################## INTERNAL FUNCTIONS ###################

    def fixMount(self, Error):
        if Error['check'] == errors.UNAVAILABLE:
            self.logError("{}: [Mount] Device is unavailable".format(Error['name']))
            self.logError("{}: [Mount] Xnas cannot fix this problem, please check your hardware".format(Error['name']))
            self.logError("{}: [Mount] References are disabled".format(Error['name']))
            refs = self.Mount.getReferenced(Error['name'])
            if refs:
                retval = True
                for ref in refs:
                    if retval:
                        retval = self.Share.dis(ref)
                    if not retval:
                        break
                if retval:
                    self.engine.update()
                else:
                    self.logError("{}: [Mount] Unable to disable reference: {}".format(Error['name'], ref))
            else:
                self.logInfo("{}: [Mount] Is not referenced".format(Error['name']))
            self.logWarning("{}: [Mount] Fix fstab or remove mount from datatase using xmount del or clr".format(Error['name']))
        elif Error['check'] == errors.AUTONOTMOUNTED:
            self.logWarning("{}: [Mount] Trying to mount device, as it is not automounted".format(Error['name']))
            retval = self.Mount.mnt(Error['name'])
            if not retval:
                self.logError("{}: [Mount] Unable to mount device, please try mounting manually".format(Error['name']))
        elif Error['check'] == errors.UNHEALTHY:
            self.logError("{}: [Mount] Device is mounted but not healthy".format(Error['name']))
            self.logError("{}: [Mount] Xnas cannot fix this problem, please check your filesystem".format(Error['name']))
        elif Error['check'] == errors.REFNOTMOUNTED:
            self.logWarning("{}: [Mount] Trying to mount device, as it is referenced".format(Error['name']))
            retval = self.Mount.mnt(Error['name'])
            if not retval:
                self.logError("{}: [Mount] Unable to mount device, references are disabled".format(Error['name']))
                refs = self.Mount.getReferenced(Error['name'])
                if refs:
                    retval = True
                    for ref in refs:
                        if retval:
                            retval = self.Share.dis(ref)
                        if not retval:
                            break
                    if retval:
                        self.engine.update()
                    else:
                        self.logError("{}: [Mount] Unable to disable reference: {}".format(Error['name'], ref))
                else:
                    self.logInfo("{}: [Mount] Is not referenced".format(Error['name']))

    def fixRemoteMount(self, Error):
        if Error['check'] == errors.UNAVAILABLE:
            self.logError("{}: [Remotemount] Device is unavailable".format(Error['name']))
            self.logError("{}: [Remotemount] Xnas cannot fix this problem, did you manually remove it from fstab?".format(Error['name']))
            refs = self.Remotemount.getReferenced(Error['name'])
            if refs:
                retval = True
                for ref in refs:
                    if retval:
                        retval = self.Share.dis(ref)
                    if not retval:
                        break
                if retval:
                    self.engine.update()
                else:
                    self.logError("{}: [Remotemount] Unable to disable reference: {}".format(Error['name'], ref))
            else:
                self.logInfo("{}: [Remotemount] Is not referenced".format(Error['name']))
            self.logWarning("{}: [Remotemount] Fix fstab or remove mount from datatase using xremotemount del or clr".format(Error['name']))
        elif Error['check'] == errors.AUTONOTMOUNTED:
            self.logWarning("{}: [Remotemount] Trying to mount device, as it is not automounted".format(Error['name']))
            retval = self.Remotemount.mnt(Error['name'])
            if not retval:
                self.logError("{}: [Remotemount] Unable to mount device, please try mounting manually".format(Error['name']))
        elif Error['check'] == errors.UNHEALTHY:
            self.logError("{}: [Remotemount] Device is mounted but not healthy".format(Error['name']))
            self.logError("{}: [Remotemount] Xnas cannot fix this problem, please check your filesystem".format(Error['name']))
        elif Error['check'] == errors.REFNOTMOUNTED:
            self.logWarning("{}: [Remotemount] Trying to mount device, as it is referenced".format(Error['name']))
            retval = self.Remotemount.mnt(Error['name'])
            if not retval:
                self.logError("{}: [Remotemount] Unable to mount device, references are disabled".format(Error['name']))
                refs = self.Remotemount.getReferenced(Error['name'])
                if refs:
                    retval = True
                    for ref in refs:
                        if retval:
                            retval = self.Share.dis(ref)
                        if not retval:
                            break
                    if retval:
                        self.engine.update()
                    else:
                        self.logError("{}: [Remotemount] Unable to disable reference: {}".format(Error['name'], ref))
                else:
                    self.logInfo("{}: [Remotemount] Is not referenced".format(Error['name']))
        elif Error['check'] == errors.HOSTFAILED:
            self.logError("{}: [Remotemount] Host is unreachable".format(Error['name']))
            self.logError("{}: [Remotemount] Xnas cannot fix this problem, check your connection or host computer".format(Error['name']))
        elif Error['check'] == errors.NONETDEV:
            self.logError("{}: [Remotemount] Device not marked as '_netdev'".format(Error['name']))
            db = self.engine.checkKey(groups.REMOTEMOUNTS, Error['name'])
            entry = self.Remotemount.getEntry(fsname=self.Remotemount.buildDbURL(db))
            entry['options'].insert(0,"_netdev")
            retval = self.Remotemount.updateEntry(entry, False)
            if retval:
                self.logInfo("{}: [Remotemount] Added '_netdev' option".format(Error['name']))
            else:
                self.logError("{}: [Remotemount] Unable to add '_netdev' option".format(Error['name']))
        elif Error['check'] == errors.NOCREDENTIALS:
            self.logError("{}: [Remotemount] Device doesn't have credentials and doesn't have 'guest' option".format(Error['name']))
            db = self.engine.checkKey(groups.REMOTEMOUNTS, Error['name'])
            entry = self.Remotemount.getEntry(fsname=self.Remotemount.buildDbURL(db))
            entry['options'].append("guest")
            retval = self.Remotemount.updateEntry(entry, False)
            if retval:
                self.logInfo("{}: [Remotemount] Added 'guest' option".format(Error['name']))
                self.logInfo("{}: [Remotemount] If credentials are required, please use 'xremotemount add' with credentials".format(Error['name']))
            else:
                self.logError("{}: [Remotemount] Unable to fix credentials option".format(Error['name']))

    def fixShare(self, Error):
        cError = deepcopy(Error)
        if cError['check'] == errors.UNAVAILABLE:
            db = self.engine.checkKey(groups.SHARES, Error['name'])
            if db:
                self.logError("{}: [Share] Source device '{}' is unavailable".format(Error['name'], db['xmount']))
                self.logWarning("{}: [Share] Trying to mount source device".format(Error['name']))
                if db['remotemount']:
                    retval = self.Remotemount.mnt(db['xmount'])
                else:
                    retval = self.Mount.mnt(db['xmount'])
                if not retval:
                    self.logError("{}: [Share] Unable to mount source device, please try mounting manually".format(Error['name']))
                    self.logError("{}: [Share] Xnas cannot fix this problem".format(Error['name']))
                else:
                    if self.Share.isReferenced(Error['name']):
                        cError['check'] = errors.REFNOTMOUNTED
                    else:
                        cError['check'] == errors.NOTMOUNTED
            else:
                self.logError("{}: [Share] Xnas cannot fix this problem, share not found in database".format(Error['name']))
        if cError['check'] == errors.REFNOTMOUNTED:
            self.logWarning("{}: [Share] Trying to bind device, as it is referenced".format(Error['name']))
            retval = self.Share.bnd(Error['name'])
            if not retval:
                self.logError("{}: [Share] Unable to bind device, references are inaccessible".format(Error['name']))
                #ref = self.Share.getReferenced(Error['name'])
                #retval = self.Netshare.dis(ref)
                #if not retval:
                #    self.logError("{}: [Share] Unable to disable reference: {}".format(Error['name'], ref))
        elif cError['check'] == errors.NOTMOUNTED:
            self.logWarning("{}: [Share] Trying to bind device, as it should be bound".format(Error['name']))
            retval = self.Share.bnd(Error['name'])
            if not retval:
                self.logError("{}: [Share] Unable to bind device".format(Error['name']))

    def fixNet(self, Error):
        if Error['check'] == errors.UNAVAILABLE:
            db = self.engine.checkKey(groups.NETSHARES, Error['name'])
            if db:
                self.logError("{}: [Netshare] Source device '{}' is unavailable".format(Error['name'], Error['name']))
                db2 = self.engine.checkKey(groups.SHARES, Error['name'])
                if not db2:
                    self.logError("{}: [Netshare] Source device doesn't exist, removing netshare".format(Error['name']))
                    retval = self.Net.delNsh(Error['name'])
                    if not retval:
                        self.logError("{}: [Netshare] Unable to remove netshare".format(Error['name']))
                        self.logError("{}: [Netshare] Xnas cannot fix this problem".format(Error['name']))
                    else:
                        self.logInfo("{}: [Netshare] Netshare removed".format(Error['name']))
                else:
                    self.logWarning("{}: [Netshare] Trying to bind source device, as it should be bound".format(Error['name']))
                    retval = self.Share.bnd(Error['name'])
                    if not retval:
                        self.logError("{}: [Netshare] Unable to bind source device, please try binding manually".format(Error['name']))
                        self.logError("{}: [Netshare] Xnas cannot fix this problem".format(Error['name']))
                    else:
                        self.logInfo("{}: [Netshare] source device bound".format(Error['name']))
            else:
                self.logError("{}: [Netshare] Xnas cannot fix this problem, netshare not found in database".format(Error['name']))

    def logError(self, message):
        msg = {}
        self.msgCnt += 1
        msg['#'] = self.msgCnt
        msg['level'] = "ERROR"
        msg['message'] = message
        self.msgLst.append(msg)
        self.logger.error(message)
        
    def logWarning(self, message):
        msg = {}
        self.msgCnt += 1
        msg['#'] = self.msgCnt
        msg['level'] = "WARNING"
        msg['message'] = message
        self.msgLst.append(msg)
        self.logger.warning(message)
        
    def logInfo(self, message):
        msg = {}
        self.msgCnt += 1
        msg['#'] = self.msgCnt
        msg['level'] = "INFO"
        msg['message'] = message
        self.msgLst.append(msg)
        self.logger.info(message)

######################### MAIN ##########################
if __name__ == "__main__":
    pass
