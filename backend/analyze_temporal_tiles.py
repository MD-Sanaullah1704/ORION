from pathlib import Path
import json

from backend.services.temporal_matching import (
    build_temporal_pairs
)

from backend.services.change_detection import (
    detect_change
)

from backend.services.change_classifier import (
    classify_regions
)


# ============================================================
# PROJECT PATHS
# ============================================================

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

MASK_DIR = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "masks"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "temporal_tile_results.json"
)


# ============================================================
# DOMINANT CLASSIFICATION
# ============================================================

def get_dominant_classification(
    classified_regions
):
    """
    Select the dominant change type based on
    total changed area.

    classification_score is a heuristic score,
    NOT a probability.
    """

    if not classified_regions:
        return (
            "OTHER CHANGE",
            0.0
        )

    area_by_type = {}

    scores_by_type = {}

    for region in classified_regions:

        change_type = region.get(
            "change_type",
            "OTHER CHANGE"
        )

        area = float(
            region.get(
                "area_pixels",
                0
            )
        )

        score = float(
            region.get(
                "classification_score",
                0.0
            )
        )

        area_by_type[change_type] = (
            area_by_type.get(
                change_type,
                0.0
            )
            + area
        )

        scores_by_type.setdefault(
            change_type,
            []
        ).append(score)

    if not area_by_type:
        return (
            "OTHER CHANGE",
            0.0
        )

    dominant_type = max(
        area_by_type,
        key=area_by_type.get
    )

    scores = scores_by_type.get(
        dominant_type,
        []
    )

    if scores:
        average_score = (
            sum(scores) / len(scores)
        )
    else:
        average_score = 0.0

    return (
        dominant_type,
        round(
            average_score,
            4
        )
    )


# ============================================================
# ANALYZE ONE TEMPORAL TILE PAIR
# ============================================================

def analyze_pair(pair):
    """
    Analyze one before/after temporal tile pair.
    """

    before_path = Path(
        pair["before"]["path"]
    )

    after_path = Path(
        pair["after"]["path"]
    )

    tile_id = pair["tile_id"]

    mask_path = (
        MASK_DIR
        / f"{tile_id}_change_mask.png"
    )

    print(
        f"Processing tile {tile_id} "
        f"x={pair['x']} "
        f"y={pair['y']}"
    )

    # --------------------------------------------------------
    # CHANGE DETECTION
    # --------------------------------------------------------

    change_result = detect_change(
        before_path,
        after_path,
        mask_path
    )

    # --------------------------------------------------------
    # REGION CLASSIFICATION
    # --------------------------------------------------------

    regions = change_result.get(
        "regions",
        []
    )

    classified_regions = classify_regions(
        regions
    )

    # --------------------------------------------------------
    # DOMINANT CHANGE TYPE
    # --------------------------------------------------------

    (
        dominant_type,
        classification_score
    ) = get_dominant_classification(
        classified_regions
    )

    # --------------------------------------------------------
    # BUILD RESULT
    # --------------------------------------------------------

    result = {
        "tile_id": tile_id,

        "x": pair["x"],

        "y": pair["y"],

        "before": pair["before"],

        "after": pair["after"],

        "change_percentage": change_result.get(
            "change_percentage",
            0.0
        ),

        "changed_pixels": change_result.get(
            "changed_pixels",
            0
        ),

        "total_pixels": change_result.get(
            "total_pixels",
            0
        ),

        "change_regions": change_result.get(
            "change_regions",
            0
        ),

        "mean_change_intensity": change_result.get(
            "mean_change_intensity",
            0.0
        ),

        "largest_region": change_result.get(
            "largest_region"
        ),

        "regions": classified_regions,

        "dominant_change_type": dominant_type,

        "classification_score": classification_score,

        "mask_path": str(
            mask_path.relative_to(
                PROJECT_ROOT
            )
        )
    }

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=== ORION Temporal Change Analysis ==="
    )

    # --------------------------------------------------------
    # CREATE OUTPUT DIRECTORIES
    # --------------------------------------------------------

    MASK_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # BUILD TEMPORAL PAIRS
    # --------------------------------------------------------

    print(
        "\nBuilding temporal pairs..."
    )

    pairs = build_temporal_pairs(
        BEFORE_DIR,
        AFTER_DIR
    )

    print(
        f"Temporal pairs: {len(pairs)}"
    )

    # --------------------------------------------------------
    # ANALYZE ALL PAIRS
    # --------------------------------------------------------

    results = []

    for pair in pairs:

        result = analyze_pair(
            pair
        )

        results.append(
            result
        )

    # --------------------------------------------------------
    # FIND TILES WITH CHANGE
    # --------------------------------------------------------

    changed_tiles = [
        result
        for result in results
        if result["change_percentage"] > 0
    ]

    # --------------------------------------------------------
    # BUILD REPORT
    # --------------------------------------------------------

    report = {
        "scene_id": "prayagraj",

        "before_date": "2024-12-13",

        "after_date": "2025-01-27",

        "total_tiles": len(
            results
        ),

        "tiles_with_detected_change": len(
            changed_tiles
        ),

        "tiles_without_detected_change": (
            len(results)
            - len(changed_tiles)
        ),

        "results": results
    }

    # --------------------------------------------------------
    # SAVE REPORT
    # --------------------------------------------------------

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=2
        )

    print(
        f"\nReport saved to:\n"
        f"{OUTPUT_REPORT}"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print(
        "\n=== SUMMARY ==="
    )

    print(
        f"Total tiles: {len(results)}"
    )

    print(
        f"Tiles with detected change: "
        f"{len(changed_tiles)}"
    )

    print(
        f"Tiles without detected change: "
        f"{len(results) - len(changed_tiles)}"
    )

    # --------------------------------------------------------
    # RANK CHANGES
    # --------------------------------------------------------

    print(
        "\n=== TOP CLASSIFIED CHANGES ==="
    )

    ranked = sorted(
        changed_tiles,
        key=lambda item: (
            item["change_percentage"],
            item["classification_score"]
        ),
        reverse=True
    )

    for rank, result in enumerate(
        ranked[:10],
        start=1
    ):

        print(
            f"{rank}. "
            f"tile={result['tile_id']} "
            f"x={result['x']} "
            f"y={result['y']} "
            f"change="
            f"{result['change_percentage']:.3f}% "
            f"type="
            f"{result['dominant_change_type']} "
            f"classification="
            f"{result['classification_score']:.4f}"
        )

    # --------------------------------------------------------
    # COMPLETION
    # --------------------------------------------------------

    print(
        "\n=== TEMPORAL ANALYSIS COMPLETE ==="
    )


if __name__ == "__main__":
    main()