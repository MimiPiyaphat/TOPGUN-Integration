"""Download and package TorchVision pretrained weights for offline training."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch
from torchvision import models


DEFAULT_OUTPUT = Path(__file__).parent / "models" / "pretrained" / "mobilenet_v3_small_imagenet.pth"
TORCH_CACHE = Path(__file__).parent / ".torch-cache"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    TORCH_CACHE.mkdir(parents=True, exist_ok=True)
    torch.hub.set_dir(str(TORCH_CACHE))

    weights = models.MobileNet_V3_Small_Weights.DEFAULT
    print(f"Downloading/loading TorchVision weights: {weights}")
    model = models.mobilenet_v3_small(weights=weights)
    artifact = {
        "schema_version": "1.0",
        "architecture": "mobilenet_v3_small",
        "source": "torchvision",
        "weights": str(weights),
        "model_state_dict": model.state_dict(),
    }
    torch.save(artifact, args.output)

    digest = sha256(args.output)
    metadata = {
        "file": args.output.name,
        "architecture": artifact["architecture"],
        "source": artifact["source"],
        "weights": artifact["weights"],
        "sha256": digest,
        "size_bytes": args.output.stat().st_size,
    }
    metadata_path = args.output.with_suffix(args.output.suffix + ".json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print(f"weights_file={args.output.resolve()}")
    print(f"metadata_file={metadata_path.resolve()}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
