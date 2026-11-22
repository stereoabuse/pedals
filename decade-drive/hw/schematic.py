"""Hand-laid-out schematic, drawn with matplotlib and checked against design.py.

Run:  uv run --with matplotlib python3 hw/schematic.py
Writes docs/schematic.pdf and docs/schematic-N.png.

Every symbol registers its pins and every wire its points, so the drawing's
connectivity is extracted and compared with the netlist. A drawing that does not
match the board netlist fails instead of being written.
"""
import os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from design import parts, NAME, REV

PARTS = {p["ref"]: p for p in parts()}
SYMMETRIC = {"R", "C", "C08"}


def tf(o, lx, ly):
    return {"r": (lx, ly), "d": (-ly, lx), "l": (-lx, -ly), "u": (ly, -lx)}[o]


class Sheet:
    def __init__(self, title):
        self.title = title
        self.lines, self.polys, self.texts, self.circles = [], [], [], []
        self.pins = {}            # (ref, pad) -> (x, y)
        self.wires = []           # list of point lists
        self.labels = []          # (x, y, name)
        self.drawn = defaultdict(set)

    # ---- primitives ----
    def L(self, pts, lw=0.9):
        self.lines.append(([p[0] for p in pts], [p[1] for p in pts], lw))

    def Lo(self, o, x, y, pts, lw=0.9):
        self.L([(x + tf(o, a, b)[0], y + tf(o, a, b)[1]) for a, b in pts], lw)

    def T(self, x, y, s, ha="center", va="center", size=6.5, color="black", weight="normal"):
        self.texts.append((x, y, s, ha, va, size, color, weight))

    def pin(self, ref, pad, x, y):
        assert (ref, pad) not in self.pins, f"{ref}.{pad} drawn twice"
        self.pins[(ref, pad)] = (x, y)
        self.drawn[ref].add(pad)

    def w(self, *pts):
        self.wires.append(list(pts)); self.L(pts)

    def val(self, ref):
        return PARTS[ref]["value"]

    def _label2(self, ref, x, y, o, off=1.4, left=False):
        if o in "ud" and left:
            self.T(x - off, y - 0.7, ref, ha="right"); self.T(x - off, y + 0.8, self.val(ref), ha="right", color="#444")
            return
        if o in "rl":
            self.T(x, y - off, f"{ref}  {self.val(ref)}", va="bottom", size=6)
        else:
            self.T(x + off, y - 0.7, ref, ha="left"); self.T(x + off, y + 0.8, self.val(ref), ha="left", color="#444")

    def _two(self, ref, x, y, o, half, first, second):
        a = tf(o, -half, 0); b = tf(o, half, 0)
        self.pin(ref, first, x + a[0], y + a[1]); self.pin(ref, second, x + b[0], y + b[1])

    # ---- symbols ----
    def R(self, ref, x, y, o="r"):
        self._two(ref, x, y, o, 3, "1", "2")
        self.Lo(o, x, y, [(-3, 0), (-1.6, 0)]); self.Lo(o, x, y, [(1.6, 0), (3, 0)])
        self.Lo(o, x, y, [(-1.6, -0.55), (1.6, -0.55), (1.6, 0.55), (-1.6, 0.55), (-1.6, -0.55)])
        self._label2(ref, x, y, o, 0.9 if o in "rl" else 1.0)

    def C(self, ref, x, y, o="r", left=False):
        polar = PARTS[ref]["kind"] == "CP"
        self._two(ref, x, y, o, 2, "1", "2")
        self.Lo(o, x, y, [(-2, 0), (-0.3, 0)]); self.Lo(o, x, y, [(0.3, 0), (2, 0)])
        self.Lo(o, x, y, [(-0.3, -1), (-0.3, 1)], 1.4); self.Lo(o, x, y, [(0.3, -1), (0.3, 1)], 1.4)
        if polar:
            px, py = tf(o, -1.0, -0.8)
            self.T(x + px, y + py, "+", size=7)
        self._label2(ref, x, y, o, 1.3, left)

    def D(self, ref, x, y, o="r", left=False):
        """Anode first, cathode second, pointing in direction o."""
        self._two(ref, x, y, o, 2, "2", "1")
        self.Lo(o, x, y, [(-2, 0), (-0.8, 0)]); self.Lo(o, x, y, [(0.8, 0), (2, 0)])
        self.Lo(o, x, y, [(-0.8, -0.8), (0.8, 0), (-0.8, 0.8), (-0.8, -0.8)])
        self.Lo(o, x, y, [(0.8, -0.8), (0.8, 0.8)], 1.3)
        if PARTS[ref]["kind"] in ("LED", "LEDT"):
            for k in (0, 0.7):
                self.Lo(o, x, y, [(-0.2 + k, -1.0), (0.5 + k, -1.8)], 0.7)
                self.Lo(o, x, y, [(0.5 + k, -1.8), (0.15 + k, -1.7)], 0.7)
        self._label2(ref, x, y, o, (2.1 if PARTS[ref]["kind"] in ("LED", "LEDT") else 1.2) if o in "rl" else 1.3, left)

    def pot(self, ref, x, y, o, first, wside=1):
        other = "3" if first == "1" else "1"
        a = tf(o, -3, 0); b = tf(o, 3, 0); wp = tf(o, 0, 2 * wside)
        self.pin(ref, first, x + a[0], y + a[1]); self.pin(ref, other, x + b[0], y + b[1]); self.pin(ref, "2", x + wp[0], y + wp[1])
        self.Lo(o, x, y, [(-3, 0), (-1.6, 0)]); self.Lo(o, x, y, [(1.6, 0), (3, 0)])
        self.Lo(o, x, y, [(-1.6, -0.55), (1.6, -0.55), (1.6, 0.55), (-1.6, 0.55), (-1.6, -0.55)])
        self.Lo(o, x, y, [(0, 2 * wside), (0, 0.6 * wside)])
        self.Lo(o, x, y, [(-0.35, 1.15 * wside), (0, 0.6 * wside), (0.35, 1.15 * wside)])
        for pad, (lx, ly) in ((first, (-2.3, -0.9 * wside)), (other, (2.3, -0.9 * wside))):
            px, py = tf(o, lx, ly)
            self.T(x + px, y + py, pad, size=5, color="#06c")
        lx, ly = tf(o, 0, -(1.9 if o in "rl" else 1.3) * wside)
        name = self.val(ref)
        if o in "rl":
            self.T(x, y + ly, f"{ref}  {name}", va="bottom" if ly < 0 else "top", weight="bold" if PARTS[ref]["kind"] == "POT" else "normal")
        else:
            self.T(x + lx, y, f"{ref}\n{name}", ha="right" if lx < 0 else "left", weight="bold" if PARTS[ref]["kind"] == "POT" else "normal")

    def opamp(self, ref, half, x, y, plus_top=False):
        out, m, p = ("1", "2", "3") if half == "A" else ("7", "6", "5")
        ym, yp = (y + 2, y - 2) if plus_top else (y - 2, y + 2)
        self.pin(ref, m, x - 5, ym); self.pin(ref, p, x - 5, yp); self.pin(ref, out, x + 5, y)
        self.L([(x - 3, y - 3.4), (x - 3, y + 3.4), (x + 3, y), (x - 3, y - 3.4)], 1.1)
        self.L([(x - 5, ym), (x - 3, ym)]); self.L([(x - 5, yp), (x - 3, yp)]); self.L([(x + 3, y), (x + 5, y)])
        self.T(x - 2.3, ym, "−", size=8); self.T(x - 2.3, yp, "+", size=7)
        self.T(x - 0.6, y, f"{ref}{half}", size=6, weight="bold")
        self.T(x + 1.0, y - 2.6, self.val(ref), ha="left", color="#444", size=5.5)
        for pad, (px, py) in ((m, (x - 4.2, ym - 0.6)), (p, (x - 4.2, yp - 0.6)), (out, (x + 4.2, y - 0.6))):
            self.T(px, py, pad, size=4.5, color="#06c")

    def pwr(self, ref, x, y):
        self.pin(ref, "8", x, y - 3); self.pin(ref, "4", x, y + 3)
        self.L([(x, y - 3), (x, y - 1.5)]); self.L([(x, y + 3), (x, y + 1.5)])
        self.L([(x - 1.6, y - 1.5), (x + 1.6, y - 1.5), (x + 1.6, y + 1.5), (x - 1.6, y + 1.5), (x - 1.6, y - 1.5)])
        self.T(x, y, ref, weight="bold"); self.T(x + 0.5, y - 2.3, "8", size=4.5, color="#06c", ha="left"); self.T(x + 0.5, y + 2.3, "4", size=4.5, color="#06c", ha="left")

    def nmos(self, ref, x, y, gate_side=-1):
        """N-channel MOSFET, drain up, source down."""
        g = gate_side
        self.pin(ref, "1", x + 3 * g, y); self.pin(ref, "2", x, y + 3); self.pin(ref, "3", x, y - 3)
        gx, cx = x + 1.5 * g, x + 1.0 * g
        self.L([(x + 3 * g, y), (gx, y)]); self.L([(gx, y - 1.2), (gx, y + 1.2)], 1.3)
        for dy in (-1.2, 0, 1.2):
            self.L([(cx, y + dy - 0.45), (cx, y + dy + 0.45)], 1.5)
        self.L([(cx, y - 1.2), (x, y - 1.2), (x, y - 3)]); self.L([(cx, y), (x, y), (x, y + 1.2)]); self.L([(cx, y + 1.2), (x, y + 1.2), (x, y + 3)])
        self.L([(cx - 0.6 * g, y - 0.35), (cx, y), (cx - 0.6 * g, y + 0.35)], 0.8)
        self.T(x + 2.4 * g, y - 0.7, "G", size=4.5, color="#06c")
        for t, yy in (("D", y - 2.4), ("S", y + 2.4)):
            self.T(x - 0.6 * g, yy, t, size=4.5, color="#06c")
        ha = "left" if g < 0 else "right"
        self.T(x - 1.6 * g, y - 0.6, ref, ha=ha); self.T(x - 1.6 * g, y + 0.9, self.val(ref), ha=ha, color="#444")

    def sw(self, ref, x, y, o, notes):
        """Toggle with the common (2) on one side, lug 1 (lever up) and lug 3 (lever down) on the other."""
        c = tf(o, -3, 0); a = tf(o, 3, -2); b = tf(o, 3, 2)
        self.pin(ref, "2", x + c[0], y + c[1]); self.pin(ref, "1", x + a[0], y + a[1]); self.pin(ref, "3", x + b[0], y + b[1])
        self.Lo(o, x, y, [(-3, 0), (-1.2, 0)]); self.Lo(o, x, y, [(3, -2), (1.4, -2)]); self.Lo(o, x, y, [(3, 2), (1.4, 2)])
        self.Lo(o, x, y, [(-1.2, 0), (1.2, 0)], 1.3)
        for lx, ly in ((-1.2, 0), (1.4, -2), (1.4, 2)):
            px, py = tf(o, lx, ly); self.circles.append((x + px, y + py, 0.28, False))
        for t, (lx, ly) in (("1 up", (2.4, -2.7)), ("3 dn", (2.4, 2.7)), ("2", (-2.4, -0.7))):
            px, py = tf(o, lx, ly)
            ha = "center" if o in "rl" or t == "2" else "left" if px > 0 else "right"
            self.T(x + px - {"left": 0.3, "right": -0.3}.get(ha, 0), y + py, t, size=4.5, color="#06c", ha=ha)
        self.T(x + notes[0], y + notes[1], f"{ref}  {self.val(ref)}\n{notes[2]}", ha=notes[3], va="center", weight="bold", size=6)

    def tog(self, ref, x, y, o, notes, cside=1):
        """Toggle drawn as a T: lug 1 (lever up) and lug 3 (lever down) in line, common (2) on the side."""
        for pad, (lx, ly) in (("1", (-3, 0)), ("3", (3, 0)), ("2", (0, 2 * cside))):
            px, py = tf(o, lx, ly); self.pin(ref, pad, x + px, y + py)
        self.Lo(o, x, y, [(-3, 0), (-1.4, 0)]); self.Lo(o, x, y, [(3, 0), (1.4, 0)]); self.Lo(o, x, y, [(0, 2 * cside), (0, 1.1 * cside)])
        self.Lo(o, x, y, [(0, 1.1 * cside), (0, -0.9 * cside)], 1.3)
        for lx, ly in ((-1.4, 0), (1.4, 0), (0, 1.1 * cside)):
            px, py = tf(o, lx, ly); self.circles.append((x + px, y + py, 0.28, False))
        for t, (lx, ly) in (("1 up", (-2.3, -0.8 * cside)), ("3 dn", (2.3, -0.8 * cside)), ("2", (0.7, 1.7 * cside))):
            px, py = tf(o, lx, ly); self.T(x + px, y + py, t, size=4.5, color="#06c")
        self.T(x + notes[0], y + notes[1], f"{ref}  {self.val(ref)}\n{notes[2]}", ha=notes[3], va="center", weight="bold", size=6)

    def pad(self, ref, x, y, side="l", text=None):
        self.pin(ref, "1", x, y)
        dx = {"l": -1, "r": 1, "u": 0, "d": 0}[side]; dy = {"l": 0, "r": 0, "u": -1, "d": 1}[side]
        self.circles.append((x + dx * 0.6, y + dy * 0.6, 0.6, False))
        kind = "pad" if PARTS[ref]["kind"] == "PAD" else "test point"
        s = text or f"{self.val(ref)} {kind}"
        self.T(x + dx * 1.6, y + dy * 1.8, s, ha={"l": "right", "r": "left"}.get(side, "center"), weight="bold", size=6)

    def gnd(self, x, y):
        self.labels.append((x, y, "GND"))
        self.L([(x, y), (x, y + 0.8)])
        for k, hw in enumerate((1.0, 0.65, 0.3)):
            self.L([(x - hw, y + 0.8 + 0.35 * k), (x + hw, y + 0.8 + 0.35 * k)], 1.1)

    def flag(self, x, y, name, d="u"):
        self.labels.append((x, y, name))
        s = -1 if d == "u" else 1
        self.L([(x, y), (x, y + s * 0.9)]); self.L([(x - 0.8, y + s * 0.9), (x + 0.8, y + s * 0.9)], 1.4)
        self.T(x, y + s * 1.2, name, va="bottom" if d == "u" else "top", color="#b00", weight="bold", size=6)

    def label(self, x, y, name, side="r", note=""):
        self.labels.append((x, y, name))
        dx = 1 if side == "r" else -1
        self.L([(x, y), (x + dx * 0.7, y - 0.5), (x + dx * 0.7, y + 0.5), (x, y)])
        self.T(x + dx * 1.0, y, name + (f"  ({note})" if note else ""), ha="left" if side == "r" else "right", color="#070", weight="bold", size=6.5)

    def note(self, x, y, s):
        self.T(x, y, s, ha="left", va="top", size=6, color="#555")

    # ---- connectivity ----
    def groups(self):
        parent = {}
        def find(a):
            parent.setdefault(a, a)
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a
        def union(a, b):
            parent[find(a)] = find(b)
        pts = set(self.pins.values()) | {(x, y) for x, y, _ in self.labels}
        for wr in self.wires:
            pts |= set(wr)
        segs = [(a, b) for wr in self.wires for a, b in zip(wr, wr[1:])]
        degree = defaultdict(int)
        for a, b in segs:
            union(a, b); degree[a] += 1; degree[b] += 1
            for p in pts:
                if p in (a, b):
                    continue
                if (a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1])) or \
                   (a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0])):
                    union(a, p); degree[p] += 2
        for p in self.pins.values():
            find(p); degree[p] += 1
        self.dots = [p for p, d in degree.items() if d >= 3]
        g = defaultdict(lambda: dict(pins=[], labels=set()))
        for key, p in self.pins.items():
            g[find(p)]["pins"].append(key)
        for x, y, name in self.labels:
            g[find((x, y))]["labels"].add(name)
        return list(g.values())


