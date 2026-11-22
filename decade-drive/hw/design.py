"""Master design data: every part, its value, JLC part number and net connections.

A drive pedal with one Level knob and twenty three-way toggles. Every toggle is
an SPDT on-off-on whose centre lug sits on a circuit node: lever up adds one
part to that node, lever down adds another, centre adds nothing. With all
twenty centred the pedal is its plain "home" sound.

Coordinates are KiCad mm, viewed from the SMD (front copper) side, which faces
the back of the pedal. Front-panel x is mirrored: x_panel = 100 - x.
"""

NAME = "DECADE DRIVE"
REV = "A"

# kind -> (footprint, pad names in order)
KINDS = {
    "R":    ("Resistor_SMD:R_0603_1608Metric", "1 2"),
    "C":    ("Capacitor_SMD:C_0603_1608Metric", "1 2"),
    "C08":  ("Capacitor_SMD:C_0805_2012Metric", "1 2"),
    "D":    ("Diode_SMD:D_SOD-123", "2 1"),                    # listed A K
    "LED":  ("LED_SMD:LED_0603_1608Metric", "2 1"),            # listed A K
    "U":    ("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "1 2 3 4 5 6 7 8"),
    "Q":    ("Package_TO_SOT_SMD:SOT-23", "1 2 3"),            # G S D
    "RV":   ("Potentiometer_SMD:Potentiometer_Bourns_3314J_Vertical", "1 2 3"),
    "TP":   ("TestPoint:TestPoint_Pad_D1.5mm", "1"),
    "POT":  ("custom:POT16", "1 2 3"),
    "SW":   ("custom:TOGGLE", "1 2 3"),                        # up lug, common, down lug
    "LEDT": ("custom:LED3", "2 1"),                            # listed A K
    "PAD":  ("custom:WIREPAD", "1"),
}

LCSC = {
    ("R", "22R"): "C23345", ("R", "100R"): "C22775", ("R", "220R"): "C22962", ("R", "560R"): "C23204",
    ("R", "1k"): "C21190", ("R", "1.5k"): "C22843", ("R", "2.2k"): "C4190", ("R", "2.7k"): "C13167",
    ("R", "3.3k"): "C22978", ("R", "4.7k"): "C23162", ("R", "6.8k"): "C23212", ("R", "7.5k"): "C23234",
    ("R", "8.2k"): "C25981", ("R", "10k"): "C25804", ("R", "15k"): "C22809",
    ("R", "20k"): "C4184", ("R", "22k"): "C31850", ("R", "27k"): "C22967", ("R", "33k"): "C4216", ("R", "47k"): "C25819",
    ("R", "68k"): "C23231", ("R", "91k"): "C23265", ("R", "100k"): "C25803", ("R", "120k"): "C25808",
    ("R", "150k"): "C22807", ("R", "220k"): "C22961", ("R", "270k"): "C22965", ("R", "680k"): "C25822", ("R", "1M"): "C22935",
    ("R", "10M"): "C7250",
    ("C", "47p"): "C1671", ("C", "100p"): "C14858", ("C", "330p"): "C1664", ("C", "1n NP0"): "C106246",
    ("C", "4.7n"): "C53987", ("C", "10n"): "C57112", ("C", "22n"): "C21122", ("C", "47n"): "C1622",
    ("C", "100n"): "C14663", ("C", "1u"): "C15849", ("C08", "10u"): "C15850",
    ("D", "1N4148W"): "C81598", ("D", "B5819W"): "C8598", ("D", "BAT54W"): "C7502705",
    ("LED", "RED"): "C2286", ("U", "TL072"): "C6961", ("U", "NE5532"): "C7426",
    ("Q", "2N7002"): "C8545", ("RV", "100k"): "C51284",
}

# ref kind value nets...   (pads in the order given in KINDS)
# Toggles are listed  up-lug  common  down-lug.
NETLIST = """
# --- power ---
J_9V  PAD  +9V     VIN
J_G1  PAD  GND     GND
D1    D    B5819W  VIN V9R
R1    R    22R     V9R VCC
C1    C08  10u     VCC GND
C2    C08  10u     VCC GND
R2    R    10k     VCC VB
R3    R    10k     VB GND
C3    C08  10u     VB GND
R4    R    2.2k    VB VBF
TP1   TP   VCC     VCC
TP2   TP   VREF    VREF
# --- op-amps: OUTA INA- INA+ V- INB+ INB- OUTB V+ ---
U1    U    TL072   IB IB INP GND VBF VREF VREF VCC
U2    U    NE5532  PO PN VREF GND SP SN S VCC
U3    U    TL072   CO CN DP GND VREF HN HX VS
U4    U    TL072   TB TB T GND VREF GN GO VCC
U5    U    TL072   V1 N1 VREF GND VREF N2 V2 VCC
U6    U    TL072   V3 N3 VREF GND VREF MN MO VCC
C4    C    100n    VCC GND
C5    C    100n    VCC GND
C6    C    100n    VS GND
C7    C    100n    VCC GND
C8    C    100n    VCC GND
C9    C    100n    VCC GND
# --- input buffer ---
J_IN  PAD  IN      IN
J_G2  PAD  GND     GND
R5    R    1M      IN GND
C10   C    100n    IN INA
R6    R    1M      INA VREF
R7    R    2.2k    INA INP
C11   C    100p    INP GND
# --- gain: inverting stage, unity at home ---
C12   C08  10u     IB IBC
R8    R    4.7k    IBC PN
R9    R    4.7k    PN PO
C13   C    47p     PN PO
SW1   SW   GAIN_9  GU9 PN GD9
R10   R    1k      IBC GU9
R11   R    1k      GD9 PO
SW2   SW   GAIN_3  GU3 PN GD3
R12   R    2.7k    IBC GU3
R13   R    2.7k    GD3 PO
SW3   SW   GAIN_1  GU1 PN GD1
R14   R    8.2k    IBC GU1
R15   R    8.2k    GD1 PO
# --- half-wave rectifier for the octave: HO = -max(PO, 0) ---
R16   R    10k     PO HN
R17   R    10k     HN HO
D2    D    1N4148W HX HN
D3    D    1N4148W HO HX
SW18  SW   OCTAVE  OCD HO OCM
R18   R    4.7k    OCD SN
R19   R    4.7k    OCD SN
R20   R    7.5k    OCM MN
# --- summer: S = -PO, or |PO| with OCTAVE up; its + input takes the negative feedback ---
R21   R    4.7k    PO SN
R22   R    4.7k    SN S
C14   C    47p     SN S
R23   R    2.2k    SP VREF
R24   R    20k     FN SP
# --- bass: high-pass into the drive stage, 720 Hz at home ---
C15   C    10n     S DP
R25   R    22k     DP VREF
SW6   SW   BASS_3  BU3 DP BD3
C16   C    47n     S BU3
C17   C    22n     S BU3
R26   R    10M     BU3 VREF
R27   R    15k     BD3 VREF
SW7   SW   BASS_1  BU1 DP BD1
C18   C    22n     S BU1
R28   R    10M     BU1 VREF
R29   R    47k     BD1 VREF
# --- drive stage, fixed gain; red LEDs are always in the loop ---
R30   R    150k    CN CO
C19   C    47p     CN CO
LED2  LED  RED     CO CN
LED3  LED  RED     CN CO
SW4   SW   DIODE_+ DPS CN DPT
D4    D    1N4148W CO DPS
D5    D    BAT54W  CO DPT
SW5   SW   DIODE_- DNS CN DNT
D6    D    1N4148W DNS CO
D7    D    BAT54W  DNT CO
C20   C08  10u     CN CNF
R31   R    33k     CNF VREF
C21   C    1u      CO CA
R32   R    100k    CA VREF
# --- treble: low-pass after the drive stage, 3.4 kHz at home ---
R33   R    10k     CA T
C22   C    4.7n    T GND
SW8   SW   TREBLE_3 TU3 T TD3
R34   R    7.5k    TU3 CA
C23   C    10n     TD3 GND
C24   C    4.7n    TD3 GND
R35   R    10M     TD3 VREF
SW9   SW   TREBLE_1 TU1 T TD1
R36   R    22k     TU1 CA
C25   C    4.7n    TD1 GND
R37   R    10M     TD1 VREF
# --- hard clipper ---
SW10  SW   CLIP    HS T HT
D8    D    1N4148W HS VREF
D9    D    1N4148W VREF HS
D10   D    BAT54W  HT VREF
D11   D    BAT54W  VREF HT
# --- resonator: Tow-Thomas band-pass fed from the drive stage, D5 (587 Hz) at home ---
R38   R    1M      CA N1
R39   R    1M      N1 V1
C26   C    1n_NP0  N1 V1
R40   R    270k    V3 N1
SW14  SW   PITCH_3 PU3 N1 PD3
R41   R    91k     PU3 V3
C27   C    1n_NP0  PD3 V1
C28   C    1n_NP0  PD3 V1
C29   C    1n_NP0  PD3 V1
R42   R    10M     PD3 VREF
R43   R    270k    V1 N2
C30   C    1n_NP0  N2 V2
SW15  SW   PITCH_1 PU1 N2 PD1
R44   R    680k    PU1 V1
C31   C    330p    PD1 V2
C32   C    330p    PD1 V2
C33   C    100p    PD1 V2
R45   R    10M     PD1 VREF
R46   R    120k    V2 N3
R47   R    68k     N3 TN
RV3   RV   100k    TN V3 V3
TP3   TP   BP      V1
# --- feedback: amount, then sign picks where it goes back in ---
R48   R    6.8k    V1 FA
R49   R    4.7k    FA VREF
SW12  SW   AMOUNT_3 AU3 FA AD3
R50   R    2.2k    AU3 V1
R51   R    1.5k    AD3 VREF
SW13  SW   AMOUNT_1 AU1 FA AD1
R52   R    6.8k    AU1 V1
R53   R    4.7k    AD1 VREF
SW11  SW   SIGN    FP FA FN
R54   R    27k     FJ CNF
RV2   RV   100k    FP FJ FJ
# --- burst: Q1 normally shorts BX to VREF; BURST up turns it off ---
R55   R    15k     CNF BX
R56   R    4.7k    BX V1
Q1    Q    2N7002  BG VREF BX
R57   R    100k    VCC BG
C34   C    10n     BG VREF
SW20  SW   BURST   BG VREF MK
# --- gate: U4B makes an inverted, limited copy of TB that cancels small signals ---
R58   R    22k     TB GN
R59   R    100k    GN GO
D12   D    1N4148W GN GO
D13   D    1N4148W GO GN
SW17  SW   GATE    GH GO GS
R60   R    100k    GH MN
R61   R    220k    GS MN
# --- mixer, Level and output ---
R62   R    22k     TB MN
R63   R    47k     MN MO
C35   C    100p    MN MO
SW19  SW   BLEND   S BL PO
R64   R    15k     BL MN
R65   R    1k      MO MK
C36   C08  10u     MK LV
RV1   POT  A10K_LEVEL GND LW LV
R66   R    100R    LW OUT
J_OUT PAD  OUT     OUT
J_G3  PAD  GND     GND
# --- sag: supply of the drive op-amp (U3) only ---
R67   R    220R    V9R VS
R68   R    220R    V9R VS
C37   C08  10u     VS GND
SW16  SW   SAG     SG1 VS SG2
R69   R    1k      SG1 GND
R70   R    1k      SG1 GND
R71   R    1k      SG1 GND
R72   R    560R    SG2 GND
R73   R    560R    SG2 GND
R74   R    1k      SG2 GND
# --- indicator LED ---
R75   R    3.3k    VCC LA
LED1  LEDT LED     LA LK
J_L   PAD  LED     LK
J_G4  PAD  GND     GND
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
    refs = Counter(p["ref"] for p in ps)
    print("duplicate refs:", [r for r, n in refs.items() if n > 1])
    for n, pins in sorted(nets.items()):
        if len(pins) < 2 and not n.startswith("NC"):
            print("SINGLE-PIN NET:", n, pins)
    smd = [p for p in ps if p["kind"] not in ("POT", "SW", "LEDT", "PAD", "TP")]
    missing = [p["ref"] for p in smd if not p["lcsc"]]
    print("missing LCSC:", missing)
    c = Counter((p["kind"], p["value"], p["lcsc"]) for p in smd)
    print(len(c), "BOM lines,", len(smd), "placements")
