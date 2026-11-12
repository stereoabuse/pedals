"""Placement: big parts are placed by hand, small two-pad parts by simulated annealing
on a slot grid (minimising half-perimeter wire length). Writes placement.json."""
import json, math, os, random
from design import parts

HERE = os.path.dirname(os.path.abspath(__file__))
FP = json.load(open(os.path.join(HERE, "fpinfo.json")))

# ---- board geometry (KiCad mm, SMD-side view) ----
X0, X1, YT, YM, YB = 59.0, 141.0, 68.0, 103.5, 130.5   # main band + legs
LEG_L, LEG_R = 85.0, 115.0                             # notch between these x below YM

def on_board(x0, y0, x1, y1, m=0.6):
    if x0 < X0 + m or x1 > X1 - m or y0 < YT + m or y1 > YB - m:
        return False
    if y1 > YM - m and not (x1 <= LEG_L - m or x0 >= LEG_R + m):
        return False
    return True

POT_DY = 16.0
POTS = {"RV2": (68.5, 77), "RV3": (89.5, 77), "RV4": (110.5, 77), "RV6": (131.5, 77),
        "RV1": (68.5, 108), "RV5": (131.5, 108)}
SWS = {"SW1": (92.0, 98.5), "SW2": (108.0, 98.5)}
LEDS = {"LED5": (80.5, 124.0), "LED6": (119.5, 124.0)}
PADY = 128.5
WPADS = {"J_IN": 61.5, "J_G2": 64.04, "J_L1": 66.58,
         "J_L1B": 118.18, "J_L2": 120.72, "J_BST": 123.26, "J_G3": 125.8,
         "J_9V": 128.34, "J_G1": 130.88, "J_G4": 135.96, "J_OUT": 138.5}

def tht_pads():
    """ref -> {pad: (x, y, pad_dia, drill)}"""
    out = {}
    for r, (x, y) in POTS.items():
        out[r] = {"1": (x + 5, y + POT_DY, 2.2, 1.3), "2": (x, y + POT_DY, 2.2, 1.3), "3": (x - 5, y + POT_DY, 2.2, 1.3)}
    for r, (x, y) in SWS.items():
        out[r] = {"1": (x - 4.7, y, 3.5, 2.3), "2": (x, y, 3.5, 2.3), "3": (x + 4.7, y, 3.5, 2.3)}
    for r, (x, y) in LEDS.items():
        out[r] = {"1": (x - 1.27, y, 1.7, 0.9), "2": (x + 1.27, y, 1.7, 0.9)}   # 1 = cathode
    for r, x in WPADS.items():
        out[r] = {"1": (x, PADY, 2.0, 1.1)}
    return out

# ref: (x, y, rot)
FIXED = {
    "U1": (71.0, 112.0, 0), "U2": (80.0, 79.0, 0), "U3": (124.0, 79.0, 0),
    "U4": (100.0, 76.0, 0), "U5": (100.0, 86.0, 0), "U6": (120.5, 109.0, 0),
    "RV7": (81.5, 108.0, 0), "RV8": (87.5, 72.5, 0), "RV9": (108.0, 72.5, 0),
    "Q1": (100.0, 93.5, 0), "Q2": (81.5, 114.6, 0),
    "JP1": (128.0, 117.5, 0), "JP2": (100.0, 99.6, 90),
    "C20": (136.8, 106.0, 90), "C27": (136.8, 115.6, 90), "C28": (137.0, 73.5, 90),
}
SLOT_W, SLOT_H = 2.6, 4.0
IGNORE = {"GND", "VCC", "VREF", "V9"}
AFFINITY = [("C6", "U1", "8"), ("C7", "U2", "8"), ("C10", "U3", "8"), ("C29", "U4", "8"),
            ("C30", "U5", "8"), ("C21", "U6", "8"), ("TP1", "C28", "1"), ("TP2", "U4", "1"),
            ("TP3", "C20", "1"), ("C25", "U4", "3"), ("R32", "U4", "3"), ("R33", "U4", "3")]


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


def main(seed=1, iters=400000):
    rnd = random.Random(seed)
    ps = {p["ref"]: p for p in parts()}
    tht = tht_pads()
    pinpos = {}                      # (ref, pad) -> (x, y) for fixed things
    blocks = []                      # rect keepouts
    circles = []                     # (x, y, r) keepouts
    for r, pads in tht.items():
        for pad, (x, y, d, _) in pads.items():
            pinpos[(r, pad)] = (x, y)
            circles.append((x, y, d / 2 + 0.45))
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

    LONG = {"D", "C12", "TP"}
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
    weight = {n: (3.0 if n.startswith("__aff") else 1.0) for n in nets}
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
           "pots": POTS, "sws": SWS, "leds": LEDS,
           "outline": dict(X0=X0, X1=X1, YT=YT, YM=YM, YB=YB, LEG_L=LEG_L, LEG_R=LEG_R)}
    json.dump(out, open(os.path.join(HERE, "placement.json"), "w"), indent=1)
    return total


if __name__ == "__main__":
    main()