def check(sheets):
    errs = []
    drawn = defaultdict(set)
    for s in sheets:
        for ref, pads in s.drawn.items():
            if drawn[ref] & pads:
                errs.append(f"{ref} pads {drawn[ref] & pads} drawn on two sheets")
            drawn[ref] |= pads
    for ref, p in PARTS.items():
        if set(p["pins"]) != drawn.get(ref, set()):
            errs.append(f"{ref}: drawn pads {sorted(drawn.get(ref, set()))} != {sorted(p['pins'])}")
    netname = {}                          # (ref, pad) -> resolved drawn net name
    owners = defaultdict(list)
    for si, s in enumerate(sheets):
        for gi, g in enumerate(s.groups()):
            if len(g["labels"]) > 1:
                errs.append(f"sheet {si + 1}: labels {sorted(g['labels'])} shorted together"); continue
            name = next(iter(g["labels"]), None)
            if name is None:
                exact = {PARTS[r]["pins"][pad] for r, pad in g["pins"] if PARTS[r]["kind"] not in SYMMETRIC}
                cands = [set(PARTS[r]["nets"]) for r, pad in g["pins"] if PARTS[r]["kind"] in SYMMETRIC]
                if len(exact) == 1:
                    name = next(iter(exact))
                elif not exact and cands:
                    common = set.intersection(*cands)
                    name = next(iter(common)) if len(common) == 1 else None
                if name is None:
                    errs.append(f"sheet {si + 1}: cannot name net with pins {sorted(g['pins'])} (exact={exact})"); continue
                owners[name].append((si, gi, "unlabelled"))
            else:
                owners[name].append((si, gi, "label"))
            for key in g["pins"]:
                netname[key] = name
    for name, lst in owners.items():
        if len(lst) > 1 and any(k == "unlabelled" for _, _, k in lst):
            errs.append(f"net {name} is drawn in {len(lst)} unconnected pieces without labels joining them")
    for ref, p in PARTS.items():
        got = {pad: netname.get((ref, pad)) for pad in p["pins"]}
        if p["kind"] in SYMMETRIC:
            if sorted(str(v) for v in got.values()) != sorted(p["nets"]):
                errs.append(f"{ref}: drawn between {sorted(str(v) for v in got.values())}, netlist says {sorted(p['nets'])}")
        else:
            for pad, n in p["pins"].items():
                if n.startswith("NC"):
                    continue
                if got[pad] != n:
                    errs.append(f"{ref}.{pad}: drawn on {got[pad]}, netlist says {n}")
    return errs


