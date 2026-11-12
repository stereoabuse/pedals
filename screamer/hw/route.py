"""Grid autorouter (A* maze router) for the pedal board.

Reads pads.json, writes routes.json. Three routing layers (F, In2, B); In1 is a solid
ground plane. GND is not routed as traces: each GND SMD pad gets a short stub and a via
to the plane; through-hole GND pads tie into the planes directly.
"""
import heapq, json, math, os, sys, time
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "pads.json")))
O, RULES = D["outline"], D["rules"]
G = 0.2
TRACK = 0.2
CLEAR = RULES["clear"]
VIA_R = RULES["via"] / 2
X0, X1, YT, YB = O["X0"], O["X1"], O["YT"], O["YB"]
W = int(round((X1 - X0) / G)) + 1
H = int(round((YB - YT) / G)) + 1
NL = 3
LAYERS = ["F.Cu", "In2.Cu", "B.Cu"]
N = W * H
EDGE = 0.5 + TRACK / 2 + 0.06
PAD_KO = CLEAR + TRACK / 2 + 0.02
LAYER_COST = (1.0, 1.6, 1.0)
VIA_COST = 12.0
POWER = ("VREF", "V9")


def cell(x, y):
    return int(round((x - X0) / G)), int(round((y - YT) / G))


def xy(i, j):
    return X0 + i * G, YT + j * G


def inside_board(x, y, m):
    if x < X0 + m or x > X1 - m or y < YT + m or y > YB - m:
        return False
    r = 1.5                                   # rounded corners
    for cx, cy in ((X0, YT), (X1, YT), (X1, YB), (X0, YB)):
        ax = cx + r if cx == X0 else cx - r
        ay = cy + r if cy == YT else cy - r
        if abs(x - cx) < r and abs(y - cy) < r and math.hypot(x - ax, y - ay) > r - m:
            return False
    return True


def disc(radius):
    k = int(radius / G) + 1
    return [(di, dj) for di in range(-k, k + 1) for dj in range(-k, k + 1) if math.hypot(di, dj) * G <= radius + 1e-6]


TRACK_KO = disc(TRACK + CLEAR)                 # other-net track centres must stay out
VIA_KO = disc(VIA_R + CLEAR + TRACK / 2)
BLOCK3 = [(di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1)]


