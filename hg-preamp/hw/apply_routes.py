"""Run with KiCad's python: add routed tracks/vias to the board, fill zones, save."""
import json, os
import pcbnew
from pcbnew import FromMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "pedal.kicad_pcb")
R = json.load(open(os.path.join(HERE, "routes.json")))
board = pcbnew.LoadBoard(PCB)
for t in list(board.GetTracks()):
    board.Remove(t)
nets = board.GetNetsByName()
lid = {"F.Cu": pcbnew.F_Cu, "In2.Cu": pcbnew.In2_Cu, "B.Cu": pcbnew.B_Cu}
for x0, y0, x1, y1, layer, net in R["segs"]:
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(VECTOR2I(FromMM(x0), FromMM(y0))); t.SetEnd(VECTOR2I(FromMM(x1), FromMM(y1)))
    t.SetWidth(FromMM(R["track"])); t.SetLayer(lid[layer]); t.SetNet(nets[net]); board.Add(t)
for x, y, net in R["vias"]:
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(VECTOR2I(FromMM(x), FromMM(y))); v.SetWidth(pcbnew.F_Cu, FromMM(0.6)); v.SetDrill(FromMM(0.3))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(nets[net]); board.Add(v)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print(len(R["segs"]), "segments,", len(R["vias"]), "vias applied")
