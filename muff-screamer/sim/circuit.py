"""SPICE models shared by the simulation scripts. Pot positions are 0..1 (0 = fully CCW)."""

MODELS = """
.model D4148 D(IS=2.52n RS=.568 N=1.752 CJO=4p M=.4 TT=20n BV=100)
.model LEDR D(IS=93.2p RS=42m N=3.73 BV=5 IBV=10u CJO=2.97p VJ=.75 M=.333 TT=4.32u)
.model DSCH D(IS=1u N=1.05 RS=0.1)
.model BC847C NPN(IS=1.8e-14 BF=520 VAF=80 IKF=0.14 ISE=5e-14 NE=1.46 BR=35 RB=10 RE=0.6 RC=0.25 CJE=13p CJC=4p TF=0.64n)
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
    if kind in ("B", "W"):      # W (TS tone taper) is treated as linear here
        return pos
    if kind == "A":  # audio: ~15% at half rotation
        return pos * 0.3 if pos < 0.5 else 0.15 + (pos - 0.5) * 1.7
    raise ValueError(kind)
