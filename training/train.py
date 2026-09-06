"""Train a YOLO car detector on the synthetic Donetsk drone dataset."""
from ultralytics import YOLO

model = YOLO("yolo11n.pt")  # nano: fast; try yolo11s.pt for more accuracy
model.train(
    data="/Users/andrewfalcon/Desktop/dnHacks/training/dataset/data.yaml",
    epochs=60,
    imgsz=960,        # larger than default 640: cars are small objects
    batch=8,
    device="mps",     # Apple GPU
    project="/Users/andrewfalcon/Desktop/dnHacks/training/runs",
    name="car-detector",
    exist_ok=True,
)
