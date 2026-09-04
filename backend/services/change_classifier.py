import math


def classify_change_region(
    region,
    before_image=None,
    after_image=None
):
    """
    Rule-based baseline classifier for detected change regions.

    before_image and after_image are accepted so that stronger
    image/spectral classifiers can be added later without changing
    the calling interface.

    IMPORTANT:
    The current classifier does NOT classify water variation because
    the available 3-band RGB imagery is not sufficient for a validated
    water-index-based decision.
    """

    bbox = region["bounding_box"]

    width = bbox["width"]
    height = bbox["height"]
    area = region["area_pixels"]
    intensity = region["mean_change_intensity"]

    if width <= 0 or height <= 0:
        return {
            "change_type": "UNKNOWN",
            "classification_score": 0.0,
            "reason": "Invalid region dimensions"
        }

    aspect_ratio = max(width, height) / min(width, height)

    bbox_area = width * height
    fill_ratio = area / bbox_area if bbox_area > 0 else 0

    # ---------------------------------------------------------
    # ROAD DEVELOPMENT
    # ---------------------------------------------------------
    if aspect_ratio >= 3.0 and fill_ratio >= 0.20:
        score = min(
            1.0,
            0.55
            + min((aspect_ratio - 3.0) / 7.0, 0.25)
            + min(intensity * 0.40, 0.20)
        )

        return {
            "change_type": "ROAD DEVELOPMENT",
            "classification_score": round(score, 3),
            "reason": (
                "Elongated change region with road-like geometry"
            )
        }

    # ---------------------------------------------------------
    # CONSTRUCTION
    # ---------------------------------------------------------
    if (
        fill_ratio >= 0.35
        and intensity >= 0.40
        and area >= 1000
    ):
        score = min(
            1.0,
            0.45
            + min(fill_ratio * 0.30, 0.25)
            + min(intensity * 0.50, 0.30)
        )

        return {
            "change_type": "CONSTRUCTION",
            "classification_score": round(score, 3),
            "reason": (
                "Compact region with substantial surface change"
            )
        }

    # ---------------------------------------------------------
    # CLEARANCE / ACTIVITY
    # ---------------------------------------------------------
    if area >= 5000 and intensity >= 0.35:
        score = min(
            1.0,
            0.40
            + min(area / 50000, 0.30)
            + min(intensity * 0.50, 0.30)
        )

        return {
            "change_type": "CLEARANCE / ACTIVITY",
            "classification_score": round(score, 3),
            "reason": (
                "Large substantial change region without "
                "strong linear geometry"
            )
        }

    # ---------------------------------------------------------
    # OTHER CHANGE
    # ---------------------------------------------------------
    score = min(
        1.0,
        0.30
        + min(intensity * 0.40, 0.30)
        + min(math.log10(max(area, 1)) / 10, 0.20)
    )

    return {
        "change_type": "OTHER CHANGE",
        "classification_score": round(score, 3),
        "reason": (
            "Substantial change detected, but the current "
            "region features do not support a more specific class"
        )
    }


def classify_regions(
    regions,
    before_image=None,
    after_image=None
):
    """
    Classify all detected regions using the current baseline rules.
    """

    classified_regions = []

    for region in regions:
        region_copy = region.copy()

        classification = classify_change_region(
            region,
            before_image=before_image,
            after_image=after_image
        )

        region_copy.update(classification)
        classified_regions.append(region_copy)

    return classified_regions