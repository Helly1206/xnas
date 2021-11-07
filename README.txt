XNAS v1.0.2

XNAS -- Extended NAS functionality on a linux computer
==== == ======== === ============= == = ===== ========

XNAS is a simple and lightweight solution to build a nas on almost any linux distribution (you need fstab, mount and samba or nfs)
- The interface is commandline based (a webgui is available for cockpit: cockpit-xnas)
- XNAS can run without daemons runnnig in the background, however xservices can and will be used to manage dynamic mounting and emptying cifs recylcebin
- XNAS is able to handle ZFS mounts
- XNAS can handle remote mounts of type cifs, nfs or davfs

Configuration is stored in an XML file (/etc/xnas.xml)
This file can be added by hand, but it is better to let xnas manage this file.
If this file is corrupted, xnas won't work.

Tools:
======

XNAS uses the following tools for configuring and managing your NAS:
- xnas: XNAS main program to set options/ bind shares and check or fix issues
- xmount: handles local filesystem mounts, updates fstab and handles ZFS mounts
- xremotemount: handles remote mounts of type cifs, nfs or davfs
- xshare: handles shares from mounts or remotemounts
- xnetshare: handles cifs or nfs shares to access shares from the network

The service runs as service on the background:
- xservices: service for 'dynmount' and 'emptyrecyclebin'

The following tools can be used for commandline accessing shared folders:
- xcd: Changes to folder location
- xdir: Lists folder contents
- xpd: Prints folder location

Referencing diagram:
=========== ========

mount -------\
             |--> share --> netshare
remotemount -/

Usage/ individual options:
====== ========== ========
xnas
----
xnas <arguments> <options>
<arguments>:
    fix           : tries to fix reported errors
    chk           : only check for errors
    shw           : shows all mounts, remotemounts, shares and netshares
    rst           : restores backups [rst <type>] (type: fstab)
    srv           : sets xservices options (restarts services)
    upd           : update xnas settings to latest version
    acl           : generate autocomplete list [acl <type>]
    <no arguments>: checks all shared folders
<options>:
    -h, --help      : this help file
    -v, --version   : print version information
    -j, --json      : display output in JSON format
    -b, --backup    : backup id to restore <string> (rst) (auto = empty)
    -s, --show      : show current dynmounts and their status (srv)
    -i, --interval  : database reloading interval (srv) (default = 60 [s])
    -e, --enable    : enables or disables xservices (srv) (default = true)
    -z, --zfshealth : disables degraded zfs pools (srv) (default = false)
    -r, --removable : dynmount devices not in fstab (srv) (default = false)
    -B, --binenable : enables or disables cifs bin (srv) (default = true)
    -a, --afenable  : enables or disables autofix (srv) (default = true)
    -A, --afretries : number of retries during autofix (srv) (default = 3)
    -f, --afinterval: autofix retry interval (srv) (default = 60)
    -S, --settings  : lists current settings (srv)

xservices run as a service for dynmount, autofix and also handles emptying
the cifs recyclebin if required. See "interval", "enable", "removable",
"binenable", "afenable", "afretries" and "afinterval" options.
xservices is always restarted after calling the "srv" command.
Options may be entered as single JSON string using full name, e.g.
xnas rst fstab '{"backup": "2"}'
Mind the single quotes to bind the JSON string.

xmount
------
xmount <arguments> <options>
<arguments>:
    add           : adds or edits a mount [add <name>]
    del           : deletes a mount [del <name>]
    pop           : populates from fstab [pop]
    mnt           : mounts a mount [mnt <name>]
    umnt          : unmounts a mount if not referenced [umnt <name>]
    clr           : removes a mount, but leaves fstab [clr <name>]
    lst           : lists xmount compatible fstab entries [lst]
    avl           : show available compatible devices not in fstab [avl]
    <no arguments>: show mounts and their status
