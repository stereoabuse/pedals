"""Build a SPICE deck straight from hw/design.py so the simulated circuit is the PCB netlist.
Run from this folder: python3 from_design.py"""
import re, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hw"))
from design import parts
from circuit import MODELS, taper
from run import ngspice

def val(v):
    m = re.fullmatch(r"([\d.]+)([RkMpnu]?)", v.split()[0])
    return float(m.group(1)) * {"": 1, "R": 1, "k": 1e3, "M": 1e6, "p": 1e-12, "n": 1e-9, "u": 1e-6}[m.group(2)]

POTS = {"RV1": ("drive", "A", 500e3), "RV2": ("ts_tone", "W", 20e3), "RV3": ("level", "B", 100e3),
        "RV4": ("sustain", "B", 100e3), "RV5": ("tone", "B", 100e3), "RV6": ("volume", "B", 100e3)}
SEL = {"11": ("12", "13", "14"), "10": ("2", "1", "15"), "9": ("5", "3", "4")}   # select pin -> (in0, in1, common)
RON = 200

def deck(extra="", ts=False, mf=False, mode="par", **pos):
    """mode: 'ts>mf', 'par' or 'mf>ts'."""
    s = dict(drive=.5, ts_tone=.5, level=.5, sustain=.5, tone=.5, volume=.5); s.update(pos)
    low = {"NTS": ts, "NMF": mf, "NAB": mode == "ts>mf", "NBA": mode == "mf>ts"}
    L = [MODELS, "VS VIN 0 9"]
    for p in parts():
        r, k, n = p["ref"], p["kind"], ["0" if x == "GND" else x for x in p["nets"]]
        if k == "R": L.append(f"R{r} {n[0]} {n[1]} {val(p['value'])}")
        elif k in ("C", "C08"): L.append(f"C{r} {n[0]} {n[1]} {val(p['value'])}")
        elif k == "D": L.append(f"D{r} {n[0]} {n[1]} {'D4148' if '4148' in p['value'] else 'DSCH'}")
        elif k == "LEDT": L.append(f"D{r} {n[0]} {n[1]} LEDR")
        elif k == "Q": L.append(f"Q{r} {n[2]} {n[0]} {n[1]} BC847C")
        elif k == "U":
            L.append(f"X{r}A {n[2]} {n[1]} {n[7]} {n[3]} {n[0]} OPA")
            L.append(f"X{r}B {n[4]} {n[5]} {n[7]} {n[3]} {n[6]} OPA")
        elif k == "U16":
            pin = p["pins"]
            for sel, (i0, i1, com) in SEL.items():
                on0 = low[pin[sel]]
                L.append(f"R{r}s{sel}a {pin[i0]} {pin[com]} {RON if on0 else 1e10}")
                L.append(f"R{r}s{sel}b {pin[i1]} {pin[com]} {1e10 if on0 else RON}")
                L.append(f"C{r}s{sel}a {pin[i0]} {pin[com]} 0.2p")      # feedthrough of the open switch
                L.append(f"C{r}s{sel}b {pin[i1]} {pin[com]} 0.2p")
        elif k == "POT":
            name, tp, rt = POTS[r]
            a = taper(s[name], tp)
            L.append(f"R{r}a {n[0]} {n[1]} {max(rt*a, 1)}")
            L.append(f"R{r}b {n[1]} {n[2]} {max(rt*(1-a), 1)}")
        elif k == "SW":
            L.append(f"R{r}a {n[0]} {n[1]} {1e-3 if mode == 'ts>mf' else 1e10}")
            L.append(f"R{r}b {n[2]} {n[1]} {1e-3 if mode == 'mf>ts' else 1e10}")
    L.append(f"RFT FT 0 {1e-3 if ts else 1e10}")
    L.append(f"RFM FM 0 {1e-3 if mf else 1e10}")
    L.append("RLOAD OUT 0 1Meg")
    return "* muff screamer\n" + "\n".join(L) + "\n" + extra + "\n.end\n"

