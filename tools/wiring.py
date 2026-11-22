"""Draw the off-board wiring diagram for each pedal: docs/wiring.svg (and .png) in its folder.

Run from the repo root:  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run --with cairosvg python3 tools/wiring.py
The board outline, pad positions and pad labels are read from each design's own files;
the footswitch lug assignments are the ones in each README's wiring tables.
"""
import ast, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COL = dict(IN="#e08a00", OUT="#1f6fd0", GND="#222222", PWR="#d42020", LED="#2a9d3a", LINK="#8a3fc0", JUMP="#888888")
KEY = [("IN", "guitar signal in"), ("OUT", "signal out"), ("LINK", "between sections / control"), ("LED", "LED"),
       ("PWR", "+9V"), ("GND", "ground"), ("JUMP", "jumper on the switch")]


def jack(name, x0, y0, side, terms):
    """Box 22 x 28 with terminals on the left or right edge. terms: names top to bottom."""
    x = x0 + 22 if side == "r" else x0
    return dict(kind="box", name=name, rect=(x0, y0, 22, 28), pts={t: (x, y0 + 7 + 7 * i) for i, t in enumerate(terms)},
                lab="l" if side == "r" else "r")


def topbox(name, x0, y0, w, terms):
    """Box with terminals on the bottom edge. terms: {name: x}."""
    return dict(kind="box", name=name, rect=(x0, y0, w, 16), pts={t: (x, y0 + 16) for t, x in terms.items()}, lab="u")


def switch(name, cx, cy, order="ABC"):
    pts = {f"{c}{r}": (cx + (i - 1) * 8, cy + (r - 2) * 7) for i, c in enumerate(order) for r in (1, 2, 3)}
    return dict(kind="sw", name=name, c=(cx, cy), pts=pts)


POWER = [("PWR", "dc.sleeve", "pad.J_9V", []), ("GND", "dc.centre", "pad.J_G1", "jog"),
         ("PWR", "bat.red", "dc.switch", "under"), ("GND", "bat.black", "in.ring", "left")]

