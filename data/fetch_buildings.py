import json, math, urllib.request
from collections import defaultdict
import numpy as np
from PIL import Image

# Same georeferencing as the terrain conversion
DEG = 0.0002777777777777778
WEST, NORTH = 37.79722221111111, 48.01805556666666
W_PX, H_PX = 219, 113
EAST, SOUTH = WEST + W_PX * DEG, NORTH - H_PX * DEG
M_LAT = 111320.0
M_LON = 111320.0 * math.cos(math.radians(48.018))
TER_W, TER_H = W_PX * DEG * M_LON, H_PX * DEG * M_LAT

dem = np.array(Image.open("/Users/andrewfalcon/Desktop/dnHacks/data/donetskTopography.tif"), dtype=np.float32)
DEM_MIN = float(dem.min())

def ground_y(lon, lat):
    c = min(max((lon - WEST) / DEG - 0.5, 0), W_PX - 1.001)
    r = min(max((NORTH - lat) / DEG - 0.5, 0), H_PX - 1.001)
    c0, r0 = int(c), int(r)
    fc, fr = c - c0, r - r0
    v = (dem[r0, c0] * (1-fc) * (1-fr) + dem[r0, c0+1] * fc * (1-fr)
         + dem[r0+1, c0] * (1-fc) * fr + dem[r0+1, c0+1] * fc * fr)
    return float(v) - DEM_MIN

# --- Fetch building footprints from Overpass ---
query = f'[out:json][timeout:180];way["building"]({SOUTH},{WEST},{NORTH},{EAST});out geom;'
data = None
for host in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
    try:
        req = urllib.request.Request(host, data=("data=" + urllib.parse.quote(query)).encode(),
                                     headers={"User-Agent": "unity-terrain-buildings/1.0"})
        with urllib.request.urlopen(req, timeout=240) as r:
            data = json.load(r)
        break
    except Exception as e:
        print(f"{host} failed: {e}")
if data is None:
    raise SystemExit("all Overpass mirrors failed")
ways = [el for el in data["elements"] if el["type"] == "way" and "geometry" in el]
print(f"fetched {len(ways)} building footprints")

def bheight(tags, bid):
    t = tags or {}
    for k in ("height", "building:height"):
        if k in t:
            try: return max(3.0, float(str(t[k]).replace("m", "").split()[0]))
            except ValueError: pass
    if "building:levels" in t:
        try: return max(3.0, float(t["building:levels"]) * 3.0)
        except ValueError: pass
    base = {"house": 5, "detached": 5, "semidetached_house": 5, "bungalow": 4,
            "garage": 3, "garages": 3, "shed": 3, "hut": 3, "service": 4,
            "apartments": 15, "office": 12, "commercial": 10, "retail": 8,
            "industrial": 9, "warehouse": 8, "school": 10, "hospital": 14,
            "church": 14, "cathedral": 20}.get(t.get("building", "yes"), 6)
    return base + (bid % 7) * 0.5

def ear_clip(pts):
    idx = list(range(len(pts)))
    tris = []
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    def in_tri(p, a, b, c):
        return cross(a, b, p) >= -1e-9 and cross(b, c, p) >= -1e-9 and cross(c, a, p) >= -1e-9
    guard = 0
    while len(idx) > 3 and guard < 5000:
        guard += 1
        found = False
        for i in range(len(idx)):
            a, b, c = idx[i-1], idx[i], idx[(i+1) % len(idx)]
            if cross(pts[a], pts[b], pts[c]) <= 1e-12: continue
            if any(in_tri(pts[j], pts[a], pts[b], pts[c]) for j in idx if j not in (a, b, c)): continue
            tris.append((a, b, c)); idx.pop(i); found = True; break
        if not found: break
    if len(idx) == 3: tris.append(tuple(idx))
    elif len(idx) > 3:
        tris.extend((idx[0], idx[i], idx[i+1]) for i in range(1, len(idx) - 1))
    return tris

# --- Build extruded geometry, chunked 4x4 for reasonable mesh sizes ---
verts = []          # (x, y, z) in terrain-local, x=east y=up z=north
chunks = defaultdict(lambda: defaultdict(list))  # (ci,cj) -> material -> [faces]
skipped = 0

for way in ways:
    bid = way["id"]
    ring = [(g["lon"], g["lat"]) for g in way["geometry"]]
    if len(ring) > 1 and ring[0] == ring[-1]: ring = ring[:-1]
    if len(ring) < 3: skipped += 1; continue
    pts = [((lon - WEST) * M_LON, (lat - SOUTH) * M_LAT) for lon, lat in ring]
    area2 = sum(pts[i][0]*pts[(i+1) % len(pts)][1] - pts[(i+1) % len(pts)][0]*pts[i][1] for i in range(len(pts)))
    if abs(area2) < 2.0: skipped += 1; continue
    if area2 < 0: ring, pts = ring[::-1], pts[::-1]   # normalize to positive shoelace

    h = bheight(way.get("tags"), bid)
    gys = [ground_y(lon, lat) for lon, lat in ring]
    y0, y1 = min(gys) - 1.5, max(gys) + h
    n = len(pts)
    base = len(verts) + 1                              # OBJ is 1-indexed
    verts.extend((x, y0, z) for x, z in pts)           # low ring: base..base+n-1
    verts.extend((x, y1, z) for x, z in pts)           # high ring: base+n..base+2n-1

    cx = sum(p[0] for p in pts) / n
    cz = sum(p[1] for p in pts) / n
    ck = (min(3, max(0, int(cx / (TER_W / 4)))), min(3, max(0, int(cz / (TER_H / 4)))))
    wall, roof = f"wall{bid % 5}", f"roof{(bid // 7) % 3}"

    for i in range(n):                                 # walls: outward-facing quads
        j = (i + 1) % n
        chunks[ck][wall].append((base+i, base+n+i, base+n+j, base+j))
    for a, b, c in ear_clip(pts):                      # roof: reversed for up-normal
        chunks[ck][roof].append((base+n+c, base+n+b, base+n+a))

# --- Write OBJ/MTL (x negated + winding reversed: Unity re-mirrors on import) ---
palette = {"wall0": (0.82, 0.80, 0.76), "wall1": (0.85, 0.78, 0.65), "wall2": (0.78, 0.72, 0.66),
           "wall3": (0.88, 0.86, 0.82), "wall4": (0.70, 0.66, 0.62),
           "roof0": (0.35, 0.33, 0.32), "roof1": (0.45, 0.30, 0.25), "roof2": (0.30, 0.35, 0.40)}
with open("/Users/andrewfalcon/Desktop/dnHacks/data/donetskBuildings.mtl", "w") as m:
    for name, (r, g, b) in palette.items():
        m.write(f"newmtl {name}\nKd {r} {g} {b}\nKs 0 0 0\n\n")

nfaces = 0
with open("/Users/andrewfalcon/Desktop/dnHacks/data/donetskBuildings.obj", "w") as f:
    f.write("mtllib donetskBuildings.mtl\n")
    for x, y, z in verts:
        f.write(f"v {-x:.2f} {y:.2f} {z:.2f}\n")
    for (ci, cj), mats in sorted(chunks.items()):
        f.write(f"o buildings_{ci}_{cj}\n")
        for mat, faces in sorted(mats.items()):
            f.write(f"usemtl {mat}\n")
            for face in faces:
                f.write("f " + " ".join(str(i) for i in reversed(face)) + "\n")
            nfaces += len(faces)

print(f"wrote donetskBuildings.obj: {len(ways)-skipped} buildings ({skipped} skipped), "
      f"{len(verts)} verts, {nfaces} faces, {len(chunks)} chunks")
