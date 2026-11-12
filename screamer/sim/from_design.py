"""Build a SPICE deck from hw/design.py and print the voicing. Run from this folder."""
import re, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hw"))
from design import parts
from circuit import MODELS
from run import ngspice

def val(v):
    m = re.fullmatch(r"([\d.]+)([RkMpnu]?)", v.split()[0])
    return float(m.group(1)) * {"": 1, "R": 1, "k": 1e3, "M": 1e6, "p": 1e-12, "n": 1e-9, "u": 1e-6}[m.group(2)]

def deck(extra="", tone=0.5, override=None):
    ov = override or {}
    L = [MODELS, "VS VIN 0 9"]
    for p in parts():
        r, k, n = p["ref"], p["kind"], ["0" if x == "GND" else x for x in p["nets"]]
        v = ov.get(r, None)
        if k == "R": L.append(f"R{r} {n[0]} {n[1]} {v or val(p['value'])}")
        elif k in ("C", "C08"): L.append(f"C{r} {n[0]} {n[1]} {v or val(p['value'])}")
        elif k == "D": L.append(f"D{r} {n[0]} {n[1]} {'D4148' if '4148' in p['value'] else 'DSCH'}")
        elif k == "U":
            L.append(f"X{r}A {n[2]} {n[1]} {n[7]} {n[3]} {n[0]} OPA")
            L.append(f"X{r}B {n[4]} {n[5]} {n[7]} {n[3]} {n[6]} OPA")
        elif k == "POT":
            a = min(max(tone, 0.001), 0.999)
            L += [f"R{r}a {n[0]} {n[1]} {20e3 * a}", f"R{r}b {n[1]} {n[2]} {20e3 * (1 - a)}"]
    L += [".model DSCH D(IS=1u N=1.05 RS=0.1)", "RLOAD OUT 0 1Meg"]
    return "* screamer\n" + "\n".join(L) + "\n" + extra + "\n.end\n"

F = (40, 80, 150, 300, 500, 750, 1000, 1500, 2500, 4000, 6000, 10000)
def ac(**kw):
    meas = "\n".join(f"meas ac g{i} find vdb(OUT) at={f}" for i, f in enumerate(F))
    out = ngspice(deck(extra=f"VIN IN 0 dc 0 ac 1\n.control\nac dec 40 10 40k\n{meas}\n.endc", **kw))
    v = [float(m) for m in re.findall(r"^g\d+\s*=\s*(\S+)", out, re.M)]
    if len(v) != len(F): print(out[-2000:]); raise SystemExit(1)
    return v
def peak(amp, **kw):
    out = ngspice(deck(extra=f"VIN IN 0 sin(0 {amp} 440)\n.options method=gear\n.control\ntran 10u 60m\nmeas tran hi max v(OUT) from=30m to=60m\nmeas tran lo min v(OUT) from=30m to=60m\n.endc", **kw))
    d = dict(re.findall(r"^(hi|lo)\s*=\s*(\S+)", out, re.M))
    return float(d["hi"]) - float(d["lo"])
def show(t, rows):
    print(f"\n{t}\n{'':>20}" + "".join(f"{f:>7}" for f in F))
    for n, v in rows: print(f"{n:>20}" + "".join(f"{x:7.1f}" for x in v))

STOCK = dict(C4=47e-9, C4B=1e-15, R9=1e-3, R10=1e9)       # 720 Hz corner, unity output stage
TIGHT = dict(C4=33e-9, C4B=1e-15, R9=6.8e3)               # 1 kHz corner, more output
if __name__ == "__main__":
    show("Small-signal gain, tone at noon (dB)", [("stock TS", ac(override=STOCK)), ("this design", ac()), ("fully tightened", ac(override=TIGHT))])
    show("This design, tone sweep (dB)", [(f"tone {t}", ac(tone=t)) for t in (0, .25, .5, .75, 1)])
    print("\nOutput, volts peak-to-peak, 440 Hz, tone at noon")
    for amp in (0.05, 0.2, 0.5):
        print(f"  input {amp*2:.1f} Vpp:  stock {peak(amp, override=STOCK):.2f}   this design {peak(amp):.2f}   tightened {peak(amp, override=TIGHT):.2f}")
