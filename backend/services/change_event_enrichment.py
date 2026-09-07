from pathlib import Path
import json
from collections import defaultdict


def classify_event(event):
    """
    Determine the dominant change type for a temporal tile.

    Classification is based on the existing heuristic
    region classifier results.

    IMPORTANT:
    This is an analytical label, not a validated probability.
    """

    regions = event.get("top_regions", [])

    if not regions:
        return {
            "dominant_change_type": "OTHER CHANGE",
            "classification_score": 0.0,
            "classification_basis": "No classified change regions"
        }

    # Aggregate region evidence by change type.
    type_area = defaultdict(float)
    type_scores = defaultdict(list)

    for region in regions:
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
                0
            )
        )

        type_area[change_type] += area
        type_scores[change_type].append(score)

    # Select the type covering the largest changed area.
    dominant_type = max(
        type_area,
        key=type_area.get
    )

    scores = type_scores[dominant_type]

    average_score = (
        sum(scores) / len(scores)
        if scores
        else 0.0
    )

    return {
        "dominant_change_type": dominant_type,
        "classification_score": round(
            average_score,
            4
        ),
        "classification_basis": (
            f"Largest classified changed area: "
            f"{int(type_area[dominant_type])} pixels"
        )
    }


def enrich_change_events(events):
    """
    Add classification information to ranked events.
    """

    enriched = []

    for event in events:
        item = event.copy()

        classification = classify_event(
            event
        )

        item.update(
            classification
        )

        enriched.append(item)

    return enriched


def load_ranked_events(path):
    """
    Load the ranked change-event report.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Ranked event report not found:\n{path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:
        report = json.load(file)

    return report.get(
        "events",
        []
    )


def save_enriched_events(
    events,
    output_path
):
    """
    Save the enriched change-event report.
    """

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    report = {
        "scene_id": "prayagraj",
        "event_count": len(events),
        "events": events
    }

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            report,
            file,
            indent=2
        )