# ------------------------------------------------------------------ sheets
def sheet_input():
    s = Sheet("1  Power, input buffer, gain, octave rectifier, summer")
    # power
    s.pad("J_9V", 6, 10, "l"); s.w((6, 10), (9, 10)); s.D("D1", 11, 10, "r"); s.w((13, 10), (24, 10)); s.flag(19.5, 10, "V9R")
    s.R("R1", 27, 10, "r"); s.w((30, 10), (54, 10)); s.flag(34, 10, "VCC")
    for ref, x in (("C1", 40), ("C2", 47)):
        s.w((x, 10), (x, 12)); s.C(ref, x, 14, "d"); s.gnd(x, 16)
    s.pad("TP1", 54, 10, "r")
    for i, r in enumerate(("J_G1", "J_G2", "J_G3", "J_G4")):
        x = 6 + 7 * i
        s.pad(r, x, 22, "u", "G pad"); s.w((x, 22), (x, 24)); s.gnd(x, 24)
    s.flag(84, 6, "VCC"); s.w((84, 6), (84, 7)); s.R("R2", 84, 10, "d"); s.w((84, 13), (84, 15)); s.R("R3", 84, 18, "d"); s.gnd(84, 21)
    s.w((84, 14), (94, 14)); s.w((90, 14), (90, 15)); s.C("C3", 90, 17, "d"); s.gnd(90, 19)
    s.R("R4", 97, 14, "r"); s.w((100, 14), (102, 14)); s.opamp("U1", "B", 107, 16, plus_top=True)
    s.w((102, 18), (100, 18), (100, 22), (114, 22), (114, 16), (112, 16)); s.w((114, 16), (122, 16)); s.flag(118, 16, "VREF"); s.pad("TP2", 122, 16, "r")
    s.flag(148, 8, "VCC"); s.w((148, 8), (202, 8))
    for i, (u, c) in enumerate((("U1", "C4"), ("U2", "C5"), ("U4", "C7"), ("U5", "C8"), ("U6", "C9"))):
        x = 150 + 12 * i
        s.w((x, 8), (x, 13)); s.pwr(u, x, 16); s.gnd(x, 19)
        s.w((x + 4, 8), (x + 4, 12)); s.C(c, x + 4, 14, "d"); s.gnd(x + 4, 16)
    s.flag(210, 8, "VS"); s.w((210, 8), (216, 8)); s.w((212, 8), (212, 13)); s.pwr("U3", 212, 16); s.gnd(212, 19)
    s.w((216, 8), (216, 12)); s.C("C6", 216, 14, "d"); s.gnd(216, 16)
    s.note(40, 30, "Power: D1 guards against a reversed supply. U1B buffers VB (half of VCC) as VREF, the bias for every stage.\n"
                   "U3 (octave rectifier here, drive stage on sheet 2) runs from VS, the sag supply on sheet 4; the other op-amps run from VCC.\n"
                   "Gain: U2A inverts, gain = -(R9 and what is across it) / (R8 and what is across it), unity with all three toggles centred.\n"
                   "Up puts a resistor from IBC across R8, down puts one across R9; 1k, 2.7k and 8.2k weigh the three toggles about 9 : 3 : 1.\n"
                   "Octave: U3B is a half-wave rectifier, HO = -max(PO, 0). Up sums it into U2B at twice the weight of PO, so S = |PO| instead of -PO;\n"
                   "down sends HO to the output mixer on sheet 4 instead.\n"
                   "Summer: SP rests at VREF through R23 and takes the degenerative feedback (SIGN down, sheet 3) through R24.\n"
                   "Toggles are all on-off-on: lug 1 joins the common (2) with the lever up, lug 3 with the lever down, centre is open.")
    # input buffer
    s.pad("J_IN", 6, 66, "l"); s.w((6, 66), (14, 66)); s.w((10, 66), (10, 67)); s.R("R5", 10, 70, "d"); s.gnd(10, 73)
    s.C("C10", 16, 66, "r"); s.w((18, 66), (29, 66)); s.w((24, 66), (24, 65)); s.R("R6", 24, 62, "d"); s.flag(24, 59, "VREF")
    s.R("R7", 32, 66, "r"); s.w((35, 66), (43, 66)); s.w((38, 66), (38, 68)); s.C("C11", 38, 70, "d", left=True); s.gnd(38, 72)
    s.opamp("U1", "A", 48, 68, plus_top=True)
    s.w((43, 70), (41, 70), (41, 76), (55, 76), (55, 68), (53, 68)); s.w((55, 68), (60, 68)); s.C("C12", 62, 68, "r")
    # gain stage
    s.w((64, 68), (76, 68)); s.R("R8", 79, 68, "r"); s.w((82, 68), (91, 68), (102, 68)); s.opamp("U2", "A", 107, 70)
    s.w((102, 72), (100, 72), (100, 74)); s.flag(100, 74, "VREF", "d")
    s.w((91, 72), (91, 54), (101, 54)); s.label(91, 72, "PN", "l"); s.R("R9", 104, 54, "r"); s.w((107, 54), (119, 54))
    s.w((91, 61), (102, 61)); s.C("C13", 104, 61, "r"); s.w((106, 61), (119, 61))
    s.w((112, 70), (119, 70)); s.w((119, 54), (119, 106)); s.w((69, 68), (69, 106))
    for ref, ru, rd, y in (("SW1", "R10", "R11", 82), ("SW2", "R12", "R13", 94), ("SW3", "R14", "R15", 106)):
        s.w((69, y), (76, y)); s.R(ru, 79, y, "r"); s.w((82, y), (91, y))
        s.tog(ref, 94, y, "r", (-23, 5, "up: more gain\ndown: less gain", "left"))
        s.w((97, y), (104, y)); s.R(rd, 107, y, "r"); s.w((110, y), (119, y))
        s.w((94, y + 2), (94, y + 4), (96, y + 4)); s.label(96, y + 4, "PN", "r")
    # octave rectifier
    s.w((119, 70), (163, 70)); s.w((135, 70), (135, 65), (137, 65)); s.label(137, 65, "PO", "r", "sheet 4")
    s.w((127, 70), (127, 98), (131, 98)); s.R("R16", 134, 98, "r"); s.w((137, 98), (149, 98)); s.opamp("U3", "B", 154, 100)
    s.w((149, 102), (147, 102), (147, 104)); s.flag(147, 104, "VREF", "d")
    s.w((142, 98), (142, 84), (151, 84)); s.R("R17", 154, 84, "r"); s.w((157, 84), (179, 84), (179, 100))
    s.w((142, 91), (150, 91)); s.D("D2", 152, 91, "l"); s.w((154, 91), (162, 91), (162, 100))
    s.w((159, 100), (168, 100)); s.D("D3", 170, 100, "l"); s.w((172, 100), (183, 100))
    s.sw("SW18", 186, 100, "r", (0, 9, "up: into the drive\ndown: into the mix", "center"))
    s.w((189, 98), (197, 98), (197, 91)); s.w((193, 89), (193, 91), (201, 91), (201, 89)); s.R("R18", 193, 86, "d"); s.R("R19", 201, 86, "d")
    s.w((193, 83), (193, 81), (201, 81), (201, 83)); s.w((197, 81), (197, 70))
    s.w((189, 102), (193, 102)); s.label(193, 102, "OCM", "r", "to the mixer, sheet 4")
    # summer
    s.R("R21", 166, 70, "r"); s.w((169, 70), (213, 70)); s.opamp("U2", "B", 218, 72)
    s.w((208, 70), (208, 54), (211, 54)); s.R("R22", 214, 54, "r"); s.w((217, 54), (227, 54))
    s.w((208, 61), (212, 61)); s.C("C14", 214, 61, "r"); s.w((216, 61), (227, 61))
    s.w((223, 72), (227, 72)); s.w((227, 54), (227, 72)); s.w((227, 72), (232, 72)); s.label(232, 72, "S", "r", "sheets 2, 4")
    s.w((213, 74), (211, 74), (211, 82)); s.R("R23", 211, 85, "d"); s.flag(211, 88, "VREF", "d")
    s.w((211, 80), (216, 80)); s.R("R24", 219, 80, "r"); s.w((222, 80), (225, 80)); s.label(225, 80, "FN", "r", "sheet 3")
    return s


