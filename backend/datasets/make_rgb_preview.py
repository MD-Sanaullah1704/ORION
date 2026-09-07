from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageOps, ImageDraw, ImageFont


OUTPUT_SIZE = 768


def find_band(root: Path, scene: str, band: str) -> Path:
    """
    Find a Sentinel-2 band inside a before/after scene directory.
    """
    scene_dir = root / scene

    if not scene_dir.exists():
        raise FileNotFoundError(f"Scene directory not found: {scene_dir}")

    candidates = list(scene_dir.rglob(f"*{band}*.tif")) + list(
        scene_dir.rglob(f"*{band}*.tiff")
    )

    if not candidates:
        raise FileNotFoundError(
            f"Could not find band {band} inside {scene_dir}"
        )

    # Prefer 10 m bands where possible.
    candidates.sort(
        key=lambda p: (
            "10m" not in p.name.lower(),
            len(p.name),
        )
    )

    return candidates[0]


def percentile_stretch(array: np.ndarray) -> np.ndarray:
    """
    Robustly normalize one Sentinel-2 band using 2nd–98th percentiles.
    """
    array = array.astype(np.float32)

    valid = np.isfinite(array) & (array > 0)

    if not np.any(valid):
        return np.zeros(array.shape, dtype=np.uint8)

    values = array[valid]

    low = np.percentile(values, 2)
    high = np.percentile(values, 98)

    if high <= low:
        high = low + 1.0

    stretched = (array - low) / (high - low)
    stretched = np.clip(stretched, 0.0, 1.0)

    # Invalid pixels become black.
    stretched[~valid] = 0.0

    return (stretched * 255).astype(np.uint8)


def create_rgb(scene_dir: Path, output_path: Path, label: str) -> None:
    """
    Create an RGB preview from Sentinel-2 B04/B03/B02.
    """

    root = scene_dir.parent
    scene_name = scene_dir.name

    print(f"\nCreating {label} preview...")
    print(f"Scene: {scene_name}")

    red_path = find_band(root, scene_name, "B04")
    green_path = find_band(root, scene_name, "B03")
    blue_path = find_band(root, scene_name, "B02")

    print(f"Red   : {red_path.name}")
    print(f"Green : {green_path.name}")
    print(f"Blue  : {blue_path.name}")

    with rasterio.open(red_path) as src_r:
        red = src_r.read(1)

    with rasterio.open(green_path) as src_g:
        green = src_g.read(1)

    with rasterio.open(blue_path) as src_b:
        blue = src_b.read(1)

    # All RGB bands should already be at 10 m resolution.
    if red.shape != green.shape or red.shape != blue.shape:
        raise ValueError(
            f"RGB band dimensions do not match: "
            f"R={red.shape}, G={green.shape}, B={blue.shape}"
        )

    print(f"Source size: {red.shape[1]} x {red.shape[0]}")

    r = percentile_stretch(red)
    g = percentile_stretch(green)
    b = percentile_stretch(blue)

    rgb = np.stack([r, g, b], axis=-1)

    image = Image.fromarray(rgb, mode="RGB")

    # Preserve aspect ratio.
    image.thumbnail(
        (OUTPUT_SIZE, OUTPUT_SIZE),
        Image.Resampling.LANCZOS,
    )

    # Put the image on a square white canvas.
    canvas = Image.new(
        "RGB",
        (OUTPUT_SIZE, OUTPUT_SIZE),
        (255, 255, 255),
    )

    x = (OUTPUT_SIZE - image.width) // 2
    y = (OUTPUT_SIZE - image.height) // 2

    canvas.paste(image, (x, y))

    # Add a small label so BEFORE/AFTER cannot be confused.
    draw = ImageDraw.Draw(canvas)

    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()

    text = label.upper()

    # Text background.
    bbox = draw.textbbox((0, 0), text, font=font)
    padding = 10

    box = (
        15,
        15,
        15 + (bbox[2] - bbox[0]) + padding * 2,
        15 + (bbox[3] - bbox[1]) + padding * 2,
    )

    draw.rectangle(box, fill=(255, 255, 255))
    draw.text(
        (15 + padding, 15 + padding),
        text,
        fill=(0, 0, 0),
        font=font,
    )

    canvas.save(
        output_path,
        format="PNG",
        optimize=True,
    )

    print(f"Saved: {output_path}")
    print(f"Preview size: {OUTPUT_SIZE} x {OUTPUT_SIZE}")


def create_side_by_side(
    before_path: Path,
    after_path: Path,
    output_path: Path,
) -> None:
    """
    Create a large side-by-side comparison image.
    """

    before = Image.open(before_path).convert("RGB")
    after = Image.open(after_path).convert("RGB")

    comparison = Image.new(
        "RGB",
        (OUTPUT_SIZE * 2, OUTPUT_SIZE),
        (255, 255, 255),
    )

    comparison.paste(before, (0, 0))
    comparison.paste(after, (OUTPUT_SIZE, 0))

    draw = ImageDraw.Draw(comparison)

    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()

    # Divider.
    draw.rectangle(
        (OUTPUT_SIZE - 2, 0, OUTPUT_SIZE + 2, OUTPUT_SIZE),
        fill=(255, 255, 255),
    )

    # Labels.
    for x, text in [
        (20, "BEFORE"),
        (OUTPUT_SIZE + 20, "AFTER"),
    ]:
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        draw.rectangle(
            (
                x - 5,
                15,
                x + width + 15,
                15 + height + 15,
            ),
            fill=(255, 255, 255),
        )

        draw.text(
            (x, 20),
            text,
            fill=(0, 0, 0),
            font=font,
        )

    comparison.save(
        output_path,
        format="PNG",
        optimize=True,
    )

    print(f"Saved comparison: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ORION Sentinel-2 RGB preview generator"
    )

    parser.add_argument(
        "--root",
        required=True,
        help="Dataset root containing before/ and after/ directories",
    )

    args = parser.parse_args()

    root = Path(args.root).resolve()

    if not root.exists():
        raise FileNotFoundError(
            f"Dataset root does not exist: {root}"
        )

    before_dir = root / "before"
    after_dir = root / "after"

    if not before_dir.exists():
        raise FileNotFoundError(
            f"Missing before directory: {before_dir}"
        )

    if not after_dir.exists():
        raise FileNotFoundError(
            f"Missing after directory: {after_dir}"
        )

    before_output = root / "before_rgb_preview.png"
    after_output = root / "after_rgb_preview.png"
    comparison_output = root / "before_after_comparison.png"

    print("=" * 70)
    print("ORION — Sentinel-2 RGB Preview Generator")
    print("=" * 70)
    print(f"Dataset: {root}")

    create_rgb(
        before_dir,
        before_output,
        "BEFORE",
    )

    create_rgb(
        after_dir,
        after_output,
        "AFTER",
    )

    create_side_by_side(
        before_output,
        after_output,
        comparison_output,
    )

    print("\n" + "=" * 70)
    print("PREVIEW GENERATION COMPLETE")
    print("=" * 70)
    print(f"BEFORE     : {before_output}")
    print(f"AFTER      : {after_output}")
    print(f"COMPARISON : {comparison_output}")


if __name__ == "__main__":
    main()