F = (40, 80, 150, 300, 500, 750, 1000, 1500, 2500, 4000, 6000, 10000)
def ac(node="OUT", **kw):
    meas = "\n".join(f"meas ac g{i} find vdb({node}) at={f}" for i, f in enumerate(F))
    out = ngspice(deck(extra=f"VSIG IN 0 dc 0 ac 1\n.control\nac dec 40 10 40k\n{meas}\n.endc", **kw))
    v = [float(m) for m in re.findall(r"^g\d+\s*=\s*(\S+)", out, re.M)]
    if len(v) != len(F): print(out[-2500:]); raise SystemExit(1)
    return v
def rel(a, b, **kw): return [x - y for x, y in zip(ac(a, **kw), ac(b, **kw))]
def tran(nodes, amp=0.1, f=220, **kw):
    """Peak-to-peak volts at each node for a sine input of the given peak amplitude."""
    meas = "".join(f"meas tran {n}_hi max v({n}) from=60m to=100m\nmeas tran {n}_lo min v({n}) from=60m to=100m\n" for n in nodes)
    out = ngspice(deck(extra=f"VSIG IN 0 sin(0 {amp} {f})\n.options method=gear\n.control\ntran 10u 100m\n{meas}\n.endc", **kw))
    d = dict((k.lower(), float(v)) for k, v in re.findall(r"^(\w+_(?:hi|lo))\s*=\s*(\S+)", out, re.M))
    if len(d) != 2 * len(nodes): print(out[-2500:]); raise SystemExit(1)
    return [d[f"{n.lower()}_hi"] - d[f"{n.lower()}_lo"] for n in nodes]
def op(nodes, **kw):
    out = ngspice(deck(extra="VSIG IN 0 0\n.control\nop\n" + "\n".join(f"print v({n})" for n in nodes) + "\n.endc", **kw))
    return dict((k.upper(), float(v)) for k, v in re.findall(r"^v\((\w+)\)\s*=\s*(\S+)", out, re.M))
def show(t, rows):
    print(f"\n{t}\n{'':>16}" + "".join(f"{f:>7}" for f in F))
    for n, v in rows: print(f"{n:>16}" + "".join(f"{x:7.1f}" for x in v))

if __name__ == "__main__":
    d = op(["VCC", "VREF", "IB", "TSO", "MFO", "MIX", "OB", "Q1C", "Q2C", "Q3C", "Q4C", "Q4E"], ts=True, mf=True)
    print("DC volts, both on: " + "  ".join(f"{k} {v:.2f}" for k, v in d.items()))
    show("Both off (bypass), IN -> OUT, dB", [(m, ac(mode=m)) for m in ("ts>mf", "par", "mf>ts")])
    show("Screamer alone, tone at noon, by Drive", [(f"drive {x}", ac(ts=True, drive=x, level=1)) for x in (0, .5, 1)])
    show("Screamer alone, drive 0.5, by Tone", [(f"tone {x}", ac(ts=True, ts_tone=x, level=1)) for x in (0, .5, 1)])
    show("Muff tone stack (Q3 collector -> tone wiper)", [(f"tone {x}", rel("MTW", "Q3C", mf=True, tone=x)) for x in (0, .25, .5, .75, 1)])
    show("Muff small-signal gain, tone at noon, volume max", [(f"sustain {x}", ac(mf=True, sustain=x, volume=1)) for x in (0, .5, 1)])
    print("\nRouting check: volts peak-to-peak for a 0.2 Vpp 220 Hz input (level, volume at noon)")
    nodes = ["TSI", "MFI", "TSO", "MFO", "OUT"]
    print(f"{'mode':>7} {'ts':>3} {'mf':>3}" + "".join(f"{n:>8}" for n in nodes))
    for m in ("ts>mf", "par", "mf>ts"):
        for ts in (False, True):
            for mf in (False, True):
                v = tran(nodes, ts=ts, mf=mf, mode=m)
                print(f"{m:>7} {'on' if ts else '-':>3} {'on' if mf else '-':>3}" + "".join(f"{x:8.3f}" for x in v))
    print("\nOutput level, volts peak-to-peak, 0.2 Vpp 220 Hz in, each effect alone")
    for x in (.25, .5, .75, 1):
        print(f"  level/volume {x}: screamer {tran(['OUT'], ts=True, level=x)[0]:.2f}   muff {tran(['OUT'], mf=True, volume=x)[0]:.2f}")
