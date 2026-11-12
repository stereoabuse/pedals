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

    def npn(self, ref, x, y):
        self.pin(ref, "1", x - 3, y); self.pin(ref, "3", x, y - 3); self.pin(ref, "2", x, y + 3)
        self.L([(x - 3, y), (x - 1, y)]); self.L([(x - 1, y - 1.3), (x - 1, y + 1.3)], 1.6)
        self.L([(x - 1, y - 0.5), (x, y - 1.5), (x, y - 3)]); self.L([(x - 1, y + 0.5), (x, y + 1.5), (x, y + 3)])
        self.L([(x - 0.75, y + 1.25), (x, y + 1.5), (x - 0.25, y + 0.75)], 0.8)
        for pad, (px, py) in (("1", (x - 2.3, y - 0.6)), ("3", (x + 0.6, y - 2.4)), ("2", (x + 0.6, y + 2.4))):
            self.T(px, py, pad, size=4.5, color="#06c")
        self.T(x + 1.0, y - 0.5, ref, ha="left"); self.T(x + 1.0, y + 0.7, self.val(ref), ha="left", color="#444")

    def chip(self, ref, x, y):
        """CD4053 drawn as a box; every pin carries its net name from the netlist."""
        left = [("12", "A0"), ("13", "A1"), ("2", "B0"), ("1", "B1"), ("5", "C0"), ("3", "C1"), ("11", "sel A"), ("10", "sel B"), ("9", "sel C")]
        right = [("14", "A"), ("15", "B"), ("4", "C"), ("16", "VDD"), ("6", "INH"), ("7", "VEE"), ("8", "VSS")]
        self.box(ref, x, y, 12, left, right)
        pins = PARTS[ref]["pins"]
        for pad, _ in left:
            px, py = self.pins[(ref, pad)]
            self.w((px, py), (px - 2, py)); self.label(px - 2, py, pins[pad], "l")
        for pad, _ in right[:4]:
            px, py = self.pins[(ref, pad)]
            self.w((px, py), (px + 2, py)); self.label(px + 2, py, pins[pad], "r")
        (px, y6), (_, y7), (_, y8) = (self.pins[(ref, k)] for k in ("6", "7", "8"))
        self.w((px, y6), (px + 3, y6), (px + 3, y8)); self.w((px, y7), (px + 3, y7)); self.w((px, y8), (px + 3, y8)); self.gnd(px + 3, y8)

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


