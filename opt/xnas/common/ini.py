# -*- coding: utf-8 -*-
#########################################################
# SERVICE : ini.py                                      #
#           reads, modifies and writes ini files        #
#           (including config files using ini format)   #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import shutil

#########################################################

####################### GLOBALS #########################
SECTION      = 0
ITEM         = 1
LINENOEXIST  = -1
COMMENT      = ['#',';']
SECTIONSTART = '['
SECTIONEND   = ']'
ITEMVALUE    = '='
OBJECTSPLIT  = ':'
BACKUPEXT    = '.bak'
ORIGEXT      = '.orig'
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : ini                                           #
#########################################################
class ini(object):
    def __init__(self, logger, filename = "", backup = True, reRead = False, shellStyle = False):
        self.logger = logger
        self.entries = {}
        self.filename = filename
        self.backup = backup
        self.reRead = reRead
        self.shellStyle = shellStyle
        try:
            self.readIni()
        except Exception as e:
            self.logger.error("Error reading file: {}".format(filename))
            self.logger.error(e)
            exit(1)

    def __del__(self):
        del self.entries

    def update(self):
        return self.updateIni()

    def clear(self):
        return self.clearIni()

    def changed(self):
        retval = False
        for key, val in self.entries.items():
            if val['changed']:
                retval = True
                break
        return retval

    def get(self, section, item, obj = ""):
        retval = ""
        if not section:
            for key, val in self.entries.items():
                if val['type'] == ITEM and not val['removed']:
                    if obj:
                        name, objname = self.splitObj(key)
                        if objname == obj and name == item:
                            retval = val['value']
                            break
                    else:
                        if key == item:
                            retval = val['value']
                            break
        else:
            for key, val in self.entries.items():
                if val['type'] == SECTION and not val['removed']:
                    if key == section:
                        for k2, v2 in val['value'].items():
                            if v2['type'] == ITEM and not v2['removed']:
                                if obj:
                                    name, objname = self.splitObj(k2)
                                    if objname == obj and name == item:
                                        retval = v2['value']
                                        break
                                else:
                                    if k2 == item:
                                        retval = v2['value']
                                        break
                        break
        return retval

    def setDefaultObject(self, section, obj, itemdict = {}):
        return self.setDefaultSection(section, itemdict, obj)

    def setObject(self, section, obj, itemdict = {}, default = False):
        return self.setSection(section, itemdict, default, obj)

    def setDefaultSection(self, section, itemdict = {}, obj = ""):
        return self.setSection(section, itemdict, default = True, obj = obj)

    def setSection(self, section, itemdict = {}, default = False, obj = ""):
        retval = False
        for key, val in itemdict.items():
            if val != None:
                retval = self.set(section, key, val, obj, default)
                if not retval:
                    break
        return retval

    def setDefault(self, section, item, value, obj = ""):
        return self.set(section, item, value, obj, default = True)

    def set(self, section, item, value, obj = "", default = False):
        retval = False
        if not section:
            lastpos = 0
            for key, val in self.entries.items():
                if val['type'] == ITEM:
                    lastpos += 1
                    if obj:
                        name, objname = self.splitObj(key)
                        if objname == obj and name == item:
                            if not default:
                                val['value'] = value
                                val['changed'] = True
                                val['removed'] = False
                            retval = True
                            break
                    else:
                        if key == item:
                            if not default:
                                val['value'] = value
                                val['changed'] = True
                                val['removed'] = False
                            retval = True
                            break
            if not retval: # new item
                if obj:
                    entry = self.addItem(self.objKey(obj, item), value, ITEM, changed = True)
                else:
                    entry = self.addItem(item, value, ITEM, changed = True)
                self.entries = self.insert(self.entries, entry, lastpos)
                retval = True
        else:
            for key, val in self.entries.items():
                if val['type'] == SECTION:
                    if key == section and not val['removed']:
                        lastpos = 0
                        for k2, v2 in val['value'].items():
                            if v2['type'] == ITEM:
                                lastpos += 1
                                if obj:
                                    name, objname = self.splitObj(k2)
                                    if objname == obj and name == item:
                                        if not default:
                                            v2['value'] = value
                                            v2['changed'] = True
                                            v2['removed'] = False
                                            val['changed'] = True
                                            val['removed'] = False
                                        retval = True
                                        break
                                else:
                                    if k2 == item:
                                        if not default:
                                            v2['value'] = value
                                            v2['changed'] = True
                                            v2['removed'] = False
                                            val['changed'] = True
                                            val['removed'] = False
                                        retval = True
                                        break
                        if not retval: # new item
                            if obj:
                                entry = self.addItem(self.objKey(obj, item), value, ITEM, changed = True)
                            else:
                                entry = self.addItem(item, value, ITEM, changed = True)
                            val['value'] = self.insert(val['value'], entry, lastpos)
                            val['changed'] = True
                            val['removed'] = False
                            retval = True
                        break
            if not retval: # new section and new item
                if obj:
                    entry = self.addItem(self.objKey(obj, item), value, ITEM, changed = True)
                else:
                    entry = self.addItem(item, value, ITEM, changed = True)
                sentry = self.addItem(section, entry, SECTION, changed = True)
                self.entries.update(sentry)
                retval = True
        return retval

    def remove(self, section, item, obj = ""):
        retval = False
        if not section:
            for key, val in self.entries.items():
                if val['type'] == ITEM and not val['removed']:
                    if obj:
                        name, objname = self.splitObj(key)
                        if objname == obj and name == item:
                            val['removed'] = True
                            val['changed'] = True
                            retval = True
                            break
                    else:
                        if key == item:
                            val['removed'] = True
                            val['changed'] = True
                            retval = True
                            break
        else:
            for key, val in self.entries.items():
                if val['type'] == SECTION and not val['removed']:
                    if key == section:
                        for k2, v2 in val['value'].items():
                            if v2['type'] == ITEM and not v2['removed']:
                                if obj:
                                    name, objname = self.splitObj(k2)
                                    if objname == obj and name == item:
                                        v2['removed'] = True
                                        v2['changed'] = True
                                        val['changed'] = True
                                        retval = True
                                        break
                                else:
                                    if k2 == item:
                                        v2['removed'] = True
                                        v2['changed'] = True
                                        val['changed'] = True
                                        retval = True
                                        break
                        break
        return retval

    def removeSection(self, section):
        retval = False
        if section:
            for key, val in self.entries.items():
                if val['type'] == SECTION and not val['removed']:
                    if key == section:
                        val['removed'] = True
                        val['changed'] = True
                        retval = True
                        for k2, v2 in val['value'].items():
                            if v2['type'] == ITEM and not v2['removed']:
                                v2['removed'] = True
                                v2['changed'] = True
                        break
        return retval

    def removeObject(self, section, obj):
        retval = False
        if not section:
            for key, val in self.entries.items():
                if val['type'] == ITEM and not val['removed']:
                    name, objname = self.splitObj(key)
                    if objname == obj:
                        val['removed'] = True
                        val['changed'] = True
                        retval = True
        else:
            for key, val in self.entries.items():
                if val['type'] == SECTION and not val['removed']:
                    if key == section:
                        for k2, v2 in val['value'].items():
                            if v2['type'] == ITEM and not v2['removed']:
                                name, objname = self.splitObj(k2)
                                if objname == obj:
                                    v2['removed'] = True
                                    v2['changed'] = True
                                    val['changed'] = True
                                    retval = True
                        break
        return retval

    def getSections(self):
        retval = []
        for key, val in self.entries.items():
            if val['type'] == SECTION and not val['removed']:
                retval.append(key)
        return retval

    def getSection(self, section):
        retval = {}
        if not section:
            for key, val in self.entries.items():
                if val['type'] == ITEM and not val['removed']:
                    retval[key] = val['value']
        else:
            for key, val in self.entries.items():
                if val['type'] == SECTION and not val['removed']:
                    if key == section:
                        for k2, v2 in val['value'].items():
                            if not v2['removed']:
                                retval[k2] = v2['value']
                        break
        return retval

    def getObjects(self, section):
        retval = []
        if not section:
            for key, val in self.entries.items():
                if val['type'] == ITEM and not val['removed']:
                    name, objname = self.splitObj(key)
                    if objname:
                        retval.append(objname) if objname not in retval else retval
        else:
            for key, val in self.entries.items():
                if val['type'] == SECTION and not val['removed']:
                    if key == section:
                        for k2, v2 in val['value'].items():
                            if v2['type'] == ITEM and not v2['removed']:
                                name, objname = self.splitObj(k2)
                                if objname:
                                    retval.append(objname) if objname not in retval else retval
                        break
        return retval

    def getObject(self, section, obj):
        retval = {}
        if not section and obj:
            for key, val in self.entries.items():
                if val['type'] == ITEM and not val['removed']:
                    name, objname = self.splitObj(key)
                    if objname == obj:
                        retval[name] = val['value']
        elif section and obj:
            for key, val in self.entries.items():
                if val['type'] == SECTION and not val['removed']:
                    if key == section:
                        for k2, v2 in val['value'].items():
                            if v2['type'] == ITEM and not v2['removed']:
                                name, objname = self.splitObj(k2)
                                if objname == obj:
                                    retval[name] = v2['value']
                        break
        return retval

    def getAll(self):
        retval = {}
        for key, val in self.entries.items():
            if val['type'] == SECTION and not val['removed']:
                sectionentries = {}
                for k2, v2 in val['value'].items():
                    if not v2['removed']:
                        sectionentries[k2] = v2['value']
                retval[key] = sectionentries
            elif not val['removed']:
                retval[key] = val['value']
        return retval