class Router:
    def __init__(self):
        self.occ = [array("h", [0]) * N for _ in range(NL)]
        for j in range(H):
            for i in range(W):
                x, y = xy(i, j)
                if not inside_board(x, y, EDGE):
                    for L in range(NL):
                        self.occ[L][j * W + i] = -1
        self.netid = {}
        self.pads = D["pads"]
        for p in self.pads:
            p["nid"] = self.nid(p["net"]) if p["net"] else -1
        for p in self.pads:
            self.mark_pad(p)
        self.segs, self.vias = [], []
        self.netcells = {}

    def nid(self, name):
        if name not in self.netid:
            self.netid[name] = len(self.netid) + 1
        return self.netid[name]

    def mark(self, L, i, j, n):
        if 0 <= i < W and 0 <= j < H:
            k = j * W + i
            o = self.occ[L][k]
            if o == 0:
                self.occ[L][k] = n
            elif o != n:
                self.occ[L][k] = -1

    def mark_pad(self, p):
        hw, hh = p["w"] / 2 + PAD_KO, p["h"] / 2 + PAD_KO
        i0, j0 = cell(p["x"] - hw, p["y"] - hh)
        i1, j1 = cell(p["x"] + hw, p["y"] + hh)
        layers = range(NL) if p["tht"] else (0,)
        rr = p["w"] / 2 + PAD_KO
        for j in range(j0 - 1, j1 + 2):
            for i in range(i0 - 1, i1 + 2):
                x, y = xy(i, j)
                if p["round"]:
                    if math.hypot(x - p["x"], y - p["y"]) > rr:
                        continue
                elif abs(x - p["x"]) > hw or abs(y - p["y"]) > hh:
                    continue
                for L in layers:
                    self.mark(L, i, j, p["nid"])

    def pad_cells(self, p):
        """Grid cells (all usable layers) from which a track can start on this pad."""
        n = p["nid"]
        best = None
        ci, cj = cell(p["x"], p["y"])
        hw, hh = max(p["w"] / 2 - 0.1, 0.05), max(p["h"] / 2 - 0.1, 0.05)
        for dj in range(-6, 7):
            for di in range(-6, 7):
                i, j = ci + di, cj + dj
                x, y = xy(i, j)
                if abs(x - p["x"]) > hw + 1e-6 or abs(y - p["y"]) > hh + 1e-6:
                    continue
                if not (0 <= i < W and 0 <= j < H) or self.occ[0][j * W + i] != n:
                    continue
                d = math.hypot(x - p["x"], y - p["y"])
                if best is None or d < best[0]:
                    best = (d, i, j)
        if best is None:
            return []
        _, i, j = best
        layers = range(NL) if p["tht"] else (0,)
        return [(L, i, j) for L in layers if self.occ[L][j * W + i] == n]

    def via_ok(self, i, j, n):
        for L in range(NL):
            occ = self.occ[L]
            for di, dj in BLOCK3:
                o = occ[(j + dj) * W + i + di]
                if o != 0 and o != n:
                    return False
        return True

    def astar(self, n, sources, targets, hint, cost_mul=LAYER_COST, limit=600000):
        """sources/targets: iterables of (L, i, j). Returns path list or None."""
        tset = set(L * N + j * W + i for L, i, j in targets)
        hx, hy = hint
        occs = self.occ
        g = {}
        heap = []
        for L, i, j in sources:
            k = L * N + j * W + i
            g[k] = 0.0
            heapq.heappush(heap, (max(abs(i - hx), abs(j - hy)), 0.0, k, -1))
        came = {}
        steps = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                 (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142))
        count = 0
        while heap:
            f, gk, k, prev = heapq.heappop(heap)
            if gk > g.get(k, 1e18):
                continue
            if k not in came:
                came[k] = prev
            if k in tset:
                path = []
                while k != -1:
                    L, r = divmod(k, N); j, i = divmod(r, W)
                    path.append((L, i, j)); k = came[k]
                return path[::-1]
            count += 1
            if count > limit:
                return None
            L, r = divmod(k, N); j, i = divmod(r, W)
            occ = occs[L]; mul = cost_mul[L]
            for di, dj, c in steps:
                i2, j2 = i + di, j + dj
                if not (0 <= i2 < W and 0 <= j2 < H):
                    continue
                k2r = j2 * W + i2
                o = occ[k2r]
                if o != 0 and o != n:
                    continue
                if di and dj:
                    o1 = occ[j * W + i2]; o2 = occ[j2 * W + i]
                    if (o1 != 0 and o1 != n) or (o2 != 0 and o2 != n):
                        continue
                k2 = L * N + k2r
                g2 = gk + c * mul
                if g2 < g.get(k2, 1e18):
                    g[k2] = g2
                    dx, dy = abs(i2 - hx), abs(j2 - hy)
                    h = (dx + dy) - 0.5858 * min(dx, dy)
                    heapq.heappush(heap, (g2 + h, g2, k2, k))
            if 1 <= i < W - 1 and 1 <= j < H - 1 and self.via_ok(i, j, n):
                for L2 in range(NL):
                    if L2 == L:
                        continue
                    k2 = L2 * N + r
                    g2 = gk + VIA_COST
                    if g2 < g.get(k2, 1e18):
                        g[k2] = g2
                        dx, dy = abs(i - hx), abs(j - hy)
                        heapq.heappush(heap, (g2 + (dx + dy) - 0.5858 * min(dx, dy), g2, k2, k))
        return None

    def commit(self, n, name, path):
        cells = self.netcells.setdefault(n, set())
        for a, b in zip(path, path[1:]):
            if a[0] != b[0]:
                i, j = a[1], a[2]
                x, y = xy(i, j)
                self.vias.append((round(x, 3), round(y, 3), name))
                for L in range(NL):
                    for di, dj in VIA_KO:
                        self.mark(L, i + di, j + dj, n)
                    cells.add((L, i, j))
            else:
                xa, ya = xy(a[1], a[2]); xb, yb = xy(b[1], b[2])
                self.segs.append([round(xa, 3), round(ya, 3), round(xb, 3), round(yb, 3), LAYERS[a[0]], name])
        for L, i, j in path:
            for di, dj in TRACK_KO:
                self.mark(L, i + di, j + dj, n)
            cells.add((L, i, j))

    def stub(self, p, c, name):
        x, y = xy(c[1], c[2])
        if abs(x - p["x"]) > 1e-6 or abs(y - p["y"]) > 1e-6:
            for L in (range(NL) if p["tht"] else (0,)):
                if L == c[0]:
                    self.segs.append([p["x"], p["y"], round(x, 3), round(y, 3), LAYERS[L], name])

    def fanout_gnd(self):
        n = self.netid["GND"]
        fails = []
        for p in self.pads:
            if p["net"] != "GND" or p["tht"]:
                continue
            src = self.pad_cells(p)
            if not src:
                fails.append(p); continue
            hw, hh = p["w"] / 2 + VIA_R + 0.1, p["h"] / 2 + VIA_R + 0.1
            # Dijkstra on layer 0 to the nearest spot where a via fits clear of the pad
            occ = self.occ[0]
            start = src[0]
            g = {(start[1], start[2]): 0.0}
            came = {(start[1], start[2]): None}
            heap = [(0.0, start[1], start[2])]
            found = None
            while heap:
                d, i, j = heapq.heappop(heap)
                if d > g[(i, j)]:
                    continue
                if d > 30:
                    break
                x, y = xy(i, j)
                if (abs(x - p["x"]) > hw or abs(y - p["y"]) > hh) and 1 <= i < W - 1 and 1 <= j < H - 1 \
                        and self.via_ok(i, j, n) and not self.in_any_pad(x, y):
                    found = (i, j); break
                for di, dj, c in ((1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1)):
                    i2, j2 = i + di, j + dj
                    if not (0 <= i2 < W and 0 <= j2 < H):
                        continue
                    o = occ[j2 * W + i2]
                    if o != 0 and o != n:
                        continue
                    if d + c < g.get((i2, j2), 1e18):
                        g[(i2, j2)] = d + c; came[(i2, j2)] = (i, j)
                        heapq.heappush(heap, (d + c, i2, j2))
            if not found:
                fails.append(p); continue
            path = []
            k = found
            while k is not None:
                path.append((0, k[0], k[1])); k = came[k]
            path = path[::-1] + [(1, found[0], found[1])]
            self.stub(p, path[0], "GND")
            self.commit(n, "GND", path)
        return fails

    def in_any_pad(self, x, y):
        for q in self.pads:
            if not q["tht"] and abs(x - q["x"]) <= q["w"] / 2 + VIA_R + 0.05 and abs(y - q["y"]) <= q["h"] / 2 + VIA_R + 0.05:
                return True
        return False

    def route_net(self, name, pads):
        n = self.netid[name]
        cost = (2.5, 1.2, 1.0) if name in POWER else LAYER_COST
        cells = self.netcells.setdefault(n, set())
        todo = list(pads)
        first = todo.pop(0)
        c0 = self.pad_cells(first)
        if not c0:
            return [(name, first["ref"], "no access")]
        self.stub(first, c0[0], name)
        cells.update(c0)
        fails = []
        while todo:
            # nearest unconnected pad to the tree (by pad centre to any tree cell)
            best = None
            tree = list(cells)
            for p in todo:
                ci, cj = cell(p["x"], p["y"])
                d, t = min(((abs(ci - i) + abs(cj - j)), (L, i, j)) for L, i, j in tree)
                if best is None or d < best[0]:
                    best = (d, p, t)
            _, p, near = best
            todo.remove(p)
            src = self.pad_cells(p)
            if not src:
                fails.append((name, p["ref"] + "." + p["num"], "no access")); continue
            path = self.astar(n, src, tree, (near[1], near[2]), cost)
            if path is None:
                fails.append((name, p["ref"] + "." + p["num"], "no path")); continue
            self.stub(p, path[0], name)
            self.commit(n, name, path)
            cells.update(src)
        return fails


