from pathlib import Path
import json


# ============================================================
# ORION CHANGE CONFIDENCE / FALSE-ALARM SUPPRESSION
# ============================================================

"""
Analyst-oriented evidence and confidence layer.

IMPORTANT:
- This is NOT a trained probability model.
- It does NOT claim validated accuracy.
- The score is a heuristic evidence score.
- The purpose is to suppress weak/noisy detections
  before they reach the analyst review queue.

The current imagery is 3-band RGB imagery, so this layer
does not use NIR/NDVI/NDWI or other multispectral indices.
"""


# ============================================================
# SCORE COMPONENTS
# ============================================================

def calculate_evidence_score(event):
    """
    Calculate a heuristic evidence score from multiple
    independent change indicators.

    Returns a value between 0 and 1.

    This is an evidence score, NOT a probability.
    """

    change_percentage = float(
        event.get(
            "change_percentage",
            0.0
        )
    )

    change_regions = int(
        event.get(
            "change_regions",
            0
        )
    )

    mean_intensity = float(
        event.get(
            "mean_change_intensity",
            0.0
        )
    )

    classification_score = float(
        event.get(
            "classification_score",
            0.0
        )
    )

    largest_region = (
        event.get(
            "largest_region"
        )
        or {}
    )

    largest_area = float(
        largest_region.get(
            "area_pixels",
            0
        )
    )

    total_pixels = float(
        event.get(
            "total_pixels",
            0
        )
    )

    # --------------------------------------------------------
    # 1. CHANGE MAGNITUDE
    # --------------------------------------------------------

    magnitude_score = min(
        change_percentage / 5.0,
        1.0
    )

    # --------------------------------------------------------
    # 2. REGION SUPPORT
    # --------------------------------------------------------

    region_score = min(
        change_regions / 3.0,
        1.0
    )

    # --------------------------------------------------------
    # 3. CHANGE INTENSITY
    # --------------------------------------------------------

    intensity_score = min(
        max(mean_intensity, 0.0),
        1.0
    )

    # --------------------------------------------------------
    # 4. LARGEST REGION SUPPORT
    # --------------------------------------------------------

    largest_region_score = min(
        largest_area / 10000.0,
        1.0
    )

    # --------------------------------------------------------
    # 5. CLASSIFICATION SUPPORT
    # --------------------------------------------------------

    classification_support = min(
        max(classification_score, 0.0),
        1.0
    )

    # --------------------------------------------------------
    # 6. SPATIAL CONCENTRATION
    # --------------------------------------------------------

    if (
        total_pixels > 0
        and largest_area > 0
    ):
        concentration = (
            largest_area / total_pixels
        )

        concentration_score = min(
            concentration * 8.0,
            1.0
        )
    else:
        concentration_score = 0.0

    # --------------------------------------------------------
    # WEIGHTED EVIDENCE SCORE
    # --------------------------------------------------------

    score = (
        magnitude_score * 0.25
        + region_score * 0.10
        + intensity_score * 0.15
        + largest_region_score * 0.15
        + classification_support * 0.20
        + concentration_score * 0.15
    )

    return round(
        min(max(score, 0.0), 1.0),
        4
    )


# ============================================================
# FALSE-ALARM CHECKS
# ============================================================

def evaluate_false_alarm_risk(event):
    """
    Evaluate whether an event contains characteristics
    commonly associated with weak or noisy detections.

    Returns:
        risk_level
        suppression decision
        reasons
    """

    reasons = []

    change_percentage = float(
        event.get(
            "change_percentage",
            0.0
        )
    )

    change_regions = int(
        event.get(
            "change_regions",
            0
        )
    )

    mean_intensity = float(
        event.get(
            "mean_change_intensity",
            0.0
        )
    )

    largest_region = (
        event.get(
            "largest_region"
        )
        or {}
    )

    largest_area = float(
        largest_region.get(
            "area_pixels",
            0
        )
    )

    # --------------------------------------------------------
    # WEAK CHANGE
    # --------------------------------------------------------

    if change_percentage < 0.5:
        reasons.append(
            "Very small detected change area"
        )

    # --------------------------------------------------------
    # LOW INTENSITY
    # --------------------------------------------------------

    if mean_intensity < 0.20:
        reasons.append(
            "Low change intensity"
        )

    # --------------------------------------------------------
    # TINY REGIONS
    # --------------------------------------------------------

    if largest_area < 500:
        reasons.append(
            "No substantial connected change region"
        )

    # --------------------------------------------------------
    # MANY SMALL REGIONS
    # --------------------------------------------------------

    if (
        change_regions >= 5
        and largest_area < 1500
    ):
        reasons.append(
            "Many small disconnected regions"
        )

    # --------------------------------------------------------
    # DETERMINE RISK
    # --------------------------------------------------------

    risk_count = len(reasons)

    if risk_count >= 3:
        risk_level = "HIGH"
        suppress = True

    elif risk_count == 2:
        risk_level = "MEDIUM"
        suppress = False

    elif risk_count == 1:
        risk_level = "LOW"
        suppress = False

    else:
        risk_level = "LOW"
        suppress = False

    return {
        "false_alarm_risk": risk_level,
        "suppressed": suppress,
        "false_alarm_reasons": reasons
    }