# ------------------------------------------------------------------ sheets
def sheet_routing():
    s = Sheet("Power, input and output buffers, routing switches, parallel mixer, footswitch and order controls")
    # power
    s.pad("J_9V", 4, 10, "l"); s.w((4, 10), (7, 10)); s.D("D1", 9, 10, "r"); s.w((11, 10), (14, 10)); s.R("R20", 17, 10, "r")
    s.w((20, 10), (40, 10)); s.flag(24, 10, "VCC")
    for ref, x in (("C20", 28), ("C21", 34)):
        s.w((x, 10), (x, 12)); s.C(ref, x, 14, "d"); s.gnd(x, 16)
    s.pad("TP1", 40, 10, "r")
    s.flag(62, 6, "VCC"); s.w((62, 6), (62, 7)); s.R("R21", 62, 10, "d"); s.w((62, 13), (62, 15)); s.R("R22", 62, 18, "d"); s.gnd(62, 21)
    s.w((62, 14), (72, 14)); s.w((68, 14), (68, 15)); s.C("C24", 68, 17, "d"); s.gnd(68, 19)
    s.R("R23", 75, 14, "r"); s.w((78, 14), (80, 14)); s.opamp("U1", "B", 85, 16, plus_top=True)
    s.w((80, 18), (78, 18), (78, 22), (92, 22), (92, 16), (90, 16)); s.w((92, 16), (98, 16)); s.flag(95, 16, "VREF"); s.pad("TP2", 98, 16, "r")
    s.flag(118, 8, "VCC"); s.w((118, 8), (190, 8))
    for i in range(7):
        x = 120 + 7 * i
        s.w((x, 8), (x, 10)); s.C(f"C3{i}", x, 12, "d"); s.gnd(x, 14)
    for u, x in (("U1", 172), ("U2", 178), ("U3", 184), ("U4", 190)):
        s.w((x, 8), (x, 13)); s.pwr(u, x, 16); s.gnd(x, 19)
    for i, r in enumerate(("J_G1", "J_G2", "J_G3", "J_G4", "J_G5")):
        x = 200 + 6 * i
        s.pad(r, x, 10, "u", "G pad"); s.w((x, 10), (x, 12)); s.gnd(x, 12)
    # input buffer
    s.pad("J_IN", 4, 40, "l"); s.w((4, 40), (11, 40)); s.w((8, 40), (8, 41)); s.R("R1", 8, 44, "d"); s.gnd(8, 47)
    s.C("C1", 13, 40, "r"); s.w((15, 40), (22, 40)); s.w((19, 40), (19, 39)); s.R("R2", 19, 36, "d"); s.flag(19, 33, "VREF")
    s.R("R3", 25, 40, "r"); s.w((28, 40), (33, 40)); s.w((30, 40), (30, 42)); s.C("C2", 30, 44, "d", left=True); s.gnd(30, 46)
    s.opamp("U1", "A", 38, 42, plus_top=True)
    s.w((33, 44), (32, 44), (32, 50), (45, 50), (45, 42), (43, 42)); s.w((45, 42), (48, 42)); s.label(48, 42, "IB", "r", "buffered input")
    # routing switches
    for u, x in (("U5", 30), ("U6", 80), ("U7", 130)):
        s.chip(u, x, 76)
    s.note(72, 30, "Each CD4053B section connects its common pin to input 0 when its select line is low, input 1 when high.\n"
                    "NTS and NMF are low while that effect is on. NAB is low for Screamer > Muff, NBA for Muff > Screamer;\n"
                    "both high (toggle centred) is parallel.\n\n"
                    "TSI   Screamer input:  IB, or XMF when Muff > Screamer\n"
                    "MFS   Muff input:  IB, or XTS when Screamer > Muff\n"
                    "MFI   MFS while the Muff is on, VREF (silent) while it is off\n"
                    "XTS   TSO while the Screamer is on, else IB\n"
                    "XMF   MFO while the Muff is on, else IB\n"
                    "W2    TSO for Muff > Screamer, else MIX (both in parallel)\n"
                    "W     MFO for Screamer > Muff, else W2\n"
                    "YSA   W while the Muff is on, else TSO\n"
                    "OSEL  YSA while the Screamer is on, else XMF.  OSEL feeds the output buffer.")
    # mixer
    s.label(4, 108, "TSO", "l"); s.w((4, 108), (8, 108)); s.R("R80", 11, 108, "r")
    s.label(4, 114, "MFO", "l"); s.w((4, 114), (8, 114)); s.R("R81", 11, 114, "r"); s.w((14, 108), (14, 114)); s.w((14, 112), (22, 112))
    s.opamp("U3", "B", 27, 110, plus_top=True); s.w((22, 108), (20, 108), (20, 104)); s.flag(20, 104, "VREF")
    s.w((18, 112), (18, 118), (22, 118)); s.R("R82", 25, 118, "r"); s.w((28, 118), (34, 118), (34, 110), (32, 110))
    s.w((18, 118), (18, 123), (23, 123)); s.C("C80", 25, 123, "r"); s.w((27, 123), (34, 123), (34, 118))
    s.w((34, 110), (38, 110)); s.label(38, 110, "MIX", "r")
    # output buffer
    s.label(60, 108, "OSEL", "l"); s.w((60, 108), (70, 108)); s.w((65, 108), (65, 105)); s.R("R83", 65, 102, "d"); s.flag(65, 99, "VREF")
    s.opamp("U4", "B", 75, 110, plus_top=True); s.w((70, 112), (68, 112), (68, 116), (82, 116), (82, 110), (80, 110))
    s.w((82, 110), (85, 110)); s.C("C81", 87, 110, "r"); s.w((89, 110), (91, 110)); s.R("R85", 94, 110, "r"); s.w((97, 110), (105, 110))
    s.w((101, 110), (101, 111)); s.R("R86", 101, 114, "d"); s.gnd(101, 117); s.pad("J_OUT", 105, 110, "r")
    # footswitches
    for x, jp, ra, rl, led, rs, c, net in ((0, "J_FT", "R90", "R92", "LED1", "R91", "C90", "NTS"), (56, "J_FM", "R93", "R95", "LED2", "R94", "C91", "NMF")):
        s.flag(x + 8, 136, "VCC"); s.w((x + 8, 136), (x + 16, 136)); s.w((x + 10, 136), (x + 10, 137)); s.w((x + 16, 136), (x + 16, 137))
        s.R(ra, x + 10, 140, "d", ); s.R(rl, x + 16, 140, "d"); s.w((x + 16, 143), (x + 16, 144)); s.D(led, x + 16, 146, "d")
        s.w((x + 10, 143), (x + 10, 150), (x + 24, 150)); s.w((x + 16, 148), (x + 16, 150))
        s.pad(jp, x + 4, 150, "l", "FS pad"); s.w((x + 4, 150), (x + 10, 150))
        s.R(rs, x + 27, 150, "r"); s.w((x + 30, 150), (x + 36, 150)); s.w((x + 33, 150), (x + 33, 151)); s.C(c, x + 33, 153, "d"); s.gnd(x + 33, 155)
        s.label(x + 36, 150, net, "r")
    s.note(4, 160, "Each footswitch only has to short its FS pad to a G pad (one pole of any latching switch). Closed = effect on, LED lit.")
    # order toggle
    s.sw("SW1", 120, 146, "r", (-3, -7, "on-off-on", "center")); s.w((117, 146), (115, 146)); s.gnd(115, 146)
    s.w((123, 144), (123, 140), (150, 140)); s.w((130, 139), (130, 140)); s.R("R96", 130, 136, "d"); s.flag(130, 133, "VCC")
    s.w((138, 140), (138, 141)); s.C("C92", 138, 143, "d"); s.gnd(138, 145); s.label(150, 140, "NAB", "r", "low = Screamer > Muff")
    s.w((123, 148), (123, 152), (150, 152)); s.w((130, 152), (130, 153)); s.R("R97", 130, 156, "d"); s.flag(130, 159, "VCC", "d")
    s.w((138, 152), (138, 153)); s.C("C93", 138, 155, "d"); s.gnd(138, 157); s.label(150, 152, "NBA", "r", "low = Muff > Screamer")
    return s


