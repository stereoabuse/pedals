import subprocess, tempfile, os, re, sys
from circuit import netlist

def ngspice(net):
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as f:
        f.write(net); p = f.name
    r = subprocess.run(["ngspice", "-b", p], capture_output=True, text=True)
    os.unlink(p)
    return r.stdout + r.stderr

def ac(node="out", freqs=(40,80,150,300,500,750,1000,1500,2500,4000,6000,10000), ref="in", **kw):
    meas = "\n".join(f"meas ac g{i} find vdb({node}) at={f}" for i, f in enumerate(freqs))
    extra = f"VIN in 0 dc 0 ac 1\n.control\nac dec 40 10 40k\n{meas}\n.endc"
    out = ngspice(netlist(extra=extra, **kw))
    vals = [float(m) for m in re.findall(r"^g\d+\s*=\s*(\S+)", out, re.M)]
    if len(vals) != len(freqs):
        print(out[-2000:]); raise SystemExit("sim failed")
    return vals

def show(title, rows, freqs=(40,80,150,300,500,750,1000,1500,2500,4000,6000,10000)):
    print(f"\n{title}\n{'':>14}" + "".join(f"{f:>7}" for f in freqs))
    for name, vals in rows:
        print(f"{name:>14}" + "".join(f"{v:7.1f}" for v in vals))

if __name__ == "__main__":
    F=(40,80,150,300,500,750,1000,1500,2500,4000,6000,10000)
    show("Stage1 out (s1): boost", [("off", ac("s1")), ("on trim0", ac("s1", boost=True)),
         ("on trim.5", ac("s1", boost=True, boost_trim=.5)), ("on trim1", ac("s1", boost=True, boost_trim=1))])
    show("Tight (u1bp)", [(f"tight {t}", ac("u1bp", tight=t)) for t in (0,.25,.5,.75,1)])
    show("Small-signal to s4 by gain", [(f"gain {g}", ac("s4", gain=g, clip='open')) for g in (0,.25,.5,.75,1)])
    base = dict(node="s6", ref="nh")
    def eq(**kw):
        # EQ section response relative to hard-clip node
        a = ac("s6", **kw); b = ac("nh", **kw)
        return [x-y for x,y in zip(a,b)]
    show("EQ nh->s6: mid", [(f"mid {m}", eq(mid=m, treble=1)) for m in (0,.25,.5,.75,1)])
    show("EQ nh->s6: treble", [(f"treble {t}", eq(treble=t)) for t in (0,.25,.5,.75,1)])
    show("EQ nh->s6: depth", [(d, eq(depth=d, treble=1)) for d in ("off","mid","deep")])
    def pr(**kw):
        a = ac("nh", clip='open', gain=0, **kw); b = ac("s4", clip='open', gain=0, **kw)
        return [x-y for x,y in zip(a,b)]
    show("Presence s4->nh", [(f"pres {p}", pr(pres=p)) for p in (0,.25,.5,.75,1)])