DESIGNS = {
    "preamp": dict(
        title="preamp: off-board wiring", view=(0, 24, 200, 190), pads_below={"J_9V", "J_G1"},
        things=dict(inj=jack("INPUT JACK (stereo)", 8, 148, "r", ["ring", "tip", "sleeve"]),
                    out=jack("OUTPUT JACK", 170, 148, "l", ["tip"]),
                    dc=topbox("DC JACK", 116, 44, 24, dict(switch=120, sleeve=128.34, centre=136)),
                    bat=topbox("9V BATTERY", 84, 44, 24, dict(black=88, red=104)),
                    L=switch("BYPASS footswitch", 70, 162), R=switch("BOOST footswitch", 130, 162, "CBA")),
        wires=[("IN", "inj.tip", "L.A2", []), ("IN", "L.A1", "pad.J_IN", [(62, 141), (61.5, 141)]),
               ("OUT", "L.B1", "pad.J_OUT", [(70, 148), (92, 148), (92, 183), (146, 183), (146, 134), (138.5, 134)]),
               ("OUT", "L.B2", "out.tip", [(70, 165.5), (88, 165.5), (88, 187), (160, 187), (160, 155)]),
               ("LED", "L.C1", "pad.J_L1", [(78, 144), (66.58, 144)]),
               ("GND", "L.C2", "pad.J_G2", [(84, 162), (84, 137), (64.04, 137)]),
               ("JUMP", "L.A3", "L.B3", [(62, 172.5), (70, 172.5)]),
               ("IN", "L.C3", "L.A1", [(78, 175), (54, 175), (54, 158.5), (62, 158.5)]),
               ("GND", "inj.sleeve", "pad.J_G2", [(50, 169), (50, 133), (64.04, 133)]),
               ("LED", "R.B1", "pad.J_L1B", [(130, 141.5), (118.18, 141.5)]),
               ("LED", "R.B2", "pad.J_L2", [(126, 162), (126, 145), (120.72, 145)]),
               ("LINK", "R.A2", "pad.J_BST", [(144, 162), (144, 136), (123.26, 136)]),
               ("GND", "R.A3", "pad.J_G3", [(142, 169), (142, 139), (125.8, 139)]),
               ("PWR", "dc.sleeve", "pad.J_9V", []), ("GND", "dc.centre", "pad.J_G1", [(136, 64), (130.88, 64)]),
               ("PWR", "bat.red", "dc.switch", [(104, 64), (120, 64)]),
               ("GND", "bat.black", "inj.ring", [(88, 64), (38, 64), (38, 155)])],
        notes=["BOOST switch: only four lugs are used. Boost is ON when BST is left open.",
               "The output jack grounds through the metal enclosure."]),
    "boost-preamp": dict(
        title="boost-preamp: off-board wiring", view=(0, 24, 200, 190), pads_below={"J_9V", "J_G1"},
        things=dict(inj=jack("INPUT JACK (stereo)", 8, 148, "r", ["ring", "tip", "sleeve"]),
                    out=jack("OUTPUT JACK", 170, 148, "l", ["tip"]),
                    dc=topbox("DC JACK", 116, 44, 24, dict(switch=120, sleeve=128.34, centre=136)),
                    bat=topbox("9V BATTERY", 84, 44, 24, dict(black=88, red=104)),
                    L=switch("BOOST footswitch", 70, 162, "CBA"), R=switch("PREAMP footswitch", 130, 162, "CBA")),
        wires=[("IN", "inj.tip", "L.A2", [(44, 162), (44, 178), (84, 178), (84, 162)]),
               ("IN", "L.A1", "pad.J_BIN", [(78, 146), (76.74, 146)]),
               ("OUT", "L.B1", "pad.J_BOUT", [(70, 146), (71.66, 146)]),
               ("LED", "L.C1", "pad.J_L1", [(62, 142), (66.58, 142)]),
               ("GND", "L.C2", "pad.J_G2", [(56, 162), (56, 136), (64.04, 136)]),
               ("JUMP", "L.A3", "L.B3", [(78, 172.5), (70, 172.5)]),
               ("IN", "L.C3", "L.A1", [(66, 169), (66, 158.5), (78, 158.5)]),
               ("LINK", "L.B2", "R.A2", [(70, 165.5), (88, 165.5), (88, 183), (142, 183), (142, 162)]),
               ("LINK", "R.A1", "pad.J_IN", [(138, 150), (146, 150), (146, 187), (50, 187), (50, 134), (61.5, 134)]),
               ("OUT", "R.B1", "pad.J_OUT", [(130, 144), (138.5, 144)]),
               ("OUT", "R.B2", "out.tip", [(130, 165.5), (160, 165.5), (160, 155)]),
               ("LED", "R.C1", "pad.J_L2", [(122, 142), (120.72, 142)]),
               ("GND", "R.C2", "pad.J_G5", [(116, 162), (116, 137), (123.26, 137)]),
               ("JUMP", "R.A3", "R.B3", [(138, 172.5), (130, 172.5)]),
               ("LINK", "R.C3", "R.A1", [(126, 169), (126, 158.5), (138, 158.5)]),
               ("GND", "inj.sleeve", "pad.J_G2", [(47, 169), (47, 131.5), (64.04, 131.5)]),
               ("PWR", "dc.sleeve", "pad.J_9V", []), ("GND", "dc.centre", "pad.J_G1", [(136, 64), (130.88, 64)]),
               ("PWR", "bat.red", "dc.switch", [(104, 64), (120, 64)]),
               ("GND", "bat.black", "inj.ring", [(88, 64), (38, 64), (38, 155)])],
        notes=["The two purple runs (BOOST B2 to PREAMP A2, and PREAMP A1 to the IN pad) should be shielded wire,",
               "shield soldered to a G pad at one end only. The output jack grounds through the metal enclosure."]),
    "screamer": dict(
        title="screamer: off-board wiring", view=(22, 36, 156, 152), pads_below={"J_9V", "J_G1", "J_G2"},
        things=dict(inj=jack("INPUT JACK (stereo)", 30, 136, "r", ["ring", "tip", "sleeve"]),
                    out=jack("OUTPUT JACK", 148, 136, "l", ["tip"]),
                    dc=topbox("DC JACK", 72, 56, 27, dict(switch=77, sleeve=85.5, centre=94)),
                    bat=topbox("9V BATTERY", 40, 56, 22, dict(black=46, red=58)),
                    S=switch("BYPASS footswitch", 100, 150)),
        wires=[("IN", "inj.tip", "S.A2", []), ("IN", "S.A1", "pad.J_IN", [(92, 132), (85.5, 132)]),
               ("OUT", "S.B1", "pad.J_OUT", [(100, 136), (114.5, 136)]),
               ("OUT", "S.B2", "out.tip", [(100, 153.5), (126, 153.5), (126, 150)]),
               ("LED", "S.C1", "pad.J_L", [(108, 131), (98.73, 131)]),
               ("GND", "S.C2", "pad.J_G4", [(112, 150), (112, 127), (101.27, 127)]),
               ("JUMP", "S.A3", "S.B3", [(92, 160.5), (100, 160.5)]),
               ("IN", "S.C3", "S.A1", [(108, 163.5), (84, 163.5), (84, 146.5), (92, 146.5)]),
               ("GND", "inj.sleeve", "pad.J_G3", [(72, 157), (72, 128), (88.04, 128)]),
               ("PWR", "dc.sleeve", "pad.J_9V", []), ("GND", "dc.centre", "pad.J_G1", [(94, 77), (88.04, 77)]),
               ("PWR", "bat.red", "dc.switch", [(58, 76), (77, 76)]),
               ("GND", "bat.black", "inj.ring", [(46, 134), (57, 134), (57, 143)])],
        notes=["The output jack grounds through the metal enclosure."]),
    "muff-screamer": dict(
        title="muff-screamer: off-board wiring", view=(0, 24, 200, 190), pads_below={"J_9V", "J_G1"},
        things=dict(inj=jack("INPUT JACK (stereo)", 8, 148, "r", ["ring", "tip", "sleeve"]),
                    out=jack("OUTPUT JACK", 170, 148, "l", ["tip"]),
                    dc=topbox("DC JACK", 116, 44, 24, dict(switch=120, sleeve=128.34, centre=136)),
                    bat=topbox("9V BATTERY", 84, 44, 24, dict(black=88, red=104)),
                    L=switch("SCREAMER footswitch", 70, 162, "CBA"), R=switch("MUFF footswitch", 130, 162)),
        wires=[("IN", "inj.tip", "pad.J_IN", [(44, 162), (44, 140), (61.5, 140)]),
               ("GND", "inj.sleeve", "pad.J_G2", [(47, 169), (47, 134), (64.04, 134)]),
               ("OUT", "pad.J_OUT", "out.tip", [(138.5, 140), (160, 140), (160, 155)]),
               ("LINK", "L.A1", "pad.J_FT", [(78, 148), (71.66, 148)]),
               ("GND", "L.A2", "pad.J_G4", [(86, 162), (86, 143), (74.2, 143)]),
               ("LINK", "R.A2", "pad.J_FM", [(114, 162), (114, 145), (120.72, 145)]),
               ("GND", "R.A1", "pad.J_G5", [(122, 150), (123.26, 150)]),
               ("PWR", "dc.sleeve", "pad.J_9V", []), ("GND", "dc.centre", "pad.J_G1", [(136, 64), (130.88, 64)]),
               ("PWR", "bat.red", "dc.switch", [(104, 64), (120, 64)]),
               ("GND", "bat.black", "inj.ring", [(88, 64), (38, 64), (38, 155)])],
        notes=["Each footswitch only shorts its FS pad to a G pad, so one pole of any latching switch does it (two lugs of a 3PDT).",
               "No signal passes through the footswitches. The output jack grounds through the metal enclosure."]),    "decade-drive": dict(
        title="decade-drive: off-board wiring", view=(6, 18, 190, 200), pads_below={"J_9V", "J_G1"},
        things=dict(inj=jack("INPUT JACK (stereo)", 14, 168, "r", ["ring", "tip", "sleeve"]),
                    out=jack("OUTPUT JACK", 164, 168, "l", ["tip"]),
                    dc=topbox("DC JACK", 110, 36, 28, dict(switch=115, sleeve=124.62, centre=133)),
                    bat=topbox("9V BATTERY", 62, 36, 26, dict(black=67, red=83)),
                    S=switch("BYPASS footswitch", 100, 186)),
        wires=[("IN", "inj.tip", "S.A2", [(80, 182), (80, 186)]), ("IN", "S.A1", "pad.J_IN", [(92, 174), (57, 174)]),
               ("OUT", "S.B1", "pad.J_OUT", [(100, 171), (117, 171)]),
               ("OUT", "S.B2", "out.tip", [(100, 189.5), (152, 189.5), (152, 175)]),
               ("LED", "S.C1", "pad.J_L", [(108, 165), (78, 165)]),
               ("GND", "S.C2", "pad.J_G4", [(113, 186), (113, 162), (80.54, 162)]),
               ("JUMP", "S.A3", "S.B3", [(92, 196.5), (100, 196.5)]),
               ("IN", "S.C3", "S.A1", [(108, 199.5), (84, 199.5), (84, 182.5), (92, 182.5)]),
               ("GND", "inj.sleeve", "pad.J_G2", [(59.54, 189)]),
               ("PWR", "dc.sleeve", "pad.J_9V", []), ("GND", "dc.centre", "pad.J_G1", [(133, 57), (122.08, 57)]),
               ("PWR", "bat.red", "dc.switch", [(83, 57), (115, 57)]),
               ("GND", "bat.black", "inj.ring", [(67, 57), (44, 57), (44, 175)])],
        notes=["The output jack grounds through the metal enclosure; the spare G pad next to OUT is for an insulated jack.",
               "The battery lies behind the board. The toggles and the Level pot solder straight to the board and need no wires."]),
}