def sheet_screamer():
    s = Sheet("Screamer: TS808 circuit (TSI in, TSO out)")
    s.label(4, 42, "TSI", "l"); s.w((4, 42), (12, 42)); s.w((8, 42), (8, 43)); s.R("R41", 8, 46, "d"); s.flag(8, 49, "VREF", "d")
    s.C("C40", 14, 42, "r"); s.w((16, 42), (26, 42)); s.w((21, 42), (21, 41)); s.R("R40", 21, 38, "d"); s.flag(21, 35, "VREF")
    s.opamp("U2", "A", 31, 44, plus_top=True)
    s.w((26, 46), (24, 46), (24, 67)); s.w((36, 44), (40, 44)); s.w((40, 44), (40, 64))
    s.w((24, 52), (26, 52)); s.R("R43", 29, 52, "r"); s.w((32, 52), (33, 52)); s.pot("RV1", 36, 52, "r", "1", -1)
    s.w((39, 52), (40, 52)); s.w((36, 50), (36, 49), (40, 49))
    s.w((24, 57), (30, 57)); s.C("C42", 32, 57, "r"); s.w((34, 57), (40, 57))
    s.w((24, 61), (30, 61)); s.D("D2", 32, 61, "r"); s.w((34, 61), (40, 61))
    s.w((24, 64), (30, 64)); s.D("D3", 32, 64, "l"); s.w((34, 64), (40, 64))
    s.R("R42", 24, 70, "d"); s.w((24, 73), (24, 74)); s.C("C41", 24, 76, "d"); s.gnd(24, 78)
    # tone
    s.w((40, 44), (46, 44)); s.R("R44", 49, 44, "r"); s.w((52, 44), (64, 44)); s.w((58, 44), (58, 46)); s.C("C43", 58, 48, "d"); s.gnd(58, 50)
    s.opamp("U2", "B", 69, 46, plus_top=True)
    s.w((64, 48), (62, 48), (62, 56), (66, 56)); s.R("R45", 69, 56, "r"); s.w((72, 56), (76, 56), (76, 46), (74, 46))
    s.w((54, 44), (54, 58)); s.pot("RV2", 54, 61, "d", "1", 1); s.w((54, 64), (62, 64), (62, 56))
    s.w((52, 61), (48, 61), (48, 64)); s.R("R46", 48, 67, "d"); s.w((48, 70), (48, 71)); s.C("C44", 48, 73, "d"); s.gnd(48, 75)
    # level
    s.w((76, 46), (80, 46)); s.C("C45", 82, 46, "r"); s.w((84, 46), (90, 46), (90, 48)); s.pot("RV3", 90, 51, "d", "3", -1); s.flag(90, 54, "VREF", "d")
    s.w((92, 51), (98, 51)); s.opamp("U3", "A", 103, 53, plus_top=True)
    s.w((98, 55), (96, 55), (96, 59), (110, 59), (110, 53), (108, 53)); s.w((110, 53), (114, 53)); s.label(114, 53, "TSO", "r")
    s.note(4, 84, "Stock TS808 values. Clipping stage: gain 1 + (R43 + Drive) / R42 above 720 Hz (R42 with C41), soft-clipped by D2/D3.\n"
                  "The original's transistor buffers are not needed: the pedal's input buffer (or the Muff's output buffer) drives TSI,\n"
                  "and U3A buffers the Level pot. Two parts differ from the original: C42 is 47p (51p) and the bias resistor R40 is 100k (10k),\n"
                  "which only lightens the load on the routing switches. RV2 should be the W20K 'TS tone' taper.")
    return s


