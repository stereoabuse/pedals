"""Trace art/manat-logo.jpg into filled polygons for the silkscreen (logo.json, mm, centred on 0,0).
Run: uv run --with opencv-python-headless python3 hw/logo.py"""
import json, os
import cv2, numpy as np
from place import LOGO, LOGO_ASPECT

HERE = os.path.dirname(os.path.abspath(__file__))
WIDTH = LOGO[2]                 # mm
PX = 0.01                       # mm per pixel while processing
GROW = 0.04                     # mm added to every edge so thin strokes survive printing (min ~0.15 mm)
MIN_AREA = 0.03                 # mm^2; smaller specks and holes are dropped

g = cv2.imread(os.path.join(HERE, "art", "manat-logo.jpg"), cv2.IMREAD_GRAYSCALE)
ys, xs = np.where(g < 128)
g = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
w = int(round((WIDTH - 2 * GROW) / PX)); h = int(round(w * g.shape[0] / g.shape[1]))
g = cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
m = (g < 128).astype(np.uint8)
k = int(round(GROW / PX))
m = cv2.copyMakeBorder(m, k + 2, k + 2, k + 2, k + 2, cv2.BORDER_CONSTANT, value=0)
m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
H, W = m.shape
assert H / W <= LOGO_ASPECT, H / W
cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

def pts(c):
    c = cv2.approxPolyDP(c, 1.2, True)
    return [[round((x - W / 2) * PX, 3), round((y - H / 2) * PX, 3)] for x, y in c[:, 0, :]]

polys = []
for i, c in enumerate(cs):
    if hier[0][i][3] != -1 or cv2.contourArea(c) * PX * PX < MIN_AREA:
        continue
    holes = []
    j = hier[0][i][2]
    while j != -1:
        if cv2.contourArea(cs[j]) * PX * PX >= MIN_AREA and len(pts(cs[j])) >= 3:
            holes.append(pts(cs[j]))
        j = hier[0][j][0]
    polys.append(dict(outer=pts(c), holes=holes))
json.dump(dict(width=W * PX, height=H * PX, polys=polys), open(os.path.join(HERE, "logo.json"), "w"))
print(len(polys), "polygons,", sum(len(p["holes"]) for p in polys), "holes,",
      sum(len(p["outer"]) + sum(map(len, p["holes"])) for p in polys), "points, %.1f x %.1f mm" % (W * PX, H * PX))
cv2.imwrite("/private/tmp/claude-503/-Users-chrisbowman-Documents-code-pedals/96c4262e-272b-48b7-a97c-8e80a08b9df1/scratchpad/logo-mask.png", 255 - m * 255)
