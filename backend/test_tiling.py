from pathlib import Path

from backend.services.tiling import generate_tiles


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RASTER_PATH = (
    PROJECT_ROOT
    / "data"
    / "scenes"
    / "prayagraj"
    / "before.tif"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "tiles"
    / "prayagraj"
    / "before"
)


def main():
    print("=== ORION Satellite Tiling Test ===")

    print(f"Input: {RASTER_PATH}")
    print(f"Output: {OUTPUT_DIR}")

    tiles = generate_tiles(
        raster_path=RASTER_PATH,
        output_dir=OUTPUT_DIR,
        tile_size=256,
        stride=256,
    )

    print(f"\nTiles generated: {len(tiles)}")

    if tiles:
        print("\nFirst tile:")
        print(tiles[0])

        print("\nLast tile:")
        print(tiles[-1])

    print("\n=== TILING COMPLETE ===")


if __name__ == "__main__":
    main()