"""Report the closest approach between the high-impedance input nets and the
high-level in-phase nets (the pairs that could make a high-gain circuit squeal)."""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(HERE, "pads.json")))["pads"]
R = json.load(open(os.path.join(HERE, "routes.json")))
INPUT = {"IN", "INA", "INP"}
HOT = {"PO", "S", "CO", "CA", "TB", "V1", "MO", "MK", "LV", "LW", "OUT"}

def pts(nets):
    out = []
    for p in P:
        if p["net"] in nets:
            out.append((p["x"], p["y"], p["net"], p["ref"]))
    for x0, y0, x1, y1, layer, net in R["segs"]:
        if net in nets:
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.2))
            for k in range(n + 1):
                out.append((x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, net, layer))
    for x, y, net in R["vias"]:
        if net in nets:
            out.append((x, y, net, "via"))
    return out

a, b = pts(INPUT), pts(HOT)
best = {}
for xa, ya, na, la in a:
    for xb, yb, nb, lb in b:
        d = math.hypot(xa - xb, ya - yb)
        if d < best.get((na, nb), (1e9,))[0]:
            best[(na, nb)] = (d, (round(xa, 1), round(ya, 1)), (round(xb, 1), round(yb, 1)), la, lb)
for k, v in sorted(best.items(), key=lambda kv: kv[1][0])[:12]:
    print("%-5s %-5s %5.1f mm  %s %s  [%s / %s]" % (k[0], k[1], v[0], v[1], v[2], v[3], v[4]))
