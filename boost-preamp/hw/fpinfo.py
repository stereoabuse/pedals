"""Run with KiCad's python: dump pad/courtyard geometry of each library footprint used."""
import json, os, sys
import pcbnew
sys.path.insert(0, os.path.dirname(__file__))
from design import KINDS

LIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
out = {}
for kind, (fp, _) in KINDS.items():
    lib, name = fp.split(":")
    if lib == "custom":
        continue
    f = pcbnew.FootprintLoad(os.path.join(LIB, lib + ".pretty"), name)
    pads = []
    for p in f.Pads():
        pos, sz = p.GetPosition(), p.GetSize(pcbnew.F_Cu) if hasattr(p, "GetSize") else None
        pads.append(dict(num=p.GetNumber(), x=pcbnew.ToMM(pos.x), y=pcbnew.ToMM(pos.y),
                         w=pcbnew.ToMM(sz.x), h=pcbnew.ToMM(sz.y), smd=p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD))
    cy = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
    out[kind] = dict(fp=fp, pads=pads, cy=[pcbnew.ToMM(cy.GetLeft()), pcbnew.ToMM(cy.GetTop()), pcbnew.ToMM(cy.GetRight()), pcbnew.ToMM(cy.GetBottom())])
json.dump(out, open(os.path.join(os.path.dirname(__file__), "fpinfo.json"), "w"), indent=1)
for k, v in out.items():
    print(k, v["cy"], [(p["num"], p["x"], p["y"], p["w"], p["h"]) for p in v["pads"]])