def main():
    t0 = time.time()
    R = Router()
    bynet = {}
    for p in R.pads:
        if p["net"] and p["net"] != "GND":
            bynet.setdefault(p["net"], []).append(p)
    gfails = R.fanout_gnd()
    print("GND fanout: %d vias, %d failed" % (len(R.vias), len(gfails)), [f"{p['ref']}.{p['num']}" for p in gfails])

    def span(ps):
        return (max(p["x"] for p in ps) - min(p["x"] for p in ps)) + (max(p["y"] for p in ps) - min(p["y"] for p in ps))
    order = sorted((n for n in bynet if len(bynet[n]) > 1), key=lambda n: (n in POWER, span(bynet[n])))
    fails = []
    for name in order:
        f = R.route_net(name, bynet[name])
        fails += f
    print("routed %d nets, %d segments, %d vias, %d failures in %.0fs" % (len(order), len(R.segs), len(R.vias), len(fails), time.time() - t0))
    for f in fails:
        print("  FAIL", f)
    # merge collinear segments
    merged = []
    for s in R.segs:
        if merged:
            m = merged[-1]
            if m[4] == s[4] and m[5] == s[5] and abs(m[2] - s[0]) < 1e-6 and abs(m[3] - s[1]) < 1e-6:
                d1 = (m[2] - m[0], m[3] - m[1]); d2 = (s[2] - s[0], s[3] - s[1])
                if abs(d1[0] * d2[1] - d1[1] * d2[0]) < 1e-9 and d1[0] * d2[0] + d1[1] * d2[1] > 0:
                    m[2], m[3] = s[2], s[3]
                    continue
        merged.append(list(s))
    R.vias = [list(v) for v in dict.fromkeys(map(tuple, R.vias))]     # two pads can share one fanout via
    json.dump(dict(segs=merged, vias=R.vias, track=TRACK, fails=[list(f) for f in fails] + [["GND", p["ref"], "fanout"] for p in gfails]),
              open(os.path.join(HERE, "routes.json"), "w"))
    return len(fails) + len(gfails)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
