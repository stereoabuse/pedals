"""Master design data: every part, its value, JLC part number and net connections.

One-knob overdrive: a Tube Screamer with Drive fixed at zero and Level fixed at
maximum. The transistor buffers of the original are op-amp followers here.
"""

NAME = "SCREAMER"
REV = "A"

# kind -> (footprint, pad names in order)
KINDS = {
    "R":    ("Resistor_SMD:R_0603_1608Metric", "1 2"),
    "C":    ("Capacitor_SMD:C_0603_1608Metric", "1 2"),
    "C08":  ("Capacitor_SMD:C_0805_2012Metric", "1 2"),
    "D":    ("Diode_SMD:D_SOD-123", "2 1"),                    # listed A K
    "U":    ("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "1 2 3 4 5 6 7 8"),
    "TP":   ("TestPoint:TestPoint_Pad_D1.5mm", "1"),
    "POT":  ("custom:POT16", "1 2 3"),
    "LEDT": ("custom:LED3", "2 1"),                            # listed A K
    "PAD":  ("custom:WIREPAD", "1"),
}

LCSC = {
    ("R", "22R"): "C23345", ("R", "100R"): "C22775", ("R", "220R"): "C22962", ("R", "1k"): "C21190",
    ("R", "3.3k"): "C22978", ("R", "4.7k"): "C23162", ("R", "10k"): "C25804", ("R", "51k"): "C23196",
    ("R", "510k"): "C23192", ("R", "1M"): "C22935",
    ("C", "47p"): "C1671", ("C", "6.8n"): "C1631", ("C", "22n"): "C21122", ("C", "33n"): "C21117", ("C", "100n"): "C14663",
    ("C", "220n"): "C21120", ("C", "1u"): "C15849", ("C08", "10u"): "C15850",
    ("D", "1N4148W"): "C81598", ("D", "B5819W"): "C8598", ("U", "TL072"): "C6961",
}

# ref kind value nets...   (pads in the order given in KINDS)
NETLIST = """
# --- power ---
J_9V  PAD  +9V     VIN
J_G1  PAD  GND     GND
D1    D    B5819W  VIN V9R
R20   R    22R     V9R V9
C20   C08  10u     V9 GND
C21   C08  10u     V9 GND
C22   C    100n    V9 GND
C23   C    100n    V9 GND
R21   R    10k     V9 VREF
R22   R    10k     VREF GND
C24   C08  10u     VREF GND
TP1   TP   9V      V9
TP2   TP   VREF    VREF
# --- op-amps: OUTA INA- INA+ V- INB+ INB- OUTB V+ ---
U1    U    TL072   B1 B1 NA GND CP CN CO V9
U2    U    TL072   TO TN T1 GND TO ON OUTA V9
# --- input buffer ---
J_IN  PAD  IN      IN
R1    R    1M      IN GND
C1    C    22n     IN NA
R2    R    510k    NA VREF
# --- clipping stage, Drive fixed at zero ---
C3    C    1u      B1 CP
R3    R    10k     CP VREF
R4    R    4.7k    CN RG
C4    C    33n     RG GND
C4B   C    6.8n    RG GND
R5    R    51k     CN CO
C5    C    47p     CN CO
D2    D    1N4148W CN CO
D3    D    1N4148W CO CN
# --- tone ---
R6    R    1k      CO T1
C6    C    220n    T1 GND
R7    R    1k      TN TO
RV1   POT  W20K_TONE T1 TW TN
R8    R    220R    TW TX
C7    C    220n    TX GND
# --- output, Level fixed at maximum ---
R9    R    3.3k    ON OUTA
R10   R    10k     ON OG
C8    C08  10u     OG GND
C9    C08  10u     OUTA OC
R11   R    100R    OC OUT
R12   R    10k     OUT GND
J_OUT PAD  OUT     OUT
J_G2  PAD  GND     GND
J_G3  PAD  GND     GND
J_G4  PAD  GND     GND
# --- indicator LED ---
R13   R    3.3k    V9 LA
LED1  LEDT LED     LA LK
J_L   PAD  LED     LK
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
