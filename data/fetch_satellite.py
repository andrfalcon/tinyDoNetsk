import math, time, io, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

# Exact bounding box from the GeoTIFF tags
DEG = 0.0002777777777777778
WEST, NORTH = 37.79722221111111, 48.01805556666666
W_PX, H_PX = 219, 113
EAST = WEST + W_PX * DEG
SOUTH = NORTH - H_PX * DEG

Z = 17  # ~0.8 m/px at this latitude
TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
OUT = "/Users/andrewfalcon/Desktop/dnHacks/data/donetskSatellite.jpg"

def to_px(lon, lat, z):
    n = 2 ** z * 256
    x = (lon + 180.0) / 360.0 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y

px_w, py_n = to_px(WEST, NORTH, Z)
px_e, py_s = to_px(EAST, SOUTH, Z)
tx0, tx1 = int(px_w // 256), int(px_e // 256)
ty0, ty1 = int(py_n // 256), int(py_s // 256)
tiles = [(tx, ty) for ty in range(ty0, ty1 + 1) for tx in range(tx0, tx1 + 1)]
print(f"fetching {len(tiles)} tiles at z{Z}...")

def fetch(txy):
    tx, ty = txy
    url = TILE_URL.format(z=Z, x=tx, y=ty)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "terrain-texture-fetch/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return txy, Image.open(io.BytesIO(r.read())).convert("RGB")
        except Exception as e:
            if attempt == 3:
                raise RuntimeError(f"tile {txy} failed: {e}")
            time.sleep(1 + attempt)

mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
with ThreadPoolExecutor(max_workers=8) as ex:
    for i, ((tx, ty), img) in enumerate(ex.map(fetch, tiles), 1):
        mosaic.paste(img, ((tx - tx0) * 256, (ty - ty0) * 256))
        if i % 100 == 0:
            print(f"  {i}/{len(tiles)}")

crop = mosaic.crop((round(px_w - tx0 * 256), round(py_n - ty0 * 256),
                    round(px_e - tx0 * 256), round(py_s - ty0 * 256)))
crop.save(OUT, quality=92)
m_per_px = (EAST - WEST) * 111320 * math.cos(math.radians(48.018)) / crop.width
print(f"saved {OUT}: {crop.width}x{crop.height} px, ~{m_per_px:.2f} m/px")
