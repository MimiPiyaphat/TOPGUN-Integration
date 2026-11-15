"""Run one-image inference with an exported ONNX classifier."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, UnidentifiedImageError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--lot-id", required=True)
    parser.add_argument("--device-id", default="rpi5_vision_01")
    parser.add_argument("--model-version", default="0.1.0")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def resize_short_edge(image: Image.Image, target_size: int) -> Image.Image:
    width, height = image.size
    if width <= height:
        resized_width = target_size
        resized_height = round(height * target_size / width)
    else:
        resized_height = target_size
        resized_width = round(width * target_size / height)
    return image.resize((resized_width, resized_height), Image.Resampling.BILINEAR)


def center_crop(image: Image.Image, crop_size: int) -> Image.Image:
    width, height = image.size
    left = (width - crop_size) // 2
    top = (height - crop_size) // 2
    return image.crop((left, top, left + crop_size, top + crop_size))


def load_image(
    image_path: Path,
    image_size: int,
    resize_short_edge_size: int,
    mean: list[float],
    std: list[float],
) -> np.ndarray:
    try:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            image = resize_short_edge(image, resize_short_edge_size)
            image = center_crop(image, image_size)
    except FileNotFoundError as error:
        raise SystemExit(f"Image not found: {image_path}") from error
    except UnidentifiedImageError as error:
        raise SystemExit(f"Unsupported or damaged image: {image_path}") from error

    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - np.asarray(mean, dtype=np.float32)) / np.asarray(std, dtype=np.float32)
    return np.transpose(array, (2, 0, 1))[None, ...]


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exponential = np.exp(shifted)
    return exponential / np.sum(exponential)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> int:
    args = parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k must be at least 1")
    metadata_path = args.metadata or args.model.with_suffix(args.model.suffix + ".json")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SystemExit(f"Model metadata not found: {metadata_path}") from error

    class_names = metadata["class_names"]
    image_size = int(metadata["image_size"])
    normalization = metadata["normalization"]
    preprocessing = metadata["preprocessing"]
    input_array = load_image(
        args.image,
        image_size,
        int(preprocessing["resize_short_edge"]),
        normalization["mean"],
        normalization["std"],
    )

    session = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    logits = session.run(None, {session.get_inputs()[0].name: input_array})[0][0]
    probabilities = softmax(logits)
    ranked_indices = np.argsort(probabilities)[::-1][: min(args.top_k, len(class_names))]
    ranked_predictions = [
        {
            "class_name": class_names[int(class_index)],
            "confidence": round(float(probabilities[class_index]), 6),
        }
        for class_index in ranked_indices
    ]

    payload = {
        "schema_version": "1.0",
        "message_id": f"vision-{uuid.uuid4()}",
        "lot_id": args.lot_id,
        "type": "vision.classification",
        "timestamp": utc_timestamp(),
        "source": {"device_id": args.device_id, "track": "vision"},
        "model": {
            "name": "coffee-bean-classifier",
            "version": args.model_version,
            "architecture": metadata["architecture"],
            "runtime": "onnxruntime",
            "task": "classification",
        },
        "data": {
            "predicted_class": ranked_predictions[0]["class_name"],
            "confidence": ranked_predictions[0]["confidence"],
            "top_k": ranked_predictions,
            "source_image": args.image.name,
            "status": "ok",
        },
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
