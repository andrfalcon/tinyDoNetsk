# dnHacks — Synthetic Drone Imagery for Car Detection

End-to-end pipeline that turns public geodata into a trained, quantized car-detection
model for drone edge compute — with **zero manual annotation**.

```
DEM (GeoTIFF)          satellite imagery         OpenStreetMap
      │                       │                       │
      ▼                       ▼                       ▼
Unity terrain  ◄──────  ground texture  ────►  6,473 extruded 3D buildings
      └──────────────────────┬────────────────────────┘
                             ▼
        Unity scene + domain randomization (cars, camera, sun)
                             ▼
        2,000 auto-labeled drone images (YOLO format)
                             ▼
        YOLO11n training → mAP50 99.4% (synthetic val)
                             ▼
        w8a16 quantization → 3.2 MB integer model for edge hardware
```

The scene models a ~4.5 × 3.5 km area of Donetsk, Ukraine (real elevation, real
satellite imagery, real building footprints), populated with procedurally generated
cars and rendered from randomized drone viewpoints.

## Repository layout

```
data/                          Geodata + generation scripts (Python)
  donetskTopography.tif        Source DEM: 219×113 px float32, EPSG:4326, 1 arc-second
  donetskTopography.raw        Unity-ready heightmap: 257×257, 16-bit LE (tif_to_raw.py)
  donetskSatellite.jpg         Stitched satellite texture: 5671×4372 px, ~0.8 m/px
  donetskBuildings.obj/.mtl    6,473 OSM buildings, extruded, terrain-aligned
  cars/                        10 procedural low-poly car models (5 types × colors)
  tif_to_raw.py                DEM → Unity RAW heightmap conversion
  fetch_satellite.py           Downloads + crops imagery tiles for the exact bbox
  fetch_buildings.py           Overpass API → extruded OBJ with per-vertex terrain elevation
  generate_cars.py             Parametric car mesh generator (OBJ/MTL)

dnHacksEnv/                    Unity 6 project (URP)
  Assets/DonetskEnvironment/   Terrain assets, car models/prefabs, C# scripts
    Scripts/
      TerrainCarPlacementRandomizer.cs   Scatters cars in clusters on terrain each iteration
      DroneCameraRandomizer.cs           Random altitude (60–140 m) + nadir↔oblique viewpoints
      SunAngleRandomizer.cs              Time-of-day / shadow randomization
      CarDatasetCapture.cs               URP-compatible capture: PNG + YOLO labels per frame
      Editor/CreateCarPrefabs.cs         Menu tool: builds labeled car prefabs
  Packages/com.unity.perception/         Perception 1.0.0-preview.1, patched for Unity 6
  CarDataset/                  Generated dataset: images/, labels/, dataset.yaml (gitignored-size)

training/                      YOLO training + quantization (Python)
  prep_dataset.py              90/10 train/val split via symlinks
  train.py                     YOLO11n, 60 epochs, imgsz 960, Apple MPS
  export_int8.py               INT8 / w8a16 TFLite export with calibration
  dataset/                     Split dataset + data.yaml
  runs/car-detector/           Weights (best.pt, best_w8a16.tflite), curves, metrics
  slide_images/                Sample predictions with drawn bounding boxes
```

## Results

| Model | Size | mAP50 | mAP50-95 | Precision | Recall |
|---|---|---|---|---|---|
| YOLO11n FP32 (`best.pt`) | 5.5 MB | 0.994 | 0.908 | 0.985 | 0.988 |
| w8a16 TFLite (`best_w8a16.tflite`) | 3.2 MB | 0.994 | 0.860 | 0.985 | 0.987 |
| full INT8 TFLite | 3.1 MB | 0.538 | 0.174 | — rejected — | |

- 2.58 M parameters, 14.4 GFLOPs @ 960×960 input. Training: ~2 h on an Apple M4 Pro.
- Full INT8 collapsed on small objects; INT8-weights/INT16-activations (w8a16) retains
  accuracy while staying integer-only. Suitable for Raspberry Pi-class SBCs, phones,
  and NPUs/DSPs with 16-bit activation support. Coral Edge TPU would require
  quantization-aware training (full INT8 only). Bare MCUs would need a low-altitude
  retrain at ~256 px input.
- **Caveat:** metrics are on *synthetic* validation data. Expect lower real-world
  performance until fine-tuned on real drone frames.

## Reproducing the pipeline

### 1. Environment (conda)

Three environments keep incompatible toolchains apart:

```bash
conda create -n tif2raw    python=3.11 numpy pillow       # geodata scripts
conda create -n car-yolo   python=3.11 && pip install ultralytics   # training
conda create -n car-export python=3.11 && pip install ultralytics   # TFLite export
# In car-export, the LiteRT converter downgrades torch to a broken 2.13 — fix with:
# pip install --force-reinstall --no-deps torch==2.14.0
```

### 2. Generate geodata assets

```bash
python data/tif_to_raw.py         # DEM → 257×257 16-bit RAW heightmap
python data/fetch_satellite.py    # satellite texture for the exact bbox
python data/fetch_buildings.py    # OSM buildings → terrain-aligned OBJ
python data/generate_cars.py      # 10 car model variants
```

All scripts share the same georeferencing (from the GeoTIFF tags), so terrain,
texture, and buildings align in Unity's coordinate system: terrain at origin,
X = east (4530 m), Z = north (3494 m), Y = up (119 m for the 118.6 m relief).

### 3. Unity scene

- Import the RAW heightmap: Terrain Settings → Import Raw (16-bit, 257×257,
  little-endian/Windows, no flip). Terrain size 4530 × 3494 × 119.
- Drape `donetskSatellite.jpg` as a Terrain Layer sized 4530 × 3494 (Max Size 8192).
- Drop `donetskBuildings.obj` at the origin, enable Generate Colliders.
- Run **dnHacks → Create Labeled Car Prefabs**, then build a Fixed Length Scenario
  with the three randomizers (car placement → drone camera → sun, in that order).
- Add `CarDatasetCapture` to the camera and press Play. Output lands in
  `dnHacksEnv/CarDataset/` as a ready-to-train YOLO dataset.

Note: Unity Perception 1.0 needed two Unity 6 compile fixes (embedded in
`Packages/com.unity.perception`), and its ground-truth capture is HDRP-only —
this project uses URP, so `CarDatasetCapture.cs` replaces the Perception Camera:
it projects each car's 3D bounds to screen space, checks occlusion by raycast,
and writes YOLO labels directly.

### 4. Train and quantize

```bash
conda activate car-yolo
python training/prep_dataset.py
python training/train.py                                   # ~2 h on Apple Silicon

conda activate car-export
python training/export_int8.py                             # w8a16 / INT8 TFLite
yolo val model=training/runs/car-detector/weights/best_w8a16.tflite \
         data=training/dataset/data.yaml imgsz=960          # verify quantized accuracy
```

## Source data & licensing

- **Elevation:** 1 arc-second DEM over Donetsk (consistent with SRTM/Copernicus
  GLO-30; source tags absent from the file). Extent 37.797–37.858°E, 47.987–48.018°N;
  elevations 129–248 m.
- **Satellite imagery:** Esri World Imagery tiles — requires attribution
  (Esri, Maxar, Earthstar Geographics); fine for research/hackathon use.
- **Buildings:** © OpenStreetMap contributors, ODbL. Multipolygon (courtyard)
  buildings are not included; heights come from OSM tags where present, otherwise
  per-type defaults.
- No license file yet for this repo's own code — add one before sharing widely.
