# -*- coding: utf-8 -*-
#########################################################
# SERVICE : ls.py                                       #
#           ls shows folder list                        #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import os
import fnmatch
import stat
import pwd
import grp
import time
import locale
from common.ansi import ansi
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : ls                                            #
#########################################################
class ls(object):
    def __init__(self):
        self.now = time.localtime()

    def __del__(self):
        pass

# -rw-r--r--   1 helly helly   27 May  4  2018  .xsessionrc
# 1 = st_mode
# 2 = st_nlink
# 3 = st_uid
# 4 = st_gid
# 5 = st_size:
# 6 = st_mtime
# 7 = entry.name

    def ls(self, point, human = False, short = False, noroot = False, nocolor = False, noclass = False, nosort = False, filter="*"):
        direntries = []

        if not noroot:
            self.root(point, direntries, human, short, nocolor, noclass)
        with os.scandir(point) as entries:
            if not nosort:
                entries = sorted(entries, key=lambda f: f.name.lower())

            for entry in entries:
                try:
                    if fnmatch.filter([entry.name], filter):
                        direntries.append(self.fillEntry(entry.name, entry.stat(), human, short, nocolor, noclass))
                except:
                    pass
        return direntries

    ################## INTERNAL FUNCTIONS ###################

    def fillEntry(self, name, info, human, short, nocolor, noclass):
        direntry = {}
        if not short:
            direntry['mode'] = stat.filemode(info.st_mode)
            direntry['n'] = info.st_nlink
            direntry['user'] = pwd.getpwuid(info.st_uid).pw_name
            direntry['group'] = grp.getgrgid(info.st_gid).gr_name
            if human:
                direntry['size'] = self.sizeof_fmt(info.st_size, "")
            else:
                direntry['size'] = info.st_size
            direntry['modified'] = self.datetime(info.st_mtime)
        direntry['filename'] = self.fname(name, info.st_mode, nocolor, noclass)

        return direntry

    def sizeof_fmt(self, num, suffix='B'):
        for unit in ['','K','M','G','T','P','E','Z','Y']:
            if abs(num) < 1024.0 or unit == 'Y':
                break
            num /= 1024.0
        return "{}{}{}".format(round(num,1), unit, suffix)

    def datetime(self, etime):
        ftime = time.localtime(etime)

        if self.yearOld(ftime):
            strformat=("{}".format(locale.nl_langinfo(locale.D_FMT)))
            strformat=strformat.replace("/", " ")
            strformat=strformat.replace("-", " ")
            strformat=strformat.replace("%m", "%b")
            strformat=strformat.replace("%y", " %Y")
        else:
            strformat=("{}{}".format(locale.nl_langinfo(locale.D_FMT),locale.nl_langinfo(locale.T_FMT)))
            strformat=strformat.replace("/", " ")
            strformat=strformat.replace("-", " ")
            strformat=strformat.replace("%m", "%b")
            strformat=strformat.replace("%y", "")
            strformat=strformat.replace(":%S", "")
        return (time.strftime(strformat, ftime))

    def yearOld(self, ftime):
        retval = False
        if ftime.tm_year < self.now.tm_year:
            if ftime.tm_year == self.now.tm_year - 1:
                if ftime.tm_mon < self.now.tm_mon:
                    retval = True
                elif ftime.tm_mon == self.now.tm_mon:
                    if ftime.tm_mday <= self.now.tm_mday:
                        retval = True
            else: # older
                retval = True

        return retval

    def fname(self, name, mode, nocolor, noclass):

        cpre = ""
        csuf = ""
        fsuf = ""
        fexec = stat.S_IMODE(mode) & stat.S_IXUSR
        flink = stat.S_ISLNK(mode)
        fdir = stat.S_ISDIR(mode)

        if not noclass:
            if fdir:
                fsuf = "/"
            elif fexec:
                fsuf = "*"
            if flink:
                fsuf = fsuf + ">"

        if not nocolor:
            csuf = ansi.fg.lightgrey
            if fdir:
                cpre = ansi.fg.blue
            elif fexec:
                cpre = ansi.fg.green
            if flink:
                cpre = cpre + ansi.italic

        return "{}{}{}{}".format(cpre, name, csuf, fsuf)

    def root(self, point, direntries, human, short, nocolor, noclass):
        fdir = os.path.dirname(point)

        try:
            direntries.append(self.fillEntry(".", os.stat(point), human, short, nocolor, noclass))
            direntries.append(self.fillEntry("..", os.stat(fdir), human, short, nocolor, noclass))
        except:
            pass

######################### MAIN ##########################
if __name__ == "__main__":
    pass
