# -*- coding: utf-8 -*-
#########################################################
# SERVICE : devices.py                                  #
#           Gets block devices and its properties       #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import json
from common.shell import shell
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : devices                                       #
#########################################################
class devices(object):
    def __init__(self, logger, human):
        self.logger = logger
        self.human = human
        self.loadDevices()

    def __del__(self):
        del self.blkdevices
        del self.blkzfsdevices

    def loadDevices(self):
        self.blkdevices = []
        self.blkzfsdevices = []
        try:
            self.dfZfsDevices()
            self.blkDevices()
        except Exception as e:
            self.logger.error("Error reading devices information")
            self.logger.error(e)
            exit(1)

    def getBlockList(self, typefilter = []):
        deviceList = []
        for device in self.blkdevices:
            if not typefilter:
                deviceList.append(device)
            elif self.tune(device['type'], True) in typefilter:
                deviceList.append(device)
        return deviceList

    def getUuid(self, entry):
        uuid = ""
        if entry['uuid']:
            uuid = entry['uuid']
        else:
            device = self.findDevices(entry['uuid'], entry['fsname'], entry['label'])
            if device:
                uuid = device[0]['uuid']
        return uuid

    def getFsname(self, uuid):
        fsname = ""
        device = self.findDevices(uuid)
        if device:
            fsname = device[0]['fsname']
        return fsname

    def getDevices(self, uuid):
        device = self.findDevices(uuid)
        if not device:
             device = self.findDevices(label = uuid)
        if not device:
             device = self.findDevices(fsname = uuid)
        return device

    def findDevices(self, uuid = "", fsname = "", label = ""):
        mydevice = []
        for device in self.blkdevices:
            if uuid and device['uuid']:
                if device['uuid'].lower() == uuid.lower():
                    mydevice.append(device)
            elif fsname and device['fsname']:
                if device['fsname'] == fsname:
                    mydevice.append(device)
            elif label and device['label']:
                if device['label'].lower() == label.lower():
                    mydevice.append(device)

        return mydevice

    def tune(self, type, device = False):
        rtype = ""
        if device:
            if type == "ntfs-3g":
                rtype = "ntfs"
            else:
                rtype = type
        else:
            if type == "ntfs":
                rtype = "ntfs-3g"
            else:
                rtype = type
        return rtype

    ################## INTERNAL FUNCTIONS ###################

    def blkDevices(self):
        entry = {}
        #sudo lsblk -fl | grep -v loop
        cmd = ""
        if self.human:
            cmd = "lsblk -Jfpe7 -o NAME,FSTYPE,LABEL,UUID,FSSIZE,FSUSE%,MOUNTPOINT"
        else:
            cmd = "lsblk -Jfbpe7 -o NAME,FSTYPE,LABEL,UUID,FSSIZE,FSUSED,MOUNTPOINT"
        try:
            lines = json.loads(shell().command(cmd))
            #['NAME', 'FSTYPE', 'LABEL', 'UUID', 'FSAVAIL', 'FSUSE%', 'MOUNTPOINT']
            for line in lines['blockdevices']:
                if 'children' in line:
                    breed = line['children']
                else:
                    breed = []
                    breed.append(line)
                for kid in breed:
                    entry = {}
                    entry['fsname'] = kid['name']
                    entry['label'] = kid['label']
                    if kid['uuid']:
                        entry['uuid'] = kid['uuid'].upper()
                    else:
                        entry['uuid'] = ""
                    entry['type'] = self.tune(kid['fstype'], True)
                    if entry['type'] == "zfs_member":
                        # zfs doesn't give all information using lsblk, so make use of df
                        self.dfGetDevice(entry)
                    else:
                        if self.human:
                            if kid['fssize']:
                                entry['size'] = kid['fssize'].replace(",",".")
                            else:
                                entry['size'] = None
                            if kid['fsuse%']:
                                entry['used'] = kid['fsuse%'].replace(",",".")
                            else:
                                entry['used'] = None
                        else:
                            entry['size'] = kid['fssize']
                            entry['used'] = kid['fsused']
                        entry['mountpoint'] = kid["mountpoint"]
                    entry['mounted'] = True if entry["mountpoint"] else False
                    self.blkdevices.append(entry)
        except:
            pass

    def dfZfsDevices(self):
        cmd = ""
        if self.human:
            cmd = "df -tzfs --output=source,size,pcent,target -h"
        else:
            cmd = "df -tzfs --output=source,size,used,target"
        try:
            lines = shell().command(cmd).splitlines()
            if len(lines) > 1:
                for line in lines[1:]:
                    data = line.split()
                    if len(data) == 4:
                        entry = {}
                        entry['label'] = data[0]
                        entry['size'] = data[1]
                        entry['used'] = data[2]
                        entry['mountpoint'] = data[3]
                        self.blkzfsdevices.append(entry)
        except:
            pass
        return

    def dfGetDevice(self, entry):
        entry['type'] = "zfs"
        entry['size'] = None
        entry['used'] = None
        entry['mountpoint'] = None
        if entry['label']:
            for zfsdevice in self.blkzfsdevices:
                if zfsdevice['label'] == entry['label']:
                    if self.human:
                        entry['size'] = zfsdevice['size'].replace(",",".")
                        entry['used'] = zfsdevice['used'].replace(",",".")
                    else:
                        entry['size'] = str(int(zfsdevice['size'])*1024)
                        entry['used'] = str(int(zfsdevice['used'])*1024)
                    entry['mountpoint'] = zfsdevice['mountpoint']
                    break
        return

######################### MAIN ##########################
if __name__ == "__main__":
    pass
