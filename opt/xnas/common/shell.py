# -*- coding: utf-8 -*-
#########################################################
# SERVICE : shell.py                                    #
#           runs shell commands and stores output       #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import subprocess
#########################################################

####################### GLOBALS #########################
CMDNOTEXIST = 127
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : shell                                         #
#########################################################
class shell(object):
    def __init__(self):
        pass

    def __del__(self):
        pass

    def runCommand(self, cmd, input = None, timeout = None):
        retval = 127, "", ""
        if input:
            input = input.encode("utf-8")
        try:
            if timeout == 0:
                timout = None
            out = subprocess.run(cmd, shell=True, capture_output=True, input = input, timeout = timeout)
            retval = out.returncode, out.stdout.decode("utf-8"), out.stderr.decode("utf-8")
        except subprocess.TimeoutExpired:
            retval = 124, "", ""

        return retval

    def command(self, cmd, retcode = 0, input = None, timeout = None, timeoutError = False):
        returncode, stdout, stderr = self.runCommand(cmd, input, timeout)

        if returncode == 124 and not timeoutError:
            returncode = 0
        if retcode != returncode:
            self.handleError(returncode, stderr)

        return stdout

    def commandExists(self, cmd):
        returncode, stdout, stderr = self.runCommand(cmd)

        return returncode != CMDNOTEXIST

    def handleError(self, returncode, stderr):
        exc = ("External command failed.\n"
               "Command returned: {}\n"
               "Error message:\n{}").format(returncode, stderr)
        raise Exception(exc)

######################### MAIN ##########################
if __name__ == "__main__":
    pass