<options>:
    -h, --help       : this help file
    -v, --version    : print version information
    -j, --json       : display output in JSON format
    -i, --interactive: ask before adding or changing mounts
    -H, --human      : show sizes in human readable format
    -f, --fsname     : filesystem <string> (add)
    -u, --uuid       : uuid <string> (add)
    -l, --label      : label <string> (also for zfs pool) (add)
    -m, --mountpoint : mountpoint <string> (add)
    -t, --type       : type <string> (filesystem) (add)
    -o, --options    : extra options, besides default <string> (add)
    -r, --rw         : mount rw <boolean> (add)
    -s, --ssd        : disk type is ssd <boolean> (add)
    -F, --freq       : dump value <value> (add)
    -p, --pass       : mount order <value> (add)
    -U, --uacc       : users access level (,r,w) (default = rw) (add)
    -S, --sacc       : superuser access level (,r,w) (default = rw) (add)
    -M, --method     : mount method <string> (see below) (add)
    -I, --idletimeout: unmount when idle timeout <int> (default = 0) (add)
    -T, --timeout    : mounting timeout <int> (default = 0) (add)

Mount methods:
disabled: do not mount
startup : mount from fstab during startup (default)
auto    : auto mount from fstab when accessed
dynmount: dynamically mount when available
Options may be entered as single JSON string using full name, e.g.
xmount add test '{"fsname": "/dev/sda1", "mountpoint": "/mnt/test",
               "type": "ext4"}'
Mind the single quotes to bind the JSON string.

xremotemount
------------
xremotemount <arguments> <options>
<arguments>:
    add           : adds or edits a remotemount [add <name>]
    del           : deletes a remotemount [del <name>]
    pop           : populates from fstab [pop]
    mnt           : mounts a remotemount [mnt <name>]
    umnt          : unmounts a remotemount if not referenced [umnt <name>]
    clr           : removes a remotemount, but leaves fstab [clr <name>]
    lst           : lists xremotemount compatible fstab entries [lst]
    url           : prints url of a <name> or <server>, <sharename> [url]
    <no arguments>: show remotemounts and their status
<options>:
    -h, --help       : this help file
    -v, --version    : print version information
    -j, --json       : display output in JSON format
    -i, --interactive: ask before adding or changing mounts
    -H, --human      : show sizes in human readable format
    -t, --https      : davfs use https <boolean> (default = True) (add)
    -s, --server     : server for remote mount <string> (add)
    -S, --sharename  : sharename for remote mount <string> (add)
    -m, --mountpoint : mountpoint <string> (add)
    -T, --type       : type <string> (davfs, cifs, nfs or nfs4) (add)
    -o, --options    : extra options, besides _netdev <string> (add)
    -r, --rw         : mount rw <boolean> (add)
    -f, --freq       : dump value <value> (add)
    -p, --pass       : mount order <value> (add)
    -u, --uacc       : users access level (,r,w) (default = rw) (add)
    -a, --sacc       : superuser access level (,r,w) (default = rw) (add)
    -U, --username   : remote mount access username (guest if omitted) (add)
    -P, --password   : remote mount access password (add)
    -A, --action     : addkey, addcred, delkey, delcred (s2hfs) (add)
    -M, --method     : mount method <string> (see below) (add)
    -I, --idletimeout: unmount when idle timeout <int> (default = 30) (add)
    -e, --timeout    : mounting timeout <int> (default = 10) (add)

URL generation from settings:
davfs: <https>://<sharename>.<server>, e.g. https://test.myserver.com/dav.php/
s2hfs: <user>@<server>:<sharename>   , e.g. test@192.168.1.1:myfolder
cifs : //<server>/<sharename>        , e.g. //192.168.1.1/test
nfs  : server:<sharename>            , e.g. 192.168.1.1:/test
"nfs4" is prefered as type for nfs, "nfs" as type refers to nfs3
A specific action for s2hfs (sshfs) can be defined:
addkey : generate and add an ssh key pair for accessing s2hfs
addcred: add credentials for accessing s2hfs
delkey : delete an existing key pair
delcred: delete existing credentials
At del, keys and credentials will be deleted
Mount methods:
disabled: do not mount
startup : mount from fstab during startup
auto    : auto mount from fstab when accessed (default)
dynmount: dynamically mount when available
Options may be entered as single JSON string using full name, e.g.
xremotemount add test '{"server": "192.168.1.1", "sharename": "test",
               "mountpoint": "/mnt/test", "type": "cifs",
               "username": "userme", "password": "secret"}'
Mind the single quotes to bind the JSON string.

xshare
------
xshare <arguments> <options>
<arguments>:
    add           : adds or edits a share [add <name>]
    del           : deletes a share [del <name>]
    ena           : enables a share [ena <name>]
    dis           : disables a share [dis <name>]
    <no arguments>: show shares and their status
