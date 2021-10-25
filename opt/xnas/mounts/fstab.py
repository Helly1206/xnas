# -*- coding: utf-8 -*-
#########################################################
# SERVICE : fstab.py                                    #
#           fstab operations for xnas                   #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import shutil
from common.ls import ls
from common.shell import shell
from common.systemdctl import systemdctl
#########################################################

####################### GLOBALS #########################
FSTABBACKUP = ".bak"
FSTABLOC = "/etc/"
FSTABNAME = "fstab"
FSTABFILE = FSTABLOC + FSTABNAME
FSTABFILTER = FSTABNAME + ".*" + FSTABBACKUP
FSTABBACKUPS = 9
TABSIZE = 8
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : fstab                                         #
#########################################################
class fstab(object):
    def __init__(self, logger, remote = False):
        self.logger = logger
        self.entries = []
        self.remote = remote
        try:
            self.tuneType("Whatever")
        except Exception as e:
            self.logger.error("devices must be loaded in parent")
            exit(1)
        try:
            self.readFstab()
        except Exception as e:
            self.logger.error("Error reading system mount information")
            self.logger.error(e)
            exit(1)

    def __del__(self):
        del self.entries

    def getEntries(self, typefilter = []):
        entries = []
        for entry in self.entries:
            if not typefilter:
                entries.append(entry['content'])
            elif self.tuneType(entry['content']['type']) in typefilter:
                entries.append(entry['content'])
        return entries

    def findEntry(self, blkdevice):
        return self.getEntryFromLine(self.findEntryLine(blkdevice['uuid'], blkdevice['fsname'], blkdevice['label']))

    def updateEntry(self, entry, new = True):
        retval = False
        linenr = -1

        if not new:
            linenr = self.findEntryLine(entry['uuid'], entry['fsname'], entry['label'])

        if linenr < 0:
            newEntry = {}
            newEntry['line'] = linenr
            newEntry['content'] = entry
            self.entries.append(newEntry)
        else:
            newEntry = self.getEntryFromLine(linenr, True)
            newEntry['content'] = entry

        try:
            self.writeFstabLine(linenr)
            retval = True
        except Exception as e:
            self.logger.error("Error writing system mount information")
            self.logger.error(e)

        return retval

    def deleteEntry(self, uuid = "", fsname = "", label = ""):
        line = self.getEntryLine(uuid, fsname, label)
        try:
            self.delFstabLine(line)
            retval = True
        except Exception as e:
            self.logger.error("Error writing system mount information")
            self.logger.error(e)
        return retval

    def getEntry(self, uuid = "", fsname = "", label = ""):
        return self.getEntryFromLine(self.getEntryLine(uuid, fsname, label))

    def getHealth(self, uuid = "", fsname = "", label = "", isMounted = False, hasHost = True):
        retval = "OFFLINE"
        if not self.getEntry(uuid, fsname, label):
            retval = "UNAVAIL"
        elif not hasHost:
            retval = "HOSTFAIL"
        elif isMounted:
            retval = "ONLINE"
        return retval

    def isEna(self, uuid = "", fsname = "", label = ""):
        retval = False
        line = self.getEntryLine(uuid, fsname, label)
        entry = self.getEntryFromLine(line)
        if not "noauto" in entry["options"]:
            retval = True
        return retval

    def ena(self, uuid = "", fsname = "", label = ""):
        retval = False
        line = self.getEntryLine(uuid, fsname, label)
        entry = self.getEntryFromLine(line)
        if "noauto" in entry["options"]:
            entry["options"].remove("noauto")
        try:
            self.writeFstabLine(line)
            retval = True
        except Exception as e:
            self.logger.error("Error writing system mount information")
            self.logger.error(e)
        return retval

    def dis(self, uuid = "", fsname = "", label = ""):
        retval = False
        line = self.getEntryLine(uuid, fsname, label)
        entry = self.getEntryFromLine(line)
        if not "noauto" in entry["options"]:
            entry["options"].append("noauto")
        try:
            self.writeFstabLine(line)
            retval = True
        except Exception as e:
            self.logger.error("Error writing system mount information")
            self.logger.error(e)
        return retval

    def makeEntry(self, entry, settings, fsname = ""):
        changed = False
        if "options" in entry:
            options = entry["options"]
        else:
            changed = True
            options = []

        device = {}
        if not self.remote:
            if "fsname" in settings and settings["fsname"]:
                device = self.findDevices(fsname = settings["fsname"])[0]
            elif "uuid" in settings and settings["uuid"]:
                device = self.findDevices(uuid = settings["uuid"])[0]
            elif "label" in settings and settings["label"]:
                device = self.findDevices(label = settings["label"])[0]

        if "fsname" in entry:
            if fsname: # remote
                changed = changed or entry['fsname'] != fsname
                entry['fsname'] = fsname
            elif entry["fsname"]:
                if device:
                    changed = changed or entry['fsname'] != device['fsname']
                    entry['fsname'] = device['fsname']
            else:
                entry["fsname"] = ""
        elif fsname: # remote
                changed = True
                entry['fsname'] = fsname
        else:
            entry["fsname"] = ""
        if "uuid" in entry:
            if entry["uuid"]:
                if device:
                    changed = changed or entry['uuid'] != device['uuid']
                    entry['uuid'] = device['uuid']
            else:
                entry["uuid"] = ""
        else:
            entry["uuid"] = ""
        if "label" in entry:
            if entry["label"]:
                if device:
                    changed = changed or entry['label'] != device['label']
                    entry['label'] = device['label']
            else:
                entry["label"] = ""
        else:
            entry["label"] = ""
        if not entry["fsname"] and not entry["uuid"] and not entry["label"]: #new device
            if device:
                entry["uuid"] = device["uuid"]
            else:
                entry["uuid"] = ""
            changed = True

        if "mountpoint" in settings:
            if "mountpoint" in entry:
                echanged =  entry['mountpoint'] != settings['mountpoint']
            else:
                echanged = True
            changed = changed or echanged
            entry['mountpoint'] = settings['mountpoint']
        elif not "mountpoint" in entry:
            changed = True
            entry['mountpoint'] = "/dev/null"
        if "type" in settings:
            if "type" in entry:
                echanged =  entry['type'] != self.tuneType(settings['type'])
            else:
                echanged = True
            changed = changed or echanged
            entry['type'] = self.tuneType(settings['type'])
        elif not "type" in entry:
            changed = True
            device = self.findDevices(uuid = entry["uuid"], fsname = entry["fsname"], label = entry["label"])
            if device:
                entry["type"] = str(device[0]["type"])
            else:
                entry['type'] = "none"
        if "options" in settings:
            doptions = list(map(str.strip, settings['options'].split(",")))
            while "" in doptions:
                doptions.remove("")
            if not doptions:
                doptions = []
            soptions = self.getExtraOptions(doptions)
            eoptions = self.getExtraOptions(options)
            ochanged = False
            if len(soptions) != len(eoptions):
                ochanged = True
            else:
                for item in soptions:
                    if item not in eoptions:
                        ochanged = True
                        break
            if ochanged:
                options = soptions.extend(self.getExtraOptions(options, True))
                changed = True
        elif not ("options" in entry or len(entry["options"]) == 0) and not self.remote:
            changed = True
            options.append("defaults")
        automount = False
        if "method" in settings:
            if settings['method'] == "startup":
                if "noauto" in options:
                    changed = True
                    options.remove("noauto")
            elif not "noauto" in options:
                changed = True
                options.append("noauto")
            if settings['method'] == "auto":
                automount = True
                if not "x-systemd.automount" in options:
                    changed = True
                    options.append("x-systemd.automount")
            elif "x-systemd.automount" in options:
                changed = True
                options.remove("x-systemd.automount")
        if automount:
            if "idletimeout" in settings:
                hasopt, value = self.getopt(options, "x-systemd.idle-timeout")
                if not hasopt and settings["idletimeout"] > 0:
                    changed = True
                    self.setopt(options, "x-systemd.idle-timeout", settings["idletimeout"])
                elif hasopt and (int(value) != settings["idletimeout"]):
                    changed = True
                    self.removeopt(options, "x-systemd.idle-timeout")
                    if settings["idletimeout"] > 0:
                        self.setopt(options, "x-systemd.idle-timeout", settings["idletimeout"])
            else:
                if self.removeopt(options, "x-systemd.idle-timeout"):
                    changed = True
        else:
            if self.removeopt(options, "x-systemd.idle-timeout"):
                changed = True
        if "timeout" in settings:
            hasopt, value = self.getopt(options, "x-systemd.mount-timeout")
            if not hasopt and settings["timeout"] > 0:
                changed = True
                self.setopt(options, "x-systemd.mount-timeout", settings["timeout"])
            elif hasopt and (int(value) != settings["timeout"]):
                changed = True
                self.removeopt(options, "x-systemd.mount-timeout")
                if settings["timeout"] > 0:
                    self.setopt(options, "x-systemd.mount-timeout", settings["timeout"])
        else:
            if self.removeopt(options, "x-systemd.mount-timeout"):
                changed = True
        if "rw" in settings:
            if settings['rw']:
                if "ro" in options:
                    changed = True
                    options.remove("ro")
            elif not "ro" in options:
                changed = True
                options.append("ro")
        if "ssd" in settings:
            if settings['ssd']:
                if not "noatime" in options:
                    changed = True
                    options.append("noatime")
                if not "nodiratime" in options:
                    changed = True
                    options.append("nodiratime")
            # If no ssd, don't care about noatime or nodiratime settings
        if self.remote:
            if not "_netdev" in options:
                options.insert(0,"_netdev")
        entry['options'] = options
        if "freq" in settings:
            if "dump" in entry:
                echanged =  entry['dump'] != str(settings['freq'])
            else:
                echanged = True
            changed = changed or echanged
            entry['dump'] = str(settings['freq'])
        elif not "dump" in entry:
            changed = True
            entry['dump'] = str(0)
        if "pass" in settings:
            if "pass" in entry:
                echanged =  entry['pass'] != str(settings['pass'])
            else:
                echanged = True
            changed = changed or echanged
            entry['pass'] = str(settings['pass'])
        elif not "pass" in entry:
            changed = True
            entry['pass'] = str(0)
        return changed

    def checkEntry(self, entry, new = True, changed = True, checkMnt = False):
        retval = True
        if not self.remote:
            self.loadDevices()

            if entry["uuid"]:
                if not new:
                    if self.findEntryLine(uuid = entry["uuid"]) < 0:
                        self.logger.info("uuid {} does not exist, item not created".format(entry["uuid"]))
                        retval = False
                if retval and not self.findDevices(uuid = entry["uuid"]):
                    self.logger.info("uuid {} is not found, item not created".format(entry["uuid"]))
                    retval = False
            elif entry["fsname"]:
                if not new:
                    if self.findEntryLine(fsname = entry["fsname"]) < 0:
                        self.logger.info("fsname {} does not exist, item not created".format(entry["fsname"]))
                        retval = False
                if retval and not self.findDevices(fsname = entry["fsname"]):
                    self.logger.info("fsname {} is not found, item not created".format(entry["fsname"]))
                    retval = False
            elif entry["label"]:
                if not new:
                    if self.findEntryLine(label = entry["label"]) < 0:
                        self.logger.info("label {} does not exist, item not created".format(entry["label"]))
                        retval = False
                if retval and not self.findDevices(label = entry["label"]):
                    self.logger.info("label {} is not found, item not created".format(entry["label"]))
                    retval = False
            else:
                self.logger.info("Item doesn't have uuid, fsname or label, item not created")
                retval = False

            if retval:
                device = self.findDevices(uuid = entry["uuid"], fsname = entry["fsname"], label = entry["label"])
                if device:
                    if self.tuneType(entry["type"]) != str(device[0]["type"]):
                        self.logger.info("Incorrect type {}, {} expected, item not created".format(self.tuneType(entry["type"]), device[0]["type"]))
                        retval = False
                    if checkMnt and changed and device[0]["mounted"]:
                        self.logger.info("Physical device is mounted as a different entry, item not created")
                        retval = False
                else:
                    self.logger.info("Physical device not found, item not created")
                    retval = False

        return retval

    def setUmaskOption(self, options, umask = None):
        changed = False
        if umask != None:
            hasopt, value = self.getopt(options, "umask")
            if not hasopt and umask != "0022":
                changed = True
                self.setopt(options, "umask", umask)
            elif hasopt and (value != umask):
                changed = True
                self.removeopt(options, "umask")
                if umask != "0022":
                    self.setopt(options, "umask", mask)
        return changed

    def restoreFstab(self, backupnr):
        retval = False
        if 0 < backupnr <= FSTABBACKUPS:
            backupfile="{}.{}{}".format(FSTABFILE,backupnr,FSTABBACKUP)
            if os.path.isfile(backupfile):
                shutil.copy2(backupfile, FSTABFILE)
                retval = True
        return retval

    def diffFstab(self, backupnr):
        diff = []
        if 0 < backupnr <= FSTABBACKUPS:
            backupfile="{}.{}{}".format(FSTABFILE,backupnr,FSTABBACKUP)
            if os.path.isfile(backupfile):
                cmd = "diff " + FSTABFILE + " " + backupfile
                try:
                    outp = shell().command(cmd, 1)
                except:
                    outp = []
                if outp:
                    diff = outp.splitlines()
                else:
                    diff = ['The files are equal']

        return diff

    def fstabBackups(self):
        dir = ls().ls(FSTABLOC, noroot = True, nocolor = True, noclass = True, filter = FSTABFILTER)
        lst = []
        for obj in dir:
            bobj = {}
            bobj['nr'] = obj['filename'][6]
            bobj['filename'] = obj['filename']
            bobj['modified'] = obj['modified']
            lst.append(bobj)
        return lst

    def getExtraOptions(self, options, default = False):
        defOpt = ["auto","noauto","rw","ro","atime","noatime","diratime","nodiratime","_netdev",
                    "x-systemd.automount","x-systemd.idle-timeout","x-systemd.mount-timeout",
                    "dir_mode", "file_mode", "umask"]
        extraOpt = []
        for opt in options:
            if not default and not self.stripopt(opt) in defOpt:
                extraOpt.append(opt)
            elif default and self.stripopt(opt) in defOpt:
                extraOpt.append(opt)
        return extraOpt

    def systemdReload(self, remote):
        retval = False
        ctl = systemdctl(self.logger)
        if ctl.available():
            retval = ctl.daemonReload()
            if retval:
                if remote:
                    retval = ctl.restart("remote-fs.target")
                else:
                    retval = ctl.restart("local-fs.target")
        del ctl
        return retval


    ################## INTERNAL FUNCTIONS ###################

    def getEntryLine(self, uuid = "", fsname = "", label = ""):
        retuuid = ""
        line = self.findEntryLine(uuid, fsname, label)
        if line < 0 and not self.remote:
            device = self.findDevices(uuid, fsname, label)
            if device:
                line = self.findEntryLine(device[0]['uuid'], device[0]['fsname'], device[0]['label'])

        return line

    def readFstab(self):
        linenr = 0
        with open(FSTABFILE, "rt") as fp:
            for line in fp:
                entry = self.parseFstabLine(line, linenr)
                if entry:
                    self.entries.append(entry)
                linenr += 1

    def writeFstabLine(self, line):
        self.backupFstab()
        lines = []
        entry = self.getEntryFromLine(line)
        if line == -1: # new entry
            #find last line
            defaultline = -1
            for entr in self.entries:
                if entr['line'] > defaultline:
                    defaultline = entr['line']
        else:
            defaultline = line

        with open(FSTABFILE, "rt") as fp:
            lines = fp.readlines()

        if defaultline == -1: # first entry in fstab
            newline = self.generateFstabLine(entry, "UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\t/whatever\t\text4\tdefaults\t\t\t0\t2\n")
        else:
            newline = self.generateFstabLine(entry, lines[defaultline])

        if line == -1:
            lines.append(newline)
        else:
            lines[line] = newline

        with open(FSTABFILE, "wt") as fp:
            fp.writelines(lines)

    def delFstabLine(self, line):
        self.backupFstab()
        with open(FSTABFILE, "rt") as fp:
            lines = fp.readlines()

        lines.pop(line)

        with open(FSTABFILE, "wt") as fp:
            fp.writelines(lines)

    def backupFstab(self):
        for i in range(FSTABBACKUPS-1,-1,-1):
            if i > 0:
                curfile="{}.{}{}".format(FSTABFILE,i,FSTABBACKUP)
            else:
                curfile=FSTABFILE
            newfile="{}.{}{}".format(FSTABFILE,i+1,FSTABBACKUP)
            if os.path.isfile(curfile):
                shutil.copy2(curfile, newfile)

    def generateFstabLine(self, entry, defaultline):
        pos = self.findPos(defaultline)
        if entry['uuid']:
            col = "UUID=" + entry['uuid']
        elif entry['label']:
            col = "LABEL=" + entry['label']
        else:
            col = entry['fsname']
        line = col
        line += self.addTabs(pos[1], pos[0]+len(col))
        col = entry['mountpoint']
        line += col
        line += self.addTabs(pos[2], pos[1]+len(col))
        col = self.tuneType(entry['type'])
        line += col
        line += self.addTabs(pos[3], pos[2]+len(col))
        col = ",".join(entry['options'])
        line += col
        line += self.addTabs(pos[4], pos[3]+len(col))
        col = entry['dump']
        line += col
        line += self.addTabs(pos[5], pos[4]+len(col))
        col = entry['pass']
        line += col
        line += "\n"

        return line

    def parseFstabLine(self, line, linenr):
        entry = {}
        if line.strip()[0] != "#":
            line = line.replace("\t", " ")
            line = " ".join(line.split())
            linelist = line.split()
            if len(linelist) == 6: #otherwise invalid entry
                entry['line'] = linenr
                entry['content'] = {}
                #<file system> <mount point> <type> <options> <dump> <pass>
                if "UUID=" in linelist[0].upper():
                    entry['content']['fsname'] = ""
                    entry['content']['label'] = ""
                    entry['content']['uuid'] = linelist[0].split("=")[1].strip()
                elif "LABEL=" in linelist[0].upper():
                    entry['content']['fsname'] = ""
                    entry['content']['label'] = linelist[0].split("=")[1].strip()
                    entry['content']['uuid'] = ""
                else:
                    entry['content']['fsname'] = linelist[0]
                    entry['content']['label'] = ""
                    entry['content']['uuid'] = ""
                entry['content']['mountpoint'] = linelist[1]
                entry['content']['type'] = linelist[2]
                entry['content']['options'] = list(map(str.strip, linelist[3].split(",")))
                entry['content']['dump'] = linelist[4]
                entry['content']['pass'] = linelist[5]

        return entry

    def findPos(self, line):
        entry = self.parseFstabLine(line, -2) #linenr irrelevant
        tabless = line.expandtabs(TABSIZE)
        pos = []
        pos.append(0)
        pos.append(tabless.find(entry['content']['mountpoint'],pos[0]+1))
        pos.append(tabless.find(entry['content']['type'],pos[1]+1))
        pos.append(tabless.find(",".join(entry['content']['options']),pos[2]+1))
        pos.append(tabless.find(entry['content']['dump'],pos[3]+1))
        pos.append(tabless.find(entry['content']['pass'],pos[4]+1))
        return pos

    def addTabs(self, pos, endpos):
        n = (pos-endpos-1)//TABSIZE + 1
        if n <= 0:
            n = 1
        return "\t"*n

    def findEntryLine(self, uuid = "", fsname = "", label = ""):
        entryLine = -1
        for entry in self.entries:
            if entry['content']['uuid'] and uuid:
                if entry['content']['uuid'].lower() == uuid.lower():
                    entryLine = entry['line']
                    break
            elif entry['content']['fsname'] and fsname:
                if entry['content']['fsname'] == fsname:
                    entryLine = entry['line']
                    break
            elif entry['content']['label'] and label:
                if entry['content']['label'].lower() == label.lower():
                    entryLine = entry['line']
                    break
        return entryLine

    def getEntryFromLine(self, entryLine, fullInfo = False):
        entry = {}

        for entr in self.entries:
            if entr['line'] == entryLine:
                if fullInfo:
                    entry = entr
                else:
                    entry = entr['content']
                break
        return entry

    def tuneType(self, type):
        rettype = ""
        if self.remote:
            rettype = type
        else:
            rettype = self.tune(type)
        return rettype

    def setopt(self, options, tag, value):
        opt = tag.strip() + "=" + str(value)
        options.append(opt)

    def getopt(self, options, tag):
        hasopt = False
        value = 0

        for opt in options:
            if tag in opt:
                hasopt = True
                try:
                    value = opt.split("=")[1].strip()
                except:
                    pass
                break

        return hasopt, value

    def removeopt(self, options, tag):
        hasopt = False

        for opt in options:
            if tag in opt:
                hasopt = True
                options.remove(opt)
                break

        return hasopt

    def stripopt(self, opt):
        tag = ""

        try:
            tag = opt.split("=")[0].strip()
        except:
            pass

        return tag

######################### MAIN ##########################
if __name__ == "__main__":
    pass
