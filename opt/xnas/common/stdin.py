# -*- coding: utf-8 -*-
#########################################################
# SERVICE : stdin.py                                    #
#           This class contians some standard input     #
#           functions                                   #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import sys
import tty
import termios
from threading import Thread
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : stdin                                         #
#########################################################
class stdin(Thread):
    def __init__(self, txt = "", exitevent = None, echo = True, mutex = None, displaylater = False, background = False):
        self.txt = txt
        self.exitevent = exitevent
        self.echo = echo
        self.mutex = mutex
        self.displaylater = displaylater
        self.lastinput = ""
        self._initspecial()
        self._inittext()
        Thread.__init__(self)
        if background:
            self.start()

    def __del__(self):
        pass

    def run(self):
        self._input()

    def input(self, txt, exitevent = None, echo = None, mutex = None, displaylater = None):
        if exitevent != None:
            self.exitevent = exitevent
        if echo != None:
            self.echo = echo
        if mutex != None:
            self.mutex = mutex
        if displaylater != None:
            self.displaylater = displaylater
        self.txt = txt
        return self._input()

    def _input(self):
        self._initspecial()
        self._inittext()
        mutexdone = False
        txtdone = False
        if not self.displaylater:
            if self.txt:
                sys.stdout.write(self.txt)
                sys.stdout.flush()
        end = False
        while not end:
            cont = True
            while cont:
                char = self._readchar()
                cont = self._testspecial(char)
                self._handlespecial()
            if self._testterm(char):
                end = True
                if not self.exitevent:
                    return(char)
            elif self._testnl(char):
                end = True
            else:
                if self.mutex and not mutexdone:
                    mutexdone = True
                    self.mutex.acquire()
                if self.displaylater and not txtdone:
                    txtdone = True
                    if self.txt:
                        sys.stdout.write(self.txt)
                        sys.stdout.flush()
                self._addtext(char)

        if self.text['val']:
            self.lastinput = self.text['val']
        else:
            self.lastinput = '\n'
        if self.mutex and mutexdone:
            self.mutex.release()
        return self.lastinput

    def getinput(self):
        retinp = self.lastinput
        self.lastinput = ""
        return retinp

    def inputchar(self, txt = "", exitevent = None, echo = None, displaylater = None):
        if exitevent != None:
            self.exitevent = exitevent
        if echo != None:
            self.echo = echo
        if displaylater != None:
            self.displaylater = displaylater
        self.txt = txt
        return self._inputchar()

    def _inputchar(self):
        self._initspecial()
        cont = True
        if not self.displaylater:
            if self.txt:
                sys.stdout.write(self.txt)
                sys.stdout.flush()
        while cont:
            char = self._readchar()

            cont = self._testspecial(char)

        if self._testterm(char):
            if self.exitevent:
                char = ""
        else:
            if self.displaylater:
                if self.txt:
                    sys.stdout.write(self.txt)
                    sys.stdout.flush()
            if self.echo:
                sys.stdout.write(char+"\n")

        return char

    def _readchar(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def _inittext(self):
        self.text = {}
        self.text['pos'] = 0
        self.text['len'] = 0
        self.text['val'] = ""

    def _addtext(self, char):
        ntext = self.text['val'][:self.text['pos']]+char+self.text['val'][self.text['pos']:]
        if self.echo:
            if self.text['pos'] == self.text['len']:
                sys.stdout.write(char)
                sys.stdout.flush()
            else:
                sys.stdout.write(ntext[self.text['pos']:])
                i = self.text['len'] - self.text['pos']
                while i:
                    sys.stdout.write('\b')
                    i -= 1
                sys.stdout.flush()
        self.text['pos'] += 1
        self.text['len'] += 1
        self.text['val'] = ntext

    def _deltext(self, bs = False):
        if bs:
            pos = self.text['pos']-1
        else:
            pos = self.text['pos']
        ntext = self.text['val'][:pos]+self.text['val'][pos+1:]
        if self.echo:
            if bs:
                if self.text['pos'] == self.text['len']:
                    sys.stdout.write(' \b')
                    sys.stdout.flush()
                else:
                    sys.stdout.write(ntext[self.text['pos'] - 1:])
                    sys.stdout.write(' ')
                    i = self.text['len'] - self.text['pos'] + 1
                    while i:
                        sys.stdout.write('\b')
                        i -= 1
                    sys.stdout.flush()
            else: # del
                if self.text['pos'] < self.text['len']:
                    sys.stdout.write(ntext[self.text['pos']:])
                    sys.stdout.write(' ')
                    i = self.text['len'] - self.text['pos']
                    while i:
                        sys.stdout.write('\b')
                        i -= 1
                    sys.stdout.flush()
        if bs:
            self.text['pos'] -= 1
        self.text['len'] -= 1
        self.text['val'] = ntext

    def _initspecial(self):
        self.escchar = False
        self.navchar = False
        self.spcchar = False
        self.chbs    = False
        self.chdel   = False
        self.chleft  = False
        self.chright = False
        self.chhome  = False
        self.chend   = False

    def _testspecial(self, char):
        retval = False

        if self.spcchar:
            if ord(char) == 126: # delete
                self.chdel = True
                retval = True
            self.spcchar = False

        if self.navchar:
            if ord(char) == 51: # special character after navigation character
                self.spcchar = True
            elif ord(char) == 68: # left navigation
                self.chleft = True
            elif ord(char) == 67: # right navigation
                self.chright = True
            elif ord(char) == 72: # home navigation
                self.chhome = True
            elif ord(char) == 70: # end navigation
                self.chend = True
            retval = True
            if ord(char) != 53 and ord(char) != 54: # page up or page down
                self.navchar = False

        if self.escchar:
            if ord(char) == 91: # navigation character after escape
                self.navchar = True
                retval = True
            self.escchar = False

        if not retval:
            if ord(char) == 27: # escape character
                self.escchar = True
                retval = True
            if ord(char) == 127: # bs
                self.chbs = True
                retval = True

        return retval

    def yn_choice(self, message, default='y'):
        choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
        choice = self.inputchar("{} ({})".format(message, choices))
        values = ('y', 'yes', '') if choices == 'Y/n' else ('y', 'yes')
        return choice.strip().lower() in values

    def eprint(self, *args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

    def _testterm(self, char):
        retval = False
        if ord(char) == 3: #^C
            if self.exitevent:
                self.exitevent.set()
            if self.echo:
                sys.stdout.write('^C\n')
            retval = True
        return retval

    def _testnl(self, char):
        retval = False
        if ord(char) == 13: #newline
            if self.echo:
                sys.stdout.write('\n')
            retval = True
        return retval

    def _handlespecial(self):
        self._handlebs()
        self._handledel()
        self._handleleft()
        self._handleright()
        self._handlehome()
        self._handleend()

    def _handlebs(self):
        if self.chbs:
            if self.text['pos'] > 0:
                if self.echo:
                    sys.stdout.write('\b')
                    sys.stdout.flush()
                self._deltext(True)
            self.chbs = False

    def _handledel(self):
        if self.chdel:
            if self.text['pos'] > 0 and self.text['pos'] < self.text['len']:
                self._deltext(False)
            self.chdel = False

    def _handleleft(self):
        if self.chleft:
            if self.text['pos'] > 0:
                if self.echo:
                    sys.stdout.write('\b')
                    sys.stdout.flush()
                self.text['pos'] -= 1
            self.chleft = False

    def _handleright(self):
        if self.chright:
            if self.text['pos'] < self.text['len']:
                if self.echo:
                    sys.stdout.write(self.text['val'][self.text['pos']])
                    sys.stdout.flush()
                self.text['pos'] += 1
            self.chright = False

    def _handlehome(self):
        if self.chhome:
            if self.text['pos'] > 0:
                if self.echo:
                    i = self.text['pos']
                    while i:
                        sys.stdout.write('\b')
                        i -= 1
                    sys.stdout.flush()
                self.text['pos'] = 0
            self.chhome = False

    def _handleend(self):
        if self.chend:
            if self.text['pos'] < self.text['len']:
                if self.echo:
                    sys.stdout.write(self.text['val'][self.text['pos']:])
                    sys.stdout.flush()
                self.text['pos'] = self.text['len']
            self.chend = False

######################### MAIN ##########################
if __name__ == "__main__":
    pass