def sheet_drive():
    s = Sheet("2  Drive: bass, drive stage, treble, hard clip")
    s.note(0, 12, "Bass: C15 with R25 is the high-pass into the drive stage, 720 Hz at home.\n"
                  "Up adds capacitance beside C15 (lower corner), down adds a resistor beside R25 (higher corner).\n"
                  "Drive: U3A is non-inverting, gain 1 + R30 / (R31 || R55) above the C20 corner;\n"
                  "R55 reaches VREF through Q1 on sheet 3. U3 runs from the sag supply VS.\n"
                  "LED2/LED3 always clip the loop. DIODE + and DIODE - each put a lower-threshold diode\n"
                  "across them for one half of the wave.\n"
                  "CNF also takes the regenerative feedback and the burst from sheet 3.\n"
                  "Treble: R33 with C22 is a low-pass, 3.4 kHz at home. Up puts a resistor across R33,\n"
                  "down adds capacitance to ground.\n"
                  "The 10M resistors hold the switched-out capacitors at VREF so the toggles do not pop.\n"
                  "Clip: SW10 puts an anti-parallel diode pair from T to VREF. U4A buffers T as TB.")
    # bass
    s.label(6, 84, "S", "l", "sheet 1"); s.w((6, 84), (20, 84)); s.w((12, 74), (12, 84), (12, 94)); s.C("C15", 22, 84, "r"); s.w((24, 84), (96, 84))
    s.w((12, 74), (15, 74)); s.w((15, 74), (15, 70), (20, 70)); s.w((15, 74), (15, 78), (20, 78)); s.C("C16", 22, 70, "r"); s.C("C17", 22, 78, "r")
    s.w((24, 70), (29, 70), (29, 74)); s.w((24, 78), (29, 78), (29, 74)); s.w((29, 74), (37, 74))
    s.w((33, 74), (33, 71)); s.R("R26", 33, 68, "d"); s.flag(33, 65, "VREF")
    s.tog("SW6", 40, 74, "r", (0, -7, "up: more bass\ndown: less bass", "left")); s.w((40, 76), (40, 84))
    s.w((43, 74), (47, 74)); s.R("R27", 50, 74, "r"); s.w((53, 74), (56, 74), (56, 76)); s.flag(56, 76, "VREF", "d")
    s.w((12, 94), (20, 94)); s.C("C18", 22, 94, "r"); s.w((24, 94), (41, 94)); s.w((33, 94), (33, 97)); s.R("R28", 33, 100, "d"); s.flag(33, 103, "VREF", "d")
    s.tog("SW7", 44, 94, "r", (-4, 7, "up: more bass\ndown: less bass", "left"), cside=-1); s.w((44, 92), (44, 84))
    s.w((47, 94), (51, 94)); s.R("R29", 54, 94, "r"); s.w((57, 94), (60, 94), (60, 96)); s.flag(60, 96, "VREF", "d")
    s.w((68, 84), (68, 85)); s.R("R25", 68, 88, "d"); s.flag(68, 91, "VREF", "d")
    # drive stage
    s.opamp("U3", "A", 101, 82)
    s.C("C20", 86, 80, "r"); s.w((88, 80), (96, 80)); s.w((84, 80), (76, 80)); s.label(76, 80, "CNF", "l", "sheet 3")
    s.w((80, 80), (80, 78)); s.R("R31", 80, 75, "d"); s.flag(80, 72, "VREF")
    s.w((92, 80), (92, 22)); s.w((106, 82), (136, 82)); s.w((128, 82), (128, 18))
    s.w((92, 72), (107, 72)); s.R("R30", 110, 72, "r"); s.w((113, 72), (128, 72))
    s.w((92, 65), (108, 65)); s.C("C19", 110, 65, "r"); s.w((112, 65), (128, 65))
    s.w((92, 58), (108, 58)); s.D("LED2", 110, 58, "l"); s.w((112, 58), (128, 58))
    s.w((92, 50), (108, 50)); s.D("LED3", 110, 50, "r"); s.w((112, 50), (128, 50))
    for ref, y, da, db, o in (("SW4", 38, "D4", "D5", "l"), ("SW5", 22, "D6", "D7", "r")):
        s.w((92, y), (97, y)); s.sw(ref, 100, y, "r", (-10, 0, "up: silicon\ncentre: red LED\ndown: Schottky", "right"))
        s.w((103, y - 2), (105, y - 2), (105, y - 4), (112, y - 4)); s.D(da, 114, y - 4, o); s.w((116, y - 4), (128, y - 4))
        s.w((103, y + 2), (105, y + 2), (105, y + 4), (112, y + 4)); s.D(db, 114, y + 4, o); s.w((116, y + 4), (128, y + 4))
    s.C("C21", 138, 82, "r"); s.w((140, 82), (152, 82)); s.w((145, 82), (145, 83)); s.R("R32", 145, 86, "d"); s.flag(145, 89, "VREF", "d")
    s.label(152, 82, "CA", "r", "below; sheet 3")
    # treble
    s.label(6, 140, "CA", "l", "from C21"); s.w((6, 140), (17, 140)); s.w((12, 124), (12, 140), (12, 154)); s.R("R33", 20, 140, "r"); s.w((23, 140), (126, 140))
    s.w((27, 140), (27, 142)); s.C("C22", 27, 144, "d"); s.gnd(27, 146)
    s.w((12, 124), (17, 124)); s.R("R34", 20, 124, "r"); s.w((23, 124), (29, 124))
    s.tog("SW8", 32, 124, "r", (-6, -7, "up: brighter\ndown: darker", "left")); s.w((32, 126), (32, 140))
    s.w((35, 124), (57, 124)); s.w((57, 124), (57, 122)); s.R("R35", 57, 119, "d"); s.flag(57, 116, "VREF")
    for ref, x in (("C23", 41), ("C24", 49)):
        s.w((x, 124), (x, 126)); s.C(ref, x, 128, "d"); s.gnd(x, 130)
    s.w((12, 154), (17, 154)); s.R("R36", 20, 154, "r"); s.w((23, 154), (33, 154))
    s.tog("SW9", 36, 154, "r", (-14, 7, "up: brighter\ndown: darker", "left"), cside=-1); s.w((36, 152), (36, 140))
    s.w((39, 154), (53, 154)); s.w((45, 154), (45, 156)); s.C("C25", 45, 158, "d"); s.gnd(45, 160)
    s.w((53, 154), (53, 156)); s.R("R37", 53, 159, "d"); s.flag(53, 162, "VREF", "d")
    # hard clip
    s.w((88, 140), (88, 144)); s.sw("SW10", 88, 147, "d", (0, -13, "up: silicon pair\ndown: Schottky pair", "center"))
    for x, lug, da, db in ((74, 86, "D10", "D11"), (102, 90, "D8", "D9")):
        s.w((lug, 150), (lug, 152), (x, 152), (x, 154)); s.w((x - 6, 156), (x - 6, 154), (x + 6, 154), (x + 6, 156))
        s.D(da, x - 6, 158, "d"); s.D(db, x + 6, 158, "u")
        s.w((x - 6, 160), (x - 6, 162), (x + 6, 162), (x + 6, 160)); s.flag(x, 162, "VREF", "d")
    s.opamp("U4", "A", 131, 142, plus_top=True)
    s.w((126, 144), (124, 144), (124, 148), (138, 148), (138, 142), (136, 142)); s.w((138, 142), (144, 142)); s.label(144, 142, "TB", "r", "sheet 4")
    return s


