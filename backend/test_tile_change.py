from pathlib import Path

from PIL import Image

from backend.services.change_detection import detect_change


PROJECT_ROOT = Path(__file__).resolve().parent.parent


BEFORE_TILE = (
    PROJECT_ROOT
    / "data"
    / "tiles"
    / "prayagraj"
    / "before"
    / "tile_00060_x1280_y1280.png"
)

AFTER_TILE = (
    PROJECT_ROOT
    / "data"
    / "tiles"
    / "prayagraj"
    / "after"
    / "tile_00060_x1280_y1280.png"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "scenes"
    / "prayagraj"
    / "tile_00060_change_mask.png"
)


def main():
    print("=== ORION Temporal Tile Change Test ===")

    print(
        f"\nBefore tile:\n{BEFORE_TILE}"
    )

    print(
        f"\nAfter tile:\n{AFTER_TILE}"
    )

    if not BEFORE_TILE.exists():
        raise FileNotFoundError(
            f"Before tile not found:\n{BEFORE_TILE}"
        )

    if not AFTER_TILE.exists():
        raise FileNotFoundError(
            f"After tile not found:\n{AFTER_TILE}"
        )

    before = Image.open(
        BEFORE_TILE
    )

    after = Image.open(
        AFTER_TILE
    )

    print(
        f"\nBefore size: "
        f"{before.width} x {before.height}"
    )

    print(
        f"After size: "
        f"{after.width} x {after.height}"
    )

    print("\nRunning change detection...")

    result = detect_change(
        BEFORE_TILE,
        AFTER_TILE,
        OUTPUT_PATH
    )

    print("\n=== CHANGE RESULTS ===")

    print(
        f"Change regions: "
        f"{result.get('change_regions', 0)}"
    )

    print(
        f"Changed pixels: "
        f"{result.get('changed_pixels', 0)}"
    )

    print(
        f"Total pixels: "
        f"{result.get('total_pixels', 0)}"
    )

    print(
        f"Change percentage: "
        f"{result.get('change_percentage', 0):.3f}%"
    )

    print(
        f"Mean change intensity: "
        f"{result.get('mean_change_intensity', 0):.4f}"
    )

    largest_region = result.get(
        "largest_region"
    )

    if largest_region:
        print("\nLargest change region:")

        print(
            f"Area: "
            f"{largest_region.get('area_pixels', 0)} px"
        )

        print(
            f"Bounding box: "
            f"{largest_region.get('bounding_box')}"
        )

        print(
            f"Centroid: "
            f"{largest_region.get('centroid')}"
        )

        print(
            f"Mean intensity: "
            f"{largest_region.get('mean_change_intensity', 0):.4f}"
        )

    print(
        f"\nChange mask:\n{OUTPUT_PATH}"
    )

    if OUTPUT_PATH.exists():
        print(
            "Change mask file check: PASS"
        )
    else:
        print(
            "Change mask file check: FAIL"
        )

    print(
        "\n=== TEMPORAL TILE CHANGE TEST COMPLETE ==="
    )


if __name__ == "__main__":
    main()