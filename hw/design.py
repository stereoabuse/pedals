"""Master design data: every part, its value, JLC part number and net connections.

Coordinates are KiCad mm, viewed from the SMD (front copper) side, which faces
the back of the pedal. Front-panel x is mirrored: x_panel = 100 - x.
"""

NAME = "HG PREAMP"
REV = "A"

# kind -> (footprint, pad names in order)
KINDS = {
    "R":    ("Resistor_SMD:R_0603_1608Metric", "1 2"),
    "C":    ("Capacitor_SMD:C_0603_1608Metric", "1 2"),
    "C08":  ("Capacitor_SMD:C_0805_2012Metric", "1 2"),
    "C12":  ("Capacitor_SMD:C_1206_3216Metric", "1 2"),
    "CP":   ("Capacitor_SMD:CP_Elec_6.3x7.7", "1 2"),          # 1 = +
    "D":    ("Diode_SMD:D_SOD-123", "2 1"),                    # listed A K
    "LED":  ("LED_SMD:LED_0603_1608Metric", "2 1"),            # listed A K
    "U":    ("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "1 2 3 4 5 6 7 8"),
    "Q":    ("Package_TO_SOT_SMD:SOT-23", "1 2 3"),            # D S G
    "RV":   ("Potentiometer_SMD:Potentiometer_Bourns_3314J_Vertical", "1 2 3"),
    "JP3":  ("Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm", "1 2 3"),
    "JP2":  ("Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm", "1 2"),
    "TP":   ("TestPoint:TestPoint_Pad_D1.5mm", "1"),
    "POT":  ("custom:POT16", "1 2 3"),
    "SW":   ("custom:TOGGLE", "1 2 3"),
    "LEDT": ("custom:LED3", "2 1"),                            # listed A K
    "PAD":  ("custom:WIREPAD", "1"),
}

LCSC = {
    ("R", "22R"): "C23345", ("R", "1k"): "C21190", ("R", "2.2k"): "C4190", ("R", "3.3k"): "C22978",
    ("R", "4.7k"): "C23162", ("R", "6.8k"): "C23212", ("R", "10k"): "C25804", ("R", "22k"): "C31850",
    ("R", "33k"): "C4216", ("R", "39k"): "C23153", ("R", "100k"): "C25803", ("R", "150k"): "C22807",
    ("R", "220k"): "C22961", ("R", "470k"): "C23178", ("R", "1M"): "C22935",
    ("C", "47p"): "C1671", ("C", "100p"): "C14858", ("C", "120p"): "C107035", ("C", "1n"): "C1588",
    ("C", "3.3n NP0"): "C107048", ("C", "4.7n NP0"): "C576818", ("C", "10n NP0"): "C2894187",
    ("C", "10n"): "C57112", ("C", "47n"): "C1622", ("C", "100n"): "C14663", ("C", "470n"): "C1623",
    ("C", "1u"): "C15849",
    ("C12", "47n NP0"): "C5451690", ("C12", "100n NP0"): "C170182",
    ("C08", "10u"): "C15850", ("CP", "100u 35V"): "C2836442",
    ("D", "1N4148W"): "C81598", ("D", "B5819W"): "C8598", ("LED", "RED"): "C2286",
    ("U", "TL072"): "C6961", ("U", "TC7660S"): "C636973", ("Q", "MMBF4393"): "C152291",
    ("RV", "100k"): "C51284", ("RV", "20k"): "C55069",
}

# ref kind value nets...   (pads in the order given in KINDS)
NETLIST = """
# --- power ---
J_9V  PAD  +9V     VIN
J_G1  PAD  GND     GND
D1    D    B5819W  VIN V9
C20   CP   100u_35V V9 GND
C21   C    100n    V9 GND
U6    U    TC7660S V9 CP GND CN VNEG NC1 NC2 V9
C22   C08  10u     CP CN
C23   C08  10u     GND VNEG
D2    D    B5819W  V9 CX
C24   C08  10u     CX CP
D3    D    B5819W  CX V18
C26   C08  10u     V18 GND
C27   CP   100u_35V V18 GND
JP1   JP3  18V/9V  V18 VSEL V9
R30   R    22R     VSEL VCC
C28   CP   100u_35V VCC GND
R32   R    10k     VCC VB
R33   R    10k     VB GND
C25   C08  10u     VB GND
R34   R    2.2k    VB VBF
TP1   TP   VCC     VCC
TP2   TP   VREF    VREF
TP3   TP   9V      V9
# --- op-amps: OUTA INA- INA+ V- INB+ INB- OUTB V+ ---
U1    U    TL072   S1 U1AN U1AP GND U1BP U1BN S2 VCC
U2    U    TL072   S3 U2AN VREF GND VREF U2BN S4 VCC
U3    U    TL072   S5 U3AN TW GND VREF U3BN S6 VCC
U4    U    TL072   VREF VREF VBF GND NS U4BN SG VCC
U5    U    TL072   CMP ENV NREF GND VREF SPARE SPARE VCC
C6    C    100n    VCC GND
C7    C    100n    VCC GND
C10   C    100n    VCC GND
C29   C    100n    VCC GND
C30   C    100n    VCC GND
# --- input stage + boost ---
J_IN  PAD  IN      IN
J_G2  PAD  GND     GND
R1    R    1M      IN GND
C1    C12  47n_NP0 IN NA
R2    R    470k    NA VREF
R3    R    10k     NA U1AP
C2    C    47p     U1AP GND
R5    R    39k     U1AN S1
R4    R    22k     U1AN VREF
R40   R    4.7k    U1AN BX
RV7   RV   20k     BX BY BY
C40   C12  47n_NP0 BY BQ
Q2    Q    MMBF4393 BQ VREF BG
R41   R    1M      BQ VREF
R42   R    1M      BG VREF
C41   C    47n     BG VREF
D12   D    1N4148W BG BC
R43   R    100k    BC VCC
C42   C    100n    BC GND
J_BST PAD  BST     BC
J_G3  PAD  GND     GND
# --- tight + gain stage ---
C3A   C    10n_NP0 S1 NB
C3B   C    10n_NP0 S1 NB
R7    R    4.7k    NB NT
RV1   POT  C100K_TIGHT VREF VREF NT
R8    R    10k     NB U1BP
C4    C    1n      U1BP GND
R9    R    22k     U1BN N9
C8    C12  100n_NP0 N9 GND
R10   R    22k     U1BN NG
RV2   POT  A1M_GAIN NG S2 S2
LED1  LED  RED     NG S2
LED2  LED  RED     S2 NG
C9    C    47p     U1BN S2
# --- clip stage ---
C11   C12  47n_NP0 S2 N11
R11   R    22k     N11 U2AN
R13   R    220k    U2AN S3
C12   C    120p    U2AN S3
R12   R    22k     U2AN ND
SW1   SW   CLIP    CLA ND CLB
D4    D    1N4148W CLA D45
D5    D    1N4148W D45 S3
D6    D    1N4148W S3 D67
D7    D    1N4148W D67 CLA
D8    D    1N4148W CLB S3
D9    D    1N4148W S3 CLB
# --- trim stage ---
R14   R    10k     S3 U2BN
R15   R    10k     U2BN NTR
RV8   RV   100k    NTR S4 S4
C13   C    100p    U2BN S4
# --- presence + hard clip ---
RV3   POT  C10K_PRES NP NP S4
R18   R    2.2k    NP NH
C14   C    10n_NP0 NH GND
LED3  LED  RED     NH VREF
LED4  LED  RED     VREF NH
# --- treble + depth stage ---
RV4   POT  B100K_TREBLE T1 TW NH
C15   C    4.7n_NP0 T1 GND
C16A  C    10n_NP0 U3AN S5
C16B  C    4.7n_NP0 U3AN S5
R19   R    33k     U3AN NM
R20   R    33k     NM S5
C17A  C    100n    NM NDP
C17B  C    47n     NM NDP
R22   R    22k     NDP DPA
R23   R    6.8k    NDP DPB
SW2   SW   DEPTH   DPA GND DPB
# --- mid stage + output ---
R53   R    100k    S5 U3BN
R54   R    100k    U3BN S6
C52   C    47p     U3BN S6
R50   R    10k     S5 MA
R51   R    10k     S6 MB
RV5   POT  B100K_MID MB MW MA
C50   C    3.3n_NP0 MA MB
C51A  C    10n_NP0 MW MX
C51B  C    4.7n_NP0 MW MX
R52   R    2.2k    MX U3BN
C18   C    1u      S6 NO
R21   R    1k      NO V3
RV6   POT  A10K_VOLUME GND OUT V3
J_OUT PAD  OUT     OUT
J_G4  PAD  GND     GND
# --- noise gate ---
C60   C    10n_NP0 S1 NS
R60   R    100k    NS VREF
R61   R    10k     U4BN N61
RV9   RV   100k    N61 SG SG
C62   C    100p    U4BN SG
R62   R    1k      U4BN N62
C61   C    1u      N62 GND
D10   D    1N4148W SG N64
R64   R    1k      N64 ENV
C63   C    470n    ENV GND
R63   R    150k    ENV VREF
R65   R    100k    VCC NREF
R66   R    100k    NREF N66
R67   R    10k     N66 GND
R68A  R    1M      CMP N68
R68B  R    1M      N68 NREF
R69   R    22k     CMP N69
D11   D    1N4148W NGATE N69
R70   R    1M      NGATE VREF
C65   C    47n     NGATE VREF
Q1    Q    MMBF4393 QD VREF NGATE
JP2   JP2  GATE    QD NH
# --- indicator LEDs ---
R71   R    3.3k    V9 LA1
LED5  LEDT BYPASS  LA1 L1
J_L1  PAD  L1      L1
R72   R    3.3k    V9 LA2
LED6  LEDT BOOST   LA2 L2
J_L2  PAD  L2      L2
J_L1B PAD  L1      L1
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
    smd = [p for p in ps if p["kind"] not in ("POT", "SW", "LEDT", "PAD", "TP", "JP2", "JP3")]
    missing = [p["ref"] for p in smd if not p["lcsc"]]
    print("missing LCSC:", missing)
    c = Counter((p["kind"], p["value"], p["lcsc"]) for p in smd)
    print(len(c), "BOM lines,", len(smd), "placements")