def sheet_resonator():
    s = Sheet("3  Resonator, feedback amount and sign, burst")
    # first integrator (band-pass output V1)
    s.label(6, 60, "CA", "l", "sheet 2"); s.w((6, 60), (11, 60)); s.R("R38", 14, 60, "r"); s.w((17, 60), (40, 60)); s.opamp("U5", "A", 45, 62)
    s.w((40, 64), (38, 64), (38, 66)); s.flag(38, 66, "VREF", "d")
    s.tog("SW14", 30, 30, "r", (4, -10, "up: octave up\ndown: octave down", "right")); s.w((30, 32), (30, 60))
    s.R("R41", 20, 30, "r"); s.w((23, 30), (27, 30)); s.R("R40", 20, 38, "r"); s.w((23, 38), (30, 38))
    s.w((17, 30), (12, 30), (12, 38), (17, 38)); s.label(12, 34, "V3", "l", "from U6A")
    s.w((30, 45), (43, 45)); s.R("R39", 46, 45, "r"); s.w((49, 45), (68, 45))
    s.w((30, 52), (44, 52)); s.C("C26", 46, 52, "r"); s.w((48, 52), (68, 52))
    s.w((50, 62), (68, 62)); s.w((68, 62), (68, 30)); s.w((58, 62), (58, 67)); s.pad("TP3", 58, 67, "d")
    s.w((68, 38), (72, 38)); s.label(72, 38, "V1", "r", "used below")
    # second integrator
    s.w((68, 62), (75, 62)); s.R("R43", 78, 62, "r"); s.w((81, 62), (104, 62)); s.opamp("U5", "B", 109, 64)
    s.w((104, 66), (102, 66), (102, 68)); s.flag(102, 68, "VREF", "d")
    s.tog("SW15", 94, 30, "r", (4, -10, "up: three semitones up (F)\ndown: five down (A)", "right")); s.w((94, 32), (94, 62))
    s.w((68, 30), (81, 30)); s.R("R44", 84, 30, "r"); s.w((87, 30), (91, 30))
    s.w((94, 52), (108, 52)); s.C("C30", 110, 52, "r"); s.w((112, 52), (132, 52))
    s.w((114, 64), (132, 64)); s.w((132, 64), (132, 30))
    for x, r, (ca, cb, cc), xb in ((30, "R42", ("C27", "C28", "C29"), 68), (94, "R45", ("C31", "C32", "C33"), 132)):
        s.w((x + 3, 30), (x + 20, 30)); s.w((x + 8, 30), (x + 8, 27)); s.R(r, x + 8, 24, "d"); s.flag(x + 8, 21, "VREF")
        s.w((x + 14, 30), (x + 14, 16), (x + 20, 16)); s.w((x + 14, 23), (x + 20, 23))
        for c, y in ((ca, 16), (cb, 23), (cc, 30)):
            s.C(c, x + 22, y, "r")
        s.w((x + 24, 16), (x + 30, 16), (x + 30, 30)); s.w((x + 24, 23), (x + 30, 23)); s.w((x + 24, 30), (xb, 30))
    # inverter with the TUNE trimmer
    s.w((132, 64), (139, 64)); s.R("R46", 142, 64, "r"); s.w((145, 64), (160, 64)); s.opamp("U6", "A", 165, 66)
    s.w((160, 68), (158, 68), (158, 70)); s.flag(158, 70, "VREF", "d")
    s.w((152, 64), (152, 52), (155, 52)); s.R("R47", 158, 52, "r"); s.w((161, 52), (166, 52)); s.pot("RV3", 169, 52, "r", "1", -1)
    s.T(169, 57.4, "TUNE trimmer", size=6); s.w((172, 52), (178, 52)); s.w((169, 50), (169, 48), (175, 48), (175, 52))
    s.w((170, 66), (178, 66)); s.w((178, 66), (178, 52)); s.w((178, 66), (184, 66)); s.label(184, 66, "V3", "r", "to R40, R41")
    s.note(0, 76, "Resonator: a Tow-Thomas band-pass (two integrators and an inverter in a loop) fed from the drive stage through R38; V1 is the band-pass output.\n"
                  "Home pitch is D5, 587 Hz, set with RV3. PITCH 3 moves the first integrator an octave: up puts R41 across R40, down puts C27..C29 across C26.\n"
                  "PITCH 1 moves the second: up puts R44 across R43, down puts C31..C33 across C30. The 10M resistors hold the switched-out capacitors at VREF.\n"
                  "Feedback: R48/R49 divide V1 down to FA; AMOUNT up puts a resistor across R48 (more), down puts one across R49 (less).\n"
                  "SIGN up sends FA through RV2 (THRESH) and R54 into CNF, the drive stage's gain leg; down sends it through R24 to the summer on sheet 1.\n"
                  "Burst: R57 holds Q1 on, shorting BX to VREF. BURST up ties the gate to VREF, so V1 drives CNF through R56 and R55; down shorts MK, the mixer output, to VREF.")
    # feedback amount and sign
    s.label(6, 120, "V1", "l"); s.w((6, 120), (19, 120)); s.w((12, 108), (12, 120), (12, 132)); s.R("R48", 22, 120, "r"); s.w((25, 120), (70, 120))
    s.w((12, 108), (19, 108)); s.R("R50", 22, 108, "r"); s.w((25, 108), (31, 108))
    s.tog("SW12", 34, 108, "r", (-7, -7, "up: more feedback\ndown: less feedback", "left")); s.w((34, 110), (34, 120))
    s.w((37, 108), (41, 108)); s.R("R51", 44, 108, "r"); s.w((47, 108), (50, 108), (50, 110)); s.flag(50, 110, "VREF", "d")
    s.w((12, 132), (19, 132)); s.R("R52", 22, 132, "r"); s.w((25, 132), (35, 132))
    s.tog("SW13", 38, 132, "r", (-11, 7, "up: more feedback\ndown: less feedback", "left"), cside=-1); s.w((38, 130), (38, 120))
    s.w((41, 132), (45, 132)); s.R("R53", 48, 132, "r"); s.w((51, 132), (54, 132), (54, 134)); s.flag(54, 134, "VREF", "d")
    s.w((60, 120), (60, 121)); s.R("R49", 60, 124, "d"); s.flag(60, 127, "VREF", "d")
    s.sw("SW11", 73, 120, "r", (-7, 14, "up: regenerative (resonance, then oscillation)\ndown: degenerative (scoop)", "left"))
    s.w((76, 118), (78, 118), (78, 114), (82, 114)); s.pot("RV2", 85, 114, "r", "1", -1); s.T(85, 119.4, "THRESH trimmer", size=6)
    s.w((88, 114), (94, 114)); s.w((85, 112), (85, 110), (91, 110), (91, 114)); s.R("R54", 97, 114, "r")
    s.w((100, 114), (104, 114)); s.label(104, 114, "CNF", "r", "sheet 2")
    s.w((76, 122), (78, 122), (78, 126), (84, 126)); s.label(84, 126, "FN", "r", "to R24, sheet 1")
    # burst
    s.sw("SW20", 138, 119, "r", (0, -9, "momentary\nup: drone burst\ndown: kill", "center"))
    s.w((135, 119), (133, 119), (133, 121)); s.flag(133, 121, "VREF", "d")
    s.w((141, 117), (184, 117)); s.w((150, 117), (150, 115)); s.R("R57", 150, 112, "d"); s.flag(150, 109, "VCC")
    s.w((160, 117), (160, 119)); s.C("C34", 160, 121, "d"); s.flag(160, 123, "VREF", "d")
    s.nmos("Q1", 187, 117); s.flag(187, 120, "VREF", "d")
    s.label(170, 108, "V1", "l"); s.w((170, 108), (174, 108)); s.R("R56", 177, 108, "r"); s.w((180, 108), (194, 108)); s.w((187, 108), (187, 114))
    s.R("R55", 197, 108, "r"); s.w((200, 108), (204, 108)); s.label(204, 108, "CNF", "r", "sheet 2")
    s.w((141, 121), (144, 121), (144, 130), (148, 130)); s.label(148, 130, "MK", "r", "mixer output, sheet 4")
    return s


