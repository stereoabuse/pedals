"""Run with KiCad's python. Builds the unrouted board from design.py + placement.json,
then writes pads.json for the router."""
import json, math, os, sys
import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from design import parts, REV
import models3d
NAME = "HG PREAMP"

LIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
PL = json.load(open(os.path.join(HERE, "placement.json")))
O = PL["outline"]
OUT = os.path.join(HERE, "pedal.kicad_pcb")

TRACK, CLEAR, VIA, VIA_DRILL = 0.25, 0.2, 0.6, 0.3
POT_LABEL = {"RV1": "TIGHT", "RV2": "GAIN", "RV3": "PRES", "RV4": "TREBLE", "RV5": "MID", "RV6": "VOLUME"}
PAD_LABEL = {"J_IN": "IN", "J_G2": "G", "J_L1": "LED", "J_BOUT": "BO", "J_G3": "G", "J_BIN": "BI",
             "J_L2": "LED", "J_G5": "G", "J_9V": "+9V", "J_G1": "G", "J_G4": "G", "J_OUT": "OUT"}
SMD_LABEL = {"JP1": "18V  9V", "JP2": "GATE",
             "TP1": "VCC", "TP2": "VREF", "TP3": "9V"}


def P(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def text(board, s, x, y, layer, size=1.0, thick=0.15, rot=0, mirror=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s); t.SetPosition(P(x, y)); t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size))); t.SetTextThickness(FromMM(thick))
    t.SetTextAngleDegrees(rot)
    if mirror is None:
        mirror = layer in (pcbnew.B_SilkS, pcbnew.B_Fab, pcbnew.B_Cu)
    t.SetMirrored(mirror)
    board.Add(t)
    return t


def line(board, x0, y0, x1, y1, layer, w=0.15):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(x0, y0)); s.SetEnd(P(x1, y1)); s.SetLayer(layer); s.SetWidth(FromMM(w)); board.Add(s)


def circle(board, x, y, r, layer, w=0.15):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(P(x, y)); s.SetEnd(P(x + r, y)); s.SetLayer(layer); s.SetWidth(FromMM(w)); board.Add(s)


def outline_pts(r_out=1.5, r_in=1.0):
    """Board outline polygon (clockwise on screen) with rounded corners."""
    X0, X1, YT, YM, YB, LL, LR = O["X0"], O["X1"], O["YT"], O["YM"], O["YB"], O["LEG_L"], O["LEG_R"]
    corners = [(X0, YT, r_out), (X1, YT, r_out), (X1, YB, r_out), (LR, YB, r_out), (LR, YM, r_in),
               (LL, YM, r_in), (LL, YB, r_out), (X0, YB, r_out)]
    pts = []
    n = len(corners)
    for i, (x, y, r) in enumerate(corners):
        px, py, _ = corners[i - 1]; nx, ny, _ = corners[(i + 1) % n]
        d1 = math.hypot(px - x, py - y); d2 = math.hypot(nx - x, ny - y)
        a = (x + (px - x) / d1 * r, y + (py - y) / d1 * r)
        b = (x + (nx - x) / d2 * r, y + (ny - y) / d2 * r)
        for k in range(7):                       # quadratic bezier is close enough at this radius
            t = k / 6
            pts.append(((1 - t) ** 2 * a[0] + 2 * t * (1 - t) * x + t * t * b[0],
                        (1 - t) ** 2 * a[1] + 2 * t * (1 - t) * y + t * t * b[1]))
    return pts


def tht_pad(fp, num, x, y, dia, drill, net):
    pad = pcbnew.PAD(fp)
    pad.SetNumber(num); pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetShape(pcbnew.F_Cu, pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.F_Cu, VECTOR2I(FromMM(dia), FromMM(dia)))
    pad.SetDrillSize(VECTOR2I(FromMM(drill), FromMM(drill)))
    pad.SetLayerSet(pad.PTHMask()); pad.SetPosition(P(x, y)); pad.SetNet(net)
    fp.Add(pad)


