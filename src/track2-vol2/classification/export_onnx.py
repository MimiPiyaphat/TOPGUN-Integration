"""Export a trained classification checkpoint to ONNX and verify parity."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

from predict import load_checkpoint
from train import IMAGENET_MEAN, IMAGENET_STD, build_model


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def benchmark_session(session: ort.InferenceSession, input_array: np.ndarray, iterations: int) -> dict:
    input_name = session.get_inputs()[0].name
    for _ in range(5):
        session.run(None, {input_name: input_array})

    started_at = time.perf_counter()
    for _ in range(iterations):
        session.run(None, {input_name: input_array})
    elapsed = time.perf_counter() - started_at
    mean_ms = elapsed * 1000 / iterations
    return {
        "iterations": iterations,
        "total_seconds": elapsed,
        "mean_inference_ms": mean_ms,
        "frames_per_second": 1000 / mean_ms,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--benchmark-iterations", type=int, default=30)
    parser.add_argument("--tolerance", type=float, default=1e-4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.benchmark_iterations < 1:
        raise SystemExit("--benchmark-iterations must be at least 1")

    device = torch.device("cpu")
    checkpoint = load_checkpoint(args.checkpoint, device)
    architecture = checkpoint["architecture"]
    class_names = checkpoint["class_names"]
    image_size = int(checkpoint["image_size"])

    model = build_model(
        architecture=architecture,
        number_of_classes=len(class_names),
        weights_mode="none",
        freeze_backbone=False,
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.eval()

    torch.manual_seed(42)
    sample_input = torch.randn(1, 3, image_size, image_size, device=device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        sample_input,
        str(args.output),
        export_params=True,
        opset_version=args.opset,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        dynamo=False,
    )

    onnx_model = onnx.load(str(args.output))
    onnx.checker.check_model(onnx_model)
    session = ort.InferenceSession(str(args.output), providers=["CPUExecutionProvider"])
    input_array = sample_input.cpu().numpy()

    with torch.inference_mode():
        pytorch_output = model(sample_input).cpu().numpy()
    onnx_output = session.run(None, {session.get_inputs()[0].name: input_array})[0]
    maximum_absolute_difference = float(np.max(np.abs(pytorch_output - onnx_output)))
    if maximum_absolute_difference > args.tolerance:
        raise RuntimeError(
            f"ONNX parity failed: max_abs_diff={maximum_absolute_difference} "
            f"> tolerance={args.tolerance}"
        )
    if int(np.argmax(pytorch_output)) != int(np.argmax(onnx_output)):
        raise RuntimeError("ONNX parity failed: PyTorch and ONNX predicted different classes")

    benchmark = benchmark_session(session, input_array, args.benchmark_iterations)
    metadata = {
        "schema_version": "1.0",
        "model_file": args.output.name,
        "architecture": architecture,
        "class_names": class_names,
        "image_size": image_size,
        "input_name": session.get_inputs()[0].name,
        "output_name": session.get_outputs()[0].name,
        "input_shape": ["batch", 3, image_size, image_size],
        "normalization": {
            "mean": list(IMAGENET_MEAN),
            "std": list(IMAGENET_STD),
        },
        "preprocessing": {
            "color_mode": "RGB",
            "resize_short_edge": int(image_size * 1.15),
            "crop": "center",
        },
        "opset": args.opset,
        "sha256": sha256(args.output),
        "size_bytes": args.output.stat().st_size,
        "parity": {
            "max_abs_diff": maximum_absolute_difference,
            "tolerance": args.tolerance,
            "passed": True,
        },
        "benchmark_cpu": benchmark,
    }
    metadata_path = args.output.with_suffix(args.output.suffix + ".json")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"onnx_file={args.output.resolve()}")
    print(f"metadata_file={metadata_path.resolve()}")
    print(f"size_mb={args.output.stat().st_size / (1024 * 1024):.2f}")
    print(f"max_abs_diff={maximum_absolute_difference:.8f}")
    print(f"mean_inference_ms={benchmark['mean_inference_ms']:.2f}")
    print("onnx_validation=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
