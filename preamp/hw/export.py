"""Produce everything JLCPCB needs (fab/) plus renders and drawings (docs/)."""
import csv, json, os, re, shutil, subprocess, zipfile
from collections import defaultdict
from design import parts

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PCB = os.path.join(HERE, "pedal.kicad_pcb")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
FAB, DOCS, GERB = os.path.join(ROOT, "fab"), os.path.join(ROOT, "docs"), os.path.join(ROOT, "fab", "gerbers")
NAME = "preamp-revA"

def run(*a):
    r = subprocess.run([CLI, *a], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("kicad-cli failed: " + " ".join(a) + "\n" + r.stdout + r.stderr)

# JLC's "0 degrees" differs from KiCad's for some packages (values from the widely used JLC rotation table)
ROT_FIX = [(r"^SOT-23", 180), (r"^SOIC-", 270), (r"^CP_Elec_", 180)]
SMD_KINDS = {"R", "C", "C08", "C12", "CP", "D", "LED", "U", "Q", "RV"}

def main():
    shutil.rmtree(FAB, ignore_errors=True)
    os.makedirs(GERB); os.makedirs(DOCS, exist_ok=True)
    run("pcb", "export", "gerbers", "-o", GERB + "/", "--layers",
        "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
        "--no-x2", "--no-netlist", "--subtract-soldermask", "--use-drill-file-origin", PCB)
    run("pcb", "export", "drill", "-o", GERB + "/", "--format", "excellon", "--drill-origin", "plot",
        "--excellon-units", "mm", "--excellon-separate-th", "--generate-map", "--map-format", "pdf", PCB)
    for f in os.listdir(GERB):
        if f.endswith(".gbrjob") or f.endswith(".pdf"):
            (shutil.move(os.path.join(GERB, f), os.path.join(DOCS, "drill-map-" + f)) if f.endswith(".pdf") else os.remove(os.path.join(GERB, f)))
    with zipfile.ZipFile(os.path.join(FAB, NAME + "-gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(GERB)):
            z.write(os.path.join(GERB, f), f)

    # placement file
    pos = os.path.join(FAB, "pos-raw.csv")
    run("pcb", "export", "pos", "-o", pos, "--format", "csv", "--units", "mm", "--side", "front",
        "--use-drill-file-origin", "--exclude-dnp", PCB)
    ps = {p["ref"]: p for p in parts()}
    rows = []
    for r in csv.DictReader(open(pos)):
        p = ps.get(r["Ref"])
        if not p or p["kind"] not in SMD_KINDS:
            continue
        rot = float(r["Rot"])
        for pat, add in ROT_FIX:
            if re.match(pat, r["Package"]):
                rot = (rot + add) % 360
        rows.append([r["Ref"], "%.4fmm" % float(r["PosX"]), "%.4fmm" % float(r["PosY"]), "Top", "%g" % rot])
    os.remove(pos)
    with open(os.path.join(FAB, NAME + "-cpl.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]); w.writerows(sorted(rows))

    # BOM grouped by JLC part number
    groups = defaultdict(list)
    for p in ps.values():
        if p["kind"] in SMD_KINDS:
            groups[(p["value"], p["fp"].split(":")[1], p["lcsc"])].append(p["ref"])
    with open(os.path.join(FAB, NAME + "-bom.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
            w.writerow([val, ",".join(sorted(refs, key=lambda s: (re.sub(r"\d.*", "", s), int(re.search(r"\d+", s).group())))), fp, lcsc])
    assert len(rows) == sum(len(v) for v in groups.values()), "CPL and BOM disagree"
    print(len(rows), "placements,", len(groups), "BOM lines")

    # renders
    R = [("render-smd-side.png", ["--side", "top"]),
         ("render-control-side.png", ["--side", "bottom"]),
         ("render-smd-perspective.png", ["--side", "top", "--rotate", "-45,0,20", "--perspective"]),
         ("render-control-perspective.png", ["--side", "bottom", "--rotate", "-50,0,-20", "--perspective"]),
         ("render-control-low.png", ["--side", "bottom", "--rotate", "-68,0,25", "--perspective"])]
    for name, opts in R:
        run("pcb", "render", "-o", os.path.join(DOCS, name), "-w", "2000", "-h", "1500", "--quality", "high",
            "--background", "opaque", *opts, PCB)
    # drawings
    run("pcb", "export", "pdf", "-o", os.path.join(DOCS, "assembly-smd-side.pdf"), "--layers", "F.Fab,F.SilkS,Edge.Cuts",
        "--mode-single", "--black-and-white", "--exclude-drawing-sheet" if False else "--drill-shape-opt", "1", PCB)
    for layer in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"):
        run("pcb", "export", "svg", "-o", os.path.join(DOCS, "copper-%s.svg" % layer.replace(".", "_")), "--layers",
            layer + ",Edge.Cuts", "--mode-single", "--page-size-mode", "2", "--exclude-drawing-sheet", PCB)

if __name__ == "__main__":
    main()
