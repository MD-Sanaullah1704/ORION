from pathlib import Path

import cv2
import numpy as np
import rasterio


def load_rgb(path):
    """
    Load the first three bands of a GeoTIFF as
    an image with shape (height, width, 3).
    """

    with rasterio.open(path) as src:
        if src.count < 3:
            raise ValueError(
                f"Expected at least 3 bands, found {src.count}"
            )

        image = src.read([1, 2, 3])

    image = np.transpose(image, (1, 2, 0))

    return image.astype(np.float32)


def normalize_image(image):
    """
    Normalize each RGB channel independently to 0-1.
    """

    normalized = np.zeros_like(
        image,
        dtype=np.float32
    )

    for channel in range(image.shape[2]):
        band = image[:, :, channel]

        minimum = np.percentile(band, 2)
        maximum = np.percentile(band, 98)

        if maximum <= minimum:
            continue

        band = np.clip(
            band,
            minimum,
            maximum
        )

        normalized[:, :, channel] = (
            (band - minimum)
            / (maximum - minimum)
        )

    return normalized


def analyze_regions(
    mask,
    difference,
    min_area=500
):
    """
    Keep meaningful connected regions and calculate
    object-level statistics for each one.
    """

    number_of_labels, labels, stats, centroids = (
        cv2.connectedComponentsWithStats(
            mask,
            connectivity=8
        )
    )

    cleaned_mask = np.zeros_like(mask)

    regions = []

    for label in range(1, number_of_labels):
        area = int(
            stats[label, cv2.CC_STAT_AREA]
        )

        if area < min_area:
            continue

        x = int(
            stats[label, cv2.CC_STAT_LEFT]
        )

        y = int(
            stats[label, cv2.CC_STAT_TOP]
        )

        width = int(
            stats[label, cv2.CC_STAT_WIDTH]
        )

        height = int(
            stats[label, cv2.CC_STAT_HEIGHT]
        )

        centroid_x = float(
            centroids[label][0]
        )

        centroid_y = float(
            centroids[label][1]
        )

        region_pixels = labels == label

        mean_change = float(
            np.mean(
                difference[region_pixels]
            )
        )

        cleaned_mask[region_pixels] = 255

        regions.append(
            {
                "region_id": len(regions) + 1,
                "area_pixels": area,
                "bounding_box": {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height
                },
                "centroid": {
                    "x": round(
                        centroid_x,
                        2
                    ),
                    "y": round(
                        centroid_y,
                        2
                    )
                },
                "mean_change_intensity": round(
                    mean_change,
                    4
                )
            }
        )

    regions.sort(
        key=lambda region: region["area_pixels"],
        reverse=True
    )

    for index, region in enumerate(
        regions,
        start=1
    ):
        region["region_id"] = index

    return cleaned_mask, regions


def detect_change(
    before_path,
    after_path,
    output_path,
    threshold=0.15,
    min_region_area=500
):
    """
    Detect spatially coherent change objects between
    two RGB satellite images.
    """

    before_path = Path(before_path)
    after_path = Path(after_path)
    output_path = Path(output_path)

    # ---------------------------------
    # Load images
    # ---------------------------------

    before = load_rgb(before_path)
    after = load_rgb(after_path)

    # ---------------------------------
    # Validate dimensions
    # ---------------------------------

    if before.shape != after.shape:
        raise ValueError(
            f"Image dimensions do not match: "
            f"{before.shape} vs {after.shape}"
        )

    # ---------------------------------
    # Normalize images
    # ---------------------------------

    before = normalize_image(before)
    after = normalize_image(after)

    # ---------------------------------
    # Image registration
    # ---------------------------------

    before_gray = cv2.cvtColor(
        before,
        cv2.COLOR_RGB2GRAY
    )

    after_gray = cv2.cvtColor(
        after,
        cv2.COLOR_RGB2GRAY
    )

    shift, response = cv2.phaseCorrelate(
        before_gray.astype(np.float32),
        after_gray.astype(np.float32)
    )

    dx, dy = shift

    transform = np.float32([
        [1, 0, -dx],
        [0, 1, -dy]
    ])

    after = cv2.warpAffine(
        after,
        transform,
        (
            after.shape[1],
            after.shape[0]
        ),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT
    )

    # ---------------------------------
    # Pixel difference
    # ---------------------------------

    difference = np.mean(
        np.abs(after - before),
        axis=2
    )

    # ---------------------------------
    # Adaptive threshold
    # ---------------------------------

    adaptive_threshold = np.percentile(
        difference,
        90
    )

    effective_threshold = max(
        threshold,
        adaptive_threshold
    )

    # ---------------------------------
    # Initial mask
    # ---------------------------------

    mask = (
        difference >= effective_threshold
    ).astype(np.uint8) * 255

    # ---------------------------------
    # Morphological cleanup
    # ---------------------------------

    kernel = np.ones(
        (5, 5),
        np.uint8
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel
    )

    # ---------------------------------
    # Object-level region analysis
    # ---------------------------------

    mask, regions = analyze_regions(
        mask,
        difference,
        min_area=min_region_area
    )

    # ---------------------------------
    # Overall statistics
    # ---------------------------------

    changed_pixels = int(
        np.count_nonzero(mask)
    )

    total_pixels = int(
        mask.shape[0] * mask.shape[1]
    )

    change_percentage = (
        changed_pixels
        / total_pixels
    ) * 100

    if changed_pixels > 0:
        mean_change_intensity = float(
            np.mean(
                difference[mask > 0]
            )
        )
    else:
        mean_change_intensity = 0.0

    if regions:
        largest_region = regions[0]
    else:
        largest_region = None

    # ---------------------------------
    # Save mask
    # ---------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    cv2.imwrite(
        str(output_path),
        mask
    )

    # ---------------------------------
    # Return result
    # ---------------------------------

    return {
        "before": str(before_path),
        "after": str(after_path),
        "width": mask.shape[1],
        "height": mask.shape[0],
        "estimated_shift": {
            "x": round(float(dx), 3),
            "y": round(float(dy), 3)
        },
        "registration_response": round(
            float(response),
            4
        ),
        "adaptive_threshold": round(
            float(adaptive_threshold),
            4
        ),
        "effective_threshold": round(
            float(effective_threshold),
            4
        ),
        "minimum_region_area": min_region_area,
        "change_regions": len(regions),
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "change_percentage": round(
            change_percentage,
            3
        ),
        "mean_change_intensity": round(
            mean_change_intensity,
            4
        ),
        "largest_region": largest_region,
        "regions": regions,
        "change_mask": str(output_path)
    }