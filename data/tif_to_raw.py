import math
import numpy as np
from PIL import Image

SRC = "/Users/andrewfalcon/Desktop/dnHacks/data/donetskTopography.tif"
DST = "/Users/andrewfalcon/Desktop/dnHacks/data/donetskTopography.raw"
RES = 257  # Unity heightmap resolution (2^n + 1)

img = Image.open(SRC)
arr = np.array(img, dtype=np.float32)
print(f"source: {arr.shape[1]}x{arr.shape[0]} px, dtype float32")

# Guard against nodata sentinels (e.g. -9999 / -3.4e38) before normalizing
valid = arr > -1000
if not valid.all():
    n_bad = int((~valid).sum())
    fill = arr[valid].min()
    print(f"masked {n_bad} nodata px, filled with min elevation {fill:.1f}")
    arr[~valid] = fill

lo, hi = float(arr.min()), float(arr.max())
print(f"elevation range: {lo:.1f} to {hi:.1f} m (relief {hi - lo:.1f} m)")

# Resample to square 2^n+1 for Unity
sq = np.array(Image.fromarray(arr).resize((RES, RES), Image.BICUBIC), dtype=np.float32)
sq = np.clip(sq, lo, hi)

# Normalize to full 16-bit range and flip so north stays north in Unity
u16 = np.round((sq - lo) / (hi - lo) * 65535.0).astype("<u2")
u16 = np.flipud(u16)
u16.tofile(DST)
print(f"wrote {DST}: {RES}x{RES}, 16-bit little-endian ({u16.nbytes} bytes)")

# Real-world extent from GeoTIFF tags: 1 arc-second pixels at ~48 N
deg = 0.0002777777777777778
lat = 48.018
m_per_deg_lat = 111320.0
m_per_deg_lon = 111320.0 * math.cos(math.radians(lat))
w_m = 219 * deg * m_per_deg_lon
h_m = 113 * deg * m_per_deg_lat
print(f"real-world extent: {w_m:.0f} m (E-W) x {h_m:.0f} m (N-S)")
