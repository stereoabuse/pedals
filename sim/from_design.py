"""Build a SPICE deck straight from hw/design.py so the simulated circuit is the PCB netlist."""
import re, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hw"))
from design import parts
from circuit import MODELS, taper
from run import ngspice

def val(v):
    v = v.split()[0]
    m = re.fullmatch(r"([\d.]+)([RkMpnu]?)", v)
    return float(m.group(1)) * {"": 1, "R": 1, "k": 1e3, "M": 1e6, "p": 1e-12, "n": 1e-9, "u": 1e-6}[m.group(2)]

POTS = {"RV1": ("tight", "C", 100e3), "RV2": ("gain", "A", 1e6), "RV3": ("pres", "C", 10e3),
        "RV4": ("treble", "B", 100e3), "RV5": ("mid", "B", 100e3), "RV6": ("vol", "A", 10e3),
        "RV7": ("boost_trim", "B", 20e3), "RV8": ("trim", "B", 100e3), "RV9": ("gate_trim", "B", 100e3)}

def deck(extra="", vcc=16.5, boost=False, clip="stock", depth="off", gate=True, **pos):
    s = dict(tight=.3, gain=.5, pres=.5, treble=.6, mid=.5, vol=.5, boost_trim=0, trim=.3, gate_trim=.5)
    s.update(pos)
    L = [MODELS, f"VCC VCC 0 {vcc}", "V9 V9 0 9", f"RBST BC 0 {1e9 if boost else 1e-3}"]
    for p in parts():
        r, k, n = p["ref"], p["kind"], p["nets"]
        n = ["0" if x == "GND" else x for x in n]
        if k == "R": L.append(f"R{r} {n[0]} {n[1]} {val(p['value'])}")
        elif k in ("C", "C08", "C12", "CP"): L.append(f"C{r} {n[0]} {n[1]} {val(p['value'])}")
        elif k == "D": L.append(f"D{r} {n[0]} {n[1]} {'D4148' if '4148' in p['value'] else 'DSCH'}")
        elif k == "LED": L.append(f"D{r} {n[0]} {n[1]} LEDR")
        elif k == "LEDT": L.append(f"D{r} {n[0]} {n[1]} LEDR")
        elif k == "Q": L.append(f"J{r} {n[0]} {n[2]} {n[1]} J4393")
        elif k == "U" and p["value"] in ("TL072", "LM358"):
            L.append(f"X{r}A {n[2]} {n[1]} {n[7]} {n[3]} {n[0]} OPA")
            L.append(f"X{r}B {n[4]} {n[5]} {n[7]} {n[3]} {n[6]} OPA")
        elif k in ("POT", "RV"):
            name, tp, rt = POTS[r]
            a = taper(s[name], tp)
            L.append(f"R{r}a {n[0]} {n[1]} {max(rt*a, 1)}")
            L.append(f"R{r}b {n[1]} {n[2]} {max(rt*(1-a), 1)}")
        elif k == "SW":
            st = {"SW1": {"stock": 0, "open": 1, "sat": 2}[clip], "SW2": {"mid": 0, "off": 1, "deep": 2}[depth]}[r]
            L.append(f"R{r}a {n[0]} {n[1]} {1e-3 if st == 0 else 1e9}")
            L.append(f"R{r}b {n[2]} {n[1]} {1e-3 if st == 2 else 1e9}")
        elif k == "JP3": L.append(f"R{r} {n[0]} {n[1]} 1m")
        elif k == "JP2": L.append(f"R{r} {n[0]} {n[1]} {1e-3 if gate else 1e9}")
    L.append(".model DSCH D(IS=1u N=1.05 RS=0.1)")
    L.append("RLOAD OUT 0 1Meg")
    L += [f"RFL{i} {n} 0 1G" for i, n in enumerate(("CP", "CN", "VNEG", "CX", "VIN"))]
    return "* from design\n" + "\n".join(L) + "\n" + extra + "\n.end\n"

F = (40,80,150,300,500,750,1000,1500,2500,4000,6000,10000)
def ac(node, **kw):
    meas = "\n".join(f"meas ac g{i} find vdb({node}) at={f}" for i, f in enumerate(F))
    out = ngspice(deck(extra=f"VIN IN 0 dc 0 ac 1\n.control\nac dec 40 10 40k\n{meas}\n.endc", **kw))
    v = [float(m) for m in re.findall(r"^g\d+\s*=\s*(\S+)", out, re.M)]
    if len(v) != len(F): print(out[-2500:]); raise SystemExit(1)
    return v
def rel(a, b, **kw): return [x - y for x, y in zip(ac(a, **kw), ac(b, **kw))]
def show(t, rows):
    print(f"\n{t}\n{'':>14}" + "".join(f"{f:>7}" for f in F))
    for n, v in rows: print(f"{n:>14}" + "".join(f"{x:7.1f}" for x in v))

if __name__ == "__main__":
    g = dict(gate=False)
    show("S1: boost", [("off", ac("S1", **g)), ("on trim0", ac("S1", boost=True, **g)), ("on trim1", ac("S1", boost=True, boost_trim=1, **g))])
    show("Tight U1BP", [(f"{t}", ac("U1BP", tight=t, **g)) for t in (0, .25, .5, .75, 1)])
    show("Gain to S4 (clip open)", [(f"{x}", ac("S4", gain=x, clip="open", **g)) for x in (0, .5, 1)])
    show("Mid NH->S6", [(f"{m}", rel("S6", "NH", mid=m, treble=1, **g)) for m in (0, .25, .5, .75, 1)])
    show("Treble NH->S6", [(f"{m}", rel("S6", "NH", treble=m, **g)) for m in (0, .5, 1)])
    show("Depth NH->S6", [(d, rel("S6", "NH", depth=d, treble=1, **g)) for d in ("off", "mid", "deep")])
    show("Presence S4->NH", [(f"{m}", rel("NH", "S4", pres=m, gain=0, clip="open", **g)) for m in (0, .5, 1)])
    # transient: gate + boost switching
    src = "BIN IN 0 V=0.002*sin(6.2832*220*time) + (time>0.15 ? 0.1*exp(-(time-0.15)/0.08)*sin(6.2832*220*time) : 0)"
    wins = [("pre", .10, .15), ("note", .17, .25), ("tail", .45, .55), ("late", .85, .95)]
    for gt in (0.2, 0.6):
        meas = "".join(f"meas tran {n}_{w}_mx max v({n}) from={a} to={b}\nmeas tran {n}_{w}_mn min v({n}) from={a} to={b}\n"
                       for n in ("NH", "CMP", "NGATE", "OUT", "BG") for w, a, b in wins)
        out = ngspice(deck(extra=f"{src}\n.control\ntran 10u 0.95\n{meas}\n.endc", gain=1, gate_trim=gt, vol=1))
        d = dict((k.lower(), float(v)) for k, v in re.findall(r"^(\w+_m[xn])\s*=\s*(\S+)", out, re.M))
        if not d: print(out[-2500:]); break
        print(f"\ngate_trim={gt}")
        for n in ("nh", "cmp", "ngate", "out", "bg"):
            print(f"  {n:>6}: " + "  ".join(f"{w}[{d[f'{n}_{w}_mn']:6.2f},{d[f'{n}_{w}_mx']:6.2f}]" for w, _, _ in wins))