def sheet_output():
    s = Sheet("4  Gate, output mixer, Level, sag supply, indicator LED")
    # mixer inputs: octave, blend, drive
    s.label(57, 30, "OCM", "l", "sheet 1"); s.w((57, 30), (72, 30)); s.R("R20", 75, 30, "r"); s.w((78, 30), (92, 30))
    s.sw("SW19", 64, 46, "l", (-2, -10, "up: clean, in phase\ndown: clean, out of phase", "left"))
    s.w((61, 44), (59, 44), (59, 42), (57, 42)); s.label(57, 42, "PO", "l", "sheet 1")
    s.w((61, 48), (59, 48), (59, 50), (57, 50)); s.label(57, 50, "S", "l", "sheet 1")
    s.w((67, 46), (72, 46)); s.R("R64", 75, 46, "r"); s.w((78, 46), (92, 46))
    s.label(6, 60, "TB", "l", "sheet 2"); s.w((6, 60), (40, 60)); s.R("R62", 43, 60, "r"); s.w((46, 60), (100, 60)); s.w((92, 30), (92, 60), (92, 92))
    # gate
    s.w((12, 60), (12, 88), (16, 88)); s.R("R58", 19, 88, "r"); s.w((22, 88), (34, 88)); s.opamp("U4", "B", 39, 86, plus_top=True)
    s.w((34, 84), (32, 84), (32, 82)); s.flag(32, 82, "VREF")
    s.w((27, 88), (27, 109), (35, 109)); s.w((27, 95), (34, 95)); s.R("R59", 37, 95, "r"); s.w((40, 95), (50, 95))
    s.w((27, 102), (35, 102)); s.D("D12", 37, 102, "r"); s.w((39, 102), (50, 102)); s.D("D13", 37, 109, "l"); s.w((39, 109), (50, 109))
    s.w((44, 86), (56, 86)); s.w((50, 86), (50, 109)); s.sw("SW17", 59, 86, "r", (-5, 13, "up: gate\ndown: soft gate", "left"))
    s.w((62, 84), (64, 84), (64, 80), (70, 80)); s.R("R60", 73, 80, "r"); s.w((76, 80), (92, 80))
    s.w((62, 88), (64, 88), (64, 92), (70, 92)); s.R("R61", 73, 92, "r"); s.w((76, 92), (92, 92))
    # mixer, Level, output
    s.opamp("U6", "B", 105, 62); s.w((100, 64), (98, 64), (98, 66)); s.flag(98, 66, "VREF", "d")
    s.w((96, 60), (96, 45), (103, 45)); s.C("C35", 105, 45, "r"); s.w((107, 45), (116, 45))
    s.w((96, 52), (102, 52)); s.R("R63", 105, 52, "r"); s.w((108, 52), (116, 52)); s.w((116, 45), (116, 62))
    s.w((110, 62), (121, 62)); s.R("R65", 124, 62, "r"); s.w((127, 62), (134, 62)); s.C("C36", 136, 62, "r")
    s.w((130, 62), (130, 56), (132, 56)); s.label(132, 56, "MK", "r", "BURST kill, sheet 3")
    s.w((138, 62), (148, 62), (148, 64)); s.pot("RV1", 148, 67, "d", "3", -1); s.gnd(148, 70)
    s.w((150, 67), (156, 67)); s.R("R66", 159, 67, "r"); s.w((162, 67), (168, 67)); s.pad("J_OUT", 168, 67, "r")
    s.note(100, 78, "Gate: U4B is an inverting copy of TB (gain -R59 / R58) that D12/D13 limit to a diode drop.\n"
                    "Summed into the mixer through R60 (R60 / R59 = R62 / R58) it cancels TB exactly until the diodes conduct;\n"
                    "through R61 it cancels about half.\n"
                    "Mixer: U6B sums the driven signal TB, the gate copy, the clean blend (S is in phase with TB at the mixer,\n"
                    "PO out of phase) and, with OCTAVE down, the rectified HO from sheet 1.\n"
                    "MK is the node BURST down shorts to VREF to kill the output.")
    # sag
    s.flag(8, 130, "V9R"); s.w((8, 130), (13, 130)); s.w((13, 130), (13, 126), (17, 126)); s.w((13, 130), (13, 134), (17, 134))
    s.R("R67", 20, 126, "r"); s.R("R68", 20, 134, "r"); s.w((23, 126), (27, 126), (27, 130)); s.w((23, 134), (27, 134), (27, 130))
    s.w((27, 130), (58, 130)); s.flag(34, 130, "VS"); s.w((42, 130), (42, 132)); s.C("C37", 42, 134, "d"); s.gnd(42, 136)
    s.w((58, 130), (58, 132)); s.sw("SW16", 58, 135, "d", (8, -1, "up: U3 supply about 6.3 V\ndown: about 5.6 V", "left"))
    s.w((60, 138), (60, 142), (82, 142)); s.w((56, 138), (56, 142), (34, 142))
    for ref, x in (("R72", 34), ("R73", 41), ("R74", 48), ("R69", 68), ("R70", 75), ("R71", 82)):
        s.w((x, 142), (x, 143)); s.R(ref, x, 146, "d"); s.gnd(x, 149)
    s.note(8, 154, "Sag: VS feeds only U3 (drive stage and octave rectifier). R67 || R68 from V9R (the 9 V input after D1) with the toggle's\n"
                   "resistors to ground make a divider; centred, VS is V9R through R67 || R68.")
    # indicator LED
    s.flag(110, 130, "VCC"); s.w((110, 130), (114, 130)); s.R("R75", 117, 130, "r"); s.w((120, 130), (124, 130)); s.D("LED1", 126, 130, "r")
    s.w((128, 130), (136, 130)); s.pad("J_L", 136, 130, "r", "LED pad")
    s.note(110, 134, "LED1 lights when the LED pad is taken to ground at the footswitch.")
    return s


