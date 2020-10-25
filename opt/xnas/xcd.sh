#!/bin/bash
rv=$(/opt/xnas/xcd.py "$@")

if [ $? -eq 255 ]
then
    cd "$rv"
else
    echo "$rv"
fi
