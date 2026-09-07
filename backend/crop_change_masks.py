from pathlib import Path
import json
from PIL import Image, ImageDraw


# ============================================================
# ORION — GENERATE TILE CHANGE MASKS FROM DETECTED REGIONS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EVENTS_FILE = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "evaluated_change_events.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "masks"
)

TILE_SIZE = 256


# ============================================================
# LOAD EVENTS
# ============================================================

def load_events():

    with open(
        EVENTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        report = json.load(file)

    return report.get(
        "events",
        []
    )


# ============================================================
# DRAW MASK
# ============================================================

def create_mask(event):

    mask = Image.new(
        "L",
        (
            TILE_SIZE,
            TILE_SIZE
        ),
        0
    )

    draw = ImageDraw.Draw(mask)

    regions = event.get(
        "regions",
        []
    )

    if not regions:

        largest = event.get(
            "largest_region"
        )

        if isinstance(
            largest,
            dict
        ):
            regions = [largest]

    for region in regions:

        bbox = region.get(
            "bounding_box",
            {}
        )

        x = int(
            bbox.get(
                "x",
                0
            )
        )

        y = int(
            bbox.get(
                "y",
                0
            )
        )

        width = int(
            bbox.get(
                "width",
                0
            )
        )

        height = int(
            bbox.get(
                "height",
                0
            )
        )

        if width <= 0 or height <= 0:
            continue

        left = max(
            0,
            min(
                TILE_SIZE - 1,
                x
            )
        )

        top = max(
            0,
            min(
                TILE_SIZE - 1,
                y
            )
        )

        right = max(
            0,
            min(
                TILE_SIZE - 1,
                x + width - 1
            )
        )

        bottom = max(
            0,
            min(
                TILE_SIZE - 1,
                y + height - 1
            )
        )

        if right < left or bottom < top:
            continue

        # Fill detected region.
        draw.rectangle(
            (
                left,
                top,
                right,
                bottom
            ),
            fill=255
        )

    return mask


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("==============================================")
    print("ORION TILE CHANGE MASK REBUILD")
    print("==============================================")
    print()

    if not EVENTS_FILE.exists():

        raise FileNotFoundError(
            f"Event file not found:\n{EVENTS_FILE}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    events = load_events()

    print(
        f"Events found: {len(events)}"
    )

    print()

    created = 0
    empty = 0
    failed = 0

    for event in events:

        try:

            tile_id = int(
                event.get(
                    "tile_id",
                    -1
                )
            )

            if tile_id < 0:
                failed += 1
                continue

            mask = create_mask(
                event
            )

            output_path = (
                OUTPUT_DIR
                / f"{tile_id}_change_mask.png"
            )

            mask.save(
                output_path,
                format="PNG"
            )

            # Count visible mask pixels.
            changed_pixels = sum(
                1
                for value in mask.getdata()
                if value > 0
            )

            expected_pixels = int(
                event.get(
                    "changed_pixels",
                    0
                )
            )

            if changed_pixels == 0:

                empty += 1

            else:

                created += 1

            print(
                f"[OK] Tile {tile_id:03d} | "
                f"mask pixels={changed_pixels} | "
                f"detected pixels={expected_pixels}"
            )

        except Exception as error:

            failed += 1

            print(
                f"[ERROR] Tile {event.get('tile_id', '?')}: "
                f"{error}"
            )

    print()
    print("==============================================")
    print("MASK REBUILD COMPLETE")
    print("==============================================")
    print(
        f"Events processed : {len(events)}"
    )
    print(
        f"Masks created    : {created}"
    )
    print(
        f"Empty masks      : {empty}"
    )
    print(
        f"Failed           : {failed}"
    )
    print(
        f"Output directory : {OUTPUT_DIR}"
    )
    print("==============================================")
    print()


if __name__ == "__main__":
    main()