def main():
    models3d.write_all(os.path.join(HERE, "3d"))
    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(4)
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    ds = board.GetDesignSettings()
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(FromMM(CLEAR)); nc.SetTrackWidth(FromMM(TRACK))
    nc.SetViaDiameter(FromMM(VIA)); nc.SetViaDrill(FromMM(VIA_DRILL))
    ds.m_TrackMinWidth = FromMM(0.15); ds.m_ViasMinSize = FromMM(0.45); ds.m_MinThroughDrill = FromMM(0.25)
    ds.m_CopperEdgeClearance = FromMM(0.3); ds.m_MinClearance = FromMM(0.15)
    ds.m_HoleClearance = FromMM(0.2); ds.m_HoleToHoleMin = FromMM(0.25)
    ds.m_SolderMaskExpansion = FromMM(0.05)
    ds.SetAuxOrigin(P(O["X0"], O["YB"]))

    # outline
    pts = outline_pts()
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        line(board, a[0], a[1], b[0], b[1], pcbnew.Edge_Cuts, 0.1)

    nets = {}
    def net(name):
        if name.startswith("NC"):
            return None
        if name not in nets:
            ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni); nets[name] = ni
        return nets[name]

    ps = parts()
    for p in ps:
        ref, kind = p["ref"], p["kind"]
        if kind in ("POT", "SW", "PAD"):
            fp = pcbnew.FOOTPRINT(board)
            fp.SetReference(ref); fp.SetValue(p["value"])
            pads = PL["tht"][ref]
            cx = sum(v[0] for v in pads.values()) / len(pads); cy = sum(v[1] for v in pads.values()) / len(pads)
            fp.SetPosition(P(cx, cy))
            fp.SetAttributes(pcbnew.FP_THROUGH_HOLE | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
            for num, (x, y, dia, drill) in pads.items():
                n = net(p["pins"][num])
                tht_pad(fp, num, x, y, dia, drill, n)
            fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
            fp.Reference().SetLayer(pcbnew.F_Fab); fp.Value().SetLayer(pcbnew.F_Fab)
            board.Add(fp)
            if kind in ("POT", "SW"):
                sx, sy = PL["pots" if kind == "POT" else "sws"][ref]
                m = pcbnew.FP_3DMODEL()
                m.m_Filename = "${KIPRJMOD}/3d/%s.wrl" % ("pot16" if kind == "POT" else "toggle")
                m.m_Scale = pcbnew.VECTOR3D(1 / 2.54, 1 / 2.54, 1 / 2.54)
                m.m_Rotation = pcbnew.VECTOR3D(0, 180, 0)        # hangs off the back of the board
                m.m_Offset = pcbnew.VECTOR3D(sx - cx, -(sy - cy), -1.6)
                fp.Models().push_back(m)
            if kind == "POT":
                sx, sy = PL["pots"][ref]
                circle(board, sx, sy, 8.5, pcbnew.B_SilkS)
                line(board, sx - 1, sy, sx + 1, sy, pcbnew.B_SilkS); line(board, sx, sy - 1, sx, sy + 1, pcbnew.B_SilkS)
                taper = p["value"].split()[0]
                text(board, POT_LABEL[ref], sx, sy - 3.2, pcbnew.B_SilkS, 1.4, 0.2)
                text(board, taper, sx, sy + 3.2, pcbnew.B_SilkS, 1.2, 0.18)
                text(board, POT_LABEL[ref], sx, sy + 13.2, pcbnew.F_SilkS, 0.9, 0.15)
                text(board, "1", sx + 5, sy + 18.2, pcbnew.B_SilkS, 0.8, 0.12)
            elif kind == "SW":
                sx, sy = PL["sws"][ref]
                for (xa, ya, xb, yb) in ((-6.6, -4, 6.6, -4), (6.6, -4, 6.6, 4), (6.6, 4, -6.6, 4), (-6.6, 4, -6.6, -4)):
                    line(board, sx + xa, sy + ya, sx + xb, sy + yb, pcbnew.B_SilkS)
                text(board, p["value"], sx, sy + 3.0, pcbnew.F_SilkS, 0.9, 0.15)
            else:
                x, y = pads["1"][0], pads["1"][1]
                text(board, PAD_LABEL[ref], x, y - 1.9, pcbnew.F_SilkS, 0.8, 0.13)
            continue

        if kind == "LEDT":
            fp = pcbnew.FootprintLoad(os.path.join(LIB, "LED_THT.pretty"), "LED_D3.0mm")
            x, y = PL["leds"][ref]
            fp.SetReference(ref); fp.SetValue(p["value"])
            fp.SetPosition(P(x - 1.27, y))
            board.Add(fp)
            fp.Flip(P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetAttributes(pcbnew.FP_THROUGH_HOLE | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
            fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
            for pad in fp.Pads():
                pad.SetNet(net(p["pins"][pad.GetNumber()]))
            text(board, p["value"], x, y - 2.6, pcbnew.F_SilkS, 0.8, 0.13)
            continue

        lib, name = p["fp"].split(":")
        fp = pcbnew.FootprintLoad(os.path.join(LIB, lib + ".pretty"), name)
        fp.SetReference(ref); fp.SetValue(p["value"])
        if ref in PL["fixed"]:
            x, y, rot = PL["fixed"][ref]
        else:
            x, y, orient, flip = PL["small"][ref]
            rot = (270 if orient == "v" else 0) + (180 if flip else 0)
            if kind == "TP":                     # pad in the left half of its double slot, label in the right half
                x -= 1.3
        fp.SetPosition(P(x, y)); fp.SetOrientationDegrees(rot)
        board.Add(fp)
        if ref in PL["small"] and len(p["pins"]) == 2:       # check the rotation convention
            p1 = [q for q in fp.Pads() if q.GetNumber() == "1"][0].GetPosition()
            want_first = not PL["small"][ref][3]
            first = (ToMM(p1.y) < y - 0.1) if PL["small"][ref][2] == "v" else (ToMM(p1.x) < x - 0.1)
            assert first == want_first, f"rotation convention wrong for {ref}"
        for pad in fp.Pads():
            n = p["pins"].get(pad.GetNumber())
            if n and net(n):
                pad.SetNet(net(n))
        if p["lcsc"]:
            fp.SetField("LCSC", p["lcsc"]); fp.GetField("LCSC").SetVisible(False)
        # silkscreen: keep only useful labels; refs go to the fab layer
        fp.Reference().SetLayer(pcbnew.F_Fab); fp.Reference().SetPosition(P(x, y))
        fp.Reference().SetTextSize(VECTOR2I(FromMM(0.45), FromMM(0.45))); fp.Reference().SetTextThickness(FromMM(0.07))
        fp.Reference().SetTextAngleDegrees(90 if (ref in PL["small"] and PL["small"][ref][2] == "v") else 0)
        fp.Value().SetVisible(False)
        if kind == "U":
            text(board, ref, x, y, pcbnew.F_SilkS, 0.8, 0.13)
        if ref in PL["trim_label"]:
            t, dy = PL["trim_label"][ref]
            text(board, t, x, y + dy, pcbnew.F_SilkS, 0.8, 0.13)
        if ref in SMD_LABEL:
            dy = {"JP3": -2.0, "JP2": 0, "TP": 0}[kind]
            if kind in ("JP2", "TP"):
                text(board, SMD_LABEL[ref], x + (-3.85 if kind == "JP2" else 2.3), y, pcbnew.F_SilkS, 0.8, 0.13)
            else:
                text(board, SMD_LABEL[ref], x, y + dy, pcbnew.F_SilkS, 0.8, 0.13)

    # branding
    lx, ly, _ = PL["logo"]
    for poly in json.load(open(os.path.join(HERE, "logo.json")))["polys"]:
        sps = pcbnew.SHAPE_POLY_SET(); sps.NewOutline()
        for (x, y) in poly["outer"]:
            sps.Append(FromMM(lx + x), FromMM(ly + y))
        for hole in poly["holes"]:
            h = sps.NewHole()
            for (x, y) in hole:
                sps.Append(FromMM(lx + x), FromMM(ly + y), -1, h)
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_POLY); s.SetPolyShape(sps)
        s.SetFilled(True); s.SetWidth(0); s.SetLayer(pcbnew.F_SilkS); board.Add(s)
    text(board, "stereoabuse", 81.6, 112.0, pcbnew.B_SilkS, 2.0, 0.3, rot=90)
    text(board, "stereoabuse", PL["credit"][0], PL["credit"][1], pcbnew.F_SilkS, 1.1, 0.17)
    text(board, f"{NAME} rev {REV}", 118.6, 112.0, pcbnew.B_SilkS, 1.3, 0.2, rot=90)
    text(board, "9V DC ONLY", 100.0, 88.3, pcbnew.B_SilkS, 0.9, 0.15)
    text(board, "CENTER NEG", 100.0, 90.0, pcbnew.B_SilkS, 0.9, 0.15)

    # ground zones on every copper layer
    for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer); z.SetNet(nets["GND"]); z.SetZoneName("GND")
        ol = z.Outline(); ol.NewOutline()
        for (x, y) in ((O["X0"] - 1, O["YT"] - 1), (O["X1"] + 1, O["YT"] - 1), (O["X1"] + 1, O["YB"] + 1), (O["X0"] - 1, O["YB"] + 1)):
            ol.Append(FromMM(x), FromMM(y))
        z.SetLocalClearance(FromMM(0.25)); z.SetMinThickness(FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(FromMM(0.25)); z.SetThermalReliefSpokeWidth(FromMM(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)

    pcbnew.SaveBoard(OUT, board)

    # pad dump for the router
    pads = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            pos = pad.GetPosition()
            pads.append(dict(ref=fp.GetReference(), num=pad.GetNumber(), net=pad.GetNetname(),
                             x=ToMM(pos.x), y=ToMM(pos.y), w=ToMM(bb.GetWidth()), h=ToMM(bb.GetHeight()),
                             tht=pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH,
                             round=pad.GetShape(pcbnew.F_Cu) == pcbnew.PAD_SHAPE_CIRCLE))
    json.dump(dict(pads=pads, outline=O, rules=dict(track=TRACK, clear=CLEAR, via=VIA, via_drill=VIA_DRILL)),
              open(os.path.join(HERE, "pads.json"), "w"))
    print(len(board.GetFootprints()), "footprints,", len(pads), "pads,", len(nets), "nets ->", OUT)


main()
