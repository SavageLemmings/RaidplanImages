#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
DEFAULT_OPACITY = 0.35
DEFAULT_MARGIN = 24
DEFAULT_SCALE = 0.18


def load_watermark(path: Path, opacity: float) -> Image.Image:
    watermark = Image.open(path).convert("RGBA")

    if opacity < 1.0:
        alpha = watermark.getchannel("A")
        alpha = alpha.point(lambda value: int(value * opacity))
        watermark.putalpha(alpha)

    return watermark


def resize_watermark(watermark: Image.Image, base: Image.Image, scale: float) -> Image.Image:
    target_width = max(1, int(base.width * scale))
    ratio = target_width / watermark.width
    target_height = max(1, int(watermark.height * ratio))
    return watermark.resize((target_width, target_height), Image.Resampling.LANCZOS)


def get_position(base: Image.Image, mark: Image.Image, position: str, margin: int) -> tuple[int, int]:
    positions = {
        "top": ((base.width - mark.width) // 2, margin),
        "right": (base.width - mark.width - margin, (base.height - mark.height) // 2),
        "bottom": ((base.width - mark.width) // 2, base.height - mark.height - margin),
        "left": (margin, (base.height - mark.height) // 2),
        "top-left": (margin, margin),
        "top-right": (base.width - mark.width - margin, margin),
        "bottom-left": (margin, base.height - mark.height - margin),
        "bottom-right": (base.width - mark.width - margin, base.height - mark.height - margin),
        "center": ((base.width - mark.width) // 2, (base.height - mark.height) // 2),
    }

    return positions[position]


def rotate_for_position(watermark: Image.Image, position: str) -> Image.Image:
    rotations = {
        "top": 0,
        "right": -90,
        "bottom": 180,
        "left": 90,
        "top-left": 0,
        "top-right": 0,
        "bottom-left": 0,
        "bottom-right": 0,
        "center": 0,
    }

    angle = rotations[position]
    if angle == 0:
        return watermark

    return watermark.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)


def apply_single_watermark(base: Image.Image, watermark: Image.Image, position: str, margin: int, scale: float) -> None:
    mark = resize_watermark(watermark, base, scale)
    mark = rotate_for_position(mark, position)
    base.alpha_composite(mark, get_position(base, mark, position, margin))


def apply_watermark(input_path: Path, output_path: Path, watermark: Image.Image, positions: list[str], margin: int, scale: float, quality: int) -> None:
    with Image.open(input_path) as img:
        base = img.convert("RGBA")

        for position in parse_positions(positions):
            apply_single_watermark(base, watermark, position, margin, scale)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        suffix = output_path.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            base.convert("RGB").save(output_path, quality=quality, optimize=True)
        elif suffix == ".webp":
            base.save(output_path, quality=quality, method=6)
        else:
            base.save(output_path, optimize=True)

        print(f"Watermarked: {input_path} -> {output_path}")


def parse_positions(value: str) -> list[str]:
    aliases = {
        "cardinal": ["top", "right", "bottom", "left"],
        "corners": ["top-left", "top-right", "bottom-left", "bottom-right"],
        "all": ["top", "right", "bottom", "left", "top-left", "top-right", "bottom-left", "bottom-right"],
    }

    if value in aliases:
        return aliases[value]

    positions = [item.strip() for item in value.split(",") if item.strip()]
    allowed = {"top", "right", "bottom", "left", "top-left", "top-right", "bottom-left", "bottom-right", "center"}

    invalid = [position for position in positions if position not in allowed]
    if invalid:
        raise argparse.ArgumentTypeError(f"Invalid position(s): {', '.join(invalid)}")

    return positions


def iter_images(input_dir: Path, watermark_path: Path):
    for path in input_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS and path.resolve() != watermark_path.resolve():
            yield path


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a watermark to all images in a folder.")
    #parser.add_argument("input", type=Path, help="Input folder containing images", default=".")
    #parser.add_argument("watermark", type=Path, help="Watermark image, preferably PNG with transparency", default="watermark.png")
    parser.add_argument("-o", "--output", type=Path, default=Path("watermarked"), help="Output folder")
    parser.add_argument("--in-place", action="store_true", help="Overwrite original files")
    parser.add_argument("--position", type=str, default="cardinal", help="Position, comma-list, or preset: cardinal, corners, all")
    parser.add_argument("--opacity", type=float, default=DEFAULT_OPACITY, help="Watermark opacity from 0.0 to 1.0")
    parser.add_argument("--margin", type=int, default=DEFAULT_MARGIN, help="Margin in pixels")
    parser.add_argument("--scale", type=float, default=DEFAULT_SCALE, help="Watermark width relative to image width, e.g. 0.18 = 18%%")
    parser.add_argument("--quality", type=int, default=92, help="JPEG/WebP output quality")
    args = parser.parse_args()

    input_dir = Path(".")
    watermark_path = Path("watermark.png")

    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input folder does not exist: {input_dir}")

    if not watermark_path.exists() or not watermark_path.is_file():
        raise SystemExit(f"Watermark file does not exist: {watermark_path}")

    if not 0.0 <= args.opacity <= 1.0:
        raise SystemExit("--opacity must be between 0.0 and 1.0")

    if args.scale <= 0:
        raise SystemExit("--scale must be greater than 0")

    watermark = load_watermark(watermark_path, args.opacity)

    for image_path in iter_images(input_dir, watermark_path):
        output_path = image_path if args.in_place else args.output / image_path.relative_to(input_dir)
        apply_watermark(image_path, output_path, watermark, args.position, args.margin, args.scale, args.quality)


if __name__ == "__main__":
    main()
