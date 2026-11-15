"""Run a disposable end-to-end rehearsal of the classification pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw


MODULE_ROOT = Path(__file__).parent
DEFAULT_WEIGHTS = MODULE_ROOT / "models" / "pretrained" / "mobilenet_v3_small_imagenet.pth"
COLORS = (
    (80, 170, 90),
    (155, 100, 55),
    (45, 45, 45),
    (120, 75, 40),
    (190, 145, 85),
    (215, 185, 115),
    (185, 195, 120),
)


def load_classes() -> list[str]:
    config_path = MODULE_ROOT / "class_names.json"
    with config_path.open(encoding="utf-8") as stream:
        return json.load(stream)["classes"]


def create_mock_image(path: Path, color: tuple[int, int, int], variant: int) -> None:
    image = Image.new("RGB", (160, 160), "white")
    draw = ImageDraw.Draw(image)
    offset = variant * 8
    draw.ellipse((35 + offset, 25, 125, 135 - offset), fill=color, outline="black", width=3)
    draw.line((80 + offset // 2, 35, 75, 125 - offset), fill="white", width=5)
    image.save(path, quality=90)


def create_mock_dataset(dataset_root: Path, classes: list[str]) -> None:
    for split, images_per_class in (("train", 2), ("val", 1)):
        for class_index, class_name in enumerate(classes):
            class_root = dataset_root / split / class_name
            class_root.mkdir(parents=True, exist_ok=True)
            for image_index in range(images_per_class):
                create_mock_image(
                    class_root / f"{class_name}_{image_index}.jpg",
                    COLORS[class_index],
                    variant=image_index + (10 if split == "val" else 0),
                )


def run_command(command: list[str], label: str) -> float:
    print(f"\n[{label}] {' '.join(command)}", flush=True)
    started_at = time.perf_counter()
    subprocess.run(command, cwd=MODULE_ROOT, check=True)
    elapsed = time.perf_counter() - started_at
    print(f"[{label}] completed in {elapsed:.2f}s", flush=True)
    return elapsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights-file", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    weights_file = args.weights_file.resolve()
    if not weights_file.is_file():
        raise SystemExit(
            f"Offline weights not found: {weights_file}\n"
            "Run: python download_weights.py"
        )

    classes = load_classes()
    results_root = MODULE_ROOT / "results"
    results_root.mkdir(exist_ok=True)
    timings: dict[str, float] = {}

    with tempfile.TemporaryDirectory(prefix="rehearsal-", dir=results_root) as temporary_directory:
        rehearsal_root = Path(temporary_directory)
        dataset_root = rehearsal_root / "dataset"
        output_root = rehearsal_root / "output"
        prediction_path = output_root / "prediction.json"
        create_mock_dataset(dataset_root, classes)

        timings["verify"] = run_command(
            [
                sys.executable,
                "verify_dataset.py",
                "--dataset",
                str(dataset_root),
                "--minimum-images",
                "1",
            ],
            "verify",
        )
        timings["train"] = run_command(
            [
                sys.executable,
                "train.py",
                "--dataset",
                str(dataset_root),
                "--output",
                str(output_root),
                "--architecture",
                "mobilenet_v3_small",
                "--weights",
                "none",
                "--weights-file",
                str(weights_file),
                "--freeze-backbone",
                "--epochs",
                "1",
                "--batch-size",
                "7",
                "--image-size",
                "64",
                "--device",
                args.device,
            ],
            "train",
        )
        timings["predict"] = run_command(
            [
                sys.executable,
                "predict.py",
                "--checkpoint",
                str(output_root / "best_model.pt"),
                "--image",
                str(dataset_root / "val" / "good" / "good_0.jpg"),
                "--lot-id",
                "lot-rehearsal-001",
                "--device",
                args.device,
                "--output",
                str(prediction_path),
                "--pretty",
            ],
            "predict",
        )

        with prediction_path.open(encoding="utf-8") as stream:
            prediction = json.load(stream)
        if prediction.get("lot_id") != "lot-rehearsal-001":
            raise RuntimeError("Prediction JSON contains the wrong lot_id")
        if prediction.get("data", {}).get("predicted_class") not in classes:
            raise RuntimeError("Prediction JSON contains a non-canonical class")
        if prediction.get("data", {}).get("status") != "ok":
            raise RuntimeError("Prediction JSON status is not ok")

    print("\n=== REHEARSAL PASSED ===")
    for label, elapsed in timings.items():
        print(f"{label}: {elapsed:.2f}s")
    print(f"total: {sum(timings.values()):.2f}s")
    print("Temporary dataset, model, and prediction files were removed.")
    print("Accuracy from this synthetic rehearsal is not a quality measurement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