# ============================================================
# CONFIDENCE LABEL
# ============================================================

def confidence_label(
    evidence_score
):
    """
    Convert heuristic evidence score into an
    analyst-facing confidence label.

    This is NOT a probability.
    """

    if evidence_score >= 0.70:
        return "HIGH"

    if evidence_score >= 0.45:
        return "MEDIUM"

    return "LOW"


# ============================================================
# ENRICH ONE EVENT
# ============================================================

def evaluate_event(event):
    """
    Add evidence score, confidence label and
    false-alarm assessment to one change event.
    """

    enriched = event.copy()

    evidence_score = (
        calculate_evidence_score(
            event
        )
    )

    false_alarm = (
        evaluate_false_alarm_risk(
            event
        )
    )

    enriched[
        "evidence_score"
    ] = evidence_score

    enriched[
        "evidence_confidence"
    ] = confidence_label(
        evidence_score
    )

    enriched[
        "false_alarm_risk"
    ] = false_alarm[
        "false_alarm_risk"
    ]

    enriched[
        "false_alarm_reasons"
    ] = false_alarm[
        "false_alarm_reasons"
    ]

    enriched[
        "suppressed"
    ] = false_alarm[
        "suppressed"
    ]

    # --------------------------------------------------------
    # EVIDENCE SUMMARY
    # --------------------------------------------------------

    evidence = []

    if float(
        event.get(
            "change_percentage",
            0
        )
    ) >= 2.0:
        evidence.append(
            "Meaningful changed area"
        )

    if int(
        event.get(
            "change_regions",
            0
        )
    ) >= 2:
        evidence.append(
            "Multiple connected change regions"
        )

    if float(
        event.get(
            "mean_change_intensity",
            0
        )
    ) >= 0.40:
        evidence.append(
            "Strong pixel-level change intensity"
        )

    if float(
        event.get(
            "classification_score",
            0
        )
    ) >= 0.70:
        evidence.append(
            "Strong region classification support"
        )

    if (
        event.get(
            "largest_region"
        )
        or {}
    ).get(
        "area_pixels",
        0
    ) >= 5000:
        evidence.append(
            "Large connected change region"
        )

    enriched[
        "evidence"
    ] = evidence

    return enriched


# ============================================================
# PROCESS ALL EVENTS
# ============================================================

def evaluate_events(events):
    """
    Evaluate every ranked change event.
    """

    evaluated = []

    for event in events:

        evaluated.append(
            evaluate_event(
                event
            )
        )

    return evaluated


# ============================================================
# LOAD RANKED REPORT
# ============================================================

def load_ranked_events(
    report_path
):
    """
    Load ranked change events JSON.
    """

    report_path = Path(
        report_path
    )

    if not report_path.exists():
        raise FileNotFoundError(
            f"Ranked event report not found:\n"
            f"{report_path}"
        )

    with open(
        report_path,
        "r",
        encoding="utf-8"
    ) as file:

        report = json.load(
            file
        )

    return report


# ============================================================
# SAVE EVALUATED REPORT
# ============================================================

def save_evaluated_events(
    events,
    output_path
):
    """
    Save evaluated change events.
    """

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    report = {
        "scene_id": "prayagraj",

        "event_count": len(
            events
        ),

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