<options>:
    -h, --help   : this help file
    -v, --version: print version information
    -j, --json   : display output in JSON format
    -m, --mount  : mount name to share <string> (add)
    -t, --type   : mount or remotemount type to search <string> (add)
    -f, --folder : relative folder in mount to share <string> (add)

Options may be entered as single JSON string using full name, e.g.
xshare add test '{"mount": "TEST", "folder": "/music"}'
Mind the single quotes to bind the JSON string.

xnetshare
---------
xnetshare <arguments> <options>
<arguments>:
    add           : adds or edits a netshare [add <name>]
    del           : deletes a netshare [del <name>]
    ena           : enables a netshare [ena <name>]
    dis           : disables a netshare [dis <name>]
    cnf           : configure a netshare [cnf]
    hms           : configure homes for cifs [hms]
    usr           : configure users for cifs [usr (add, del, exists, list)]
    prv           : configure user privileges for cifs [prv <name>]
    bin           : empty recycle bin for cifs [bin <name>] or [bin] for all
    rfr           : refreshes netshares
    lst           : lists xshares to netshare [lst]
    ip            : generates ip address/ mask
    <no arguments>: show netshares and their status
<options>:
    -h, --help   : this help file
    -v, --version: print version information
    -j, --json   : display output in JSON format
    -t, --type   : cifs or nfs type share <string> (add, cnf)

Show specific help for commands by filesystem type by e.g.
xnetshare add -t cifs -h
The name entered needs to be an existing share name.
Options may be entered as single JSON string using full name, e.g.
xnetshare add test '{"type": "cifs"}'
Mind the single quotes to bind the JSON string.

"recyclemaxage' is handled by xservices and needs xservices and
cifs automatically empty recycle bin to be enabled.
command: 'xnas srv -e -B' (xservices and bin are enabled by default)
Specific options for 'xnetshare add -t cifs':
    <options>:
        -c, --comment           : comment for cifs share (default = '')
        -g, --guest             : allow guests (no, allow, only) (default = no)
        -r, --readonly          : readonly share (default = false)
        -b, --browseable        : browseable share (default = true)
        -R, --recyclebin        : use recycle bin (default = false)
        -e, --recyclemaxsize    : max bin size [bytes] (default = 0 = no limit)
        -E, --recyclemaxage     : max bin age [days] (default = 0 = no max)
        -H, --hidedotfiles      : hide dot files (default = true)
        -i, --inheritacls       : inherit acls (default = true)
        -I, --inheritpermissions: inherit permissions (default = false)
        -a, --easupport         : ea support (default = false)
        -s, --storedosattr      : store dos attributes (default = false)
        -o, --hostsallow        : allow hosts (default = '')
        -O, --hostsdeny         : deny hosts (default = '')
        -A, --audit             : use audit (default = false)
        -x, --extraoptions      : extra options (default = '{}')
        -S, --settings          : lists current netshare settings

Specific options for 'xnetshare add -t nfs':
    <options>:
        -c, --client      : ip address/mask (default = 192.168.1.0/24)
        -r, --readonly    : read only share (default = false)
        -e, --extraoptions: extra options (default = '{}')
        -s, --settings    : lists current netshare settings

Specific options for 'xnetshare cnf -t cifs':
    <options>:
        -e, --enable      : enable cifs server <boolean>
        -w, --workgroup   : name of the workgroup (default = WORKGROUP)
        -s, --serverstring: server string (default = %h server)
        -l, --loglevel    : log level (default = 0)
        -S, --sendfile    : use send file (default = true)
        -a, --aio         : use asynchronous io (default = true)
        -L, --localmaster : use local master (default = true)
        -T, --timeserver  : use time server (default = false)
        -W, --winssupport : use wins support (default = false)
        -i, --winsserver  : wins server (default = '')
        -E, --extraoptions: extra options (default = '{}')
        -c, --clear       : clear (remove) existing configfile (default = false)
        -I, --settings    : lists current configuration settings

Specific options for 'xnetshare cnf -t nfs':
    <options>:
        -e, --enable : enable nfs server <boolean>
        -s, --servers: number of servers to startup (default = 8)
        -c, --clear  : clear (remove) existing configfile (default = false)
        -S, --settings: lists current configuration settings

