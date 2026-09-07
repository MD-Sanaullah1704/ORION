from pathlib import Path

from backend.services.temporal_matching import (
    build_temporal_pairs
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


BEFORE_DIR = (
    PROJECT_ROOT
    / "data"
    / "tiles"
    / "prayagraj"
    / "before"
)


AFTER_DIR = (
    PROJECT_ROOT
    / "data"
    / "tiles"
    / "prayagraj"
    / "after"
)


def main():
    print("=== ORION Temporal Tile Matching Test ===")

    print(
        f"\nBefore directory:\n{BEFORE_DIR}"
    )

    print(
        f"\nAfter directory:\n{AFTER_DIR}"
    )

    pairs = build_temporal_pairs(
        before_dir=BEFORE_DIR,
        after_dir=AFTER_DIR
    )

    print(
        f"\nTemporal pairs created: {len(pairs)}"
    )

    if not pairs:
        raise RuntimeError(
            "No temporal pairs were created."
        )

    print("\nFirst pair:")

    first = pairs[0]

    print(
        f"Tile ID: {first['tile_id']}"
    )

    print(
        f"Coordinates: "
        f"x={first['x']} "
        f"y={first['y']}"
    )

    print(
        f"Before: "
        f"{first['before']['filename']}"
    )

    print(
        f"After:  "
        f"{first['after']['filename']}"
    )

    print("\nMiddle pair:")

    middle = pairs[
        len(pairs) // 2
    ]

    print(
        f"Tile ID: {middle['tile_id']}"
    )

    print(
        f"Coordinates: "
        f"x={middle['x']} "
        f"y={middle['y']}"
    )

    print(
        f"Before: "
        f"{middle['before']['filename']}"
    )

    print(
        f"After:  "
        f"{middle['after']['filename']}"
    )

    print("\nLast pair:")

    last = pairs[-1]

    print(
        f"Tile ID: {last['tile_id']}"
    )

    print(
        f"Coordinates: "
        f"x={last['x']} "
        f"y={last['y']}"
    )

    print(
        f"Before: "
        f"{last['before']['filename']}"
    )

    print(
        f"After:  "
        f"{last['after']['filename']}"
    )

    print("\n=== VERIFICATION ===")

    if len(pairs) == 121:
        print(
            "Temporal pair count check: PASS"
        )
    else:
        print(
            "Temporal pair count check: FAIL"
        )

    coordinates_match = all(
        pair["before"]["x"]
        == pair["after"]["x"]
        and
        pair["before"]["y"]
        == pair["after"]["y"]
        for pair in pairs
    )

    if coordinates_match:
        print(
            "Coordinate matching check: PASS"
        )
    else:
        print(
            "Coordinate matching check: FAIL"
        )

    print(
        "\n=== TEMPORAL MATCHING COMPLETE ==="
    )


if __name__ == "__main__":
    main()