"""SPICE model of the pedal. Pot positions are 0..1 (0 = fully CCW)."""

MODELS = """
.model D4148 D(IS=2.52n RS=.568 N=1.752 CJO=4p M=.4 TT=20n BV=100)
.model LEDR D(IS=93.2p RS=42m N=3.73 BV=5 IBV=10u CJO=2.97p VJ=.75 M=.333 TT=4.32u)
.model J4393 NJF(BETA=9.1m VTO=-1.4 LAMBDA=6m RD=1 RS=1 CGS=4p CGD=4p IS=1e-14)
.subckt OPA inp inn vcc vee out
Rin inp inn 1e12
B1 0 n1 I=70u*tanh((V(inp)-V(inn))*1.43)
R1 n1 0 2G
C1 n1 0 5.3p
Vhi vh vcc -1.5
Vlo vl vee 1.5
Dh n1 vh DCL
Dl vl n1 DCL
E1 n2 0 n1 0 1
Ro n2 out 100
.model DCL D(IS=1e-12 N=0.5)
.ends
"""

def taper(pos, kind):
    pos = min(max(pos, 0.0005), 0.9995)
    if kind == "B":
        return pos
    if kind == "A":  # audio: ~15% at half rotation
        return pos * 0.3 if pos < 0.5 else 0.15 + (pos - 0.5) * 1.7
    if kind == "C":  # reverse audio
        return 1 - taper(1 - pos, "A")
    raise ValueError(kind)

def netlist(gain=0.5, tight=0.3, mid=0.5, treble=0.6, pres=0.5, vol=0.5,
            boost=False, boost_trim=0.0, depth="off", clip="stock",
            trim=0.3, gate=False, gate_trim=0.5, vcc=16.5, extra="", params=None):
    L = [MODELS, f"VCC vcc 0 {vcc}",
         "R32 vcc vb 10k", "R33 vb 0 10k", "C25 vb 0 10u", "R34 vb vbf 2.2k",
         "XU4A vbf vref vcc 0 vref OPA"]
    # stage 1 + boost
    L += ["R1 in 0 1Meg", "C1 in na 22n", "R2 na vref 470k", "R3 na u1ap 10k", "C2 u1ap 0 47p",
          "XU1A u1ap u1an vcc 0 s1 OPA", "R5 u1an s1 39k", "R4 u1an vref 22k",
          "R40 u1an bx 3.3k", f"RVB bx by {max(20e3*boost_trim,1)}", "C40 by bst 68n",
          f"RSWB bst 0 {1e-3 if boost else 2.2e6}"]
    # tight
    rt = 100e3 * (1 - taper(tight, "C"))
    L += ["C3 s1 nb 15n", "R7 nb nt 6.8k", f"RVT nt vref {max(rt,1)}", "R8 nb u1bp 10k", "C4 u1bp 0 1n"]
    # gain stage
    rg = 1e6 * taper(gain, "A")
    L += ["XU1B u1bp u1bn vcc 0 s2 OPA", "R9 u1bn n9 22k", "C8 n9 0 100n", "R10 u1bn ng 22k",
          f"RVG ng s2 {max(rg,1)}", "DL1 ng s2 LEDR", "DL2 s2 ng LEDR", "C9 u1bn s2 47p"]
    # clip stage
    L += ["C11 s2 n11 47n", "R11 n11 u2an 22k", "XU2A vref u2an vcc 0 s3 OPA", "R13 u2an s3 220k",
          "C12 u2an s3 120p", "R12 u2an nd 22k"]
    if clip == "stock":
        L += ["D2 nd d23 D4148", "D3 d23 s3 D4148", "D4 s3 d45 D4148", "D5 d45 nd D4148"]
    elif clip == "sat":
        L += ["D6 nd s3 D4148", "D7 s3 nd D4148"]
    # trim stage
    L += ["R14 s3 u2bn 10k", "XU2B vref u2bn vcc 0 s4 OPA", f"RF4 u2bn s4 {10e3 + 100e3*trim}", "C13 u2bn s4 100p"]
    # presence + hard clip
    rp = 10e3 * (1 - taper(pres, "C"))
    L += [f"RVP s4 np {max(rp,1)}", "R18 np nh 2.2k", "C14 nh 0 10n", "DL3 nh vref LEDR", "DL4 vref nh LEDR"]
    # treble
    L += [f"RTa nh tw {max(100e3*(1-treble),1)}", f"RTb tw t1 {max(100e3*treble,1)}", "C15 t1 0 4.7n"]
    # depth stage
    L += ["XU3A tw u3an vcc 0 s5 OPA", "C16 u3an s5 {CD1}", "R19 u3an nm 33k", "R20 nm s5 33k", "C17 nm ndp {CD2}"]
    L += {"off": ["RDP ndp 0 1G"], "mid": ["RDP ndp 0 {DEPTH_MID}"], "deep": ["RDP ndp 0 {DEPTH_DEEP}"]}[depth]
    # mid stage
    L += ["XU3B vref u3bn vcc 0 s6 OPA", "R53 s5 u3bn {RMIN}", "R54 u3bn s6 {RMFB}",
          "R50 s5 ma {RMA}", "R51 s6 mb {RMA}",
          f"RMa ma mw {max(100e3*(1-mid),1)}", f"RMb mw mb {max(100e3*mid,1)}",
          "C50 ma mb {CMP}", "C51 mw mx {CMW}", "R52 mx u3bn {RMW}"]
    # output
    v = taper(vol, "A")
    L += ["C18 s6 no 1u", "R21 no v3 1k", f"RVOa v3 out {max(10e3*(1-v),1)}", f"RVOb out 0 {max(10e3*v,1)}", "RL out 0 1Meg"]
    # gate
    if gate:
        L += ["C60 s1 ns 10n", "R60 ns vref 100k", "XU4B ns u4bn vcc 0 sg OPA",
              f"RF6 u4bn sg {10e3 + 500e3*gate_trim}", "C62 u4bn sg 100p", "R62 u4bn n62 4.7k", "C61 n62 0 220n",
              "D60 sg n64 D4148", "R64 n64 env 1k", "C63 env 0 470n", "R63 env vref 150k",
              "R65 vcc nref 91k", "R66 nref 0 100k", "XU5A nref env vcc 0 cmp OPA", "R67 cmp nref 2.2Meg",
              "R68 cmp n68 22k", "D61 ngate n68 D4148", "R69 ngate vref 1Meg", "C65 ngate vref 47n",
              "J1 nh ngate vref J4393"]
    P = dict(CD1="15n", CD2="150n", DEPTH_MID="22k", DEPTH_DEEP="6.8k", RMIN="100k", RMFB="100k", RMA="10k", CMP="3.3n", CMW="15n", RMW="2.2k")
    P.update(params or {})
    s = "\n".join(L)
    for k, val in P.items():
        s = s.replace("{" + k + "}", val)
    return "* pedal\n" + s + "\n" + extra + "\n.end\n"
