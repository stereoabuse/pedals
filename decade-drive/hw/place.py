"""Placement: big parts are placed by hand, small two-pad parts by simulated annealing
on a slot grid (minimising half-perimeter wire length). Writes placement.json."""
import json, math, os, random
from design import parts

HERE = os.path.dirname(os.path.abspath(__file__))
FP = json.load(open(os.path.join(HERE, "fpinfo.json")))

# ---- board geometry (KiCad mm, SMD-side view; front-panel x = 100 - x, y = 100 - y) ----
X0, X1, YT, YM, YB = 53.0, 147.0, 60.0, 140.0, 159.5   # main area + legs either side of the footswitch
LEG_L, LEG_R = 86.0, 114.0                             # notch between these x below YM

def on_board(x0, y0, x1, y1, m=0.6):
    if x0 < X0 + m or x1 > X1 - m or y0 < YT + m or y1 > YB - m:
        return False
    if y1 > YM - m and not (x1 <= LEG_L - m or x0 >= LEG_R + m):
        return False
    return True

POT_DY = 16.0
POTS = {"RV1": (136.0, 141.5)}
COLS = (132.0, 116.0, 100.0, 84.0, 68.0)               # front-panel left to right
ROWS = (69.0, 86.0, 103.0, 120.0)                      # top to bottom
SWS = {f"SW{5 * j + i + 1}": (COLS[i], ROWS[j]) for j in range(4) for i in range(5)}
SW_DY = 4.7                                            # lug pitch; levers move up and down
LEDS = {"LED1": (100.0, 133.0)}
PADY = 157.0
WPADS = {"J_IN": 57.0, "J_G2": 59.54, "J_L": 78.0, "J_G4": 80.54,
         "J_OUT": 117.0, "J_G3": 119.54, "J_G1": 122.08, "J_9V": 124.62}
CREDIT = (100.0, 137.6)                                # "stereoabuse", SMD side
KEEPOUT = [(94.0, 136.6, 106.0, 138.7)]
SW_LABEL_DX = 3.3                                      # toggle names run vertically beside the lugs, SMD side

def label_box(text, x, y, size, vertical=False):
    w, h = len(text) * size * 0.85 + 0.2, size + 0.3
    if vertical:
        w, h = h, w
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)

# silkscreen labels on the SMD side that parts must stay clear of
POT_LABEL = {"RV1": "LEVEL"}
TRIM_LABEL = {"RV2": ("THRESH", 4.1), "RV3": ("TUNE", 4.1)}

def tht_pads():
    """ref -> {pad: (x, y, pad_dia, drill)}"""
    out = {}
    for r, (x, y) in POTS.items():
        out[r] = {"1": (x + 5, y + POT_DY, 2.2, 1.3), "2": (x, y + POT_DY, 2.2, 1.3), "3": (x - 5, y + POT_DY, 2.2, 1.3)}
    for r, (x, y) in SWS.items():                      # 1 = lower lug on the panel, the one the lever-up position connects
        out[r] = {"1": (x, y + SW_DY, 3.5, 2.3), "2": (x, y, 3.5, 2.3), "3": (x, y - SW_DY, 3.5, 2.3)}
    for r, (x, y) in LEDS.items():
        out[r] = {"1": (x - 1.27, y, 1.7, 0.9), "2": (x + 1.27, y, 1.7, 0.9)}   # 1 = cathode
    for r, x in WPADS.items():
        out[r] = {"1": (x, PADY, 2.0, 1.1)}
    return out

# ref: (x, y, rot)
FIXED = {
    "U1": (62.0, 146.5, 0),                              # input buffer + VREF, by the IN pad
    "U2": (124.0, 77.5, 0),                              # gain stage + summer, by the GAIN toggles
    "U3": (92.0, 77.5, 0),                               # drive stage + octave rectifier
    "U4": (76.0, 94.5, 0),                               # buffer after the clipper + gate
    "U5": (76.0, 111.5, 0),                              # resonator integrators, by the PITCH toggles
    "U6": (108.0, 130.5, 0),                             # resonator inverter + mixer
    "Q1": (60.0, 120.0, 0),
    "RV2": (60.0, 77.5, 0), "RV3": (60.0, 103.0, 0),
}
SLOT_W, SLOT_H = 2.6, 3.7
IGNORE = {"GND", "VCC", "VREF"}
QUIET = {"IN", "INA", "INP", "PN", "SN", "DP", "CN", "T", "N1", "N2", "N3", "MN", "GN", "HN"}   # keep these nets short
AFFINITY = [("C4", "U1", "8"), ("C5", "U2", "8"), ("C6", "U3", "8"), ("C7", "U4", "8"), ("C8", "U5", "8"), ("C9", "U6", "8"),
            ("C3", "U1", "5"), ("R2", "U1", "5"), ("R3", "U1", "5"), ("TP2", "U1", "7"), ("C37", "U3", "8")]


