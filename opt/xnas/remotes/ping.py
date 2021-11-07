# -*- coding: utf-8 -*-
#########################################################
# SERVICE : ping.py                                     #
#           remotemount ping remote devices             #
#           for xnas                                    #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
from urllib.parse import urlsplit
from common.shell import shell
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : ping                                          #
#########################################################
class ping(object):
    def __init__(self):
        pass

    def __del__(self):
        pass

    ### Use socket to test complete url and port if port if applicable
    # and required somewher
    #https://serverfault.com/questions/309357/ping-a-specific-port

    def ping(self, url, timeout = None):
        available = False
        base = self.getBaseUrl(url)
        to=""
        if timeout:
            to="-w{} ".format(timeout)
        cmd = "ping -c1 {}{}".format(to, base)

        try:
            shell().command(cmd)
            available = True
        except:
            pass
        return available

    def getBaseUrl(self, url):
        base = ""
        try:
            tmp = urlsplit(url)
            base = tmp.netloc
            if not base:
                # try to find between @ and :
                part = url.split(":")[0]
                base = part.split("@")[-1]
        except:
            pass
        return base

    def getPath(self, url):
        path = ""
        try:
            tmp = urlsplit(url)
            path = tmp.path
        except:
            pass
        return path

    def getPort(self, url):
        port = 0

        try:
            tmp = urlsplit(url)
            port = int(tmp.port)
        except:
            pass

        return port

######################### MAIN ##########################
if __name__ == "__main__":
    pass
