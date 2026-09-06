"""Split the Unity-generated CarDataset into train/val (90/10) using symlinks."""
import os

SRC = "/Users/andrewfalcon/Desktop/dnHacks/dnHacksEnv/CarDataset"
DST = "/Users/andrewfalcon/Desktop/dnHacks/training/dataset"

images = sorted(os.listdir(f"{SRC}/images"))
for sub in ("images/train", "images/val", "labels/train", "labels/val"):
    os.makedirs(f"{DST}/{sub}", exist_ok=True)

n_train = n_val = 0
for i, img in enumerate(images):
    split = "val" if i % 10 == 9 else "train"   # deterministic 90/10
    stem = os.path.splitext(img)[0]
    for kind, name in (("images", img), ("labels", f"{stem}.txt")):
        link = f"{DST}/{kind}/{split}/{name}"
        if not os.path.lexists(link):
            os.symlink(f"{SRC}/{kind}/{name}", link)
    if split == "val": n_val += 1
    else: n_train += 1

with open(f"{DST}/data.yaml", "w") as f:
    f.write(f"path: {DST}\ntrain: images/train\nval: images/val\nnc: 1\nnames: [car]\n")
print(f"train: {n_train}  val: {n_val}  ->  {DST}/data.yaml")
