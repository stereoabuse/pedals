"""Hand-laid-out schematic, drawn with matplotlib and checked against design.py.

Run:  uv run --with matplotlib python3 hw/schematic.py
Writes docs/schematic.pdf and docs/schematic-1.png.

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

    def JP2(self, ref, x, y, o="r"):
        self._two(ref, x, y, o, 2, "1", "2")
        self.Lo(o, x, y, [(-2, 0), (2, 0)])
        for sx in (-0.7, 0.7):
            self.Lo(o, x, y, [(sx - 0.5, -0.6), (sx + 0.5, -0.6), (sx + 0.5, 0.6), (sx - 0.5, 0.6), (sx - 0.5, -0.6)])
        self.T(x + 1.4, y - 0.4, ref + "  solder jumper", ha="left")
        self.T(x + 1.4, y + 0.8, "bridged by default; cut to remove the gate", ha="left", color="#444")

    def JP3(self, ref, x, y):
        self.pin(ref, "1", x - 3, y); self.pin(ref, "3", x + 3, y); self.pin(ref, "2", x, y + 2)
        self.L([(x - 3, y), (x - 1.6, y)]); self.L([(x + 3, y), (x + 1.6, y)]); self.L([(x, y + 2), (x, y + 0.6)])
        for sx in (-1.1, 0, 1.1):
            self.L([(x + sx - 0.45, y - 0.6), (x + sx + 0.45, y - 0.6), (x + sx + 0.45, y + 0.6), (x + sx - 0.45, y + 0.6), (x + sx - 0.45, y - 0.6)])
        self.L([(x - 0.65, y), (x - 0.45, y)], 2.0)
        self.T(x, y - 1.0, ref + "  18V | 9V", va="bottom")
        self.T(x + 0.8, y + 1.6, "bridged to the 18V side", ha="left", color="#444")

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
        lx, ly = tf(o, 0, -1.3 * wside)
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

    def jfet(self, ref, x, y, drain_top=True, gate_side=-1):
        g = gate_side
        yd, ys = (y - 2, y + 2) if drain_top else (y + 2, y - 2)
        self.pin(ref, "1", x, yd); self.pin(ref, "2", x, ys); self.pin(ref, "3", x + 3 * g, y)
        bx = x + 0.9 * g
        self.L([(bx, y - 1.1), (bx, y + 1.1)], 1.5)
        self.L([(x, y - 2), (x, y - 0.7), (bx, y - 0.7)]); self.L([(x, y + 2), (x, y + 0.7), (bx, y + 0.7)])
        self.L([(x + 3 * g, y), (bx, y)])
        self.L([(bx + 0.6 * g, y - 0.35), (bx, y), (bx + 0.6 * g, y + 0.35)])
        self.T(x + 0.5, yd + (0.5 if drain_top else -0.5), "D", size=4.5, color="#06c", ha="left")
        self.T(x + 0.5, ys + (-0.5 if drain_top else 0.5), "S", size=4.5, color="#06c", ha="left")
        self.T(x + 1.2, y - 0.3, ref, ha="left"); self.T(x + 1.2, y + 0.8, self.val(ref), ha="left", color="#444")

    def sw(self, ref, x, y, o, notes):
        c = tf(o, -3, 0); a = tf(o, 3, -2); b = tf(o, 3, 2)
        self.pin(ref, "2", x + c[0], y + c[1]); self.pin(ref, "1", x + a[0], y + a[1]); self.pin(ref, "3", x + b[0], y + b[1])
        self.Lo(o, x, y, [(-3, 0), (-1.2, 0)]); self.Lo(o, x, y, [(3, -2), (1.4, -2)]); self.Lo(o, x, y, [(3, 2), (1.4, 2)])
        self.Lo(o, x, y, [(-1.2, 0), (1.2, 0)], 1.3)
        for lx, ly in ((-1.2, 0), (1.4, -2), (1.4, 2)):
            px, py = tf(o, lx, ly); self.circles.append((x + px, y + py, 0.28, False))
        for pad, (lx, ly) in (("1", (2.4, -2.7)), ("3", (2.4, 2.7)), ("2", (-2.4, -0.7))):
            px, py = tf(o, lx, ly); self.T(x + px, y + py, pad, size=4.5, color="#06c")
        self.T(x + notes[0], y + notes[1], f"{ref}  {self.val(ref)}\n{notes[2]}", ha=notes[3], va="center", weight="bold", size=6)

    def box(self, ref, x, y, w, left, right):
        n = max(len(left), len(right)); h = 2 * n + 1
        y0 = y - (n - 1)
        self.L([(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2), (x - w / 2, y - h / 2)], 1.1)
        for side, lst in ((-1, left), (1, right)):
            for i, (pad, name) in enumerate(lst):
                py = y0 + 2 * i; px = x + side * (w / 2 + 2)
                self.pin(ref, pad, px, py); self.L([(px, py), (x + side * w / 2, py)])
                self.T(x + side * (w / 2 - 0.4), py, name, ha="right" if side > 0 else "left", size=5.5)
                self.T(x + side * (w / 2 + 0.9), py - 0.6, pad, size=4.5, color="#06c")
        self.T(x, y - h / 2 - 0.9, f"{ref}  {self.val(ref)}", weight="bold")

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


# ------------------------------------------------------------------ sheet
def sheet_all():
    s = Sheet("One-knob overdrive: Tube Screamer with Drive fixed at zero and Level fixed at maximum")
    # power
    s.pad("J_9V", 4, 10, "l"); s.w((4, 10), (7, 10)); s.D("D1", 9, 10, "r"); s.w((11, 10), (14, 10)); s.R("R20", 17, 10, "r")
    s.w((20, 10), (52, 10)); s.flag(24, 10, "V9")
    for ref, x in (("C20", 28), ("C21", 34), ("C22", 40), ("C23", 46)):
        s.w((x, 10), (x, 12)); s.C(ref, x, 14, "d"); s.gnd(x, 16)
    s.pad("TP1", 52, 10, "r")
    s.flag(62, 6, "V9"); s.w((62, 6), (62, 7)); s.R("R21", 62, 10, "d"); s.w((62, 13), (62, 15)); s.R("R22", 62, 18, "d"); s.gnd(62, 21)
    s.w((62, 14), (72, 14)); s.w((66, 14), (66, 15)); s.C("C24", 66, 17, "d"); s.gnd(66, 19); s.flag(69, 14, "VREF"); s.pad("TP2", 72, 14, "r")
    s.w((98, 8), (110, 8)); s.flag(98, 8, "V9")
    for u, x in (("U1", 102), ("U2", 110)):
        s.w((x, 8), (x, 13)); s.pwr(u, x, 16); s.gnd(x, 19)
    for i, r in enumerate(("J_G1", "J_G2", "J_G3", "J_G4")):
        x = 120 + 5 * i
        s.pad(r, x, 10, "u", "G pad"); s.w((x, 10), (x, 12)); s.gnd(x, 12)
    # input buffer
    s.pad("J_IN", 4, 40, "l"); s.w((4, 40), (11, 40)); s.w((8, 40), (8, 41)); s.R("R1", 8, 44, "d"); s.gnd(8, 47)
    s.C("C1", 13, 40, "r"); s.w((15, 40), (23, 40)); s.w((19, 40), (19, 39)); s.R("R2", 19, 36, "d"); s.flag(19, 33, "VREF")
    s.opamp("U1", "A", 28, 42, plus_top=True)
    s.w((23, 44), (21, 44), (21, 48), (35, 48), (35, 42), (33, 42)); s.w((35, 42), (38, 42))
    # clipping stage
    s.C("C3", 40, 42, "r"); s.w((42, 42), (50, 42)); s.w((46, 42), (46, 41)); s.R("R3", 46, 38, "d"); s.flag(46, 35, "VREF")
    s.opamp("U1", "B", 55, 44, plus_top=True)
    s.w((50, 46), (48, 46), (48, 67)); s.w((60, 44), (62, 44)); s.w((62, 44), (62, 64))
    s.w((48, 52), (52, 52)); s.R("R5", 55, 52, "r"); s.w((58, 52), (62, 52))
    s.w((48, 56), (53, 56)); s.C("C5", 55, 56, "r"); s.w((57, 56), (62, 56))
    s.w((48, 60), (53, 60)); s.D("D2", 55, 60, "r"); s.w((57, 60), (62, 60))
    s.w((48, 64), (53, 64)); s.D("D3", 55, 64, "l"); s.w((57, 64), (62, 64))
    s.R("R4", 48, 70, "d", ); s.w((48, 73), (48, 75)); s.C("C4", 48, 77, "d", left=True); s.gnd(48, 79)
    s.w((48, 74), (53, 74), (53, 75)); s.C("C4B", 53, 77, "d"); s.gnd(53, 79)
    # tone
    s.w((62, 44), (66, 44)); s.R("R6", 69, 44, "r"); s.w((72, 44), (82, 44)); s.w((76, 44), (76, 46)); s.C("C6", 76, 48, "d"); s.gnd(76, 50)
    s.opamp("U2", "A", 87, 46, plus_top=True)
    s.w((82, 48), (81, 48), (81, 54), (84, 54)); s.R("R7", 87, 54, "r"); s.w((90, 54), (94, 54), (94, 46), (92, 46))
    s.w((72, 44), (72, 54)); s.pot("RV1", 72, 57, "d", "1", 1); s.w((72, 60), (81, 60), (81, 54))
    s.w((70, 57), (67, 57), (67, 60)); s.R("R8", 67, 63, "d"); s.w((67, 66), (67, 68)); s.C("C7", 67, 70, "d"); s.gnd(67, 72)
    # output stage
    s.w((94, 46), (100, 46)); s.opamp("U2", "B", 105, 48, plus_top=True)
    s.w((100, 50), (98, 50), (98, 59)); s.w((98, 56), (102, 56)); s.R("R9", 105, 56, "r"); s.w((108, 56), (112, 56), (112, 48), (110, 48))
    s.R("R10", 98, 62, "d"); s.w((98, 65), (98, 67)); s.C("C8", 98, 69, "d"); s.gnd(98, 71)
    s.w((112, 48), (115, 48)); s.C("C9", 117, 48, "r"); s.w((119, 48), (121, 48)); s.R("R11", 124, 48, "r"); s.w((127, 48), (135, 48))
    s.w((131, 48), (131, 49)); s.R("R12", 131, 52, "d"); s.gnd(131, 55); s.pad("J_OUT", 135, 48, "r")
    # LED
    s.flag(110, 70, "V9"); s.w((110, 70), (112, 70)); s.R("R13", 115, 70, "r"); s.w((118, 70), (120, 70)); s.D("LED1", 122, 70, "r")
    s.w((124, 70), (128, 70)); s.pad("J_L", 128, 70, "r", "LED pad")
    s.T(4, 95, "")
    s.note(4, 86, "U1A and U2B stand in for the transistor buffers of the original. Clipping stage: gain 1 + R5 / R4 = 11.9 above about 850 Hz\n"
                  "(R4 with C4 + C4B; the original is 720 Hz), soft-clipped by D2/D3. R5 is the 51k that the Drive pot adds to, so Drive is at zero.\n"
                  "Tone is the stock circuit; RV1 should be the W20K 'TS tone' taper. There is no Level pot: the tone stage feeds the output stage\n"
                  "directly, which adds 2.5 dB (1 + R9 / R10). The footswitch is wired to the IN, OUT, LED and G pads for true bypass.")
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
    sheets = [sheet_all()]
    errs = check(sheets)
    for e in errs:
        print("MISMATCH:", e)
    if errs and "--force" not in sys.argv:
        raise SystemExit(f"{len(errs)} mismatches against design.py; nothing written")
    render(sheets, os.path.join(os.path.dirname(HERE), "docs"))
    print("schematic matches design.py:", len(PARTS), "parts on", len(sheets), "sheets")


if __name__ == "__main__":
    main()
