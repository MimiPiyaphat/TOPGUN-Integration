"""Train a seven-class coffee-bean image classifier."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import torch
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

from verify_dataset import load_classes, validate_dataset


IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class CanonicalImageFolder(datasets.ImageFolder):
    """ImageFolder that preserves the canonical class order from class_names.json."""

    def __init__(self, root: Path, class_names: list[str], transform: transforms.Compose):
        self.canonical_class_names = class_names
        super().__init__(root=str(root), transform=transform)

    def find_classes(self, directory: str) -> tuple[list[str], dict[str, int]]:
        root = Path(directory)
        actual = {path.name for path in root.iterdir() if path.is_dir()}
        expected = set(self.canonical_class_names)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise FileNotFoundError(f"Class directories do not match: missing={missing}, extra={extra}")
        classes = list(self.canonical_class_names)
        return classes, {name: index for index, name in enumerate(classes)}


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_transforms(image_size: int) -> tuple[transforms.Compose, transforms.Compose]:
    train_transform = transforms.Compose(
        [
            transforms.RandomResizedCrop(image_size, scale=(0.75, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.15),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )
    validation_transform = transforms.Compose(
        [
            transforms.Resize(int(image_size * 1.15)),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )
    return train_transform, validation_transform


def build_model(
    architecture: str,
    number_of_classes: int,
    weights_mode: str,
    freeze_backbone: bool,
) -> nn.Module:
    if weights_mode == "default":
        weights = (
            models.MobileNet_V3_Small_Weights.DEFAULT
            if architecture == "mobilenet_v3_small"
            else models.ResNet18_Weights.DEFAULT
        )
    else:
        weights = None

    if architecture == "mobilenet_v3_small":
        model = models.mobilenet_v3_small(weights=weights)
        if freeze_backbone:
            for parameter in model.features.parameters():
                parameter.requires_grad = False
        input_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(input_features, number_of_classes)
    elif architecture == "resnet18":
        model = models.resnet18(weights=weights)
        if freeze_backbone:
            for name, parameter in model.named_parameters():
                if not name.startswith("fc."):
                    parameter.requires_grad = False
        model.fc = nn.Linear(model.fc.in_features, number_of_classes)
    else:
        raise ValueError(f"Unsupported architecture: {architecture}")

    return model


def calculate_class_weights(dataset: CanonicalImageFolder) -> torch.Tensor:
    counts = torch.zeros(len(dataset.classes), dtype=torch.float32)
    for _, class_index in dataset.samples:
        counts[class_index] += 1
    if torch.any(counts == 0):
        raise ValueError(f"Every class must contain at least one image; counts={counts.tolist()}")
    return counts.sum() / (len(counts) * counts)


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: AdamW | None = None,
) -> tuple[float, float]:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_correct = 0
    total_examples = 0

    for inputs, labels in loader:
        inputs = inputs.to(device)
        labels = labels.to(device)

        if training:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(training):
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            if training:
                loss.backward()
                optimizer.step()

        batch_size = labels.size(0)
        total_loss += loss.item() * batch_size
        total_correct += (outputs.argmax(dim=1) == labels).sum().item()
        total_examples += batch_size

    return total_loss / total_examples, total_correct / total_examples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True, help="Dataset root containing train/val[/test]")
    parser.add_argument(
        "--classes",
        type=Path,
        default=Path(__file__).with_name("class_names.json"),
        help="Canonical class configuration",
    )
    parser.add_argument("--output", type=Path, default=Path("results/classification"))
    parser.add_argument("--architecture", choices=("mobilenet_v3_small", "resnet18"), default="mobilenet_v3_small")
    parser.add_argument(
        "--weights",
        choices=("default", "none"),
        default="default",
        help="Use ImageNet pretrained weights or initialize randomly",
    )
    parser.add_argument("--freeze-backbone", action="store_true", help="Train only the classification head")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--num-workers", type=int, default=0, help="Use 0 on Windows for maximum compatibility")
    parser.add_argument("--minimum-images", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser.parse_args()


def resolve_device(requested_device: str) -> torch.device:
    if requested_device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available")
        return torch.device("cuda")
    if requested_device == "cpu":
        return torch.device("cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def main() -> int:
    args = parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.image_size < 32:
        raise SystemExit("epochs and batch-size must be positive; image-size must be at least 32")
    if args.freeze_backbone and args.weights == "none":
        raise SystemExit("--freeze-backbone requires --weights default")

    seed_everything(args.seed)
    class_names = load_classes(args.classes)
    validation_report = validate_dataset(args.dataset, class_names, args.minimum_images)
    if not validation_report["valid"]:
        print(json.dumps(validation_report, ensure_ascii=False, indent=2))
        raise SystemExit("Dataset validation failed")

    train_transform, validation_transform = build_transforms(args.image_size)
    train_dataset = CanonicalImageFolder(args.dataset / "train", class_names, train_transform)
    validation_dataset = CanonicalImageFolder(args.dataset / "val", class_names, validation_transform)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    device = resolve_device(args.device)
    model = build_model(args.architecture, len(class_names), args.weights, args.freeze_backbone).to(device)
    class_weights = calculate_class_weights(train_dataset).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = AdamW(
        (parameter for parameter in model.parameters() if parameter.requires_grad),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs)

    args.output.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []
    best_accuracy = -1.0
    started_at = time.time()

    print(f"device={device} architecture={args.architecture} classes={class_names}")
    print(f"train_images={len(train_dataset)} validation_images={len(validation_dataset)}")

    for epoch in range(1, args.epochs + 1):
        train_loss, train_accuracy = run_epoch(model, train_loader, criterion, device, optimizer)
        validation_loss, validation_accuracy = run_epoch(
            model, validation_loader, criterion, device, optimizer=None
        )
        scheduler.step()

        metrics = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_accuracy": train_accuracy,
            "validation_loss": validation_loss,
            "validation_accuracy": validation_accuracy,
            "learning_rate": optimizer.param_groups[0]["lr"],
        }
        history.append(metrics)
        print(
            f"epoch={epoch:03d} "
            f"train_loss={train_loss:.4f} train_acc={train_accuracy:.4f} "
            f"val_loss={validation_loss:.4f} val_acc={validation_accuracy:.4f}"
        )

        if validation_accuracy > best_accuracy:
            best_accuracy = validation_accuracy
            torch.save(
                {
                    "schema_version": "1.0",
                    "architecture": args.architecture,
                    "class_names": class_names,
                    "image_size": args.image_size,
                    "epoch": epoch,
                    "validation_accuracy": validation_accuracy,
                    "model_state_dict": model.state_dict(),
                },
                args.output / "best_model.pt",
            )

    summary = {
        "architecture": args.architecture,
        "weights": args.weights,
        "class_names": class_names,
        "device": str(device),
        "train_images": len(train_dataset),
        "validation_images": len(validation_dataset),
        "best_validation_accuracy": best_accuracy,
        "elapsed_seconds": time.time() - started_at,
        "history": history,
    }
    (args.output / "training_history.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"best_model={args.output / 'best_model.pt'}")
    print(f"best_validation_accuracy={best_accuracy:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
