"""Build a SPICE deck straight from hw/design.py so the simulated circuit is the PCB netlist.
Run from this folder: python3 from_design.py

Toggle positions are +1 (lever up), 0 (centre) or -1 (lever down), keyed by the
toggle's label in lower case without spaces: gain9, diode+, bass3, clip, sign,
amount1, pitch3, sag, gate, octave, blend, burst.
"""
import math, os, re, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hw"))
from design import parts
from circuit import MODELS, taper
from run import ngspice as _ngspice

def ngspice(net):
    """Run a deck; fail loudly if the DC operating point did not converge (results would be garbage)."""
    out = _ngspice(net)
    if "Transient op" in out:
        out = _ngspice(net.replace("rshunt=1e11", "rshunt=1e10"))
        if "Transient op" in out:
            raise SystemExit("ngspice could not find the DC operating point")
    return out

def val(v):
    m = re.fullmatch(r"([\d.]+)([RkMpnu]?)", v.split()[0])
    return float(m.group(1)) * {"": 1, "R": 1, "k": 1e3, "M": 1e6, "p": 1e-12, "n": 1e-9, "u": 1e-6}[m.group(2)]

def key(p):
    return p["value"].lower().replace(" ", "")

SWITCHES = [key(p) for p in parts() if p["kind"] == "SW"]
TRIMS = {"RV2": "thresh", "RV3": "tune"}
DIODES = {"1N4148W": "D4148", "B5819W": "DSCH", "BAT54W": "DBAT54"}
IQ = {"TL072": 2.8e-3, "NE5532": 8e-3}                      # typical quiescent current per package

def deck(extra="", level=1.0, thresh=0.5, tune=0.5, vin=9.0, override=None, **sw):
    bad = set(sw) - set(SWITCHES)
    assert not bad, f"unknown toggles {bad}"
    ov = override or {}
    trim = dict(thresh=thresh, tune=tune)
    L = [MODELS, ".options rshunt=1e11", f"VS VIN 0 {vin}"]
    for p in parts():
        r, k, n = p["ref"], p["kind"], ["0" if x == "GND" else x for x in p["nets"]]
        if k == "R": L.append(f"R{r} {n[0]} {n[1]} {ov.get(r) or val(p['value'])}")
        elif k in ("C", "C08"): L.append(f"C{r} {n[0]} {n[1]} {ov.get(r) or val(p['value'])}")
        elif k == "D": L.append(f"D{r} {n[0]} {n[1]} {DIODES[p['value']]}")
        elif k in ("LED", "LEDT"): L.append(f"D{r} {n[0]} {n[1]} LEDR")
        elif k == "Q": L.append(f"M{r} {n[2]} {n[0]} {n[1]} {n[1]} N7002")
        elif k == "U":
            L.append(f"X{r}A {n[2]} {n[1]} {n[7]} {n[3]} {n[0]} OPA")
            L.append(f"X{r}B {n[4]} {n[5]} {n[7]} {n[3]} {n[6]} OPA")
            L.append(f"I{r}q {n[7]} {n[3]} {IQ[p['value']]}")       # the op-amp model draws no supply current itself
        elif k == "RV":
            a = min(max(trim[TRIMS[r]], 0.001), 0.999)
            L += [f"R{r}a {n[0]} {n[1]} {100e3 * a}", f"R{r}b {n[1]} {n[2]} {100e3 * (1 - a)}"]
        elif k == "POT":
            a = taper(level, "A")
            L += [f"R{r}a {n[0]} {n[1]} {max(10e3 * a, 1)}", f"R{r}b {n[1]} {n[2]} {max(10e3 * (1 - a), 1)}"]
        elif k == "SW":
            pos = sw.get(key(p), 0)
            L.append(f"R{r}a {n[0]} {n[1]} {1 if pos > 0 else 1e9}")      # 1 ohm / 1 G keeps the matrix well conditioned
            L.append(f"R{r}b {n[2]} {n[1]} {1 if pos < 0 else 1e9}")
    L += ["RLK LK 0 1m", "RLOAD OUT 0 1Meg"]
    return "* decade drive\n" + "\n".join(L) + "\n" + extra + "\n.end\n"

F = (40, 80, 150, 300, 500, 750, 1000, 1500, 2500, 4000, 6000, 10000)
def ac(node="OUT", freqs=F, **kw):
    meas = "\n".join(f"meas ac g{i} find vdb({node}) at={f}" for i, f in enumerate(freqs))
    out = ngspice(deck(extra=f"VSIG IN 0 dc 0 ac 1\n.control\nac dec 100 10 40k\n{meas}\n.endc", **kw))
    v = [float(m) for m in re.findall(r"^g\d+\s*=\s*(\S+)", out, re.M)]
    if len(v) != len(freqs): print(out[-2500:]); raise SystemExit(1)
    return v

