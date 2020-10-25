#!/bin/bash
NAME="xnas"
SERVICENAME="xservices"
INSTALL="/usr/bin/install -c"
INSTALL_DATA="$INSTALL -m 644"
INSTALL_PROGRAM="$INSTALL"
ETCDIR="/etc"
USRDIR="/usr"
OPTDIR="/opt"
OPTLOC="$OPTDIR/$NAME"
ETCLOC=$ETCDIR
BINDIR="$USRDIR/bin"
BINDSCRIPT="$NAME.service"
SERVICESCRIPT="$SERVICENAME.service"
SERVICEDIR="/etc/systemd/system"

DEBFOLDER="debian"
BASHRC1="$ETCDIR/bash.bashrc"
BASHRC2="$ETCDIR/bashrc"
XCDALIAS="alias xcd='. $OPTLOC/xcd.sh'"

PY=".py"
XDIR="xdir"
PYXDIR="$XDIR$PY"
BINXDIR="$BINDIR/$XDIR"
XMOUNT="xmount"
PYXMOUNT="$XMOUNT$PY"
BINXMOUNT="$BINDIR/$XMOUNT"
XNAS="xnas"
PYXNAS="$XNAS$PY"
BINXNAS="$BINDIR/$XNAS"
XNET="xnetshare"
PYXNET="$XNET$PY"
BINXNET="$BINDIR/$XNET"
XPD="xpd"
PYXPD="$XPD$PY"
BINXPD="$BINDIR/$XPD"
XREM="xremotemount"
PYXREM="$XREM$PY"
BINXREM="$BINDIR/$XREM"
XSRV="xservices"
PYXSRV="$XSRV$PY"
BINXSRV="$BINDIR/$XSRV"
XSHR="xshare"
PYXSHR="$XSHR$PY"
BINXSHR="$BINDIR/$XSHR"

if [ "$EUID" -ne 0 ]
then
	echo "Please execute as root ('sudo install.sh' or 'sudo make install')"
	exit
fi

if [ "$1" == "-u" ] || [ "$1" == "-U" ]
then
	echo "$NAME uninstall script"

	echo "Uninstalling service $SERVICENAME"
    if [ -f "$SERVICEDIR/$SERVICESCRIPT" ]; then
        systemctl stop $SERVICESCRIPT
        systemctl disable $SERVICESCRIPT
    fi
    if [ -e "$SERVICEDIR/$SERVICESCRIPT" ]; then rm -f "$SERVICEDIR/$SERVICESCRIPT"; fi

    echo "Uninstalling service $NAME"
    if [ -f "$SERVICEDIR/$BINDSCRIPT" ]; then
        systemctl stop $BINDSCRIPT
        systemctl disable $BINDSCRIPT
    fi
    if [ -e "$SERVICEDIR/$BINDSCRIPT" ]; then rm -f "$SERVICEDIR/$BINDSCRIPT"; fi

    echo "Uninstalling $NAME"

    # Remove aliases
    echo "Removing alias for xcd in interactive shells"
    if [ -f $BASHRC1 ]; then
        BASHRC=$BASHRC1
    elif [ -f $BASHRC2 ]; then
        BASHRC=$BASHRC2
    else
        BASHRC=
        echo "bashrc doesn't exist, aliases not removed"
    fi

    if [ -n $BASHRC ]; then
        if grep -q "$XCDALIAS" $BASHRC; then
            echo "$(grep -v "$XCDALIAS" $BASHRC)" > $BASHRC
        fi
    fi

    # Remove links
    echo "Removing binaries"
    unlink $BINXDIR
    unlink $BINXMOUNT
    unlink $BINXNAS
    unlink $BINXNET
    unlink $BINXPD
    unlink $BINXREM
    unlink $BINXSRV
    unlink $BINXSHR

    echo "Removing files"
	if [ -d "$OPTLOC" ]; then rm -rf "$OPTLOC"; fi
elif [ "$1" == "-h" ] || [ "$1" == "-H" ]
then
	echo "Usage:"
	echo "  <no argument>: install $NAME"
	echo "  -u/ -U       : uninstall $NAME"
	echo "  -h/ -H       : this help file"
	echo "  -d/ -D       : build debian package"
	echo "  -c/ -C       : Cleanup compiled files in install folder"
