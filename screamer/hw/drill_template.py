"""1:1 drill template for a Hammond 1590B2 face, seen from the FRONT (knob side)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
PL = json.load(open(os.path.join(HERE, "placement.json")))
W, L = 60.0, 112.0                       # 1590B2 face, portrait
FSW = (0.0, -40.0)
holes = [("TONE", 100 - PL["pots"]["RV1"][0], 100 - PL["pots"]["RV1"][1], 7.5),
         ("LED", 100 - PL["leds"]["LED1"][0], 100 - PL["leds"]["LED1"][1], 3.2),
         ("FOOTSWITCH", FSW[0], FSW[1], 12.5)]
o = PL["outline"]
m = 10
def X(x): return m + W / 2 + x
def Y(y): return m + L / 2 - y
s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W+2*m}mm" height="{L+2*m+18}mm" viewBox="0 0 {W+2*m} {L+2*m+18}" font-family="Helvetica" font-size="2.4">',
     f'<rect x="{m}" y="{m}" width="{W}" height="{L}" rx="4" fill="none" stroke="black" stroke-width="0.2"/>',
     f'<line x1="{X(0)}" y1="{m}" x2="{X(0)}" y2="{m+L}" stroke="#999" stroke-width="0.1" stroke-dasharray="1 1"/>',
     f'<line x1="{m}" y1="{Y(0)}" x2="{m+W}" y2="{Y(0)}" stroke="#999" stroke-width="0.1" stroke-dasharray="1 1"/>',
     f'<rect x="{X(100-o["X1"])}" y="{Y(100-o["YT"])}" width="{o["X1"]-o["X0"]}" height="{o["YB"]-o["YT"]}" rx="1.5" fill="none" stroke="#9c9" stroke-width="0.15" stroke-dasharray="2 1"/>',
     f'<text x="{X(100-o["X1"])+1}" y="{Y(100-o["YT"])+3}" fill="#696">board (inside)</text>',
     f'<rect x="{X(-13.25)}" y="{Y(21)}" width="26.5" height="48.5" fill="none" stroke="#99c" stroke-width="0.15" stroke-dasharray="2 1"/>',
     f'<text x="{X(0)}" y="{Y(-25)}" text-anchor="middle" fill="#669">9V battery (behind the board)</text>']
rows = []
for name, x, y, d in holes:
    s.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{d/2}" fill="none" stroke="black" stroke-width="0.2"/>')
    s.append(f'<path d="M{X(x)-1.5:.2f} {Y(y):.2f}h3M{X(x):.2f} {Y(y)-1.5:.2f}v3" stroke="black" stroke-width="0.12"/>')
    s.append(f'<text x="{X(x):.2f}" y="{Y(y)+d/2+3:.2f}" text-anchor="middle">{name} {d:g}</text>')
    rows.append(f"| {name.title()} | {x:+.1f} | {y:+.1f} | {d:g} |")
s.append(f'<text x="{m}" y="{m+L+5}">1590B2 face, FRONT view, 1:1 (print at 100%). mm from face centre: x right, y up.</text>')
s.append(f'<text x="{m}" y="{m+L+9}">Jacks and DC socket go on the top end wall (suggested: jacks 19 mm either</text>')
s.append(f'<text x="{m}" y="{m+L+12}">side of centre, DC socket in the centre). Mark those from the parts you buy.</text>')
s.append(f'<line x1="{m}" y1="{m+L+16}" x2="{m+50}" y2="{m+L+16}" stroke="black" stroke-width="0.3"/><text x="{m+52}" y="{m+L+17}">50 mm check</text>')
s.append("</svg>")
os.makedirs(os.path.join(os.path.dirname(HERE), "docs"), exist_ok=True)
open(os.path.join(os.path.dirname(HERE), "docs", "drill-template-1590B2.svg"), "w").write("\n".join(s))
print("| Hole | x mm | y mm | dia mm |\n|---|---|---|---|\n" + "\n".join(rows))