def corner(node, ref, kind, **kw):
    """-3 dB frequency of node relative to ref: kind 'hp' or 'lp'."""
    edge = "rise=1" if kind == "hp" else "fall=1"
    out = ngspice(deck(extra=f"VSIG IN 0 dc 0 ac 1\n.control\nac dec 200 5 80k\nlet h = vdb({node}) - vdb({ref})\n"
                             f"meas ac top max h\nlet t3 = top - 3\nmeas ac fc when h=t3 {edge}\n.endc", **kw))
    m = re.search(r"^fc\s*=\s*(\S+)", out, re.M)
    return float(m.group(1)) if m else float("nan")

def op(nodes, **kw):
    out = ngspice(deck(extra="VSIG IN 0 0\n.control\nop\n" + "\n".join(f"print v({n})" for n in nodes) + "\n.endc", **kw))
    return dict((k.upper(), float(v)) for k, v in re.findall(r"^v\((\w+)\)\s*=\s*(\S+)", out, re.M))

def wave(nodes, src="VSIG IN 0 0", tstop=0.3, tstep=10e-6, tstart=0.0, ic="", **kw):
    """Transient run. Returns (times, {node: samples}) on a uniform grid from tstart to tstop."""
    f = tempfile.NamedTemporaryFile(suffix=".txt", delete=False); f.close()
    cols = " ".join(f"v({n})" for n in nodes)
    ctl = (f"{src}\n{ic}\n.options method=gear reltol=1e-4\n.control\ntran {tstep} {tstop} {tstart} {tstep}\n"
           f"linearize {cols}\nset wr_singlescale\nwrdata {f.name} {cols}\n.endc")
    out = ngspice(deck(extra=ctl, **kw))
    rows = [[float(x) for x in line.split()] for line in open(f.name) if line.strip()]
    os.unlink(f.name)
    if not rows: print(out[-2500:]); raise SystemExit(1)
    return [r[0] for r in rows], {n: [r[i + 1] for r in rows] for i, n in enumerate(nodes)}

def stats(t, v, frac=0.5):
    """Peak-to-peak and zero-crossing frequency over the last `frac` of the run."""
    i0 = int(len(v) * (1 - frac)); seg = v[i0:]; ts = t[i0:]
    mean = sum(seg) / len(seg)
    pp = max(seg) - min(seg)
    ups = []
    for i in range(1, len(seg)):
        a, b = seg[i - 1] - mean, seg[i] - mean
        if a < 0 <= b:
            ups.append(ts[i - 1] + (ts[i] - ts[i - 1]) * (-a) / (b - a))
    f = (len(ups) - 1) / (ups[-1] - ups[0]) if len(ups) > 2 and pp > 1e-3 else 0.0
    return pp, f

def note(f):
    if f <= 0: return "-"
    n = 12 * math.log2(f / 440.0) + 57
    k = round(n)
    return f"{'C C# D D# E F F# G G# A A# B'.split()[k % 12]}{k // 12} {100 * (n - k):+.0f}c"

def show(t, rows, freqs=F):
    print(f"\n{t}\n{'':>22}" + "".join(f"{f:>7}" for f in freqs))
    for n, v in rows: print(f"{n:>22}" + "".join(f"{x:7.1f}" for x in v))

def peak(node, ref=None, lo=100, hi=3000, **kw):
    """Largest magnitude of node (relative to ref if given) between lo and hi Hz: (dB, Hz)."""
    h = f"vdb({node}) - vdb({ref})" if ref else f"vdb({node})"
    out = ngspice(deck(extra=f"VSIG IN 0 dc 0 ac 1\n.control\nac dec 2000 {lo} {hi}\nlet h = {h}\nmeas ac top max h\n.endc", **kw))
    m = re.search(r"^top\s*=\s*(\S+) at=\s*(\S+)", out, re.M)
    return float(m.group(1)), float(m.group(2))

def loop_gain(**kw):
    """Open-loop gain of the regenerative path at the resonator peak: drive FP (SIGN centred), read FA."""
    out = ngspice(deck(extra="VSIG IN 0 0\nVT FSX 0 dc 0 ac 1\nCT FSX FP 1\n.control\nac dec 2000 100 3k\nlet m = vm(fa)\nmeas ac top max m\n.endc", **kw))
    return float(re.search(r"^top\s*=\s*(\S+)", out, re.M).group(1))

KICK = "VSIG IN 0 pulse(0 5m 1m 10u 10u 2m 10)"       # a 5 mV tick stands in for the noise that starts a real oscillator
def drone(tstop=0.6, **kw):
    """No input: peak-to-peak volts at CO and OUT and the frequency, once settled."""
    t, w = wave(["CO", "OUT"], src=KICK, tstop=tstop, tstep=20e-6, **kw)
    pc, f = stats(t, w["CO"], 0.25); po, _ = stats(t, w["OUT"], 0.25)
    return pc, po, f

