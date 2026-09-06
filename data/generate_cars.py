import os
from collections import defaultdict

OUT = "/Users/andrewfalcon/Desktop/dnHacks/data/cars"
os.makedirs(OUT, exist_ok=True)

class Mesh:
    def __init__(self):
        self.v = []
        self.f = defaultdict(list)

    def quad(self, mat, a, b, c, d):
        i = len(self.v)
        self.v += [a, b, c, d]
        self.f[mat].append((i + 1, i + 2, i + 3, i + 4))

    # Axis-aligned box; outward-facing quads (x=width, y=up, z=forward)
    def box(self, mat, x0, x1, y0, y1, z0, z1, mats=None, bottom=False):
        m = lambda face: (mats or {}).get(face, mat)
        self.quad(m("top"),   (x0,y1,z0), (x0,y1,z1), (x1,y1,z1), (x1,y1,z0))
        if bottom:
            self.quad(m("bottom"), (x0,y0,z0), (x1,y0,z0), (x1,y0,z1), (x0,y0,z1))
        self.quad(m("front"), (x0,y0,z1), (x1,y0,z1), (x1,y1,z1), (x0,y1,z1))
        self.quad(m("back"),  (x1,y0,z0), (x0,y0,z0), (x0,y1,z0), (x1,y1,z0))
        self.quad(m("right"), (x1,y0,z1), (x1,y0,z0), (x1,y1,z0), (x1,y1,z1))
        self.quad(m("left"),  (x0,y0,z0), (x0,y0,z1), (x0,y1,z1), (x0,y1,z0))

    # Tapered cabin: bottom rect -> smaller top rect (slanted windshield/rear)
    def loft(self, y0, y1, bx0, bx1, bz0, bz1, tx0, tx1, tz0, tz1, mats):
        self.quad(mats["top"],   (tx0,y1,tz0), (tx0,y1,tz1), (tx1,y1,tz1), (tx1,y1,tz0))
        self.quad(mats["front"], (bx0,y0,bz1), (bx1,y0,bz1), (tx1,y1,tz1), (tx0,y1,tz1))
        self.quad(mats["back"],  (bx1,y0,bz0), (bx0,y0,bz0), (tx0,y1,tz0), (tx1,y1,tz0))
        self.quad(mats["right"], (bx1,y0,bz1), (bx1,y0,bz0), (tx1,y1,tz0), (tx1,y1,tz1))
        self.quad(mats["left"],  (bx0,y0,bz0), (bx0,y0,bz1), (tx0,y1,tz1), (tx0,y1,tz0))

def wheels(m, half_w, z_front, z_rear, r=0.36, wl=0.62):
    for zc in (z_front, z_rear):
        for x0, x1 in ((half_w - 0.26, half_w + 0.02), (-half_w - 0.02, -half_w + 0.26)):
            m.box("tire", x0, x1, 0.0, r, zc - wl/2, zc + wl/2)

GLASS = {"top": "body", "front": "glass", "back": "glass", "left": "glass", "right": "glass"}

def sedan(m):
    m.box("body", -0.92, 0.92, 0.30, 0.95, -2.25, 2.25)
    m.loft(0.95, 1.42, -0.84, 0.84, -1.55, 1.05, -0.80, 0.80, -1.30, 0.55, GLASS)
    wheels(m, 0.92, 1.45, -1.45)

def hatchback(m):
    m.box("body", -0.88, 0.88, 0.32, 0.92, -1.95, 1.95)
    m.loft(0.92, 1.40, -0.80, 0.80, -1.70, 0.85, -0.76, 0.76, -1.50, 0.30, GLASS)
    wheels(m, 0.88, 1.20, -1.20, r=0.34)

def suv(m):
    m.box("body", -0.95, 0.95, 0.38, 1.12, -2.30, 2.30)
    m.loft(1.12, 1.80, -0.88, 0.88, -1.95, 1.30, -0.84, 0.84, -1.80, 0.85, GLASS)
    wheels(m, 0.95, 1.48, -1.48, r=0.42, wl=0.68)

def van(m):
    m.box("body", -0.95, 0.95, 0.32, 1.05, -2.50, 2.50)
    m.loft(1.05, 2.15, -0.90, 0.90, -2.42, 1.65, -0.86, 0.86, -2.38, 1.15,
           {"top": "body", "front": "glass", "back": "body", "left": "body", "right": "body"})
    wheels(m, 0.95, 1.60, -1.60, r=0.38)

def pickup(m):
    m.box("body", -0.95, 0.95, 0.38, 1.05, -2.60, 2.60)
    m.loft(1.05, 1.78, -0.88, 0.88, 0.10, 1.75, -0.84, 0.84, 0.25, 1.30, GLASS)
    m.box("body", -0.95, -0.74, 1.05, 1.38, -2.55, 0.05)   # bed walls
    m.box("body",  0.74,  0.95, 1.05, 1.38, -2.55, 0.05)
    m.box("body", -0.95,  0.95, 1.05, 1.38, -2.60, -2.40)  # tailgate
    wheels(m, 0.95, 1.65, -1.65, r=0.40, wl=0.68)

PALETTE = {"white": (0.91, 0.91, 0.90), "black": (0.07, 0.07, 0.08),
           "silver": (0.72, 0.73, 0.75), "red": (0.62, 0.10, 0.09),
           "blue": (0.13, 0.22, 0.50), "green": (0.13, 0.30, 0.18),
           "yellow": (0.85, 0.68, 0.10), "darkgray": (0.25, 0.26, 0.28)}
VARIANTS = [(sedan, "white"), (sedan, "black"), (sedan, "red"),
            (hatchback, "silver"), (hatchback, "blue"),
            (suv, "darkgray"), (suv, "green"),
            (van, "white"), (van, "yellow"), (pickup, "blue")]

for build, color in VARIANTS:
    m = Mesh()
    build(m)
    name = f"car_{build.__name__}_{color}"
    with open(f"{OUT}/{name}.mtl", "w") as f:
        r, g, b = PALETTE[color]
        f.write(f"newmtl body\nKd {r} {g} {b}\nKs 0.3 0.3 0.3\nNs 60\n\n")
        f.write("newmtl glass\nKd 0.10 0.13 0.18\nKs 0.5 0.5 0.5\nNs 120\n\n")
        f.write("newmtl tire\nKd 0.05 0.05 0.05\nKs 0 0 0\n\n")
    with open(f"{OUT}/{name}.obj", "w") as f:
        f.write(f"mtllib {name}.mtl\no {name}\n")
        # x negated + reversed winding: Unity's OBJ import mirrors X back
        for x, y, z in m.v:
            f.write(f"v {-x:.3f} {y:.3f} {z:.3f}\n")
        for mat, faces in m.f.items():
            f.write(f"usemtl {mat}\n")
            for face in faces:
                f.write("f " + " ".join(str(i) for i in reversed(face)) + "\n")
    print(f"{name}.obj: {len(m.v)} verts")