################## INTERNAL FUNCTIONS ###################

# format: ["itemname": {type: Item, value: "test", line: 7, changed: False}, "sectname": {type: section, value: [items], line: 7, changed: False}}]
# added objects: if object != "" handle as object

    def readIni(self):
        linenr = 0
        self.entries = {}
        sectionentries = {}
        mainSection = True
        with open(self.filename, "rt") as fp:
            for line in fp:
                entry = self.parseIniLine(line, linenr)
                if entry:
                    entryval = (list(entry.values()))[0]
                    entrykey = (list(entry.keys()))[0]
                    if entryval['type'] == SECTION:
                        sectionentries = entryval['value']
                        self.entries.update(entry)
                        mainSection = False
                    elif not mainSection:
                        if entrykey in sectionentries:
                            if isinstance(sectionentries[entrykey]["value"], list):
                                sectionentries[entrykey]["value"].append(entryval["value"])
                                sectionentries[entrykey]["line"].append(entryval["line"])
                            else:
                                oldValue = sectionentries[entrykey]["value"]
                                oldLine = sectionentries[entrykey]["line"]
                                sectionentries[entrykey]["value"] = []
                                sectionentries[entrykey]["value"].append(oldValue)
                                sectionentries[entrykey]["value"].append(entryval["value"])
                                sectionentries[entrykey]["line"] = []
                                sectionentries[entrykey]["line"].append(oldLine)
                                sectionentries[entrykey]["line"].append(entryval["line"])
                        else:
                            sectionentries.update(entry)
                    else:
                        if entrykey in self.entries:
                            if isinstance(self.entries[entrykey]["value"], list):
                                self.entries[entrykey]["value"].append(entryval["value"])
                                self.entries[entrykey]["line"].append(entryval["line"])
                            else:
                                oldValue = self.entries[entrykey]["value"]
                                oldLine = self.entries[entrykey]["line"]
                                self.entries[entrykey]["value"] = []
                                self.entries[entrykey]["value"].append(oldValue)
                                self.entries[entrykey]["value"].append(entryval["value"])
                                self.entries[entrykey]["line"] = []
                                self.entries[entrykey]["line"].append(oldLine)
                                self.entries[entrykey]["line"].append(entryval["line"])
                        else:
                            self.entries.update(entry)
                linenr += 1

    def updateIni(self):
        retval = False
        if self.changed():
            if self.backup:
                self.backupIni()
            with open(self.filename, "rt") as fp:
                lines = fp.readlines()
            #cycle through the dict and execute modifications
            offset = 0
            insertline = 0

            for key, val in self.entries.items():
                lineL = self.syncLines(val['value'], val['line'], True)
                value = self.listValue(val['value'])
                i = 0
                for line in lineL:
                    if line >= 0:
                        insertline = line + 1
                    if val['changed']: # If not changed, do nothing
                        if val['type'] == SECTION:
                            if val['removed']:
                                if not lines[line + offset -1].strip():
                                    lines.pop(line + offset -1)
                                    offset -= 1
                                lines.pop(line + offset)
                                offset -= 1
                                for k2, v2 in value[i].items():
                                    line2L = self.syncLines(v2['value'], v2['line'], True)
                                    for line2 in line2L:
                                        lines.pop(line2 + offset)
                                        offset -= 1
                            elif line == LINENOEXIST:
                                insertline = len(lines)
                                lines.insert(insertline + offset, "\n")
                                offset += 1
                                lines.insert(insertline + offset, self.section2line(key))
                                offset += 1
                                for k2, v2 in value[i].items():
                                    line2L = self.syncLines(v2['value'], v2['line'], True)
                                    value2 = self.listValue(v2['value'])
                                    j = 0
                                    for line2 in line2L:
                                        lines.insert(insertline + offset, self.item2line(k2, value2[j]))
                                        offset += 1
                                        j += 1
                            else: #check all items for changed
                                insertitemline = 0
                                for k2, v2 in value[i].items():
                                    line2L = self.syncLines(v2['value'], v2['line'], True)
                                    value2 = self.listValue(v2['value'])
                                    j = 0
                                    for line2 in line2L:
                                        if line2 >= 0:
                                            insertitemline = line2 + 1
                                        if v2['changed']: # If not changed, do nothing
                                            if v2['type'] == ITEM:
                                                if v2['removed']:
                                                    lines.pop(line2 + offset)
                                                    offset -= 1
                                                elif line2 == LINENOEXIST:
                                                    lines.insert(insertitemline + offset, self.item2line(k2, value2[j]))
                                                    offset += 1
                                                else:
                                                    lines[line2 + offset] = self.item2line(k2, value2[j])
                                        j += 1
                        elif val['type'] == ITEM:
                            if val['removed']:
                                lines.pop(line + offset)
                                offset -= 1
                            elif line == LINENOEXIST:
                                lines.insert(insertline + offset, self.item2line(key, value[i]))
                                offset += 1
                            else:
                                lines[line + offset] = self.item2line(key, value[i])
                    i += 1
            with open(self.filename, "wt") as fp:
                fp.writelines(lines)
                retval = True
            #reread file afterwards if required
            if self.reRead:
               self.readIni()
        return retval

    def clearIni(self):
        retval = False

        self.origIni()
        #if self.backup:
        #    self.backupIni()

        lines = ["#\n",
                 "# Autogenerated configuration file by XNAS\n",
                 "#\n",
                 "#\n"]

        with open(self.filename, "wt") as fp:
            fp.writelines(lines)
            retval = True
        #always reread file afterwards
        self.readIni()
        return retval

    def parseIniLine(self, line, linenr):
        entry = {}
        line = line.strip()
        if line and not COMMENT[0] in line[0] and not COMMENT[1] in line[0]:
            if SECTIONSTART in line and SECTIONEND in line: # probably section
                ssta = line.find(SECTIONSTART)
                send = line.find(SECTIONEND)
                c0 = line.find(COMMENT[0])
                c1 = line.find(COMMENT[1])
                if (c0 < 0 and c1 < 0) or (c0 >= 0 and ssta < c0 and send < c0) or (c1 >= 0 and ssta < c1 and send < c1):
                    #valid
                    name = line[ssta+1:send].strip()
                    entry = self.addItem(name, {}, SECTION, linenr)
            elif ITEMVALUE in line:# probably item
                ista = line.find(ITEMVALUE)
                c0 = line.find(COMMENT[0])
                c1 = line.find(COMMENT[1])
                if c0 > 0:
                    iend = c0
                elif c1 > 0:
                    iend = c1
                else:
                    iend = len(line)
                if (c0 < 0 and c1 < 0) or (c0 >= 0 and ista < c0) or (c1 >= 0 and ista < c1):
                    #valid
                    name = line[0:ista].strip()
                    value = line[ista+1:iend].strip()
                    entry = self.addItem(name, value, ITEM, linenr)
        return entry

    def addItem(self, name, value = {}, type = ITEM, line = LINENOEXIST, changed = False):
        entry = {}
        entrycontent = {}
        entrycontent['type'] = type
        entrycontent['value'] = value
        entrycontent['line'] = self.syncLines(value, line)
        entrycontent['removed'] = False
        entrycontent['changed'] = changed
        entry[name]= entrycontent
        return entry

    def syncLines(self, value, line, toList = False):
        if isinstance(value, list):
            if not isinstance(line, list):
                line = [line]
            if len(line) < len(value):
                line.extend([LINENOEXIST] * (len(value)-len(line)))
            elif len(line) > len(value):
                del line[len(value):]
        elif toList:
            line = [line]
        return line

    def listValue(self, value):
        if not isinstance(value, list):
            value = [value]
        return value

    def insert(self, dct, obj, pos):
        return {k: v for k, v in (list(dct.items())[:pos] + list(obj.items()) + list(dct.items())[pos:])}

    def backupIni(self):
        bufile = "{}{}".format(self.filename, BACKUPEXT)
        if os.path.isfile(self.filename):
            shutil.copy2(self.filename, bufile)

    def origIni(self):
        origfile = "{}{}".format(self.filename, ORIGEXT)
        if os.path.isfile(self.filename) and not os.path.isfile(origfile):
            shutil.copy2(self.filename, origfile)

    def item2line(self, item, value, obj = ""):
        sep = " "
        objsep = ""
        if self.shellStyle:
            sep = ""
        if obj:
            objsep = ":"
        return "{}{}{}{}={}{}\n".format(obj, objsep, item, sep, sep, value)

    def objKey(self, obj, key):
        return "{}:{}".format(obj, key)

    def splitObj(self, key):
        objend = key.find(OBJECTSPLIT)
        objname = ""
        if objend > 0:
            objname = key[0:objend].strip()
            name = key[objend+1:].strip()
        else:
            name = key.strip()
        return name, objname

    def section2line(self, section):
        return "[{}]\n".format(section)

######################### MAIN ##########################
if __name__ == "__main__":
    pass
