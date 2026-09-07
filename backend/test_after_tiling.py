from pathlib import Path

from backend.services.tiling import generate_tiles


PROJECT_ROOT = Path(__file__).resolve().parent.parent


AFTER_RASTER = (
    PROJECT_ROOT
    / "data"
    / "scenes"
    / "prayagraj"
    / "after.tif"
)


AFTER_TILES_DIR = (
    PROJECT_ROOT
    / "data"
    / "tiles"
    / "prayagraj"
    / "after"
)


def main():
    print("=== ORION After-Image Tiling Test ===")

    print(
        f"\nInput raster:\n{AFTER_RASTER}"
    )

    if not AFTER_RASTER.exists():
        raise FileNotFoundError(
            f"After image not found:\n{AFTER_RASTER}"
        )

    print(
        f"\nOutput directory:\n{AFTER_TILES_DIR}"
    )

    tiles = generate_tiles(
        raster_path=AFTER_RASTER,
        output_dir=AFTER_TILES_DIR,
        tile_size=256,
        stride=256,
    )

    print(
        f"\nTiles generated: {len(tiles)}"
    )

    if not tiles:
        raise RuntimeError(
            "No tiles were generated."
        )

    print("\nFirst tile:")
    print(
        tiles[0]["filename"]
    )

    print("\nLast tile:")
    print(
        tiles[-1]["filename"]
    )

    print("\n=== VERIFICATION ===")

    if len(tiles) == 121:
        print(
            "Tile count check: PASS"
        )
    else:
        print(
            "Tile count check: FAIL"
        )

    first_tile = tiles[0]

    if (
        first_tile["width"] == 256
        and first_tile["height"] == 256
    ):
        print(
            "Tile dimensions check: PASS"
        )
    else:
        print(
            "Tile dimensions check: FAIL"
        )

    print(
        "\n=== AFTER TILING COMPLETE ==="
    )


if __name__ == "__main__":
    main()