def sheet_muff():
    s = Sheet("Muff: black Russian Big Muff circuit (MFI in, MFO out)")
    s.flag(4, 8, "VCC"); s.w((4, 8), (8, 8)); s.R("R73", 11, 8, "r"); s.w((14, 8), (26, 8)); s.w((20, 8), (20, 9)); s.C("C64", 20, 11, "d"); s.gnd(20, 13)
    s.flag(26, 8, "VM")
    # input stage
    s.label(4, 40, "MFI", "l"); s.w((4, 40), (10, 40)); s.w((7, 40), (7, 41)); s.R("R84", 7, 44, "d"); s.flag(7, 47, "VREF", "d")
    s.C("C50", 12, 42 - 2, "r"); s.w((14, 40), (16, 40)); s.R("R50", 19, 40, "r"); s.w((22, 40), (31, 40)); s.npn("Q1", 34, 40)
    s.w((26, 40), (26, 42)); s.R("R51", 26, 45, "d", ); s.gnd(26, 48); s.R("R54", 34, 46, "d"); s.gnd(34, 49)
    s.w((34, 37), (34, 30)); s.R("R53", 34, 27, "d"); s.flag(34, 24, "VM")
    s.R("R52", 27, 34, "r"); s.w((30, 34), (34, 34)); s.w((24, 34), (24, 40))
    s.C("C51", 27, 29, "r"); s.w((29, 29), (31, 29), (31, 34)); s.w((25, 29), (24, 29), (24, 34))
    s.w((34, 36), (42, 36)); s.C("C52", 44, 36, "r"); s.w((46, 36), (60, 36), (60, 37)); s.pot("RV4", 60, 40, "d", "3", -1)
    s.R("R55", 60, 46, "d"); s.gnd(60, 49)
    s.w((62, 40), (66, 40)); s.C("C53", 68, 40, "r"); s.w((70, 40), (72, 40)); s.R("R56", 75, 40, "r"); s.w((78, 40), (87, 40))
    # two clipping stages
    for x, q, rb, re, rc, rf, cf, cd, da, db in ((12, "Q2", "R57", "R60", "R59", "R58", "C54", "C55", "D4", "D5"),
                                                 (58, "Q3", "R62", "R65", "R64", "R63", "C57", "C58", "D6", "D7")):
        s.npn(q, x + 78, 40)
        s.w((x + 70, 40), (x + 70, 42)); s.R(rb, x + 70, 45, "d"); s.gnd(x + 70, 48); s.R(re, x + 78, 46, "d"); s.gnd(x + 78, 49)
        s.w((x + 78, 37), (x + 78, 30)); s.R(rc, x + 78, 27, "d"); s.flag(x + 78, 24, "VM")
        s.R(rf, x + 71, 34, "r"); s.w((x + 74, 34), (x + 78, 34)); s.w((x + 68, 34), (x + 68, 40))
        s.C(cf, x + 71, 29, "r"); s.w((x + 73, 29), (x + 75, 29), (x + 75, 34)); s.w((x + 69, 29), (x + 68, 29), (x + 68, 34))
        s.w((x + 68, 29), (x + 68, 13)); s.w((x + 68, 13), (x + 69, 13)); s.D(da, x + 71, 13, "l"); s.w((x + 68, 20), (x + 69, 20)); s.D(db, x + 71, 20, "r")
        s.w((x + 73, 13), (x + 73, 20)); s.w((x + 73, 16), (x + 81, 16)); s.C(cd, x + 83, 16, "r")
        s.w((x + 85, 16), (x + 88, 16), (x + 88, 32), (x + 78, 32))
    s.w((90, 36), (104, 36), (104, 40), (110, 40)); s.C("C56", 112, 40, "r"); s.w((114, 40), (116, 40)); s.R("R61", 119, 40, "r"); s.w((122, 40), (133, 40))
    # tone stack
    s.w((136, 36), (150, 36)); s.w((150, 36), (150, 26), (154, 26)); s.C("C59", 156, 26, "r"); s.w((158, 26), (176, 26), (176, 33))
    s.w((176, 26), (177, 26)); s.R("R66", 180, 26, "r"); s.gnd(183, 26)
    s.pot("RV5", 176, 36, "d", "3", -1)
    s.w((150, 36), (150, 46), (154, 46)); s.R("R67", 157, 46, "r"); s.w((160, 46), (176, 46), (176, 39)); s.w((166, 46), (166, 48)); s.C("C60", 166, 50, "d"); s.gnd(166, 52)
    # recovery stage
    s.w((178, 36), (184, 36)); s.C("C61", 186, 36, "r"); s.w((188, 36), (201, 36)); s.npn("Q4", 204, 36)
    s.R("R68", 194, 31, "d"); s.w((194, 34), (194, 36)); s.flag(194, 28, "VM"); s.w((194, 36), (194, 38)); s.R("R69", 194, 41, "d"); s.gnd(194, 44)
    s.R("R70", 204, 28, "d"); s.w((204, 31), (204, 33)); s.flag(204, 25, "VM"); s.R("R71", 204, 42, "d"); s.gnd(204, 45)
    s.w((204, 32), (212, 32)); s.C("C62", 214, 32, "r"); s.w((216, 32), (232, 32), (232, 34)); s.pot("RV6", 232, 37, "d", "3", -1); s.gnd(232, 40)
    s.w((234, 37), (238, 37)); s.C("C63", 240, 37, "r"); s.w((242, 37), (252, 37)); s.w((246, 37), (246, 36)); s.R("R72", 246, 33, "d"); s.flag(246, 30, "VREF")
    s.opamp("U4", "A", 257, 39, plus_top=True)
    s.w((252, 41), (250, 41), (250, 45), (264, 45), (264, 39), (262, 39)); s.w((264, 39), (268, 39)); s.label(268, 39, "MFO", "r")
    s.note(4, 58, "Values follow Kit Rae's trace of the V7C/V8 black Russian Big Muff (bigmuffpage.com). BC847C stands in for the BC547C.\n"
                  "R73/C64 give the Muff its own filtered supply. U4A buffers the Volume pot so the routing switches see a low impedance.")
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
    sheets = [sheet_routing(), sheet_screamer(), sheet_muff()]
    errs = check(sheets)
    for e in errs:
        print("MISMATCH:", e)
    if errs and "--force" not in sys.argv:
        raise SystemExit(f"{len(errs)} mismatches against design.py; nothing written")
    render(sheets, os.path.join(os.path.dirname(HERE), "docs"))
    print("schematic matches design.py:", len(PARTS), "parts on", len(sheets), "sheets")


if __name__ == "__main__":
    main()
