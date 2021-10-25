# -*- coding: utf-8 -*-
#########################################################
# SERVICE : xnas_engine.py                              #
#           Engine file with common funcitons for Xnas  #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import sys
import logging
import logging.handlers
import locale
import json
import signal
from common.ansi import ansi
import re
#########################################################

####################### GLOBALS #########################
VERSION = "1.0.0"
LOG_FILENAME     = "xnas.log"
LOG_MAXSIZE      = 100*1024*1024
HELPSTANDARD     = {"help": "this help file",
                    "version": "print version information",
                    "json": "display output in JSON format"}
NOARGS           = "no arguments"
SHARESFOLDER     = "/shares"
#########################################################

###################### FUNCTIONS ########################

#########################################################

class errors:
    OK                   = 0
    UNAVAILABLE          = 1
    DYNNOTMOUNTED        = 2
    UNHEALTHY            = 3
    REFNOTMOUNTED        = 4
    NOTMOUNTED           = 5
    HOSTFAILED           = 6
    NONETDEV             = 7
    NOCREDENTIALS        = 8
    ENABLEDNOTLINKED     = 9
    DISABLEDLINKED       = 10
    DISABLEDREFERENCED   = 11

class objects:
    NONE                 = 0
    MOUNT                = 1
    REMOTEMOUNT          = 2
    SHARE                = 3
    NETSHARE             = 4

class groups:
    SETTINGS = 'settings'
    MOUNTS = 'mounts'
    SHARES = 'shares'
    REMOTEMOUNTS = "remotemounts"
    NETSHARES = "netshares"

from common.database import database

#########################################################
# Class : xnas_engine                                   #
#########################################################

