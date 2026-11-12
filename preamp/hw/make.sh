#!/bin/sh
# Rebuild the board end to end: place -> build -> route -> apply -> DRC
set -e
cd "$(dirname "$0")"
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
[ "$1" = "noplace" ] || python3 place.py
$KP build_pcb.py 2>&1 | grep -v wxApp
python3 route.py
$KP apply_routes.py 2>&1 | grep -v wxApp
./drc.sh
