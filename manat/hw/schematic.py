"""Hand-laid-out schematic, drawn with matplotlib and checked against design.py.

Run:  uv run --with matplotlib python3 hw/schematic.py
Writes docs/schematic.pdf (6 pages) and docs/schematic-N.png.

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
SYMMETRIC = {"R", "C", "C08", "C12"}


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


# ------------------------------------------------------------------ sheets
def sheet_power():
    s = Sheet("1  Power: 9V input, voltage doubler, VREF, indicator LEDs")
    s.pad("J_9V", 4, 20, "l"); s.w((4, 20), (7, 20)); s.D("D1", 9, 20, "r")
    s.w((11, 20), (58, 20)); s.flag(13, 20, "V9")
    s.w((17, 20), (17, 22)); s.C("C20", 17, 24, "d"); s.gnd(17, 26)
    s.w((24, 20), (24, 22)); s.C("C21", 24, 24, "d"); s.gnd(24, 26)
    s.w((30, 20), (30, 16)); s.pad("TP3", 30, 16, "u")
    s.box("U6", 36, 30, 12, [("1", "BOOST"), ("2", "CAP+"), ("3", "GND"), ("4", "CAP-")],
          [("8", "V+"), ("7", "OSC"), ("6", "LV"), ("5", "VOUT")])
    s.w((44, 27), (46, 27), (46, 20)); s.w((28, 27), (26, 27), (26, 20))
    s.w((28, 31), (25, 31)); s.gnd(25, 31)
    s.w((28, 29), (23, 29), (23, 40)); s.w((28, 33), (27, 33), (27, 40)); s.C("C22", 25, 40, "r")
    s.w((44, 33), (46, 33), (46, 36)); s.C("C23", 46, 38, "u"); s.gnd(46, 40)
    s.T(47.5, 30, "OSC, LV: not connected", ha="left", size=5.5, color="#555")
    s.D("D2", 60, 20, "r"); s.w((62, 20), (66, 20)); s.D("D3", 68, 20, "r")
    s.w((64, 20), (64, 22)); s.C("C24", 64, 24, "d"); s.w((64, 26), (64, 46), (23, 46), (23, 40))
    s.w((70, 20), (84, 20))
    s.w((73, 20), (73, 22)); s.C("C26", 73, 24, "d"); s.gnd(73, 26)
    s.w((78, 20), (78, 22)); s.C("C27", 78, 24, "d"); s.gnd(78, 26)
    s.T(77, 18.6, "V18, about 16-17 V", size=6, color="#b00")
    s.JP3("JP1", 87, 20); s.w((90, 20), (92, 20)); s.flag(92, 20, "V9")
    s.w((87, 22), (87, 26), (92, 26)); s.R("R30", 95, 26, "r"); s.w((98, 26), (108, 26)); s.flag(104, 26, "VCC")
    s.w((101, 26), (101, 28)); s.C("C28", 101, 30, "d"); s.gnd(101, 32)
    s.pad("TP1", 108, 26, "r")
    # indicator LEDs
    s.flag(70, 40, "V9"); s.w((70, 40), (72, 40)); s.R("R71", 75, 40, "r"); s.w((78, 40), (80, 40)); s.D("LED5", 82, 40, "r")
    s.w((84, 40), (90, 40)); s.pad("J_L1", 90, 40, "r", "LED pad (boost side)")
    s.flag(70, 48, "V9"); s.w((70, 48), (72, 48)); s.R("R72", 75, 48, "r"); s.w((78, 48), (80, 48)); s.D("LED6", 82, 48, "r")
    s.w((84, 48), (90, 48)); s.pad("J_L2", 90, 48, "r", "LED pad (preamp side)")
    s.note(70, 51, "LED5 = boost, LED6 = preamp. Each footswitch grounds its own LED pad.")
    for i, r in enumerate(("J_G1", "J_G2", "J_G3", "J_G4", "J_G5")):
        x = 104 + 5 * i
        s.pad(r, x, 38, "u", "G pad"); s.w((x, 38), (x, 40)); s.gnd(x, 40)
    # VREF
    s.flag(10, 56, "VCC"); s.w((10, 56), (10, 57)); s.R("R32", 10, 60, "d"); s.w((10, 63), (10, 65)); s.R("R33", 10, 68, "d"); s.gnd(10, 71)
    s.w((10, 64), (20, 64)); s.w((15, 64), (15, 65)); s.C("C25", 15, 67, "d"); s.gnd(15, 69)
    s.R("R34", 23, 64, "r"); s.w((26, 64), (29, 64)); s.opamp("U4", "A", 34, 66, plus_top=True)
    s.w((29, 68), (27, 68), (27, 72), (41, 72), (41, 66), (39, 66)); s.w((41, 66), (48, 66)); s.flag(45, 66, "VREF"); s.pad("TP2", 48, 66, "r")
    s.note(20, 75, "VREF = VCC / 2, buffered. Every op-amp stage is biased from it.")
    # op-amp supply pins
    s.w((58, 56), (116, 56)); s.flag(58, 56, "VCC")
    for i, (u, c) in enumerate((("U1", "C6"), ("U2", "C7"), ("U3", "C10"), ("U4", "C29"), ("U5", "C30"), ("U7", "C87"))):
        x = 60 + 10 * i
        s.w((x, 56), (x, 61)); s.pwr(u, x, 64); s.gnd(x, 67)
        s.w((x + 4, 56), (x + 4, 60)); s.C(c, x + 4, 62, "d"); s.gnd(x + 4, 64)
    return s


def sheet_input():
    s = Sheet("2  Preamp input stage, Tight, gain stage")
    s.pad("J_IN", 6, 28, "l"); s.w((6, 28), (13, 28)); s.w((10, 28), (10, 29)); s.R("R1", 10, 32, "d"); s.gnd(10, 35)
    s.C("C1", 15, 28, "r"); s.w((17, 28), (22, 28)); s.w((20, 28), (20, 27)); s.R("R2", 20, 24, "d"); s.flag(20, 21, "VREF")
    s.R("R3", 25, 28, "r"); s.w((28, 28), (35, 28)); s.w((29, 28), (29, 29)); s.C("C2", 29, 31, "d"); s.gnd(29, 33)
    s.opamp("U1", "A", 40, 30, plus_top=True)
    s.w((35, 32), (33, 32), (33, 38), (37, 38)); s.R("R5", 40, 38, "r"); s.w((43, 38), (47, 38), (47, 30), (45, 30))
    s.w((33, 38), (33, 39)); s.R("R4", 33, 42, "d"); s.flag(33, 45, "VREF", "d")
    # tight
    s.w((47, 30), (52, 30)); s.w((47, 30), (47, 21)); s.label(47, 21, "S1", "r", "to gate, sheet 5")
    s.C("C3A", 54, 30, "r"); s.C("C3B", 54, 25, "r"); s.w((52, 30), (52, 25)); s.w((56, 25), (56, 30))
    s.w((56, 30), (62, 30)); s.w((59, 30), (59, 31)); s.R("R7", 59, 34, "d"); s.w((59, 37), (59, 38))
    s.pot("RV1", 59, 41, "d", "3", -1); s.w((61, 41), (63, 41), (63, 44), (59, 44)); s.flag(59, 44, "VREF", "d")
    s.R("R8", 65, 30, "r"); s.w((68, 30), (75, 30)); s.w((70, 30), (70, 31)); s.C("C4", 70, 33, "d"); s.gnd(70, 35)
    # gain stage
    s.opamp("U1", "B", 80, 32, plus_top=True)
    s.w((75, 34), (73, 34), (73, 43)); s.R("R9", 73, 46, "d"); s.w((73, 49), (73, 50)); s.C("C8", 73, 52, "d"); s.gnd(73, 54)
    s.w((73, 42), (75, 42)); s.R("R10", 78, 42, "r"); s.w((81, 42), (85, 42)); s.pot("RV2", 88, 42, "r", "1")
    s.w((88, 44), (91, 44), (91, 42)); s.w((91, 42), (93, 42))
    s.w((83, 42), (83, 53), (86, 53)); s.w((83, 48), (86, 48)); s.D("LED1", 88, 48, "r"); s.D("LED2", 88, 53, "l")
    s.w((90, 48), (93, 48)); s.w((90, 53), (93, 53), (93, 32)); s.w((85, 32), (98, 32)); s.label(98, 32, "S2", "r", "sheet 3")
    s.w((73, 37), (81, 37)); s.C("C9", 83, 37, "r"); s.w((85, 37), (93, 37))
    s.note(52, 59, "Tight: C3A/C3B with R7 + RV1 form a high-pass, about 75 Hz (CCW) to 1.7 kHz (CW).\nGain stage: gain = 1 + (R10 + RV2) / R9; LED1/LED2 soft-clip across the gain pot.")
    return s


def sheet_clip():
    s = Sheet("3  Clip stage, gain trim, Presence, hard clip, gate switch")
    s.label(4, 30, "S2", "l", "sheet 2"); s.w((4, 30), (6, 30)); s.C("C11", 8, 30, "r"); s.w((10, 30), (12, 30)); s.R("R11", 15, 30, "r")
    s.w((18, 30), (25, 30)); s.opamp("U2", "A", 30, 32)
    s.w((25, 34), (23, 34), (23, 36)); s.flag(23, 36, "VREF", "d")
    s.w((21, 30), (21, 10), (22, 10)); s.w((35, 32), (58, 32)); s.w((52, 32), (52, 2))
    s.w((21, 22), (27, 22)); s.R("R13", 30, 22, "r"); s.w((33, 22), (52, 22))
    s.w((21, 18), (28, 18)); s.C("C12", 30, 18, "r"); s.w((32, 18), (52, 18))
    s.R("R12", 25, 10, "r"); s.w((28, 10), (29, 10))
    s.sw("SW1", 32, 10, "r", (-9, -5, "1 = stock   centre = open   3 = saturated", "center"))
    s.w((35, 8), (37, 8), (37, 2), (39, 2)); s.D("D4", 41, 2, "r"); s.w((43, 2), (47, 2)); s.D("D5", 49, 2, "r"); s.w((51, 2), (52, 2))
    s.w((52, 6), (51, 6)); s.D("D6", 49, 6, "l"); s.w((47, 6), (43, 6)); s.D("D7", 41, 6, "l"); s.w((39, 6), (37, 6))
    s.w((35, 12), (37, 12), (42, 12)); s.D("D8", 44, 12, "r"); s.w((46, 12), (52, 12))
    s.w((52, 15), (46, 15)); s.D("D9", 44, 15, "l"); s.w((42, 15), (37, 15), (37, 12))
    s.T(54, 27, "S3", color="#070", weight="bold", ha="left")
    # trim stage
    s.R("R14", 61, 32, "r"); s.w((64, 32), (69, 32)); s.opamp("U2", "B", 74, 34)
    s.w((69, 36), (67, 36), (67, 38)); s.flag(67, 38, "VREF", "d")
    s.w((66, 32), (66, 19), (72, 19)); s.C("C13", 74, 19, "r"); s.w((76, 19), (83, 19), (83, 34))
    s.w((66, 24), (67, 24)); s.R("R15", 70, 24, "r"); s.w((73, 24), (75, 24)); s.pot("RV8", 78, 24, "r", "1")
    s.w((78, 26), (81, 26), (81, 24)); s.w((81, 24), (83, 24))
    s.w((79, 34), (88, 34)); s.T(85, 32.8, "S4", color="#070", weight="bold")
    # presence, hard clip
    s.C("C19", 90, 34, "r"); s.w((92, 34), (94, 34)); s.pot("RV3", 97, 34, "r", "3")
    s.w((97, 36), (100, 36), (100, 34)); s.w((100, 34), (102, 34)); s.R("R18", 105, 34, "r")
    s.w((108, 34), (134, 34)); s.label(134, 34, "NH", "r", "sheet 4")
    s.w((110, 34), (110, 36)); s.C("C14", 110, 38, "d"); s.gnd(110, 40)
    s.w((118, 34), (118, 36)); s.D("LED3", 118, 38, "d", left=True); s.w((124, 34), (124, 36)); s.D("LED4", 124, 38, "u")
    s.w((118, 40), (118, 42), (124, 42), (124, 40)); s.flag(121, 42, "VREF", "d")
    s.w((130, 34), (130, 35)); s.R("R24", 130, 38, "d"); s.flag(130, 41, "VREF", "d")
    # gate JFET
    s.w((114, 34), (114, 32)); s.JP2("JP2", 114, 30, "d"); s.w((114, 28), (114, 25)); s.jfet("Q1", 114, 23, drain_top=False)
    s.flag(114, 21, "VREF"); s.w((111, 23), (104, 23)); s.label(104, 23, "NGATE", "l", "sheet 5")
    s.note(60, 46, "Clip stage gain is -R13/R11 = -10, soft-clipped by the diode branch chosen with SW1.\n"
                   "RV8 (GAIN TRIM) sets the gain of the last stage, -1 to -11.\n"
                   "Presence: RV3 + R18 with C14 is a low-pass, about 1.3 kHz (CCW) to 7.2 kHz (CW).\n"
                   "LED3/LED4 hard-clip to VREF. Q1 shorts NH to VREF when the gate closes.")
    return s


def sheet_eq():
    s = Sheet("4  Treble, Depth, Mid, output")
    s.label(4, 20, "NH", "l", "sheet 3"); s.w((4, 20), (8, 20), (8, 21)); s.pot("RV4", 8, 24, "d", "3", -1)
    s.w((8, 27), (8, 28)); s.C("C15", 8, 30, "d"); s.gnd(8, 32)
    s.w((10, 24), (17, 24)); s.opamp("U3", "A", 22, 26, plus_top=True)
    s.w((17, 28), (15, 28), (15, 40), (16, 40)); s.w((27, 26), (45, 26)); s.w((31, 26), (31, 40), (30, 40))
    s.w((15, 32), (21, 32)); s.C("C16A", 23, 32, "r"); s.w((25, 32), (31, 32))
    s.w((15, 36), (21, 36)); s.C("C16B", 23, 36, "r"); s.w((25, 36), (31, 36))
    s.R("R19", 19, 40, "r"); s.w((22, 40), (24, 40)); s.R("R20", 27, 40, "r")
    s.w((23, 40), (23, 43)); s.C("C17A", 23, 45, "d", left=True); s.w((23, 43), (27, 43)); s.C("C17B", 27, 45, "d"); s.w((27, 47), (23, 47)); s.w((23, 47), (23, 50)); s.w((23, 50), (23, 51))
    s.w((15, 50), (31, 50)); s.w((15, 50), (15, 51)); s.R("R25", 15, 54, "d"); s.gnd(15, 57)
    s.R("R22", 23, 54, "d"); s.w((31, 50), (31, 51)); s.R("R23", 31, 54, "d")
    s.w((23, 57), (23, 59), (25, 59)); s.w((31, 57), (31, 59), (29, 59))
    s.sw("SW2", 27, 62, "u", (5, 2, "1 = medium   centre = flat   3 = deep", "left")); s.gnd(27, 65)
    s.T(36, 25, "S5", color="#070", weight="bold")
    # mid stage
    s.R("R53", 48, 26, "r"); s.w((51, 26), (55, 26)); s.opamp("U3", "B", 60, 28)
    s.w((55, 30), (53, 30), (53, 32)); s.flag(53, 32, "VREF", "d")
    s.w((53, 26), (53, 15)); s.w((65, 28), (74, 28)); s.w((69, 28), (69, 6))
    s.w((53, 22), (58, 22)); s.R("R54", 61, 22, "r"); s.w((64, 22), (69, 22))
    s.w((53, 19), (59, 19)); s.C("C52", 61, 19, "r"); s.w((63, 19), (69, 19))
    s.w((42, 26), (42, 6), (44, 6)); s.R("R50", 47, 6, "r"); s.w((50, 6), (56, 6)); s.pot("RV5", 59, 6, "r", "3")
    s.w((62, 6), (63, 6)); s.R("R51", 66, 6, "r")
    s.w((54, 6), (54, 2), (57, 2)); s.C("C50", 59, 2, "r"); s.w((61, 2), (62, 2), (62, 6))
    s.w((59, 8), (59, 9)); s.C("C51A", 59, 11, "d", left=True); s.w((59, 9), (63, 9)); s.C("C51B", 63, 11, "d"); s.w((63, 13), (59, 13)); s.w((59, 13), (59, 15))
    s.R("R52", 56, 15, "r")
    # output
    s.C("C18", 76, 28, "r"); s.w((78, 28), (80, 28)); s.R("R21", 83, 28, "r"); s.w((86, 28), (90, 28), (90, 29))
    s.pot("RV6", 90, 32, "d", "3", -1); s.gnd(90, 35); s.w((92, 32), (99, 32)); s.pad("J_OUT", 99, 32, "r")
    s.note(40, 44, "Treble: RV4 blends NH with the low-passed signal on C15.\n"
                   "Depth: bridged-T bass boost around U3A, about +6 dB (R22) or +10 dB (R23) near 90 Hz.\n"
                   "Mid: Baxandall mid band around U3B, about +/-13 dB centred near 750 Hz. Flat gain is -1.")
    return s


def sheet_gate():
    s = Sheet("5  Noise gate sidechain")
    s.label(4, 20, "S1", "l", "sheet 2"); s.w((4, 20), (6, 20)); s.C("C60", 8, 20, "r"); s.w((10, 20), (19, 20))
    s.w((13, 20), (13, 21)); s.R("R60", 13, 24, "d"); s.flag(13, 27, "VREF", "d")
    s.opamp("U4", "B", 24, 22, plus_top=True)
    s.w((19, 24), (17, 24), (17, 36)); s.w((17, 30), (19, 30)); s.R("R61", 22, 30, "r"); s.w((25, 30), (27, 30)); s.pot("RV9", 30, 30, "r", "1")
    s.w((30, 32), (33, 32), (33, 30)); s.w((33, 30), (35, 30)); s.w((29, 22), (40, 22)); s.w((35, 22), (35, 34))
    s.w((17, 34), (24, 34)); s.C("C62", 26, 34, "r"); s.w((28, 34), (35, 34))
    s.R("R62", 17, 39, "d"); s.w((17, 42), (17, 43)); s.C("C61", 17, 45, "d"); s.gnd(17, 47)
    s.D("D10", 42, 22, "r"); s.w((44, 22), (46, 22)); s.R("R64", 49, 22, "r"); s.w((52, 22), (66, 22))
    s.w((55, 22), (55, 24)); s.C("C63", 55, 26, "d"); s.gnd(55, 28)
    s.w((60, 22), (60, 23)); s.R("R63", 60, 26, "d"); s.flag(60, 29, "VREF", "d")
    s.T(58, 20.8, "ENV", color="#070", weight="bold")
    s.opamp("U5", "A", 71, 24)
    s.w((66, 26), (64, 26), (64, 44)); s.w((64, 44), (64, 45)); s.w((58, 44), (72, 44)); s.w((58, 44), (58, 43)); s.R("R65", 58, 40, "d"); s.flag(58, 37, "VCC")
    s.R("R66", 64, 48, "d"); s.w((64, 51), (64, 52)); s.R("R67", 64, 55, "d"); s.gnd(64, 58)
    s.R("R68B", 75, 44, "r"); s.w((78, 44), (80, 44)); s.R("R68A", 83, 44, "r"); s.w((86, 44), (88, 44), (88, 24))
    s.w((76, 24), (92, 24)); s.T(82, 22.8, "CMP", color="#070", weight="bold")
    s.R("R69", 95, 24, "r"); s.w((98, 24), (100, 24)); s.D("D11", 102, 24, "l"); s.w((104, 24), (118, 24)); s.label(118, 24, "NGATE", "r", "sheet 3")
    s.w((108, 24), (108, 25)); s.R("R70", 108, 28, "d"); s.w((112, 24), (112, 26)); s.C("C65", 112, 28, "d")
    s.w((108, 31), (108, 32), (112, 32), (112, 30)); s.flag(110, 32, "VREF", "d")
    s.opamp("U5", "B", 100, 48, plus_top=True)
    s.w((95, 46), (93, 46), (93, 44)); s.flag(93, 44, "VREF")
    s.w((95, 50), (93, 50), (93, 54), (107, 54), (107, 48), (105, 48))
    s.T(100, 56, "unused half, parked as a follower", size=5.5, color="#555")
    s.note(4, 62, "U4B amplifies the clean signal from the input stage (RV9 GATE sets the sensitivity).\n"
                  "D10/C63 hold its peak as ENV. U5A compares ENV with a reference just above VREF (R65/R66/R67), with hysteresis.\n"
                  "Playing: CMP goes low and pulls Q1's gate down through R69/D11, so Q1 is off and the signal passes.\n"
                  "Silent: CMP goes high, D11 blocks, R70 lets the gate rise to VREF over about 50 ms and Q1 mutes node NH.")
    return s


def sheet_boost():
    s = Sheet("6  Boost section (stands alone: BI pad in, BO pad out)")
    s.pad("J_BIN", 6, 28, "l"); s.w((6, 28), (13, 28)); s.w((10, 28), (10, 29)); s.R("R80", 10, 32, "d"); s.gnd(10, 35)
    s.C("C80", 15, 28, "r"); s.w((17, 28), (22, 28)); s.w((20, 28), (20, 27)); s.R("R81", 20, 24, "d"); s.flag(20, 21, "VREF")
    s.R("R82", 25, 28, "r"); s.w((28, 28), (35, 28)); s.w((29, 28), (29, 29)); s.C("C81", 29, 31, "d"); s.gnd(29, 33)
    s.opamp("U7", "A", 40, 30, plus_top=True)
    # level: RV7 is the feedback resistor
    s.w((35, 32), (33, 32), (33, 38), (37, 38)); s.pot("RV7", 40, 38, "r", "1")
    s.w((40, 40), (43, 40), (43, 38)); s.w((43, 38), (47, 38)); s.w((47, 43), (47, 30), (45, 30))
    s.w((33, 38), (33, 43), (38, 43)); s.C("C85", 40, 43, "r"); s.w((42, 43), (47, 43))
    # voice: R83 with the capacitance chosen by SW3 sets where the boost starts
    s.w((33, 43), (33, 47)); s.R("R83", 33, 50, "d"); s.w((33, 53), (33, 56)); s.C("C82", 33, 58, "d", left=True); s.flag(33, 60, "VREF", "d")
    s.w((33, 54), (36, 54)); s.w((36, 54), (38, 54))
    s.sw("SW3", 41, 54, "r", (25, 0, "1 = mid hump   centre = tight   3 = flat", "left"))
    s.w((44, 52), (50, 52)); s.C("C83", 52, 52, "r"); s.w((44, 56), (50, 56)); s.C("C84", 52, 56, "r")
    s.w((54, 52), (57, 52), (57, 58)); s.w((54, 56), (57, 56)); s.flag(57, 58, "VREF", "d")
    s.R("R84", 47, 47, "r"); s.w((50, 47), (50, 52)); s.R("R85", 47, 61, "r"); s.w((50, 61), (50, 56))
    s.w((44, 47), (36, 47), (36, 61), (44, 61))
    # output
    s.w((47, 30), (52, 30)); s.C("C86", 54, 30, "r"); s.w((56, 30), (58, 30)); s.R("R86", 61, 30, "r"); s.w((64, 30), (72, 30))
    s.w((68, 30), (68, 31)); s.R("R87", 68, 34, "d"); s.gnd(68, 37); s.pad("J_BOUT", 72, 30, "r")
    s.opamp("U7", "B", 92, 48, plus_top=True)
    s.w((87, 46), (85, 46), (85, 44)); s.flag(85, 44, "VREF")
    s.w((87, 50), (85, 50), (85, 54), (99, 54), (99, 48), (97, 48))
    s.T(92, 56, "unused half, parked as a follower", size=5.5, color="#555")
    s.note(4, 66, "Clean boost with its own footswitch; it works with the preamp on or off.\n"
                  "Gain above the corner = 1 + RV7 / R83: unity (RV7 at zero) to about +21 dB. Below the corner the gain falls back to unity.\n"
                  "Corner = 1 / (2 pi R83 C): C82 alone 1.6 kHz (tight), C82 + C83 800 Hz (mid hump), C82 + C84 16 Hz (flat, full range).\n"
                  "R84/R85 keep the switched capacitors charged so the toggle does not pop.")
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
    sheets = [sheet_power(), sheet_input(), sheet_clip(), sheet_eq(), sheet_gate(), sheet_boost()]
    errs = check(sheets)
    for e in errs:
        print("MISMATCH:", e)
    if errs and "--force" not in sys.argv:
        raise SystemExit(f"{len(errs)} mismatches against design.py; nothing written")
    render(sheets, os.path.join(os.path.dirname(HERE), "docs"))
    print("schematic matches design.py:", len(PARTS), "parts on", len(sheets), "sheets")


if __name__ == "__main__":
    main()
