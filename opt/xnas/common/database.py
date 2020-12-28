# -*- coding: utf-8 -*-
#########################################################
# SERVICE : database.py                                 #
#           Manages the XML database                    #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
import random
import string
from common.xnas_engine import groups # database is always imported in engine
#########################################################

####################### GLOBALS #########################
XML_FILENAME     = "xnas.xml"
ENCODING         = 'utf-8'
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : database                                      #
#########################################################
class database(object):
    def __init__(self, logger):
        self.logger = logger
        self.db = {}
        if not self.getXMLpath(False):
            # only create xml if super user, otherwise keep empty
            self.createXML()
            self.getXML()
        else:
            self.getXML()

    def __del__(self):
        pass

    def update(self):
        self.updateXML()

    def reload(self):
        del self.db
        self.db = {}
        self.getXML()

    def checkGroup(self, group):
        retval = None
        if group in self.db:
            if self.db[group]:
                retval = self.db[group]
        return retval

    def checkKey(self, group, key):
        retval = None
        if group in self.db:
            if self.db[group]:
                if key in self.db[group]:
                    retval = self.db[group][key]
        return retval

    def checkKeyDef(self, group, key, default):
        retval = self.checkKey(group, key)
        if not retval:
            retval = default
        return retval

    def findInGroup(self, group, key, value):
        retkey = None
        retval = None
        if group in self.db:
            if self.db[group]:
                for ikey, ivalue in self.db[group].items():
                    try:
                        if self.db[group][ikey][key] == value:
                            retkey = ikey
                            retval = self.db[group][ikey]
                            break
                    except:
                        pass
        return retkey, retval

    def findAllInGroup(self, group, key, value):
        retkey = None
        retval = {}
        if group in self.db:
            if self.db[group]:
                for ikey, ivalue in self.db[group].items():
                    try:
                        if self.db[group][ikey][key] == value:
                            retkey = ikey
                            retval[ikey] = self.db[group][ikey]
                    except:
                        pass
        return retval

    def addToGroup(self, group, item):
        if not group in self.db:
            self.db[group]={}
        if not isinstance(self.db[group], dict):
            self.db[group]={}
        self.db[group].update(item)

    def removeFromGroup(self, group, item):
        retval = False
        if self.checkKey(group, item):
            self.db[group].pop(item)
            retval = True
        return retval

    def generateUniqueName(self, group, value, value2 = "", value3 = ""):
        name = ""
        pname = ""
        value4 = ""

        if value:
            name = self.decodeName(value)
            value4 = os.path.split(value)[0].replace("/","")

        if not name or self.checkKey(group, name):
            if value2:
                name = self.decodeName(value2)

        if not name or self.checkKey(group, name):
            if value3:
                name = self.decodeName(value3)

        if not name:
            name = self.randomString()
        elif self.checkKey(group, name):
            if value4:
                name = value4+name

        i = 1
        pname = name
        while self.checkKey(group, name):
            name = pname + str(i)
            i += 1

        return name(value3)

        if not name:
            name = self.randomString()
        elif self.checkKey(group, name):
            if value4:
                name = value4+name

        i = 1
        pname = name
        while self.checkKey(group, name):
            name = pname + str(i)
            i += 1

        return name

    def gettype(self, text, txtype = True):
        try:
            retval = int(text)
        except:
            try:
                retval = float(text)
            except:
                if text:
                    if text.lower() == "false":
                        retval = False
                    elif text.lower() == "true":
                        retval = True
                    elif txtype:
                        retval = text
                    else:
                        retval = ""
                else:
                    retval = ""

        return retval

    def settype(self, element):
        retval = ""
        if type(element) == bool:
            if element:
                retval = "true"
            else:
                retval = "false"
        elif element != None:
            retval = str(element)

        return retval

    def valid(self, name):
        return not name[0].isdigit() and all(c.isalnum() or c == '_' for c in name)

    ################## INTERNAL FUNCTIONS ###################

    def decodeName(self, value):
        name = ""
        if value == "/":
            name = "_root_"
        else:
            name = os.path.split(value)[1]

        return name

    def randomString(self, stringLength=8):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(stringLength))

    def getXML(self):
        XMLpath = self.getXMLpath()
        try:
            tree = ET.parse(XMLpath)
            root = tree.getroot()
            self.db = self.parseKids(root)
        except Exception as e:
            self.logger.error("Error parsing xml file")
            self.logger.error("Check XML file syntax for errors")
            self.logger.exception(e)
            exit(1)

    def parseKids(self, item):
        db = {}
        if self.hasKids(item):
            for kid in item:
                if self.hasKids(kid):
                    db[kid.tag] = self.parseKids(kid)
                else:
                    db.update(self.parseKids(kid))
        else:
            db[item.tag] = self.gettype(item.text)
        return db

    def hasKids(self, item):
        retval = False
        for kid in item:
            retval = True
            break
        return retval

    def updateXML(self):
        db = ET.Element('config')
        comment = ET.Comment(self.getXMLcomment("config"))
        db.append(comment)
        self.buildXML(db, self.db)

        XMLpath = self.getXMLpath(dowrite = True)

        with open(XMLpath, "w") as xml_file:
            xml_file.write(self.prettify(db))

    def buildXML(self, xmltree, item):
        if isinstance(item, dict):
            for key, value in item.items():
                kid = ET.SubElement(xmltree, key)
                self.buildXML(kid, value)
        else:
            xmltree.text = self.settype(item)

    def createXML(self):
        self.logger.info("Creating new XML file")
        db = ET.Element('config')
        comment = ET.Comment("This XML file describes the XNAS configuration.\n"
        "            This file is managed by XNAS, edit at your own risk.")
        db.append(comment)
        sections = {groups.SETTINGS: "", groups.MOUNTS: "", groups.REMOTEMOUNTS: "", groups.SHARES: "", groups.NETSHARES: ""}
        for key, value in sections.items():
            child = ET.SubElement(db, key)
        XMLpath = self.getNewXMLpath()

        with open(XMLpath, "w") as xml_file:
            xml_file.write(self.prettify(db))

    def getXMLcomment(self, tag):
        comment = ""
        XMLpath = self.getXMLpath()
        with open(XMLpath, 'r') as xml_file:
            content = xml_file.read()
            xmltag = "<{}>".format(tag)
            xmlend = "</{}>".format(tag)
            begin = content.find(xmltag)
            end = content.find(xmlend)
            content = content[begin:end]
            cmttag = "<!--"
            cmtend = "-->"
            begin = content.find(cmttag)
            end = content.find(cmtend)
            if (begin > -1) and (end > -1):
                comment = content[begin+len(cmttag):end]
        return comment

    def prettify(self, elem):
        """Return a pretty-printed XML string for the Element.
        """
        rough_string = ET.tostring(elem, ENCODING)
        reparsed = parseString(rough_string)
        return reparsed.toprettyxml(indent="\t").replace('<?xml version="1.0" ?>','<?xml version="1.0" encoding="%s"?>' % ENCODING)

    def getXMLpath(self, doexit = True, dowrite = False):
        etcpath = "/etc/"
        XMLpath = ""
        # first look in etc
        if os.path.isfile(os.path.join(etcpath,XML_FILENAME)):
            XMLpath = os.path.join(etcpath,XML_FILENAME)
            if dowrite and not os.access(XMLpath, os.W_OK):
                self.logger.error("No valid writable XML file location found")
                self.logger.error("XML file cannot be written, please run as super user")
                if doexit:
                    exit(1)
        else: # Only allow etc location
            self.logger.error("No XML file found")
            if doexit:
                exit(1)
        return XMLpath

    def getNewXMLpath(self):
        etcpath = "/etc/"
        XMLpath = ""
        # first look in etc
        if os.path.exists(etcpath):
            if os.access(etcpath, os.W_OK):
                XMLpath = os.path.join(etcpath,XML_FILENAME)
        if (not XMLpath):
            self.logger.error("No valid writable XML file location found")
            self.logger.error("XML file cannot be created, please run as super user")
            exit(1)
        return XMLpath

######################### MAIN ##########################
if __name__ == "__main__":
    pass
