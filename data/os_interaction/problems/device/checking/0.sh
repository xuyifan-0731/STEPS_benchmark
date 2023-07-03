#!/bin/bash

target="cat /proc/cpuinfo | grep -m1 -E 'cpu MHz' | grep 'cpu MHz' | awk -F ': ' '{print $2}'"
percentage=5
range=$(echo "${percentage}/100+1" | bc -l)

if [ "$(echo "${target} * ${range}" | bc -l)" \< "$(echo "$1" | bc -l)" ] || [ "$(echo "${target} * ${range}" | bc -l)" \> "$(echo "$1" | bc -l)" ]; then
    exit 1
else
    exit 0
fi