def rot_pt(x, y, rot):
    """KiCad rotation (degrees CCW on screen, y down)."""
    a = math.radians(rot)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def fixed_pad_pos(kind, x, y, rot):
    return {p["num"]: tuple(a + b for a, b in zip((x, y), rot_pt(p["x"], p["y"], rot))) for p in FP[kind]["pads"]}


def courtyard(kind, x, y, rot):
    l, t, r, b = FP[kind]["cy"]
    pts = [rot_pt(px, py, rot) for px, py in ((l, t), (r, t), (r, b), (l, b))]
    return (x + min(p[0] for p in pts), y + min(p[1] for p in pts), x + max(p[0] for p in pts), y + max(p[1] for p in pts))


def main(seed=4, iters=700000):
    rnd = random.Random(seed)
    ps = {p["ref"]: p for p in parts()}
    tht = tht_pads()
    pinpos = {}                      # (ref, pad) -> (x, y) for fixed things
    blocks = list(KEEPOUT)           # rect keepouts
    circles = []                     # (x, y, r) keepouts
    for r, pads in tht.items():
        for pad, (x, y, d, _) in pads.items():
            pinpos[(r, pad)] = (x, y)
            circles.append((x, y, d / 2 + 0.45))
    for r, t in POT_LABEL.items():
        blocks.append(label_box(t, POTS[r][0], POTS[r][1] + 13.2, 0.9))
    for r, (t, dy) in TRIM_LABEL.items():
        blocks.append(label_box(t, FIXED[r][0], FIXED[r][1] + dy, 0.8))
    for r, (x, y) in SWS.items():
        blocks.append(label_box(ps[r]["value"], x + SW_LABEL_DX, y, 0.9, vertical=True))
    for r, (x, y) in LEDS.items():
        blocks.append(label_box(ps[r]["value"], x, y - 2.6, 0.8))
    for r, x in WPADS.items():
        blocks.append(label_box("+9V", x, PADY - 1.9, 0.8))
    for r, (x, y, rot) in FIXED.items():
        k = ps[r]["kind"]
        for pad, pos in fixed_pad_pos(k, x, y, rot).items():
            pinpos[(r, pad)] = pos
        c = courtyard(k, x, y, rot)
        blocks.append((c[0] - 0.15, c[1] - 0.15, c[2] + 0.15, c[3] + 0.15))

    def slot_ok(cx, cy):
        x0, y0, x1, y1 = cx - SLOT_W / 2, cy - SLOT_H / 2, cx + SLOT_W / 2, cy + SLOT_H / 2
        if not on_board(x0, y0, x1, y1):
            return False
        for b in blocks:
            if x0 < b[2] and x1 > b[0] and y0 < b[3] and y1 > b[1]:
                return False
        for (px, py, pr) in circles:
            dx = max(x0 - px, 0, px - x1); dy = max(y0 - py, 0, py - y1)
            if dx * dx + dy * dy < pr * pr:
                return False
        return True

    LONG = {"D", "TP"}
    cols = int((X1 - X0 - 1.2) // SLOT_W); rows = int((YB - YT - 1.2) // SLOT_H)
    ox = X0 + ((X1 - X0) - cols * SLOT_W) / 2 + SLOT_W / 2
    oy = YT + 0.7 + SLOT_H / 2
    grid = {}                                   # (i, j) -> (x, y)
    for j in range(rows + 1):
        for i in range(cols):
            cx, cy = ox + i * SLOT_W, oy + j * SLOT_H
            if slot_ok(cx, cy):
                grid[(i, j)] = (round(cx, 3), round(cy, 3))
    keys = list(grid)
    pairs = [k for k in keys if (k[0] + 1, k[1]) in grid]
    movable = [r for r, p in ps.items() if r not in FIXED and r not in tht]
    longs = [r for r in movable if ps[r]["kind"] in LONG]
    shorts = [r for r in movable if ps[r]["kind"] not in LONG]
    print(len(keys), "slots for", len(shorts), "short +", len(longs), "long parts")

    nets = {}
    for r, p in ps.items():
        for pad, n in p["pins"].items():
            if n in IGNORE or n.startswith("NC"):
                continue
            nets.setdefault(n, []).append((r, pad))
    for i, (a_, b_, pad) in enumerate(AFFINITY):
        nets[f"__aff{i}"] = [(a_, "1"), (b_, pad)]
    weight = {n: (3.0 if n.startswith("__aff") else 6.0 if n in QUIET else 1.0) for n in nets}
    nets_of = {}
    for n, pins in nets.items():
        for r, _ in pins:
            nets_of.setdefault(r, set()).add(n)

    dpad = {r: abs(FP[ps[r]["kind"]]["pads"][0]["x"]) for r in movable}
    where, flip, occ = {}, {}, {}
    free_pairs = pairs[:]; rnd.shuffle(free_pairs)
    for r in longs:
        while True:
            k = free_pairs.pop()
            k2 = (k[0] + 1, k[1])
            if k not in occ and k2 not in occ:
                break
        where[r] = k; occ[k] = r; occ[k2] = r; flip[r] = False
    free = [k for k in keys if k not in occ]; rnd.shuffle(free)
    for r in shorts:
        k = free.pop(); where[r] = k; occ[k] = r; flip[r] = False
    is_long = set(longs)

    def center(r):
        x, y = grid[where[r]]
        return (x + SLOT_W / 2, y) if r in is_long else (x, y)

    def ppos(r, pad):
        if r in where:
            x, y = center(r)
            if len(ps[r]["pins"]) == 1:
                return (x, y)
            first = (pad == "1") != flip[r]
            if r in is_long:
                return (x - dpad[r] if first else x + dpad[r], y)
            return (x, y - dpad[r] if first else y + dpad[r])
        return pinpos[(r, pad)]

    def net_cost(n):
        xs = [ppos(r, pad) for r, pad in nets[n]]
        return weight[n] * ((max(p[0] for p in xs) - min(p[0] for p in xs)) + (max(p[1] for p in xs) - min(p[1] for p in xs)))

    cost = {n: net_cost(n) for n in nets}
    total = sum(cost.values())

    def attempt(touched, apply, undo, T):
        nonlocal total
        apply()
        new = {n: net_cost(n) for n in touched}
        d = sum(new.values()) - sum(cost[n] for n in touched)
        if d <= 0 or rnd.random() < math.exp(-d / T):
            cost.update(new); total += d
            return True
        undo()
        return False

    for it in range(iters):
        T = 8.0 * (1 - it / iters) ** 2 + 0.02
        a_ = rnd.choice(movable)
        ta = nets_of.get(a_, set())
        if rnd.random() < 0.15:
            def ap(): flip[a_] = not flip[a_]
            attempt(ta, ap, ap, T)
            continue
        if a_ in is_long:
            k = rnd.choice(pairs); k2 = (k[0] + 1, k[1])
            if any(occ.get(q) not in (None, a_) for q in (k, k2)):
                continue
            old = where[a_]
            def ap():
                del occ[old]; del occ[(old[0] + 1, old[1])]
                where[a_] = k; occ[k] = a_; occ[k2] = a_
            def un():
                del occ[k]; del occ[k2]
                where[a_] = old; occ[old] = a_; occ[(old[0] + 1, old[1])] = a_
            attempt(ta, ap, un, T)
            continue
        k = rnd.choice(keys); old = where[a_]
        b_ = occ.get(k)
        if k == old or b_ in is_long:
            continue
        touched = set(ta) | (nets_of.get(b_, set()) if b_ else set())
        def ap():
            where[a_] = k; occ[k] = a_
            if b_:
                where[b_] = old; occ[old] = b_
            else:
                del occ[old]
        def un():
            where[a_] = old; occ[old] = a_
            if b_:
                where[b_] = k; occ[k] = b_
            else:
                del occ[k]
        attempt(touched, ap, un, T)
    print("final wirelength %.0f mm" % total)
    small = {}
    for r in movable:
        x, y = center(r)
        small[r] = [round(x, 3), round(y, 3), "h" if r in is_long else "v", bool(flip[r])]
    out = {"fixed": {r: list(v) for r, v in FIXED.items()}, "small": small,
           "tht": {r: {k: list(v) for k, v in pads.items()} for r, pads in tht.items()},
           "pots": POTS, "sws": SWS, "leds": LEDS, "credit": CREDIT, "trim_label": TRIM_LABEL, "sw_label_dx": SW_LABEL_DX,
           "outline": dict(X0=X0, X1=X1, YT=YT, YM=YM, YB=YB, LEG_L=LEG_L, LEG_R=LEG_R)}
    json.dump(out, open(os.path.join(HERE, "placement.json"), "w"), indent=1)
    return total


if __name__ == "__main__":
    main()
