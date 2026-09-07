from pathlib import Path
import json
import shutil
from datetime import datetime, timezone


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EVENT_REPORT = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "evaluated_change_events.json"
)

JEWAR_REPORT = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "jewar_airport"
    / "jewar_2022_2023_change_analysis.json"
)

BACKUP_REPORT = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "evaluated_change_events_before_jewar.json"
)


# ============================================================
# JEWAR EVENT
# ============================================================

JEWAR_EVENT_ID = 1000


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def save_json(path, data):
    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=2
        )


def relative_path(path):
    return str(
        Path(path).resolve().relative_to(
            PROJECT_ROOT.resolve()
        )
    ).replace(
        "\\",
        "/"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("ORION JEWAR CHANGE EVENT REGISTRATION")
    print("=" * 70)

    # --------------------------------------------------------
    # VERIFY REPORTS
    # --------------------------------------------------------

    if not EVENT_REPORT.exists():

        raise FileNotFoundError(
            "Existing evaluated event report not found:\n"
            f"{EVENT_REPORT}"
        )

    if not JEWAR_REPORT.exists():

        raise FileNotFoundError(
            "Jewar change analysis report not found:\n"
            f"{JEWAR_REPORT}"
        )

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    report = load_json(
        EVENT_REPORT
    )

    jewar = load_json(
        JEWAR_REPORT
    )

    events = report.get(
        "events",
        []
    )

    # --------------------------------------------------------
    # BACKUP
    # --------------------------------------------------------

    if not BACKUP_REPORT.exists():

        shutil.copy2(
            EVENT_REPORT,
            BACKUP_REPORT
        )

        print()
        print(
            "Backup created:"
        )

        print(
            BACKUP_REPORT
        )

    # --------------------------------------------------------
    # REMOVE EXISTING JEWAR EVENT IF PRESENT
    # --------------------------------------------------------

    original_count = len(
        events
    )

    events = [
        event
        for event in events
        if str(
            event.get(
                "tile_id"
            )
        ) != str(
            JEWAR_EVENT_ID
        )
    ]

    removed_count = (
        original_count
        - len(events)
    )

    if removed_count:

        print()
        print(
            f"Existing Jewar event "
            f"{JEWAR_EVENT_ID} replaced."
        )

    # --------------------------------------------------------
    # CHANGE RESULT
    # --------------------------------------------------------

    change_result = jewar.get(
        "change_result",
        {}
    )

    regions = change_result.get(
        "regions",
        []
    )

    largest_region = (
        regions[0]
        if regions
        else None
    )

    change_percentage = float(
        change_result.get(
            "change_percentage",
            0.0
        )
    )

    changed_pixels = int(
        change_result.get(
            "changed_pixels",
            0
        )
    )

    total_pixels = int(
        change_result.get(
            "total_pixels",
            0
        )
    )

    mean_change_intensity = float(
        change_result.get(
            "mean_change_intensity",
            0.0
        )
    )

    classification_score = float(
        jewar.get(
            "classification_score",
            0.0
        )
    )

    dominant_change_type = (
        jewar.get(
            "dominant_change_type",
            "OTHER CHANGE"
        )
    )

    # --------------------------------------------------------
    # CENTROID
    # --------------------------------------------------------

    centroid = None

    if largest_region:

        centroid = largest_region.get(
            "centroid"
        )

    # --------------------------------------------------------
    # BOUNDING BOX
    # --------------------------------------------------------

    bounding_box = None

    if largest_region:

        bounding_box = largest_region.get(
            "bounding_box"
        )

    # --------------------------------------------------------
    # SOURCE FILES
    # --------------------------------------------------------

    before_image = (
        PROJECT_ROOT
        / "data"
        / "tiles"
        / "jewar_airport"
        / "before"
        / "jewar_airport_before.png"
    )

    after_image = (
        PROJECT_ROOT
        / "data"
        / "tiles"
        / "jewar_airport"
        / "after"
        / "jewar_airport_after.png"
    )

    mask_image = (
        PROJECT_ROOT
        / "data"
        / "change_analysis"
        / "jewar_airport"
        / "jewar_2022_2023_change_mask.png"
    )

    source_raster = (
        PROJECT_ROOT
        / "data"
        / "datasets"
        / "jewar_airport_best"
        / "before"
        / "B04.tif"
    )

    required_files = [
        before_image,
        after_image,
        mask_image,
        source_raster
    ]

    missing = [
        str(path)
        for path in required_files
        if not path.exists()
    ]

    if missing:

        raise FileNotFoundError(
            "Required Jewar evidence files are missing:\n"
            + "\n".join(missing)
        )

    # --------------------------------------------------------
    # PIXEL LOCATION
    # --------------------------------------------------------

    if centroid:

        x = float(
            centroid.get(
                "x",
                0
            )
        )

        y = float(
            centroid.get(
                "y",
                0
            )
        )

    else:

        x = None
        y = None

    # --------------------------------------------------------
    # JEWAR EVENT
    # --------------------------------------------------------

    jewar_event = {

        "tile_id": JEWAR_EVENT_ID,

        "scene_id": "jewar_airport",

        "dataset": "jewar_airport_best",

        "location": (
            "Noida International Airport area, "
            "Jewar, Uttar Pradesh"
        ),

        "x": x,

        "y": y,

        "before_date": "2022-12-10",

        "after_date": "2023-10-06",

        "before": {

            "date": "2022-12-10",

            "observation": "2022-12-10",

            "filename": (
                "jewar_airport_before.png"
            ),

            "path": relative_path(
                before_image
            ),

            "source_raster": relative_path(
                source_raster
            ),

            "sensor": (
                "Copernicus Sentinel-2"
            ),

            "platform": "Sentinel-2",

            "product": (
                "Sentinel-2 Level-2A "
                "Surface Reflectance"
            )
        },

        "after": {

            "date": "2023-10-06",

            "observation": "2023-10-06",

            "filename": (
                "jewar_airport_after.png"
            ),

            "path": relative_path(
                after_image
            ),

            "source_raster": relative_path(
                PROJECT_ROOT
                / "data"
                / "datasets"
                / "jewar_airport_best"
                / "after"
                / "B04.tif"
            ),

            "sensor": (
                "Copernicus Sentinel-2"
            ),

            "platform": "Sentinel-2",

            "product": (
                "Sentinel-2 Level-2A "
                "Surface Reflectance"
            )
        },

        "change_percentage": (
            change_percentage
        ),

        "changed_pixels": (
            changed_pixels
        ),

        "total_pixels": (
            total_pixels
        ),

        "change_regions": (
            len(regions)
        ),

        "mean_change_intensity": (
            mean_change_intensity
        ),

        "largest_region": (
            largest_region
        ),

        "regions": regions,

        "dominant_change_type": (
            dominant_change_type
        ),

        "classification_score": (
            classification_score
        ),

        "mask_path": relative_path(
            mask_image
        ),

        "source_raster": relative_path(
            source_raster
        ),

        "source_crs": "EPSG:32643",

        "pixel_size_m": 10,

        "mgrs_tile": "43RGM",

        "detection_method": (
            "Jewar-specific temporal change "
            "detection using RGB percentile "
            "normalization, phase-correlation "
            "registration, adaptive percentile "
            "thresholding, morphology and "
            "connected-component analysis."
        ),

        "detection_configuration": {

            "change_percentile": (
                change_result.get(
                    "change_percentile",
                    80
                )
            ),

            "minimum_region_area": (
                change_result.get(
                    "minimum_region_area",
                    25
                )
            ),

            "morphology_kernel_size": (
                change_result.get(
                    "morphology_kernel_size",
                    3
                )
            )
        },

        # Conservative operational ranking.
        #
        # This is not a probability.
        "severity_score": round(
            min(
                1.0,
                (
                    change_percentage
                    / 20.0
                )
                * 0.6
                + classification_score
                * 0.4
            ),
            4
        ),

        "priority": "MEDIUM",

        "evidence_score": round(
            min(
                1.0,
                (
                    change_percentage
                    / 15.0
                )
                * 0.5
                + classification_score
                * 0.5
            ),
            4
        ),

        "evidence_confidence": "MEDIUM",

        "false_alarm_risk": "MEDIUM",

        "false_alarm_reasons": [
            (
                "Small AOI and multiple detected "
                "regions require analyst verification."
            ),
            (
                "RGB temporal change alone cannot "
                "prove construction activity."
            )
        ],

        "suppressed": False,

        "analyst_status": "UNREVIEWED",

        "registered_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "evidence": [

            {
                "type": "before",
                "path": relative_path(
                    before_image
                )
            },

            {
                "type": "after",
                "path": relative_path(
                    after_image
                )
            },

            {
                "type": "change_mask",
                "path": relative_path(
                    mask_image
                )
            }
        ]
    }

    # --------------------------------------------------------
    # APPEND
    # --------------------------------------------------------

    events.append(
        jewar_event
    )

    report["events"] = events

    # Keep the original report identity because this file
    # remains the shared evaluated-event registry.
    report["scene_id"] = "prayagraj"

    # Add dataset information without changing
    # the original Prayagraj data.
    report["datasets"] = [
        "prayagraj",
        "jewar_airport_best"
    ]

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_json(
        EVENT_REPORT,
        report
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("JEWAR EVENT REGISTERED")
    print("=" * 70)

    print(
        "Event ID:",
        JEWAR_EVENT_ID
    )

    print(
        "Dataset:",
        "jewar_airport_best"
    )

    print(
        "Before:",
        "2022-12-10"
    )

    print(
        "After:",
        "2023-10-06"
    )

    print(
        "Change:",
        f"{change_percentage}%"
    )

    print(
        "Changed pixels:",
        changed_pixels
    )

    print(
        "Regions:",
        len(regions)
    )

    print(
        "Change type:",
        dominant_change_type
    )

    print(
        "Classification:",
        classification_score
    )

    print(
        "Priority:",
        "MEDIUM"
    )

    print(
        "Confidence:",
        "MEDIUM"
    )

    print()
    print(
        "Mask:",
        relative_path(
            mask_image
        )
    )

    print()
    print(
        "Updated event registry:",
        EVENT_REPORT
    )

    print()
    print(
        f"Total registered events: "
        f"{len(events)}"
    )

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()