def sine(nodes, amp=0.1, f=1000, tstop=0.06, **kw):
    """Peak-to-peak volts at each node for a sine input of the given peak amplitude."""
    t, w = wave(nodes, src=f"VSIG IN 0 sin(0 {amp} {f})", tstop=tstop, tstep=5e-6, **kw)
    return [max(w[n][len(t) // 2:]) - min(w[n][len(t) // 2:]) for n in nodes]

def harmonic(t, v, f):
    n = len(v); m = sum(v) / n
    a = sum((x - m) * math.cos(2 * math.pi * f * tt) for x, tt in zip(v, t)); b = sum((x - m) * math.sin(2 * math.pi * f * tt) for x, tt in zip(v, t))
    return 2 * math.hypot(a, b) / n

P3 = {1: "up", 0: "centre", -1: "down"}
if __name__ == "__main__":
    d = op(["VCC", "VREF", "VS", "IB", "PO", "S", "CO", "TB", "MO", "V1", "V2", "V3", "GO", "BX", "BG"])
    print("DC volts at home: " + "  ".join(f"{k} {v:.2f}" for k, v in d.items()))
    show("Home (all toggles centred), IN -> node, dB", [(n, ac(n)) for n in ("PO", "CO", "TB", "OUT")])

    print("\nGain stage (PO re IN, 1 kHz), toggles GAIN 9 / 3 / 1")
    for g in ((1, 1, 1), (1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0), (0, 0, -1), (0, -1, 0), (-1, 0, 0), (-1, -1, -1)):
        print(f"  {P3[g[0]]:>6} {P3[g[1]]:>6} {P3[g[2]]:>6}   {ac('PO', (1000,), gain9=g[0], gain3=g[1], gain1=g[2])[0]:+6.1f} dB")

    print("\nBass corner, Hz (rows BASS 3, columns BASS 1: up, centre, down)")
    for b3 in (1, 0, -1):
        print(f"  {P3[b3]:>6}: " + "  ".join(f"{corner('DP', 'S', 'hp', bass3=b3, bass1=b1):6.0f}" for b1 in (1, 0, -1)))
    print("Treble corner, Hz (rows TREBLE 3, columns TREBLE 1: up, centre, down)")
    for t3 in (1, 0, -1):
        print(f"  {P3[t3]:>6}: " + "  ".join(f"{corner('T', 'CA', 'lp', treble3=t3, treble1=t1):6.0f}" for t1 in (1, 0, -1)))

    print("\nClipping: volts peak-to-peak for a 0.2 Vpp 1 kHz input, home gain, Level at maximum")
    for name, kw in (("LED / LED (home)", {}), ("Si / Si", {"diode+": 1, "diode-": 1}), ("Schottky / Schottky", {"diode+": -1, "diode-": -1}),
                     ("Si / LED", {"diode+": 1}), ("Si / Schottky", {"diode+": 1, "diode-": -1}),
                     ("home + CLIP up (Si)", {"clip": 1}), ("home + CLIP down (Schottky)", {"clip": -1})):
        co, tb, out = sine(["CO", "TB", "OUT"], **kw)
        print(f"  {name:<28} drive stage {co:5.2f}   after clipper {tb:5.2f}   OUT {out:5.2f}")

    print("\nResonator (V1 re CA): peak frequency for PITCH 3 / PITCH 1")
    for p3 in (1, 0, -1):
        for p1 in (1, 0, -1):
            db, f = peak("V1", "CA", pitch3=p3, pitch1=p1)
            print(f"  {P3[p3]:>6} {P3[p1]:>6}   {f:7.1f} Hz  {note(f):<9} peak {db:+.2f} dB")
    print("TUNE trimmer, home pitch: " + "  ".join(f"{x}: {peak('V1', 'CA', tune=x)[1]:.0f} Hz" for x in (0, .25, .5, .75, 1)))

    print("\nLoop gain of the SIGN-up path (above 1 it oscillates). Rows AMOUNT 3, columns AMOUNT 1: up, centre, down")
    for th in (0, 0.5, 1):
        print(f"  THRESH trimmer at {th}")
        for a3 in (1, 0, -1):
            print(f"    {P3[a3]:>6}: " + "  ".join(f"{loop_gain(amount3=a3, amount1=a1, thresh=th):5.2f}" for a1 in (1, 0, -1)))
    print("  by GAIN toggles, home amount: " + "  ".join(f"{P3[g]}: {loop_gain(gain9=g, gain3=g, gain1=g):.2f}" for g in (1, 0, -1)))
    print("  by DIODE toggles (both), home amount: " + "  ".join(f"{n}: {loop_gain(**{'diode+': k, 'diode-': k}):.2f}" for n, k in (("Si", 1), ("LED", 0), ("Schottky", -1))))

    fr = (150, 300, 450, 580, 750, 1000, 2000, 4000)
    show("SIGN and AMOUNT, IN -> OUT, dB", [(n, ac("OUT", fr, **kw)) for n, kw in (
        ("sign centre", {}), ("up, amount home", dict(sign=1)), ("up, amount 1 down", dict(sign=1, amount1=-1)), ("up, amount 3 down", dict(sign=1, amount3=-1)),
        ("down, amount home", dict(sign=-1)), ("down, amount 3 up", dict(sign=-1, amount3=1)), ("down, amount 3 down", dict(sign=-1, amount3=-1)))], fr)

    print("\nDrone with no input: volts peak-to-peak at the drive stage and at OUT (Level max), frequency")
    for name, kw in (("SIGN up, amount home", dict(sign=1)), ("SIGN up, AMOUNT 1 up", dict(sign=1, amount1=1)), ("SIGN up, AMOUNT 3 up", dict(sign=1, amount3=1)),
                     ("same, Si diodes", {"sign": 1, "amount3": 1, "diode+": 1, "diode-": 1}),
                     ("same, 8.0 V supply", dict(sign=1, amount3=1, vin=8.0)), ("same, 9.6 V supply", dict(sign=1, amount3=1, vin=9.6)),
                     ("BURST held, all else home", dict(burst=1)), ("BURST held, gain fully down", dict(burst=1, gain9=-1, gain3=-1, gain1=-1)),
                     ("SIGN up, AMOUNT 3 up, KILL held", dict(sign=1, amount3=1, burst=-1))):
        pc, po, f = drone(**kw)
        print(f"  {name:<32} {pc:5.2f}  {po:5.2f}   {f:7.1f} Hz  {note(f)}")

    print("\nA decaying 147 Hz note (0.2 V peak, 0.35 s decay), SIGN up, AMOUNT 3 up, GAIN 3 up: what the drive stage puts out")
    t, w = wave(["CO"], src="VSIG IN 0 sin(0 0.2 146.83 0 2.857)", tstop=1.2, tstep=20e-6, sign=1, amount3=1, gain3=1)
    k = len(t) // 6
    for i in range(6):
        ts, cs = t[i * k:(i + 1) * k], w["CO"][i * k:(i + 1) * k]
        print(f"  {ts[0]:4.1f} s   input {200 * math.exp(-ts[0] / 0.35):5.1f} mV   note {harmonic(ts, cs, 146.83):5.2f} V   drone {harmonic(ts, cs, 581.2):5.2f} V")

    print("\nGate: OUT volts peak-to-peak against input level (1 kHz, Si diodes): off, up (gate), down (soft)")
    for amp in (0.0005, 0.002, 0.005, 0.02, 0.1):
        print(f"  {2000 * amp:6.1f} mVpp in:  " + "   ".join(f"{sine(['OUT'], amp=amp, gate=g, **{'diode+': 1, 'diode-': 1})[0]:6.3f}" for g in (0, 1, -1)))

    print("\nOctave: share of the output at twice the input frequency (220 Hz in, 0.2 Vpp)")
    for name, kw in (("off", {}), ("up (into the drive)", dict(octave=1)), ("down (into the mix)", dict(octave=-1)), ("down, BLEND down", dict(octave=-1, blend=-1))):
        t, w = wave(["OUT"], src="VSIG IN 0 sin(0 0.1 220)", tstop=0.1, tstep=5e-6, **kw)
        h = len(t) // 2; f1, f2 = harmonic(t[h:], w["OUT"][h:], 220), harmonic(t[h:], w["OUT"][h:], 440)
        print(f"  {name:<22} 220 Hz {f1:5.2f} V   440 Hz {f2:5.2f} V")

    show("Blend, IN -> OUT, dB", [(f"blend {P3[b]}", ac("OUT", fr, blend=b)) for b in (0, 1, -1)], fr)

    print("\nSag: drive op-amp supply, and drive-stage peaks about VREF for a 0.2 Vpp 1 kHz input")
    for sg in (0, 1, -1):
        v = op(["VS", "VREF"], sag=sg)
        t, w = wave(["CO"], src="VSIG IN 0 sin(0 0.1 1000)", tstop=0.06, tstep=5e-6, sag=sg)
        seg = w["CO"][len(t) // 2:]
        print(f"  {P3[sg]:>6}: VS {v['VS']:.2f} V   {max(seg) - v['VREF']:+.2f} / {min(seg) - v['VREF']:+.2f} V")
