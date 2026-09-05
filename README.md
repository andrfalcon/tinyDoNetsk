# dnhacks

Working repo for the Donetsk topography hack. At present the repo contains a single
raster dataset and no code.

## Contents

```
data/donetskTopography.tif    single-band elevation raster (101 KB)
```

## Dataset: `data/donetskTopography.tif`

A single-band float32 digital elevation model on a 1 arc-second geographic grid.

| Property | Value |
| --- | --- |
| Driver | GTiff |
| Size | 219 x 113 px, 1 band |
| Data type | float32 |
| CRS | EPSG:4326 (WGS 84, lon/lat degrees) |
| Pixel size | 0.00027778 deg (1 arc-second) |
| Ground resolution | approx. 20.7 m east/west, 30.9 m north/south at this latitude |
| NoData | none set (every pixel carries a value) |
| Pixel convention | `AREA_OR_POINT = Point` |

### Extent

| | Longitude (E) | Latitude (N) |
| --- | --- | --- |
| Min | 37.797083 | 47.986806 |
| Max | 37.857917 | 48.018194 |
| Center | 37.827500 | 48.002500 |

The tile covers roughly 4.54 km east/west by 3.49 km north/south, about 15.8 km2.
It sits over Donetsk, Donetsk Oblast, Ukraine. The city center (approx. 48.016 N,
37.803 E) falls near the northwest corner of the tile, so the raster mostly covers
the central and southern parts of the city.

### Elevation statistics

Computed over all 24,747 pixels, values in metres:

| Statistic | Value |
| --- | --- |
| Min | 129.45 |
| 5th percentile | 138.80 |
| 25th percentile | 163.35 |
| Median | 181.47 |
| Mean | 179.50 |
| 75th percentile | 197.29 |
| 95th percentile | 210.45 |
| Max | 248.04 |
| Std dev | 21.56 |

Terrain is gentle. Mean slope is about 4.9 degrees, with a maximum of about 38.4
degrees at the 30 m sampling scale.

### Provenance

The file carries no source or vertical-datum tags beyond `AREA_OR_POINT`. The
1 arc-second grid and the value range are consistent with a 30 m global DEM product
such as SRTM or Copernicus GLO-30, but the source is not recorded in the file and
has not been confirmed. Treat the vertical datum as unknown until someone who knows
the download path confirms it. This matters for anything that mixes these heights
with GPS ellipsoidal altitudes.

## Loading the data

Requires `rasterio` (which bundles GDAL) and `numpy`:

```bash
pip install rasterio numpy
```

```python
import rasterio

with rasterio.open("data/donetskTopography.tif") as src:
    dem = src.read(1)          # (113, 219) float32 array, metres
    transform = src.transform  # affine: pixel -> lon/lat
    crs = src.crs              # EPSG:4326
```

Sampling elevation at a coordinate:

```python
with rasterio.open("data/donetskTopography.tif") as src:
    lon, lat = 37.8275, 48.0025
    row, col = src.index(lon, lat)
    elevation = src.read(1)[row, col]
```

Slope in degrees, accounting for the anisotropic pixel size in EPSG:4326:

```python
import numpy as np

PX_M, PY_M = 20.7, 30.9  # metres per pixel, east/west and north/south
gy, gx = np.gradient(dem.astype("float64"), PY_M, PX_M)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))
```

Note that the grid is in degrees, not metres. Any distance, slope, area, or
viewshed calculation needs either the metre-per-pixel factors above or a reprojection
to a local projected CRS (UTM zone 37N, EPSG:32637, covers this area).

## Repo notes

- A `.DS_Store` file is committed at the repo root. Worth removing and adding a
  `.gitignore` entry.
- There is no license file. Add one before the repo is shared more widely.