def render(sheets, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import Circle
    pdf = PdfPages(os.path.join(outdir, "schematic.pdf"))
    for i, s in enumerate(sheets):
        xs = [x for l in s.lines for x in l[0]] + [t[0] for t in s.texts]
        ys = [y for l in s.lines for y in l[1]] + [t[1] for t in s.texts]
        x0, x1, y0, y1 = min(xs) - 12, max(xs) + 16, min(ys) - 7, max(ys) + 5
        fig = plt.figure(figsize=(17, max(6.0, 17 * (y1 - y0) / (x1 - x0)))); ax = fig.add_axes([0, 0, 1, 1])
        for lx, ly, lw in s.lines:
            ax.plot(lx, ly, color="black", lw=lw, solid_capstyle="round", solid_joinstyle="round")
        for x, y, r, filled in s.circles:
            ax.add_patch(Circle((x, y), r, fill=filled, color="black", lw=0.9))
        for x, y in s.dots:
            ax.add_patch(Circle((x, y), 0.3, color="black"))
        for x, y, t, ha, va, size, color, weight in s.texts:
            ax.text(x, y, t, ha=ha, va=va, fontsize=size * 1.25, color=color, fontweight=weight, linespacing=1.4)
        ax.text(x0 + 1, y0 + 1, s.title, fontsize=14, fontweight="bold", va="top")
        ax.text(x1 - 1, y1 - 1, f"stereoabuse  {NAME}  rev {REV}   sheet {i + 1} of {len(sheets)}", fontsize=9, ha="right", va="bottom")
        ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect("equal", adjustable="datalim"); ax.axis("off")
        pdf.savefig(fig); fig.savefig(os.path.join(outdir, f"schematic-{i + 1}.png"), dpi=130); plt.close(fig)
    pdf.close()


def main():
    sheets = [sheet_input(), sheet_drive(), sheet_resonator(), sheet_output()]
    errs = check(sheets)
    for e in errs:
        print("MISMATCH:", e)
    if errs and "--force" not in sys.argv:
        raise SystemExit(f"{len(errs)} mismatches against design.py; nothing written")
    render(sheets, os.path.join(os.path.dirname(HERE), "docs"))
    print("schematic matches design.py:", len(PARTS), "parts on", len(sheets), "sheets")


if __name__ == "__main__":
    main()
