"""1:1 drill template for a 1590BB enclosure face, seen from the FRONT (knob side)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
PL = json.load(open(os.path.join(HERE, "placement.json")))
W, L = 94.0, 119.5                       # 1590BB face, portrait
NAMES = {"RV1": "DRIVE", "RV2": "TONE", "RV3": "LEVEL", "RV4": "SUSTAIN", "RV5": "TONE", "RV6": "VOLUME",
         "SW1": "ORDER", "LED1": "LED", "LED2": "LED"}
holes = []                                # (name, x_front, y_front, dia)
for r, (x, y) in PL["pots"].items(): holes.append((NAMES[r], 100 - x, 100 - y, 7.5))
for r, (x, y) in PL["sws"].items(): holes.append((NAMES[r], 100 - x, 100 - y, 6.5))
for r, (x, y) in PL["leds"].items(): holes.append((NAMES[r], 100 - x, 100 - y, 3.2))
holes += [("SCREAMER", 27.0, -43.0, 12.5), ("MUFF", -27.0, -43.0, 12.5)]
m = 10
def X(x): return m + W / 2 + x
def Y(y): return m + L / 2 - y
s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W+2*m}mm" height="{L+2*m+14}mm" viewBox="0 0 {W+2*m} {L+2*m+14}" font-family="Helvetica" font-size="2.6">',
     f'<rect x="{m}" y="{m}" width="{W}" height="{L}" rx="4" fill="none" stroke="black" stroke-width="0.2"/>',
     f'<line x1="{X(0)}" y1="{m}" x2="{X(0)}" y2="{m+L}" stroke="#999" stroke-width="0.1" stroke-dasharray="1 1"/>',
     f'<line x1="{m}" y1="{Y(0)}" x2="{m+W}" y2="{Y(0)}" stroke="#999" stroke-width="0.1" stroke-dasharray="1 1"/>',
     f'<rect x="{X(-13.25)}" y="{Y(-3.5)}" width="26.5" height="53" fill="none" stroke="#99c" stroke-width="0.15" stroke-dasharray="2 1"/>',
     f'<text x="{X(0)}" y="{Y(-30)}" text-anchor="middle" fill="#669">9V battery (inside)</text>']
rows = []
for name, x, y, d in sorted(holes, key=lambda h: (-h[2], h[1])):
    s.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{d/2}" fill="none" stroke="black" stroke-width="0.2"/>')
    s.append(f'<path d="M{X(x)-1.5:.2f} {Y(y):.2f}h3M{X(x):.2f} {Y(y)-1.5:.2f}v3" stroke="black" stroke-width="0.12"/>')
    s.append(f'<text x="{X(x):.2f}" y="{Y(y)+d/2+3.2:.2f}" text-anchor="middle">{name} {d:g}</text>')
    rows.append(f"| {name} | {x:+.1f} | {y:+.1f} | {d:g} |")
s.append(f'<text x="{m}" y="{m+L+5}">1590BB face, FRONT view, 1:1 (print at 100%). mm from face centre: x right, y up.</text>')
s.append(f'<text x="{m}" y="{m+L+9}">Jacks and DC socket go on the top end; mark those from the parts you buy.</text>')
s.append(f'<line x1="{m}" y1="{m+L+12}" x2="{m+50}" y2="{m+L+12}" stroke="black" stroke-width="0.3"/><text x="{m+52}" y="{m+L+13}">50 mm check</text>')
s.append("</svg>")
out = os.path.join(os.path.dirname(HERE), "docs", "drill-template-1590BB.svg")
open(out, "w").write("\n".join(s))
print("| Hole | x mm | y mm | dia mm |\n|---|---|---|---|\n" + "\n".join(rows))
