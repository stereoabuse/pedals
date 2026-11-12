"""Master design data: every part, its value, JLC part number and net connections.

Black Russian Big Muff and TS808 Tube Screamer on one board, each with its own
footswitch, routed by CMOS switches: Screamer into Muff, parallel, or Muff into
Screamer. Bypass is buffered.

Coordinates are KiCad mm, viewed from the SMD (front copper) side, which faces
the back of the pedal. Front-panel x is mirrored: x_panel = 100 - x.
"""

NAME = "MUFF SCREAMER"
REV = "A"

# kind -> (footprint, pad names in order)
KINDS = {
    "R":    ("Resistor_SMD:R_0603_1608Metric", "1 2"),
    "C":    ("Capacitor_SMD:C_0603_1608Metric", "1 2"),
    "C08":  ("Capacitor_SMD:C_0805_2012Metric", "1 2"),
    "D":    ("Diode_SMD:D_SOD-123", "2 1"),                    # listed A K
    "U":    ("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "1 2 3 4 5 6 7 8"),
    "U16":  ("Package_SO:SOIC-16_3.9x9.9mm_P1.27mm", "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16"),
    "Q":    ("Package_TO_SOT_SMD:SOT-23", "1 2 3"),            # B E C
    "TP":   ("TestPoint:TestPoint_Pad_D1.5mm", "1"),
    "POT":  ("custom:POT16", "1 2 3"),
    "SW":   ("custom:TOGGLE", "1 2 3"),
    "LEDT": ("custom:LED3", "2 1"),                            # listed A K
    "PAD":  ("custom:WIREPAD", "1"),
}

LCSC = {
    ("R", "22R"): "C23345", ("R", "100R"): "C22775", ("R", "220R"): "C22962", ("R", "390R"): "C23151",
    ("R", "1k"): "C21190", ("R", "2.2k"): "C4190", ("R", "2.7k"): "C13167", ("R", "3.3k"): "C22978",
    ("R", "4.7k"): "C23162", ("R", "10k"): "C25804", ("R", "12k"): "C22790", ("R", "20k"): "C4184",
    ("R", "22k"): "C31850", ("R", "39k"): "C23153", ("R", "51k"): "C23196", ("R", "100k"): "C25803",
    ("R", "470k"): "C23178", ("R", "1M"): "C22935",
    ("C", "47p"): "C1671", ("C", "100p"): "C14858", ("C", "470p"): "C106211", ("C", "3.9n"): "C1618",
    ("C", "10n"): "C57112", ("C", "47n"): "C1622", ("C", "100n"): "C14663", ("C", "220n"): "C21120",
    ("C", "1u"): "C15849", ("C08", "10u"): "C15850",
    ("D", "1N4148W"): "C81598", ("D", "B5819W"): "C8598",
    ("U", "TL072"): "C6961", ("U16", "CD4053B"): "C6742", ("Q", "BC847C"): "C8664",
}

# ref kind value nets...   (pads in the order given in KINDS)
NETLIST = """
# --- power ---
J_9V  PAD  +9V     VIN
J_G1  PAD  GND     GND
D1    D    B5819W  VIN V9R
R20   R    22R     V9R VCC
C20   C08  10u     VCC GND
C21   C08  10u     VCC GND
R21   R    10k     VCC VB
R22   R    10k     VB GND
C24   C08  10u     VB GND
R23   R    2.2k    VB VBF
TP1   TP   VCC     VCC
TP2   TP   VREF    VREF
# --- op-amps: OUTA INA- INA+ V- INB+ INB- OUTB V+ ---
U1    U    TL072   IB IB INP GND VBF VREF VREF VCC
U2    U    TL072   CO CN CP GND T1 TN TO VCC
U3    U    TL072   TSO TSO LW GND VREF MN MIX VCC
U4    U    TL072   MFO MFO MBP GND OSEL OB OB VCC
C30   C    100n    VCC GND
C31   C    100n    VCC GND
C32   C    100n    VCC GND
C33   C    100n    VCC GND
C34   C    100n    VCC GND
C35   C    100n    VCC GND
C36   C    100n    VCC GND
# --- input buffer ---
J_IN  PAD  IN      IN
J_G2  PAD  GND     GND
R1    R    1M      IN GND
C1    C    100n    IN INA
R2    R    1M      INA VREF
R3    R    10k     INA INP
C2    C    47p     INP GND
# --- routing switches: 1=B1 2=B0 3=C1 4=C 5=C0 6=INH 7=VEE 8=VSS 9=selC 10=selB 11=selA 12=A0 13=A1 14=A 15=B 16=VDD
# a select line is low when its effect is on (NTS, NMF) or its order is chosen (NAB, NBA); low picks the 0 input
U5    U16  CD4053B XMF YSA IB XMF MFO GND GND GND NMF NTS NTS TSO IB XTS OSEL VCC
U6    U16  CD4053B VREF MFS IB MFS XTS GND GND GND NAB NMF NMF W TSO YSA MFI VCC
U7    U16  CD4053B IB XMF MIX W2 TSO GND GND GND NBA NBA NAB MFO W2 W TSI VCC
R41   R    1M      TSI VREF
R84   R    1M      MFI VREF
R83   R    1M      OSEL VREF
# --- parallel mixer ---
R80   R    10k     TSO MN
R81   R    10k     MFO MN
R82   R    10k     MN MIX
C80   C    100p    MN MIX
# --- output buffer ---
C81   C08  10u     OB OC
R85   R    100R    OC OUT
R86   R    100k    OUT GND
J_OUT PAD  OUT     OUT
J_G3  PAD  GND     GND
# --- footswitches, LEDs and the order toggle ---
J_FT  PAD  FS      FT
J_G4  PAD  GND     GND
R90   R    100k    VCC FT
R91   R    10k     FT NTS
C90   C    100n    NTS GND
R92   R    3.3k    VCC LA1
LED1  LEDT SCREAMER LA1 FT
J_FM  PAD  FS      FM
J_G5  PAD  GND     GND
R93   R    100k    VCC FM
R94   R    10k     FM NMF
C91   C    100n    NMF GND
R95   R    3.3k    VCC LA2
LED2  LEDT MUFF    LA2 FM
SW1   SW   ORDER   NAB GND NBA
R96   R    100k    VCC NAB
C92   C    100n    NAB GND
R97   R    100k    VCC NBA
C93   C    100n    NBA GND
# --- screamer (TS808) ---
C40   C    1u      TSI CP
R40   R    100k    CP VREF
R42   R    4.7k    CN RG
C41   C    47n     RG GND
R43   R    51k     CN DR
RV1   POT  A500K_DRIVE DR CO CO
C42   C    47p     CN CO
D2    D    1N4148W CN CO
D3    D    1N4148W CO CN
R44   R    1k      CO T1
C43   C    220n    T1 GND
R45   R    1k      TN TO
RV2   POT  W20K_TONE T1 TW TN
R46   R    220R    TW TX
C44   C    220n    TX GND
C45   C    1u      TO LV
RV3   POT  B100K_LEVEL VREF LW LV
# --- muff (black Russian) ---
R73   R    100R    VCC VM
C64   C08  10u     VM GND
C50   C    100n    MFI MA
R50   R    39k     MA Q1B
Q1    Q    BC847C  Q1B Q1E Q1C
R51   R    100k    Q1B GND
R52   R    470k    Q1C Q1B
C51   C    470p    Q1C Q1B
R53   R    12k     VM Q1C
R54   R    390R    Q1E GND
C52   C    100n    Q1C SU3
RV4   POT  B100K_SUSTAIN SU1 SUW SU3
R55   R    1k      SU1 GND
C53   C    100n    SUW Q2A
R56   R    10k     Q2A Q2B
Q2    Q    BC847C  Q2B Q2E Q2C
R57   R    100k    Q2B GND
R58   R    470k    Q2C Q2B
C54   C    470p    Q2C Q2B
C55   C    47n     Q2C D2X
D4    D    1N4148W D2X Q2B
D5    D    1N4148W Q2B D2X
R59   R    12k     VM Q2C
R60   R    390R    Q2E GND
C56   C    100n    Q2C Q3A
R61   R    10k     Q3A Q3B
Q3    Q    BC847C  Q3B Q3E Q3C
R62   R    100k    Q3B GND
R63   R    470k    Q3C Q3B
C57   C    470p    Q3C Q3B
C58   C    47n     Q3C D3X
D6    D    1N4148W D3X Q3B
D7    D    1N4148W Q3B D3X
R64   R    12k     VM Q3C
R65   R    390R    Q3E GND
C59   C    3.9n    Q3C TH
R66   R    22k     TH GND
R67   R    20k     Q3C TL
C60   C    10n     TL GND
RV5   POT  B100K_TONE TL MTW TH
C61   C    100n    MTW Q4B
R68   R    470k    VM Q4B
R69   R    100k    Q4B GND
Q4    Q    BC847C  Q4B Q4E Q4C
R70   R    10k     VM Q4C
R71   R    2.7k    Q4E GND
C62   C    100n    Q4C MV
RV6   POT  B100K_VOLUME GND MVW MV
C63   C    100n    MVW MBP
R72   R    1M      MBP VREF
"""


def parts():
    out = []
    for line in NETLIST.strip().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        ref, kind, value, *nets = line.split()
        value = value.replace("_", " ")
        fp, padnames = KINDS[kind]
        pads = padnames.split()
        assert len(pads) == len(nets), f"{ref}: {len(nets)} nets for {len(pads)} pads"
        out.append(dict(ref=ref, kind=kind, value=value, fp=fp,
                        pins=dict(zip(pads, nets)), nets=nets,
                        lcsc=LCSC.get((kind, value))))
    return out


if __name__ == "__main__":
    from collections import Counter, defaultdict
    ps = parts()
    nets = defaultdict(list)
    for p in ps:
        for pad, n in p["pins"].items():
            nets[n].append(f"{p['ref']}.{pad}")
    print(len(ps), "parts,", len(nets), "nets")
    for n, pins in sorted(nets.items()):
        if len(pins) < 2 and not n.startswith("NC"):
            print("SINGLE-PIN NET:", n, pins)
    smd = [p for p in ps if p["kind"] not in ("POT", "SW", "LEDT", "PAD", "TP")]
    missing = [p["ref"] for p in smd if not p["lcsc"]]
    print("missing LCSC:", missing)
    c = Counter((p["kind"], p["value"], p["lcsc"]) for p in smd)
    print(len(c), "BOM lines,", len(smd), "placements")