Specific options for 'xnetshare hms -t cifs':
    <options>:
        -e, --enable    : enable homes folders (default = true)
        -b, --browseable: homes folders are browseable (default = true)
        -w, --writable  : homes folders are writable (default = true)
        -E, --extraoptions: extra options (default = '{}')
        -s, --settings  : lists current homes settings

Specific arguments for 'xnetshare usr -t cifs':
    <arguments>
        list  : displays a list of users
        exists: checks whether a user with <username> exists
        add   : adds or modifies a user with <username>
        del   : deletes a user with <username>
Specific options for 'xnetshare usr -t cifs':
    <options>:
        -u, --username: cifs username (error if omitted)
        -p, --password: cifs password (interactive if omitted or empty)
        -f, --fullname: cifs user full name (optional)
        -c, --comment : cifs user comment (optional)

Specific options for 'xnetshare prv -t cifs':
    <options>:
        -l, --list    : lists users and privileges for this netshare
        -u, --username: cifs username (guest user if omitted)
        -i, --invalid : explicitly deny access for this user
        -r, --readonly: readonly access for this user (default is read write)
        -d, --delete  : delete access for this user

xservices
---------
xservices <options>
<options>:
    -h, --help   : this help file
    -v, --version: print version information
    -j, --json   : display output in JSON format
    -V, --verbose: be verbose in actions (for debugging)

xservices needs to preferably run as a service
It takes care of:
Dynmount:        dynamically mount mounts or remotemounts when they become
                 available. Options can be changed with: "xnas srv ..."
Emptyrecyclebin: automatically delete old files from cifs recycle bin
                 Maximum age can be changed with: "xnetshare add ..."
Autofix:         Check for errors and automatically fix them
                 Options can be changed with: "xnas srv ..."
xservices can be enabled or disabled with "xnas srv -e

xcd
---
xcd <arguments> <options>
<arguments>:
    <name>: Name of the folder to lookup
    <loc> : (Optional) Relative location from the name folder
    <type>: (Optional) Type of object to look at
<options>:
    -h, --help   : this help file
    -v, --version: print version information
    -j, --json   : display output in JSON format

Changes to folder location
When type is not defined, first shares is checked, then mounts and remote mounts
Types: mount, remotemount, share, netshare

xdir
----
xdir <arguments> <options>
 <arguments>:
     <name>: Name of the folder to change to
     <loc> : (Optional) Relative location from the name folder
     <type>: (Optional) Type of object to look at
 <options>:
     -h, --help   : this help file
     -v, --version: print version information
     -j, --json   : display output in JSON format
     -H, --human  : show sizes in human readable format
     -s, --short  : show in short format (only names)
     -n, --noroot : don't show root folders (. and ..)
     -N, --nocolor: don't show colors
     -o, --noclass: don't classify
     -O, --nosort : don't soft alphabetically by name

Lists folder contents
When type is not defined, first shares is checked, then mounts and remote mounts
<type>: mount, remotemount, share, netshare
<loc>: can also be a file or multiple files with wildcards *? etc.

xpd
---
xpd <arguments> <options>
<arguments>:
    <name>: Name of the folder to lookup
    <loc> : (Optional) Relative location from the name folder
    <type>: (Optional) Type of object to look at
<options>:
    -h, --help   : this help file
    -v, --version: print version information
    -j, --json   : display output in JSON format

Prints folder location
When type is not defined, first shares is checked, then mounts and remote mounts
Types: mount, remotemount, share, netshare

Simple example:
====== ========
Say you have a local drive mounted at '/dev/sda1' that is not in fstab yet
with a folder 'MyFolder' that you want to share using cifs.
This share is only accessible (read and write) by the user 'MeAsUser' with
as password 'SecretPassword'

sudo xmount add MyLocalDrive --fsname /dev/sda1 --type ext4 --ssd

sudo xshare add MyShare --mount MyLocalDrive --type mount --folder MyFolder

sudo xnetshare add MyShare --type cifs --comment "my first share!"

sudo xnetshare usr add --type cifs --username MeAsUser --password SecretPassword

sudo xnetshare prv MyShare --username MeAsUser

That's all for now ...

Please send Comments and Bugreports to hellyrulez@home.nl
