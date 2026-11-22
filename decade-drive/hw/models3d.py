"""Tiny VRML generators for the hand-soldered parts, so 3D renders show them. Units: mm."""
import math, os

def _shape(points, faces, rgb, shiny=0.4):
    pts = ", ".join("%.3f %.3f %.3f" % p for p in points)
    fcs = ", ".join(" ".join(str(i) for i in f) + " -1" for f in faces)
    return ("Shape { appearance Appearance { material Material { diffuseColor %.2f %.2f %.2f "
            "specularColor 0.5 0.5 0.5 shininess %.2f } } geometry IndexedFaceSet { solid FALSE "
            "coord Coordinate { point [ %s ] } coordIndex [ %s ] } }\n") % (*rgb, shiny, pts, fcs)

def cyl(x, y, z0, z1, r, rgb, n=28):
    pts, faces = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        pts += [(x + r * math.cos(a), y + r * math.sin(a), z0), (x + r * math.cos(a), y + r * math.sin(a), z1)]
    for k in range(n):
        a, b = 2 * k, 2 * ((k + 1) % n)
        faces.append((a, b, b + 1, a + 1))
    faces.append(tuple(range(0, 2 * n, 2))); faces.append(tuple(range(1, 2 * n, 2)))
    return _shape(pts, faces, rgb)

def box(x0, y0, z0, x1, y1, z1, rgb):
    p = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return _shape(p, f, rgb, 0.2)

STEEL, DARK, BLACK, BRASS = (0.72, 0.72, 0.74), (0.25, 0.25, 0.27), (0.08, 0.08, 0.08), (0.75, 0.62, 0.3)

def pot16():
    """Alpha RV16AF-41: origin at shaft axis on the board surface, pins toward -y (board +y), +z away from board."""
    s = cyl(0, 0, 1.6, 10.7, 8.25, STEEL) + cyl(0, 0, 10.7, 17.2, 3.5, BRASS) + cyl(0, 0, 17.2, 25.7, 3.0, STEEL)
    s += box(-7.2, -16.6, 3.5, 7.2, -6, 6.0, DARK)
    for dx in (-5, 0, 5):
        s += box(dx - 0.5, -16.4, -3.0, dx + 0.5, -15.6, 4.0, BRASS)
    return s

def toggle():
    """Mini toggle, lugs in a line along y, lever centred (on-off-on at rest)."""
    s = box(-4, -6.5, 0.3, 4, 6.5, 9.8, (0.1, 0.25, 0.6)) + cyl(0, 0, 9.8, 18.6, 3.0, STEEL) + cyl(0, 0, 18.6, 29.0, 1.4, STEEL)
    for dy in (-4.7, 0, 4.7):
        s += box(-0.4, dy - 1.0, -3.2, 0.4, dy + 1.0, 0.3, BRASS)
    return s

def write_all(folder):
    os.makedirs(folder, exist_ok=True)
    for name, fn in (("pot16", pot16), ("toggle", toggle)):
        open(os.path.join(folder, name + ".wrl"), "w").write("#VRML V2.0 utf8\n" + fn())