elif [ "$1" == "-c" ] || [ "$1" == "-C" ]
then
	echo "$NAME Deleting compiled files in install folder"
	py3clean .
	rm -f ./*.deb
	rm -rf "$DEBFOLDER"/$NAME
	rm -rf "$DEBFOLDER"/.debhelper
	rm -f "$DEBFOLDER"/files
	rm -f "$DEBFOLDER"/files.new
	rm -f "$DEBFOLDER"/$NAME.*
elif [ "$1" == "-d" ] || [ "$1" == "-D" ]
then
	echo "$NAME build debian package"
	py3clean .
	fakeroot debian/rules clean binary
	mv ../*.deb .
else
	echo "$NAME install script"

	echo "Stop running services"
    if [ -f "$SERVICEDIR/$SERVICESCRIPT" ]; then
        systemctl stop $SERVICESCRIPT
        systemctl disable $SERVICESCRIPT
    fi
    if [ -f "$SERVICEDIR/$BINDSCRIPT" ]; then
        systemctl stop $BINDSCRIPT
        systemctl disable $BINDSCRIPT
    fi

    echo "Installing $NAME"
    if [ -d "$OPTLOC" ]; then rm -rf "$OPTLOC"; fi
	if [ ! -d "$OPTLOC" ]; then
		mkdir "$OPTLOC"
		chmod 755 "$OPTLOC"
	fi

    # Install all files and folders
    echo "Installing files"
    cp -r ".$OPTLOC"/* "$OPTLOC"
	$INSTALL_PROGRAM ".$OPTLOC/$PYXDIR" "$OPTLOC"
    $INSTALL_PROGRAM ".$OPTLOC/$PYXMOUNT" "$OPTLOC"
    $INSTALL_PROGRAM ".$OPTLOC/$PYXNAS" "$OPTLOC"
    $INSTALL_PROGRAM ".$OPTLOC/$PYXNET" "$OPTLOC"
    $INSTALL_PROGRAM ".$OPTLOC/$PYXPD" "$OPTLOC"
    $INSTALL_PROGRAM ".$OPTLOC/$PYXREM" "$OPTLOC"
    $INSTALL_PROGRAM ".$OPTLOC/$PYXSRV" "$OPTLOC"
    $INSTALL_PROGRAM ".$OPTLOC/$PYXSHR" "$OPTLOC"

    # Add symbolic links
    echo "Installing binaries"
    ln -s "$OPTLOC/$PYXDIR" $BINXDIR
    ln -s "$OPTLOC/$PYXMOUNT" $BINXMOUNT
    ln -s "$OPTLOC/$PYXNAS" $BINXNAS
    ln -s "$OPTLOC/$PYXNET" $BINXNET
    ln -s "$OPTLOC/$PYXPD" $BINXPD
    ln -s "$OPTLOC/$PYXREM" $BINXREM
    ln -s "$OPTLOC/$PYXSRV" $BINXSRV
    ln -s "$OPTLOC/$PYXSHR" $BINXSHR

    # Add aliases
    echo "Adding alias for xcd in interactive shells"
    if [ -f $BASHRC1 ]; then
        BASHRC=$BASHRC1
    elif [ -f $BASHRC2 ]; then
        BASHRC=$BASHRC2
    else
        BASHRC=
        echo "bashrc doesn't exist, aliases not added"
    fi

    if [ -n $BASHRC ]; then
        if ! grep -q "$XCDALIAS" $BASHRC; then
            echo -e "$XCDALIAS\n" >> $BASHRC
        fi
    fi

	#echo "Installing daemon $NAME"
	#read -p "Do you want to install an automatic startup service for $NAME (Y/n)? " -n 1 -r
	#echo    # (optional) move to a new line
	#if [[ $REPLY =~ ^[Nn]$ ]]
	#then
	#	echo "Skipping install automatic startup service for $NAME"
	#else
    if true; then
		echo "Install automatic startup service for $NAME"
        $INSTALL_DATA ".$SERVICEDIR/$BINDSCRIPT" "$SERVICEDIR/$BINDSCRIPT"
		$INSTALL_DATA ".$SERVICEDIR/$SERVICESCRIPT" "$SERVICEDIR/$SERVICESCRIPT"

        if [ -f "$SERVICEDIR/$BINDSCRIPT" ]; then
            systemctl enable $BINDSCRIPT
            systemctl start $BINDSCRIPT
        fi
        if [ -f "$SERVICEDIR/$SERVICESCRIPT" ]; then
            systemctl enable $SERVICESCRIPT
            systemctl start $SERVICESCRIPT
        fi
	fi
fi
