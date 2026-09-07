from pathlib import Path
import json


def calculate_severity_score(result):
    """
    Calculate a ranking score for a detected change tile.

    IMPORTANT:
    This is a prioritization score, NOT a probability
    and NOT a validated confidence score.
    """

    change_percentage = float(
        result.get("change_percentage", 0)
    )

    change_regions = int(
        result.get("change_regions", 0)
    )

    mean_intensity = float(
        result.get("mean_change_intensity", 0)
    )

    largest_region = result.get(
        "largest_region"
    ) or {}

    largest_area = int(
        largest_region.get(
            "area_pixels",
            0
        )
    )

    # Change-area component.
    area_score = min(
        change_percentage / 8.0,
        1.0
    )

    # Region-count component.
    region_score = min(
        change_regions / 5.0,
        1.0
    )

    # Intensity component.
    intensity_score = min(
        mean_intensity,
        1.0
    )

    # Largest-region component.
    largest_region_score = min(
        largest_area / 10000.0,
        1.0
    )

    severity = (
        area_score * 0.40
        + region_score * 0.20
        + intensity_score * 0.20
        + largest_region_score * 0.20
    )

    return round(
        severity,
        4
    )


def assign_priority(severity_score):
    """
    Convert the severity ranking score into an
    analyst-review priority.

    This is a workflow priority, not a probability.
    """

    if severity_score >= 0.65:
        return "HIGH"

    if severity_score >= 0.40:
        return "MEDIUM"

    return "LOW"


def rank_change_events(results):
    """
    Add severity and priority to temporal tile results
    and return them sorted from highest to lowest
    priority.
    """

    events = []

    for result in results:
        event = result.copy()

        severity_score = (
            calculate_severity_score(result)
        )

        event["severity_score"] = (
            severity_score
        )

        event["priority"] = (
            assign_priority(
                severity_score
            )
        )

        events.append(event)

    events.sort(
        key=lambda item: (
            item["severity_score"],
            item.get(
                "change_percentage",
                0
            ),
            item.get(
                "changed_pixels",
                0
            )
        ),
        reverse=True
    )

    return events


def load_temporal_results(report_path):
    """
    Load the temporal tile-analysis JSON report.
    """

    report_path = Path(report_path)

    if not report_path.exists():
        raise FileNotFoundError(
            f"Temporal analysis report not found:\n"
            f"{report_path}"
        )

    with open(
        report_path,
        "r",
        encoding="utf-8"
    ) as file:
        report = json.load(file)

    return report


def save_ranked_events(
    events,
    output_path
):
    """
    Save ranked change events as JSON.
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