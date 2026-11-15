"""Validate the organizer classification dataset before training."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
REQUIRED_SPLITS = ("train", "val")
OPTIONAL_SPLITS = ("test",)


def load_classes(config_path: Path) -> list[str]:
    with config_path.open(encoding="utf-8") as stream:
        config = json.load(stream)
    classes = config.get("classes")
    if not isinstance(classes, list) or not classes or not all(isinstance(item, str) for item in classes):
        raise ValueError(f"Invalid classes in {config_path}")
    if len(classes) != len(set(classes)):
        raise ValueError(f"Duplicate classes in {config_path}")
    return classes


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_dataset(dataset_root: Path, classes: list[str], minimum_images: int) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    counts: dict[str, dict[str, int]] = {}
    hashes: dict[str, list[tuple[str, str]]] = defaultdict(list)
    expected_classes = set(classes)

    if not dataset_root.is_dir():
        return {
            "valid": False,
            "errors": [f"Dataset directory not found: {dataset_root}"],
            "warnings": [],
            "counts": {},
            "cross_split_duplicates": [],
        }

    split_names = list(REQUIRED_SPLITS)
    split_names.extend(split for split in OPTIONAL_SPLITS if (dataset_root / split).is_dir())

    for required_split in REQUIRED_SPLITS:
        if not (dataset_root / required_split).is_dir():
            errors.append(f"Missing required split: {required_split}")

    for split in split_names:
        split_root = dataset_root / split
        if not split_root.is_dir():
            continue

        actual_classes = {path.name for path in split_root.iterdir() if path.is_dir()}
        for missing_class in sorted(expected_classes - actual_classes):
            errors.append(f"{split}: missing class directory '{missing_class}'")
        for extra_class in sorted(actual_classes - expected_classes):
            errors.append(f"{split}: unexpected class directory '{extra_class}'")

        counts[split] = {}
        for class_name in classes:
            class_root = split_root / class_name
            if not class_root.is_dir():
                counts[split][class_name] = 0
                continue

            image_paths: list[Path] = []
            for path in class_root.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    warnings.append(f"Unsupported file ignored: {path}")
                    continue
                image_paths.append(path)

            counts[split][class_name] = len(image_paths)
            if len(image_paths) < minimum_images:
                errors.append(
                    f"{split}/{class_name}: found {len(image_paths)} image(s), "
                    f"requires at least {minimum_images}"
                )

            for image_path in image_paths:
                hashes[file_sha256(image_path)].append((split, str(image_path)))

    duplicates: list[dict] = []
    for digest, occurrences in hashes.items():
        occurrence_splits = {split for split, _ in occurrences}
        if len(occurrence_splits) > 1:
            duplicates.append(
                {
                    "sha256": digest,
                    "files": [path for _, path in occurrences],
                    "splits": sorted(occurrence_splits),
                }
            )

    if duplicates:
        errors.append(f"Found {len(duplicates)} image(s) duplicated across dataset splits")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": counts,
        "cross_split_duplicates": duplicates,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True, help="Dataset root containing train/val[/test]")
    parser.add_argument(
        "--classes",
        type=Path,
        default=Path(__file__).with_name("class_names.json"),
        help="Class configuration JSON",
    )
    parser.add_argument("--minimum-images", type=int, default=1, help="Minimum images per class and split")
    parser.add_argument("--report", type=Path, help="Optional path for the JSON validation report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.minimum_images < 1:
        raise SystemExit("--minimum-images must be at least 1")

    classes = load_classes(args.classes)
    report = validate_dataset(args.dataset, classes, args.minimum_images)
    rendered_report = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered_report)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered_report + "\n", encoding="utf-8")

    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