class xnas_engine(database):
    def __init__(self, name):
        self.name = name
        signal.signal(signal.SIGINT, self.exitSignal)
        signal.signal(signal.SIGTERM, self.exitSignal)
        self.logger = logging.getLogger('xnas')
        self.logger.setLevel(logging.INFO)
        logging.captureWarnings(True)
        tmformat=("{} {}".format(locale.nl_langinfo(locale.D_FMT),locale.nl_langinfo(locale.T_FMT)))
        tmformat=tmformat.replace("%y", "%Y")
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', tmformat)
        self.ch = None
        # Only write to logfile if write access
        LoggerPath = self.getLogger()
        if LoggerPath:
            # create file handler which logs even debug messages
            self.fh = logging.handlers.RotatingFileHandler(LoggerPath, maxBytes=LOG_MAXSIZE, backupCount=5)
            self.logger.addHandler(self.fh)
            self.fh.setFormatter(self.formatter)
        database.__init__(self, self.logger)

    def __del__(self):
        database.__del__(self)
        logging.shutdown()

    def __str__(self):
        str = """{}{}\    /
 \  /
  \/                  ____
  /\    |\  |   /\   /
 /  \   | \ |  /--\  \---\ <-------------------------------------------->
/    \  |  \| /    \ ____/ {}
{}A lightweight, eXtended Network Attached Storage system for linux devices{}
Version: {}""".format(ansi.bold, ansi.fg.blue, ansi.reset, ansi.italic, ansi.reset, VERSION)
        return str

    def __repr__(self):
        return "{}{}XNAS{}: {}A lightweight, eXtended Network Attached Storage system for linux devices{}".format(
                ansi.bold, ansi.fg.blue, ansi.reset, ansi.italic, ansi.reset)

    def isSudo(self):
        return os.getuid() == 0

    def StdoutLogging(self, switch):
        if switch:
            if not self.ch:
                # create console handler with a higher log level
                self.ch = logging.StreamHandler(sys.stdout)
                self.logger.addHandler(self.ch)
                self.ch.setFormatter(self.formatter)
        else:
            if self.ch:
                self.logger.removeHandler(self.ch)
                self.ch = None

    def needSudo(self):
        if not self.isSudo():
            print(repr(self))
            print("Superuser access required for this operation")
            print("Try running with: 'sudo {}'".format(self.name))
            exit(2)

    def parseOpts(self, argv, opts, args, extra, specopts = {}, specextra = (), preCheck = False):
        try:
            basicopts = opts.copy()
            opts.update(specopts)
            optlong, optshort = self.buildOpts(opts)
            parsedOpts, parsedArgs = self.GetOpt(argv[1:], optshort, optlong, preCheck)
        except:
            self.parseError()
        if not preCheck:
            for opt, arg in parsedOpts.items():
                if opt in ("help"):
                    self.printHelp(basicopts, args, extra, specopts, specextra)
                    exit()
                elif opt in ("version"):
                    print(self)
                    if self.name != "xnas":
                        print("Module: {}{}{}".format(ansi.underline, self.name, ansi.reset))
                        exit()
        return parsedOpts, parsedArgs

    def parseError(self, opt = ""):
        print(repr(self))
        print("Invalid option entered")
        if opt:
            print(opt)
        print("Enter '{} -h' for help".format(self.name))
        exit(2)

    def isJSON(self, jsonstr):
        retval = True
        try:
            json.loads(jsonstr)
        except:
            retval = False
        return retval

    def parseJSONStr(self, jsonstr):
        retval = {}
        if self.isJSON(jsonstr):
            retval = json.loads(jsonstr)
        return retval

    def parseJSON(self, jsonstr, opts):
        jsonopts = self.parseJSONStr(jsonstr)
        optlong, optshort = self.buildOpts(opts)

        for key, value in jsonopts.items():
            if not key in optlong:
                self.parseError()
        return jsonopts

    def settingsBool(self, settings, testkey, addkey = True, value = False):
        if self.hasSetting(settings, testkey):
            settings[testkey] = self.toBool(settings[testkey])
        elif addkey:
            settings[testkey] = value

    def toBool(self, val):
        retval = False
        if val == '':
            retval = True
        else:
            try:
                f = float(val)
                if f > 0:
                    retval = True
            except:
                if val.lower() == "true":
                    retval = True

        return retval

    def settingsInt(self, settings, testkey, addkey = True):
        if self.hasSetting(settings, testkey):
            settings[testkey] = self.toInt(settings[testkey])
        elif addkey:
            settings[testkey] = 0

    def toInt(self, val):
        retval = 0
        try:
            retval = int(val)
        except:
            pass
        return retval

    def settingsFloat(self, settings, testkey, addkey = True):
        if self.hasSetting(settings, testkey):
            settings[testkey] = self.toFloat(settings[testkey])
        elif addkey:
            settings[testkey] = 0.0

    def toFloat(self, val):
        retval = 0.0
        try:
            retval = float(val)
        except:
            pass
        return retval

    def settingsStr(self, settings, testkey, addkey = True, default = ""):
        if self.hasSetting(settings, testkey):
            pass
        elif addkey:
            settings[testkey] = default

    def hasSetting(self, settings, testkey):
        return testkey in settings

    def printJson(self, list):
        print(json.dumps(list))

    def printJsonResult(self, result):
        r = {}
        r['result'] = result
        print(json.dumps(r))

    def printUnmarked(self, data):
        print("{}".format(data))

    def printMarked(self, data, underline = False):
        if underline:
            print("{}{}{}{}".format(ansi.underline, ansi.bold, data, ansi.reset))
        else:
            print("{}{}{}{}{}".format(ansi.bg.lightgrey, ansi.fg.black, ansi.bold, data, ansi.reset))

    def printValues(self, dct):
        for item in self.getValues(dct):
            if item:
                print(item)
            else:
                self.printMarked("No data")

    def printList(self, lst):
        for item in lst:
            if item:
                print(item)

    def prettyPrintTable(self, tablelist):
        try:
            listlen = len(tablelist)
        except:
            listlen = 0
        if listlen == 0:
            self.printMarked("No data")
        else:
            keys = self.getKeys(tablelist[0])
            # get lengths
            collen = []
            for key in keys:
                collen.append(self.lentxt(key))
            for row in tablelist:
                i = 0
                for item in self.getValues(row):
                    if isinstance(item, list):
                        for listitem in item:
                            if self.lentxt(str(listitem)) > collen[i]:
                                collen[i] = self.lentxt(str(listitem))
                    else:
                        if self.lentxt(str(item)) > collen[i]:
                            collen[i] = self.lentxt(str(item))
                    i += 1
            #print keys
            i = 0
            print(ansi.bg.lightgrey + ansi.fg.black + ansi.bold, end = '')
            for key in keys:
                spaces = " " * (collen[i] - self.lentxt(key))
                i += 1
                print("{}{} ".format(key, spaces), end = '')
            print(ansi.reset)
            i = 0
            #print values:
            even = False
            for row in tablelist:
                if even:
                    print(ansi.bg.darkgrey, end = '')
                subrows = 1
                for item in self.getValues(row): # get longest list in row
                    if isinstance(item, list):
                        if len(item) > subrows:
                            subrows = len(item)
                for subrow in range(subrows):
                    i = 0
                    if even:
                        print(ansi.bg.darkgrey, end = '')
                    for item in self.getValues(row):
                        if isinstance(item, list):
                            if subrow < len(item):
                                spaces = " " * (collen[i] - self.lentxt(str(item[subrow])))
                                print("{}{} ".format(str(item[subrow]), spaces), end = '')
                            else:
                                spaces = " " * (collen[i])
                                print("{} ".format(spaces), end = '')
                        else:
                            if subrow == 0:
                                spaces = " " * (collen[i] - self.lentxt(str(item)))
                                print("{}{} ".format(str(item), spaces), end = '')
                            else:
                                spaces = " " * (collen[i])
                                print("{} ".format(spaces), end = '')
                        i += 1
                    if subrow<subrows-1:
                        print(ansi.reset)
                print(ansi.reset)
                even = not even

    def settings2Table(self, settings):
        settingsList = []

        if isinstance(settings, dict):
            for key, value in settings.items():
                setting = {}
                setting['setting'] = key
                if isinstance(value, dict):
                    extralist = []
                    for k2, v2 in value.items():
                        if isinstance(v2, list):
                            for v2item in v2:
                                extralist.append("{}={}".format(k2, v2item))
                        else:
                            extralist.append("{}={}".format(k2, v2))
                    setting['value'] = extralist
                else:
                    setting['value'] = value
                settingsList.append(setting)

        return settingsList

    def printObj(obj):
        prtObj = "none"
        if obj == objects.MOUNT:
            prtObj = "xmount"
        elif obj == objects.REMOTEMOUNT:
            prtObj = "xremotemount"
        elif obj == objects.SHARE:
            prtObj = "xshare"
        elif obj == objects.NETSHARE:
            prtObj = "xnetshare"
        return prtObj

    def exitSignal(self, signum = 0, frame = 0):
        self.logger.error("Execution interrupted, exit ...")
        exit(0)

    def findType(self, type):
        etype = None
        if type:
            stype = "groups." + type.upper() + "S"
            try:
                etype = eval(stype)
            except:
                pass
        return etype

    def findName(self, name, type):
        eobj = objects.NONE
        db = None

        etype = self.findType(type)

        if etype:
            db = self.checkKey(etype, name)
        else:
            # First look in shares
            db = self.checkKey(groups.SHARES, name)
            if not db:
                # Then on mounts
                db = self.checkKey(groups.MOUNTS, name)
                if not db:
                    # Then on remotemounts
                    db = self.checkKey(groups.REMOTEMOUNTS, name)
                    if not db:
                        # Finally on netshares
                        db = self.checkKey(groups.NETSHARES, name)
                        if db:
                            etype = groups.NETSHARES
                        else:
                            etype = ""
                    else:
                        etype = groups.REMOTEMOUNTS
                else:
                    etype = groups.MOUNTS
            else:
                etype = groups.SHARES

        if etype:
            sobj = "objects." + etype[:-1].upper()
            try:
                eobj = eval(sobj)
            except:
                pass

        return db, eobj

    def shareDir(self, dir):
        retval = ""
        if not dir:
            retval = SHARESFOLDER
        else:
            retval = os.path.join(SHARESFOLDER, dir)
        return retval

    def checkMethod(self, method):
        return method in ["disabled", "startup", "auto", "dynmount"]

    def tryInt(self, var):
        val = 0
        if not isinstance(var, int):
            try:
                val = int(var)
            except:
                pass
        else:
            val = var
        return val


    ################## INTERNAL FUNCTIONS ###################
    def lentxt(self, txt):
        ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
        return len(ansi_escape.sub('', txt))

    def getKeys(self, dct):
        keys = []
        for key, value in dct.items():
            keys.append(key)
        return keys

    def getValues(self, dct):
        values = []
        for key, value in dct.items():
            values.append(value)
        return values

    def buildOpts(self, opts):
        longopts = []
        shortopts = []
        allopts = HELPSTANDARD.copy()
        allopts.update(opts)

        for key, value in allopts.items():
            shortopt = self.mkShortOpt(shortopts, key)
            if shortopt:
                longopts.append(key)
                shortopts.append(shortopt)

        return longopts, shortopts

    def mkShortOpt(self, shortopts, name):
        opt = ""
        if len(name):
            st1 = name[0].lower()
            st2 = name[0].upper()
            if st1 in shortopts:
                if st2 in shortopts:
                    opt = self.mkShortOpt(shortopts, name[1:])
                else:
                    opt = st2
            else:
                opt = st1
        return opt

    def printHelp(self, opts, args, extra, specopts, specextra):
        allopts = HELPSTANDARD.copy()
        allopts.update(opts)

        HasOpts = len(allopts)>0
        HasArgs = len(args)>0
        HasSpecOpts = len(specopts)>0

        Arglist = ""
        MaxArg = 0
        MaxOpt = 0
        MaxSpecOpt = 0
        Dash = False
        if HasArgs:
            for key, value in args.items():
                if key == "-":
                    Dash = True
                    key = "<" + NOARGS + ">"
                if len(key) > MaxArg:
                    MaxArg = len(key)
            if Dash:
                key = NOARGS
                args[key] = args["-"]
                del args["-"]
            Arglist += "<arguments> "
        if HasOpts:
            Arglist += "<options> "
            for key, value in allopts.items():
                if len(key) > MaxOpt:
                    MaxOpt = len(key)
        if HasSpecOpts:
            for key, value in specopts.items():
                if len(key) > MaxSpecOpt:
                    MaxSpecOpt = len(key)

        print(repr(self))
        if self.name != "xnas":
            print("Module: {}{}{}".format(ansi.underline, self.name, ansi.reset))
        print("Usage:")
        print("    {} {}".format(self.name, Arglist))
        if HasArgs:
            print("    <arguments>:")
            for key, value in args.items():
                if key == NOARGS:
                    key = "<" + NOARGS + ">"
                spaces = " " * (MaxArg - len(key))
                print("        {}{}: {}".format(key, spaces, value))
        if HasOpts:
            print("    <options>: ")
            shortopts = []
            for key, value in allopts.items():
                shortopt = self.mkShortOpt(shortopts, key)
                shortopts.append(shortopt)
                if shortopt:
                    spaces = " " * (MaxOpt - len(key))
                    print("        -{}, --{}{}: {}".format(shortopt, key, spaces, value))
        if extra:
            print("")
            print(extra)

        if specextra:
            print("")
            print(specextra)

        if HasSpecOpts:
            print("    <options>: ")
            shortspecopts = []
            for key, value in specopts.items():
                shortopt = self.mkShortOpt(shortopts, key)
                shortopts.append(shortopt)
                if shortopt:
                    spaces = " " * (MaxSpecOpt - len(key))
                    print("        -{}, --{}{}: {}".format(shortopt, key, spaces, value))

    def GetOpt(self, argv, optshort, optlong, preCheck):
        args = []
        opts = {}
        i = 0
        argc = len(argv)
        while i < argc:
            key = ""
            if argv[i][0] == "-": #opt
                if argv[i][1] == "-": # long opt
                    key, value, nextind = self.ParseOpt(argv, i, optshort, optlong)
                    try:
                        ind = optlong.index(key) # ValueError if not in list
                    except ValueError as e:
                        key = ""
                        if not preCheck:
                            raise ValueError(e)
                    i += nextind
                else: # short opt
                    key, value, nextind = self.ParseOpt(argv, i, optshort, optlong)
                    try:
                        ind = optshort.index(key) # ValueError if not in list
                        key = optlong[ind]
                    except ValueError as e:
                        key = ""
                        if not preCheck:
                            raise ValueError(e)
                    i += nextind
                if key:
                    opts[key] = value
            else: # arg
                args.append(argv[i])
                i += 1
        return opts, args

    def ParseOpt(self, argv, i, optshort, optlong):
        key = ""
        value = ""
        isLong = argv[i][1] == "-"
        argc = len(argv)
        IsPos = argv[i].find("=")
        SpacePos = argv[i].find(" ")
        nextind = 1

        if isLong:
            if IsPos >= 0:
                key = argv[i][2:IsPos]
                value = argv[i][IsPos+1:]
            elif SpacePos >= 0:
                key = argv[i][2:SpacePos]
                value = argv[i][SpacePos+1:]
            else:
                key = argv[i][2:]
                #try to find value in next word
                if (i+2) < argc:
                    if (len(argv[i+2]) > 0) and (argv[i+2][0] == "-"):
                        if len(argv[i+1]) == 0:
                            nextind = 2
                        elif argv[i+1][0] != "-":
                            value = argv[i+1]
                            nextind = 2
                elif (i+1) < argc:
                    if len(argv[i+1]) == 0:
                        nextind = 2
                    elif argv[i+1][0] != "-":
                        value = argv[i+1]
                        nextind = 2
        else: # short
            key = argv[i][1]
            slen = len(argv[i][1:])
            if IsPos == 2:
                value = argv[i][IsPos+1:]
            elif SpacePos == 2:
                value = argv[i][SpacePos+1:]
            elif slen > 1:
                value = argv[i][2:]
            else:
                #try to find value in next word
                if (i+2) < argc:
                    if (len(argv[i+2]) > 0) and (argv[i+2][0] == "-"):
                        if len(argv[i+1]) == 0:
                            nextind = 2
                        elif argv[i+1][0] != "-":
                            value = argv[i+1]
                            nextind = 2
                elif (i+1) < argc:
                    if len(argv[i+1]) == 0:
                        nextind = 2
                    elif  argv[i+1][0] != "-":
                        value = argv[i+1]
                        nextind = 2
        return key, value, nextind

    def getLogger(self):
        logpath = "/var/log"
        LoggerPath = "/dev/null"
        # first look in log path
        if os.path.exists(logpath):
            if os.access(logpath, os.W_OK):
                LoggerPath = os.path.join(logpath,LOG_FILENAME)
        return LoggerPath

######################### MAIN ##########################
if __name__ == "__main__":
    pass
