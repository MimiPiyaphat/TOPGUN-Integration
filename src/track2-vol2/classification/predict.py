"""Run single-image classification and emit an integration-friendly JSON result."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import torch
from PIL import Image, UnidentifiedImageError

from train import build_model, build_transforms, resolve_device


def load_checkpoint(checkpoint_path: Path, device: torch.device) -> dict:
    try:
        checkpoint = torch.load(
            checkpoint_path,
            map_location=device,
            weights_only=False,
        )
    except FileNotFoundError as error:
        raise SystemExit(f"Checkpoint not found: {checkpoint_path}") from error

    required_fields = {
        "architecture",
        "class_names",
        "image_size",
        "model_state_dict",
    }
    missing_fields = required_fields - checkpoint.keys()
    if missing_fields:
        raise SystemExit(f"Invalid checkpoint; missing fields: {sorted(missing_fields)}")

    class_names = checkpoint["class_names"]
    if not isinstance(class_names, list) or not class_names:
        raise SystemExit("Invalid checkpoint; class_names must be a non-empty list")

    return checkpoint


def open_rgb_image(image_path: Path) -> Image.Image:
    try:
        with Image.open(image_path) as image:
            return image.convert("RGB")
    except FileNotFoundError as error:
        raise SystemExit(f"Image not found: {image_path}") from error
    except UnidentifiedImageError as error:
        raise SystemExit(f"Unsupported or damaged image: {image_path}") from error


def predict_image(
    image: Image.Image,
    model: torch.nn.Module,
    class_names: list[str],
    image_size: int,
    top_k: int,
    device: torch.device,
) -> tuple[str, float, list[dict]]:
    _, inference_transform = build_transforms(image_size)
    input_tensor = inference_transform(image).unsqueeze(0).to(device)

    model.eval()
    with torch.inference_mode():
        logits = model(input_tensor)
        probabilities = torch.softmax(logits, dim=1)[0]

    number_of_results = min(top_k, len(class_names))
    confidence_values, class_indices = torch.topk(probabilities, number_of_results)
    ranked_predictions = [
        {
            "class_name": class_names[class_index],
            "confidence": round(float(confidence), 6),
        }
        for confidence, class_index in zip(confidence_values.cpu(), class_indices.cpu().tolist())
    ]
    best_prediction = ranked_predictions[0]
    return (
        best_prediction["class_name"],
        best_prediction["confidence"],
        ranked_predictions,
    )


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True, help="Path to best_model.pt")
    parser.add_argument("--image", type=Path, required=True, help="Image to classify")
    parser.add_argument("--lot-id", required=True, help="Coffee lot identifier")
    parser.add_argument("--device-id", default="rpi5_vision_01")
    parser.add_argument("--model-version", default="0.1.0")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k must be at least 1")

    device = resolve_device(args.device)
    checkpoint = load_checkpoint(args.checkpoint, device)
    class_names = checkpoint["class_names"]
    architecture = checkpoint["architecture"]
    image_size = int(checkpoint["image_size"])

    model = build_model(
        architecture=architecture,
        number_of_classes=len(class_names),
        weights_mode="none",
        freeze_backbone=False,
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)

    image = open_rgb_image(args.image)
    predicted_class, confidence, ranked_predictions = predict_image(
        image=image,
        model=model,
        class_names=class_names,
        image_size=image_size,
        top_k=args.top_k,
        device=device,
    )

    payload = {
        "schema_version": "1.0",
        "message_id": f"vision-{uuid.uuid4()}",
        "lot_id": args.lot_id,
        "type": "vision.classification",
        "timestamp": utc_timestamp(),
        "source": {
            "device_id": args.device_id,
            "track": "vision",
        },
        "model": {
            "name": "coffee-bean-classifier",
            "version": args.model_version,
            "architecture": architecture,
            "task": "classification",
        },
        "data": {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "top_k": ranked_predictions,
            "source_image": args.image.name,
            "status": "ok",
        },
    }

    indent = 2 if args.pretty else None
    rendered_payload = json.dumps(payload, ensure_ascii=False, indent=indent)
    print(rendered_payload)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered_payload + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
