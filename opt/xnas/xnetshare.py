#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : xnetshare.py                                 #
#          Xnas manage netshares                        #
#          (shares over the network)                    #
#          I. Helwegen 2020                             #
#########################################################

####################### IMPORTS #########################
import sys
from common.xnas_engine import xnas_engine
from common.xnas_check import xnas_check
from common.ip import ip
from net.netshare import netshare
from net.nfsshare import CfgNfs
from net.cifsshare import CfgCifs, HomesCifs, ShareCifs, VfsRecycleCifs
#########################################################

####################### GLOBALS #########################
NAMELIST = ["add", "del", "ena", "dis", "shw", "usr", "prv"]
NAMECHECK = ["del", "shw", "dis", "add", "usr", "prv"]
#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : xnetshare                                     #
#########################################################
class xnetshare(xnas_engine):
    def __init__(self):
        xnas_engine.__init__(self, "xnetshare")
        self.settings = {}

    def __del__(self):
        xnas_engine.__del__(self)

    def run(self, argv):
        result = True
        self.handleArgs(argv)
        Netshare = netshare(self)
        xcheck = xnas_check(self, Net = Netshare, json = self.settings['json'])
        if xcheck.ErrorExit(xcheck.check(), self.settings, NAMECHECK):
            if self.settings["json"]:
                self.printJsonResult(False)
            exit(1)
        del xcheck
        if not self.hasSetting(self.settings,"command"):
            netshares = Netshare.getNetshares()
            if self.settings["json"]:
                self.printJson(netshares)
            else:
                self.prettyPrintTable(netshares)
        elif self.settings["command"] == "add":
            self.needSudo()
            result = Netshare.addNsh(self.settings["name"])
            if self.hasSetting(self.settings, "settings"):
                if self.settings["json"]:
                    self.printJson(result)
                else:
                    self.prettyPrintTable(self.settings2Table(result))
                result = True
            else:
                if result:
                    self.update()
                    self.logger.info("Database updated with new netshare entries")
                if self.settings["json"]:
                    self.printJsonResult(result)
        elif self.settings["command"] == "del":
            self.needSudo()
            result = Netshare.delNsh(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated")
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "ena":
            self.needSudo()
            result = Netshare.ena(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated")
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "dis":
            self.needSudo()
            result = Netshare.dis(self.settings["name"])
            if result:
                self.update()
                self.logger.info("Database updated")
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "shw":
            netshareData = Netshare.shw(self.settings["name"])
            if self.settings["json"]:
                self.printJson(netshareData)
            else:
                self.prettyPrintTable(self.settings2Table(netshareData))
        elif self.settings["command"] == "cnf":
            self.needSudo()
            result = Netshare.config()
            if self.settings["json"]:
                if self.hasSetting(self.settings, "settings"):
                    self.printJson(result)
                    result = True
                else:
                    self.printJsonResult(result)
            elif self.hasSetting(self.settings, "settings"):
                self.prettyPrintTable(self.settings2Table(result))
                result = True
        elif self.settings["command"] == "hms":
            self.needSudo()
            result = Netshare.homes()
            if self.settings["json"]:
                if self.hasSetting(self.settings, "settings"):
                    self.printJson(result)
                    result = True
                else:
                    self.printJsonResult(result)
            elif self.hasSetting(self.settings, "settings"):
                self.prettyPrintTable(self.settings2Table(result))
                result = True
        elif self.settings["command"] == "usr":
            self.needSudo()
            result = Netshare.users(self.settings["name"])
            if self.settings["json"]:
                if self.settings["name"].lower() == "list" or self.settings["name"].lower() == "avl":
                    self.printJson(result)
                    result = True
                else:
                    self.printJsonResult(result)
            elif self.settings["name"].lower() == "list" or self.settings["name"].lower() == "avl":
                self.prettyPrintTable(result)
                result = True
            elif self.settings["name"].lower() == "exists":
                if result:
                    self.printMarked("User exists")
                else:
                    self.printMarked("User doesn't exist")
        elif self.settings["command"] == "prv":
            self.needSudo()
            result = Netshare.privileges(self.settings["name"])
            if self.settings["json"]:
                if self.hasSetting(self.settings, "list"):
                    self.printJson(result)
                    result = True
                else:
                    self.printJsonResult(result)
            elif self.hasSetting(self.settings, "list"):
                self.prettyPrintTable(result)
                result = True
        elif self.settings["command"] == "bin":
            self.needSudo()
            result = False
            if "name" in self.settings:
                result = Netshare.bin(self.settings["name"])
            else:
                result = Netshare.bin(None)
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "rfr":
            self.needSudo()
            result = Netshare.refresh()
            if self.settings["json"]:
                self.printJsonResult(result)
        elif self.settings["command"] == "lst":
            listData = Netshare.lst()
            if self.settings["json"]:
                self.printJson(listData)
            else:
                self.prettyPrintTable(listData)
        elif self.settings["command"] == "ip":
            myIp = ""
            if "name" in self.settings:
                if ip().isIpMask(self.settings["name"]):
                    myIp = ip().ipMask(self.settings["name"])
                elif ip().isIp(self.settings["name"]):
                    myIp = ip().mask(32, self.settings["name"])
                elif ip().isMaskOnly(self.settings["name"]):
                    myIp = ip().mask(ip().getMask(self.settings["name"]))
                else:
                    myIp = ip().mask(32)
            else:
                myIp = ip().mask(32)
            ipData = [{"ip": myIp}]
            if self.settings["json"]:
                self.printJson(ipData)
            else:
                self.prettyPrintTable(ipData)
        else:
            self.parseError("Unknown command argument")
            result = False
            if self.settings["json"]:
                self.printJsonResult(result)
        exit(0 if result else 1)

    def nameRequired(self):
        if self.hasSetting(self.settings,"command"):
            if self.settings["command"] in NAMELIST and not "name" in self.settings:
                self.parseError("The option {} requires a <name> as argument".format(self.settings["command"]))

    def handleArgs(self, argv):
        xargs = {"add": "adds or edits a netshare [add <name>]",
                 "del": "deletes a netshare [del <name>]",
                 "ena": "enables a netshare [ena <name>]",
                 "dis": "disables a netshare [dis <name>]",
                 "shw": "shows current netshare settings [shw <name>]",
                 "cnf": "configure a netshare [cnf]",
                 "hms": "configure homes for cifs [hms]",
                 "usr": "configure users for cifs [usr (add, del, exists, ...)]",
                 "prv": "configure user privileges for cifs [prv <name>]",
                 "bin": "empty recycle bin for cifs [bin <name>] or [bin] for all",
                 "rfr": "refreshes netshares",
                 "lst": "lists xshares to netshare [lst]",
                 "ip": "generates ip address/ mask",
                 "-": "show netshares and their status"}
        xopts = {"type": "cifs or nfs type share <string> (add, cnf)"}
        extra = ('Show specific help for commands by filesystem type by e.g.\n'
        'xnetshare add -t cifs -h\n'
        'The name entered needs to be an existing share name.\n'
        'Options may be entered as single JSON string using full name, e.g.\n'
        'xnetshare add test \'{"type": "cifs"}\'\n'
        'Mind the single quotes to bind the JSON string.')

        cmd, type = self.preSettings(self.parseOpts(argv, xopts, xargs, extra, preCheck = True), xopts)
        specextra = ("")
        specopts = {}

        if cmd == "add":
            if type == "cifs":
                specopts = {"comment": "comment for cifs share (default = '')",
                            "guest": "allow guests (no, allow, only) (default = no)",
                            "readonly": "readonly share (default = {})".format(ShareCifs.tf(ShareCifs.bl(ShareCifs.read_only))),
                            "browseable": "browseable share (default = {})".format(ShareCifs.tf(ShareCifs.bl(ShareCifs.browseable))),
                            "recyclebin": "use recycle bin (default = {})".format(ShareCifs.tf(False)),
                            "recyclemaxsize": "max bin size [bytes] (default = {} = no limit)".format(VfsRecycleCifs.maxsize),
                            "recyclemaxage": "max bin age [days] (default = 0 = no max)",
                            "hidedotfiles": "hide dot files (default = {})".format(ShareCifs.tf(ShareCifs.bl(ShareCifs.hide_dot_files))),
                            "inheritacls": "inherit acls (default = {})".format(ShareCifs.tf(ShareCifs.bl(ShareCifs.inherit_acls))),
                            "inheritpermissions": "inherit permissions (default = {})".format(ShareCifs.tf(ShareCifs.bl(ShareCifs.inherit_permissions))),
                            "easupport": "ea support (default = {})".format(ShareCifs.tf(ShareCifs.bl(ShareCifs.ea_support))),
                            "storedosattr": "store dos attributes (default = {})".format(ShareCifs.tf(ShareCifs.bl(ShareCifs.store_dos_attributes))),
                            "hostsallow": "allow hosts (default = {})".format("''"),
                            "hostsdeny": "deny hosts (default = {})".format("''"),
                            "audit": "use audit (default = {})".format(ShareCifs.tf(False)),
                            "extraoptions": "extra options (default = {})".format("'{}'"),
                            "settings": "lists current netshare settings"}
                specextra = ("'recyclemaxage' is handled by xservices and needs xservices and \n"
                "cifs automatically empty recycle bin to be enabled.\n"
                "command: 'xnas srv -e -B' (xservices and bin are enabled by default)\n")
            elif type == "nfs":
                specopts = {#"comment": "comment for nfs share (default = '')", NOT SUPPORTED
                            "client": "ip address/mask (default = {})".format(ip().mask(24)),
                            "readonly": "read only share (default = {})".format("false"),
                            "extraoptions": "extra options (default = {})".format("'{}'"),
                            "settings": "lists current netshare settings"}
        elif cmd == "cnf":
            if type == "cifs":
                specopts = {"enable": "enable cifs server <boolean>",
                            "workgroup": "name of the workgroup (default = {})".format(CfgCifs.workgroup),
                            "serverstring": "server string (default = {})".format(CfgCifs.server_string),
                            "loglevel": "log level (default = {})".format(CfgCifs.log_level),
                            "sendfile": "use send file (default = {})".format(CfgCifs.tf(CfgCifs.bl(CfgCifs.use_sendfile))),
                            "aio": "use asynchronous io (default = {})".format(CfgCifs.tf(True)),
                            "localmaster": "use local master (default = {})".format(CfgCifs.tf(CfgCifs.bl(CfgCifs.local_master))),
                            "timeserver": "use time server (default = {})".format(CfgCifs.tf(CfgCifs.bl(CfgCifs.time_server))),
                            "winssupport": "use wins support (default = {})".format(CfgCifs.tf(CfgCifs.bl(CfgCifs.wins_support))),
                            "winsserver": "wins server (default = {})".format("''"),
                            "extraoptions": "extra options (default = {})".format("'{}'"),
                            "clear": "clear (remove) existing configfile (default = {})".format(CfgCifs.tf(False)),
                            "settings": "lists current configuration settings"}
            elif type == "nfs":
                specopts = {"enable": "enable nfs server <boolean>",
                            "servers": "number of servers to startup (default = {})".format(CfgNfs.RPCNFSDCOUNT),
                            "clear": "clear (remove) existing configfile (default = {})".format(CfgNfs.tf(False)),
                            "settings": "lists current configuration settings"}
        elif cmd == "hms":
            type = "cifs"
            specopts = {"enable": "enable homes folders (default = {})".format(CfgCifs.tf(True)),
                        "browseable": "homes folders are browseable (default = {})".format(HomesCifs.tf(HomesCifs.bl(HomesCifs.browseable))),
                        "writable": "homes folders are writable (default = {})".format(HomesCifs.tf(HomesCifs.bl(HomesCifs.writable))),
                        "extraoptions": "extra options (default = {})".format("'{}'"),
                        "settings": "lists current homes settings"}
        elif cmd == "usr":
            type = "cifs"
            specopts = {"username": "cifs username (error if omitted)",
                        "password": "cifs password (interactive if omitted or empty)",
                        "fullname": "cifs user full name (optional)",
                        "comment": "cifs user comment (optional)"}

            specextra = ("Specific arguments for 'xnetshare {} -t {}':\n".format(cmd,type))
            specextra = specextra + ("    <arguments>\n"
            "        list  : displays a list of cifs users\n"
            "        avl   : displays available linux users to add as cifs user\n"
            "        exists: checks whether a user with <username> exists\n"
            "        add   : adds or modifies a user with <username>\n"
            "        del   : deletes a user with <username>\n")
        elif cmd == "prv":
            type = "cifs"
            specopts = {"list": "lists users and privileges for this netshare",
                        "username": "cifs username (guest user if omitted)",
                        "invalid": "explicitly deny access for this user",
                        "readonly": "readonly access for this user (default is read write)",
                        "delete": "delete access for this user"}

        if specopts:
            specextra = specextra + ("Specific options for 'xnetshare {} -t {}':".format(cmd,type))

        self.fillSettings(self.parseOpts(argv, xopts, xargs, extra, specopts, specextra), xopts)

    def fillSettings(self, optsnargs, xopts):
        if len(optsnargs[1]) > 0:
            self.settings["command"]=optsnargs[1][0]
            xopts[self.settings["command"]] = "NA" # Add command for optional JSON input
        if len(optsnargs[1]) > 1:
            if self.settings["command"] in NAMELIST:
                self.settings["name"]=optsnargs[1][1]
            else:
                if self.isJSON(optsnargs[1][1]):
                    self.settings.update(self.parseJSON(optsnargs[1][1], xopts))
                else:
                    self.settings["name"]=optsnargs[1][1]
        if len(optsnargs[1]) > 2:
            self.settings.update(self.parseJSON(optsnargs[1][2], xopts))

        if len(optsnargs[1]) > 3:
            self.parseError("Too many arguments")

        self.settings.update(optsnargs[0])
        self.settingsBool(self.settings, 'json')
        self.nameRequired()

        if self.settings['json']:
            self.StdoutLogging(False)
        else:
            self.StdoutLogging(True)

    def preSettings(self, optsnargs, xopts):
        cmd = ""
        settings = {}
        type = ""
        if len(optsnargs[1]) > 0:
            cmd=optsnargs[1][0]
        if len(optsnargs[1]) > 1:
            if not cmd in NAMELIST:
                if self.isJSON(optsnargs[1][1]):
                    settings.update(self.parseJSON(optsnargs[1][1], xopts))
        if len(optsnargs[1]) > 2:
            settings.update(self.parseJSON(optsnargs[1][2], xopts))

        settings.update(optsnargs[0])

        if 'type' in settings:
            type = settings['type']

        return cmd, type
#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    xnetshare().run(sys.argv)
