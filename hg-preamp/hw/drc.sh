#!/bin/sh
# Run KiCad DRC and summarise violations by type.
cd "$(dirname "$0")"
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc --format json --severity-all -o drc.json pedal.kicad_pcb >/dev/null 2>&1
python3 - <<'PY'
import json, collections
d = json.load(open("drc.json"))
for key in ("violations", "unconnected_items", "schematic_parity"):
    items = d.get(key, [])
    c = collections.Counter((v["severity"], v["type"]) for v in items)
    print(key, len(items))
    for (sev, t), n in c.most_common():
        print(f"   {n:4d} {sev:8s} {t}")
PY
