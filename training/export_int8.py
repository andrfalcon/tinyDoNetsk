"""Export a trained car detector to INT8 TFLite (TinyML-ready).

Usage: python export_int8.py [path/to/best.pt] [imgsz]
Defaults to the main training run's best.pt at 960 px.
"""
import sys
from pathlib import Path
from ultralytics import YOLO

weights = sys.argv[1] if len(sys.argv) > 1 else \
    "/Users/andrewfalcon/Desktop/dnHacks/training/runs/car-detector/weights/best.pt"
imgsz = int(sys.argv[2]) if len(sys.argv) > 2 else 960

model = YOLO(weights)
path = model.export(
    format="tflite",
    int8=True,   # full INT8 quantization
    data="/Users/andrewfalcon/Desktop/dnHacks/training/dataset/data.yaml",  # calibration images
    imgsz=imgsz,
)
out = Path(path)
print(f"\nINT8 model: {out}")
print(f"size: {out.stat().st_size / 1e6:.2f} MB (FP32 .pt was {Path(weights).stat().st_size / 1e6:.2f} MB)")
