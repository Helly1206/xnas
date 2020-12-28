# -*- coding: utf-8 -*-
#########################################################
# SERVICE : ip.py                                       #
#           Get the current ip address                  #
#                                                       #
#           I. Helwegen 2020                            #                                            #
#########################################################

####################### IMPORTS #########################
from common.shell import shell
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : ip                                            #
#########################################################
class ip(object):
    def __init__(self):
        pass

    def __del__(self):
        pass

    def get(self):
        myIp = ""
        cmd = "hostname -I"
        try:
            myIp = shell().command(cmd).strip().split()[0]
        except:
            pass
        return myIp

    def mask(self, mask, myIp = ""):
        if not myIp:
            myIp = self.get()
        else:
            if not self.isIp(myIp):
                myIp = self.get()
        ipParts = myIp.split('.')
        myMask = ""
        if mask > 32:
            mask = 32
        useMask = (2**mask-1) << (32 - mask)

        ipInt=[]
        for ipPart in reversed(ipParts):
            maskPart = useMask % 256
            useMask = useMask >> 8

            try:
                ipInt.append(int(ipPart) & maskPart)
            except:
                pass

        myMask =  "{}.{}.{}.{}/{}".format(ipInt[3],ipInt[2],ipInt[1],ipInt[0],mask)

        return myMask
        
    def ipMask(self, myIp):
        return self.mask(self.getMask(myIp), self.getIp(myIp))

    def isIp(self, myIp):
        retval = False
        ipParts = myIp.split('.')
        if len(ipParts) == 4:
            for ipPart in ipParts:
                retval = self.isInt(ipPart, 255)
                if not retval:
                    break

        return retval

    def getIp(self, myIp):
        retval = 32
        maskParts = myIp.split('/')
        if len(maskParts) >= 1:
            if self.isIp(maskParts[0]):
                retval = maskParts[0]
            
        return retval

    def getMask(self, myIp):
        retval = 32
        maskParts = myIp.split('/')
        if len(maskParts) == 2:
            if self.isInt(maskParts[1], 32):
                retval = int(maskParts[1])
            
        return retval

    def isMaskOnly(self, myIp):
        retval = False
        maskParts = myIp.split('/')
        if len(maskParts) == 2:
            retval = len(maskParts[0]) == 0
            if retval:
                retval = self.isInt(maskParts[1], 32)

        return retval

    def isIpMask(self, myIp):
        retval = False
        maskParts = myIp.split('/')
        if len(maskParts) == 2:
            retval = self.isIp(maskParts[0])
            if retval:
                retval = self.isInt(maskParts[1], 32)

        return retval

################## INTERNAL FUNCTIONS ###################

    def isInt(self, val, maxval, minval = 0):
        retval = False
        try:
            ival = int(val)
            if ival <= maxval and ival >= minval:
                retval = True
        except:
            pass

        return retval


######################### MAIN ##########################
if __name__ == "__main__":
    pass