def pad_labels(design):
    src = open(os.path.join(ROOT, design, "hw", "build_pcb.py")).read()
    return ast.literal_eval(re.search(r"PAD_LABEL = (\{.*?\})", src, re.S).group(1))


def draw(design, spec):
    PL = json.load(open(os.path.join(ROOT, design, "hw", "placement.json")))
    labels = pad_labels(design)
    o = PL["outline"]
    pts = {f"pad.{r}": tuple(v["1"][:2]) for r, v in PL["tht"].items() if r.startswith("J_")}
    for key, t in spec["things"].items():
        for n, p in t["pts"].items():
            pts[f"{key}.{n}"] = p
    vx, vy, vw, vh = spec["view"]
    S = 7
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw*S}" height="{vh*S}" viewBox="{vx} {vy} {vw} {vh}" font-family="Helvetica, Arial, sans-serif">',
           f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" fill="white"/>',
           f'<text x="{vx+3}" y="{vy+6}" font-size="4.2" font-weight="bold">{spec["title"]}</text>',
           f'<text x="{vx+3}" y="{vy+10.5}" font-size="2.5" fill="#555">Seen from the back of the pedal (the SMD side of the board). Shows connections only; not to scale.</text>']
    # board
    if "LEG_L" in o:
        poly = [(o["X0"], o["YT"]), (o["X1"], o["YT"]), (o["X1"], o["YB"]), (o["LEG_R"], o["YB"]), (o["LEG_R"], o["YM"]),
                (o["LEG_L"], o["YM"]), (o["LEG_L"], o["YB"]), (o["X0"], o["YB"])]
    else:
        poly = [(o["X0"], o["YT"]), (o["X1"], o["YT"]), (o["X1"], o["YB"]), (o["X0"], o["YB"])]
    out.append('<polygon points="%s" fill="#3f5d43" stroke="#22382a" stroke-width="0.5" stroke-linejoin="round"/>' % " ".join(f"{x},{y}" for x, y in poly))
    out.append(f'<text x="{(o["X0"]+o["X1"])/2}" y="{o["YT"]+ (o.get("YM", o["YB"]) - o["YT"]) / 2}" font-size="3.4" fill="#cfe3d0" text-anchor="middle">BOARD (SMD side)</text>')
    names = []
    # boxes and switches
    for key, t in spec["things"].items():
        if t["kind"] == "box":
            x, y, w, h = t["rect"]
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="1.5" fill="#eef0f3" stroke="#555" stroke-width="0.4"/>')
            if t["lab"] == "u":
                out.append(f'<text x="{x+w/2}" y="{y+5}" font-size="2.6" font-weight="bold" text-anchor="middle">{t["name"]}</text>')
                for n, (px, py) in t["pts"].items():
                    out.append(f'<text x="{px}" y="{py-2.2}" font-size="2.1" text-anchor="middle">{n}</text>')
            else:
                out.append(f'<text x="{x+w/2}" y="{y+h+3.6}" font-size="2.6" font-weight="bold" text-anchor="middle">{t["name"]}</text>')
                for n, (px, py) in t["pts"].items():
                    dx, anchor = (-2.2, "end") if t["lab"] == "l" else (2.2, "start")
                    out.append(f'<text x="{px+dx}" y="{py+0.8}" font-size="2.3" text-anchor="{anchor}">{n}</text>')
        else:
            cx, cy = t["c"]
            out.append(f'<rect x="{cx-15}" y="{cy-18}" width="30" height="30" rx="2" fill="#dfe6f5" stroke="#44588a" stroke-width="0.4"/>')
            w = len(t["name"]) * 1.36 + 2
            names.append(f'<rect x="{cx-w/2}" y="{cy-16.6}" width="{w}" height="3.6" rx="0.8" fill="#dfe6f5" opacity="0.9"/>')
            names.append(f'<text x="{cx}" y="{cy-13.8}" font-size="2.4" font-weight="bold" text-anchor="middle" fill="#223">{t["name"]}</text>')
    wires = []
    for col, a, b, via in spec["wires"]:
        path = [pts[a]] + list(via) + [pts[b]]
        d = " ".join(f"{x},{y}" for x, y in path)
        wires.append(f'<polyline points="{d}" fill="none" stroke="white" stroke-width="2.0" stroke-linejoin="round" stroke-linecap="round"/>')
        wires.append(f'<polyline points="{d}" fill="none" stroke="{COL[col]}" stroke-width="0.9" stroke-linejoin="round" stroke-linecap="round"/>')
    out += wires
    # terminals on top of the wires
    for key, t in spec["things"].items():
        for n, (px, py) in t["pts"].items():
            if t["kind"] == "sw":
                out.append(f'<rect x="{px-1.6}" y="{py-0.8}" width="3.2" height="1.6" rx="0.4" fill="#c9a227" stroke="#5c4a10" stroke-width="0.25"/>')
                out.append(f'<text x="{px+1.9}" y="{py-1.1}" font-size="1.9" fill="#223">{n}</text>')
            else:
                out.append(f'<circle cx="{px}" cy="{py}" r="1.0" fill="#c9a227" stroke="#5c4a10" stroke-width="0.25"/>')
    out += names
    used = {a for _, a, _, _ in spec["wires"]} | {b for _, _, b, _ in spec["wires"]}
    pads = sorted((xy[1], xy[0], name[4:]) for name, xy in pts.items() if name.startswith("pad."))
    prev = None
    for y, x, ref in pads:
        below = ref in spec["pads_below"]
        high = prev is not None and prev[0] == (y, below) and x - prev[1] < 4.5 and not prev[2]
        prev = ((y, below), x, high)
        ly = y + (3.7 if below else -2.0) + ((2.4 if below else -2.4) if high else 0)
        inside = o["YT"] < ly - 1 and ly < o["YB"]
        out.append(f'<circle cx="{x}" cy="{y}" r="1.05" fill="#f2d21b" stroke="#5c4a10" stroke-width="0.25"/>')
        out.append(f'<text x="{x}" y="{ly}" font-size="1.9" fill="{"white" if inside else "#222"}" text-anchor="middle"'
                   f'{"" if "pad." + ref in used else " opacity=\'0.55\'"}>{labels[ref]}</text>')
    # key and notes
    kx, ky = vx + 3, vy + vh - 7.5 - 3.2 * len(spec["notes"])
    for row, items in enumerate((KEY[:4], KEY[4:])):
        x = kx
        for col, text in items:
            out.append(f'<line x1="{x}" y1="{ky + 3.4 * row - 0.8}" x2="{x+6}" y2="{ky + 3.4 * row - 0.8}" stroke="{COL[col]}" stroke-width="0.9"/>')
            out.append(f'<text x="{x+7}" y="{ky + 3.4 * row}" font-size="2.3">{text}</text>')
            x += 38
    ky += 3.4
    for i, n in enumerate(spec["notes"]):
        out.append(f'<text x="{kx}" y="{ky + 4 + 3.2 * i}" font-size="2.3" fill="#333">{n}</text>')
    out.append(f'<text x="{vx+vw-3}" y="{vy+6}" font-size="2.3" fill="#555" text-anchor="end">Switch lugs: columns A B C, row 2 is the common.</text>')
    out.append("</svg>")
    svg = "\n".join(out)
    dst = os.path.join(ROOT, design, "docs", "wiring.svg")
    open(dst, "w").write(svg)
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg.encode(), write_to=dst[:-4] + ".png", output_width=1800)
    except (ImportError, OSError):
        print("cairosvg or the cairo library not available: wrote the SVG only")
    print("wrote", os.path.relpath(dst, ROOT))


if __name__ == "__main__":
    for d in sys.argv[1:] or DESIGNS:
        draw(d, DESIGNS[d])
