from pathlib import Path
import re


TILE_PATTERN = re.compile(
    r"tile_(\d+)_x(\d+)_y(\d+)"
)


def parse_tile_coordinates(filename):
    """
    Extract tile index and spatial coordinates
    from a tile filename.

    Example:
        tile_00060_x1280_y1280.png

    Returns:
        {
            "tile_index": 60,
            "x": 1280,
            "y": 1280
        }
    """

    match = TILE_PATTERN.search(
        Path(filename).stem
    )

    if not match:
        raise ValueError(
            f"Invalid tile filename: {filename}"
        )

    return {
        "tile_index": int(match.group(1)),
        "x": int(match.group(2)),
        "y": int(match.group(3)),
    }


def build_temporal_pairs(
    before_dir,
    after_dir
):
    """
    Match before and after tiles using their
    spatial x/y coordinates.

    Returns a list of dictionaries containing
    corresponding observations.
    """

    before_dir = Path(before_dir)
    after_dir = Path(after_dir)

    if not before_dir.exists():
        raise FileNotFoundError(
            f"Before tile directory not found:\n"
            f"{before_dir}"
        )

    if not after_dir.exists():
        raise FileNotFoundError(
            f"After tile directory not found:\n"
            f"{after_dir}"
        )

    before_tiles = sorted(
        before_dir.glob("*.png")
    )

    after_tiles = sorted(
        after_dir.glob("*.png")
    )

    if not before_tiles:
        raise FileNotFoundError(
            f"No before tiles found:\n"
            f"{before_dir}"
        )

    if not after_tiles:
        raise FileNotFoundError(
            f"No after tiles found:\n"
            f"{after_dir}"
        )

    before_by_coordinates = {}

    for tile in before_tiles:
        coordinates = parse_tile_coordinates(
            tile.name
        )

        key = (
            coordinates["x"],
            coordinates["y"]
        )

        if key in before_by_coordinates:
            raise ValueError(
                "Duplicate before tile coordinates: "
                f"{key}"
            )

        before_by_coordinates[key] = {
            "path": str(tile),
            "filename": tile.name,
            **coordinates,
        }

    after_by_coordinates = {}

    for tile in after_tiles:
        coordinates = parse_tile_coordinates(
            tile.name
        )

        key = (
            coordinates["x"],
            coordinates["y"]
        )

        if key in after_by_coordinates:
            raise ValueError(
                "Duplicate after tile coordinates: "
                f"{key}"
            )

        after_by_coordinates[key] = {
            "path": str(tile),
            "filename": tile.name,
            **coordinates,
        }

    before_coordinates = set(
        before_by_coordinates.keys()
    )

    after_coordinates = set(
        after_by_coordinates.keys()
    )

    missing_in_after = (
        before_coordinates
        - after_coordinates
    )

    missing_in_before = (
        after_coordinates
        - before_coordinates
    )

    if missing_in_after:
        raise ValueError(
            "Before tiles without matching after "
            f"tiles: {sorted(missing_in_after)}"
        )

    if missing_in_before:
        raise ValueError(
            "After tiles without matching before "
            f"tiles: {sorted(missing_in_before)}"
        )

    pairs = []

    for key in sorted(before_coordinates):
        before = before_by_coordinates[key]
        after = after_by_coordinates[key]

        pairs.append(
            {
                "tile_id": before["tile_index"],
                "x": before["x"],
                "y": before["y"],
                "before": before,
                "after": after,
            }
        )

    return pairs