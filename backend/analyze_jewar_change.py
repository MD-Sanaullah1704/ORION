from pathlib import Path
import json

import cv2
import numpy as np
import rasterio

from backend.services.change_detection import normalize_image
from backend.services.change_classifier import classify_regions


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_DIR = (
    PROJECT_ROOT
    / "data"
    / "datasets"
    / "jewar_airport_best"
)

BEFORE_DIR = DATASET_DIR / "before"
AFTER_DIR = DATASET_DIR / "after"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "jewar_airport"
)

RGB_DIR = OUTPUT_DIR / "rgb"

BEFORE_RGB = (
    RGB_DIR
    / "jewar_before_rgb.tif"
)

AFTER_RGB = (
    RGB_DIR
    / "jewar_after_rgb.tif"
)

CHANGE_MASK = (
    OUTPUT_DIR
    / "jewar_2022_2023_change_mask.png"
)

REPORT_PATH = (
    OUTPUT_DIR
    / "jewar_2022_2023_change_analysis.json"
)


# ============================================================
# JEWAR-SPECIFIC DETECTION SETTINGS
# ============================================================

# The original ORION detector uses:
#
#   90th percentile
#   5 x 5 morphology
#   500 pixels
#
# Jewar is a much smaller Sentinel-2 AOI.
#
# For this dataset we use a more sensitive configuration.

JEWAR_CHANGE_PERCENTILE = 80

JEWAR_MIN_REGION_AREA = 25

JEWAR_MORPHOLOGY_KERNEL_SIZE = 3


# ============================================================
# BAND PATHS
# ============================================================

BEFORE_B04 = BEFORE_DIR / "B04.tif"
BEFORE_B03 = BEFORE_DIR / "B03.tif"
BEFORE_B02 = BEFORE_DIR / "B02.tif"

AFTER_B04 = AFTER_DIR / "B04.tif"
AFTER_B03 = AFTER_DIR / "B03.tif"
AFTER_B02 = AFTER_DIR / "B02.tif"


# ============================================================
# READ BAND
# ============================================================

def read_band(path):

    with rasterio.open(path) as src:

        image = src.read(1)

        profile = src.profile.copy()

        transform = src.transform

        crs = src.crs

        width = src.width

        height = src.height

    return (
        image,
        profile,
        transform,
        crs,
        width,
        height
    )


# ============================================================
# VERIFY GRID
# ============================================================

def verify_same_grid(
    reference,
    other,
    reference_name,
    other_name
):

    if reference[4] != other[4]:
        raise ValueError(
            f"Width mismatch: "
            f"{reference_name} vs {other_name}"
        )

    if reference[5] != other[5]:
        raise ValueError(
            f"Height mismatch: "
            f"{reference_name} vs {other_name}"
        )

    if reference[2] != other[2]:
        raise ValueError(
            f"Transform mismatch: "
            f"{reference_name} vs {other_name}"
        )

    if reference[3] != other[3]:
        raise ValueError(
            f"CRS mismatch: "
            f"{reference_name} vs {other_name}"
        )


# ============================================================
# BUILD RGB GEOTIFF
# ============================================================

def build_rgb_geotiff(
    red_path,
    green_path,
    blue_path,
    output_path
):

    print()
    print("=" * 70)
    print("BUILDING RGB GEOTIFF")
    print("=" * 70)

    print("Red  :", red_path)
    print("Green:", green_path)
    print("Blue :", blue_path)

    red_info = read_band(red_path)

    green_info = read_band(green_path)

    blue_info = read_band(blue_path)

    verify_same_grid(
        red_info,
        green_info,
        "B04",
        "B03"
    )

    verify_same_grid(
        red_info,
        blue_info,
        "B04",
        "B02"
    )

    red = red_info[0]

    green = green_info[0]

    blue = blue_info[0]

    rgb = np.stack(
        [
            red,
            green,
            blue
        ],
        axis=0
    ).astype(np.float32)

    profile = red_info[1].copy()

    profile.update(
        driver="GTiff",
        dtype="float32",
        count=3,
        width=red_info[4],
        height=red_info[5],
        crs=red_info[3],
        transform=red_info[2],
        compress="deflate"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with rasterio.open(
        output_path,
        "w",
        **profile
    ) as dst:

        dst.write(rgb)

        dst.set_band_description(
            1,
            "B04 - Red"
        )

        dst.set_band_description(
            2,
            "B03 - Green"
        )

        dst.set_band_description(
            3,
            "B02 - Blue"
        )

    print(
        f"Saved: {output_path}"
    )

    print(
        f"Raster size: "
        f"{red_info[4]} x {red_info[5]}"
    )

    print(
        f"CRS: {red_info[3]}"
    )

    return red_info


# ============================================================
# LOAD RGB
# ============================================================

def load_rgb(path):

    with rasterio.open(path) as src:

        image = src.read()

    image = np.transpose(
        image,
        (1, 2, 0)
    )

    return image.astype(
        np.float32
    )


# ============================================================
# REGION ANALYSIS
# ============================================================

def analyze_regions(
    mask,
    difference,
    min_area
):

    number_of_labels, labels, stats, centroids = (
        cv2.connectedComponentsWithStats(
            mask,
            connectivity=8
        )
    )

    cleaned_mask = np.zeros_like(
        mask
    )

    regions = []

    for label in range(
        1,
        number_of_labels
    ):

        area = int(
            stats[
                label,
                cv2.CC_STAT_AREA
            ]
        )

        if area < min_area:
            continue

        x = int(
            stats[
                label,
                cv2.CC_STAT_LEFT
            ]
        )

        y = int(
            stats[
                label,
                cv2.CC_STAT_TOP
            ]
        )

        width = int(
            stats[
                label,
                cv2.CC_STAT_WIDTH
            ]
        )

        height = int(
            stats[
                label,
                cv2.CC_STAT_HEIGHT
            ]
        )

        centroid_x = float(
            centroids[label][0]
        )

        centroid_y = float(
            centroids[label][1]
        )

        region_pixels = (
            labels == label
        )

        mean_change = float(
            np.mean(
                difference[
                    region_pixels
                ]
            )
        )

        cleaned_mask[
            region_pixels
        ] = 255

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
        key=lambda item:
            item["area_pixels"],
        reverse=True
    )

    for index, region in enumerate(
        regions,
        start=1
    ):

        region["region_id"] = index

    return (
        cleaned_mask,
        regions
    )


# ============================================================
# JEWAR CHANGE DETECTOR
# ============================================================

def detect_jewar_change(
    before_path,
    after_path,
    output_path
):

    print()
    print("=" * 70)
    print("JEWAR-SPECIFIC CHANGE DETECTION")
    print("=" * 70)

    print(
        "Change percentile:",
        JEWAR_CHANGE_PERCENTILE
    )

    print(
        "Minimum region:",
        JEWAR_MIN_REGION_AREA
    )

    print(
        "Morphology kernel:",
        JEWAR_MORPHOLOGY_KERNEL_SIZE,
        "x",
        JEWAR_MORPHOLOGY_KERNEL_SIZE
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    before = load_rgb(
        before_path
    )

    after = load_rgb(
        after_path
    )

    if before.shape != after.shape:

        raise ValueError(
            f"Image dimensions do not match: "
            f"{before.shape} vs "
            f"{after.shape}"
        )

    # --------------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------------

    before = normalize_image(
        before
    )

    after = normalize_image(
        after
    )

    # --------------------------------------------------------
    # REGISTRATION
    # --------------------------------------------------------

    before_gray = cv2.cvtColor(
        before,
        cv2.COLOR_RGB2GRAY
    )

    after_gray = cv2.cvtColor(
        after,
        cv2.COLOR_RGB2GRAY
    )

    shift, response = (
        cv2.phaseCorrelate(
            before_gray.astype(
                np.float32
            ),
            after_gray.astype(
                np.float32
            )
        )
    )

    dx, dy = shift

    print(
        "Registration shift:",
        dx,
        dy
    )

    print(
        "Registration response:",
        response
    )

    transform = np.float32(
        [
            [1, 0, -dx],
            [0, 1, -dy]
        ]
    )

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

    # --------------------------------------------------------
    # TEMPORAL DIFFERENCE
    # --------------------------------------------------------

    difference = np.mean(
        np.abs(
            after - before
        ),
        axis=2
    )

    # --------------------------------------------------------
    # ADAPTIVE THRESHOLD
    # --------------------------------------------------------

    adaptive_threshold = np.percentile(
        difference,
        JEWAR_CHANGE_PERCENTILE
    )

    # Keep a minimum threshold so very small
    # numerical variations do not become change.

    effective_threshold = max(
        0.15,
        adaptive_threshold
    )

    print(
        "Adaptive threshold:",
        adaptive_threshold
    )

    print(
        "Effective threshold:",
        effective_threshold
    )

    # --------------------------------------------------------
    # INITIAL MASK
    # --------------------------------------------------------

    mask = (
        difference >= effective_threshold
    ).astype(
        np.uint8
    ) * 255

    print(
        "Pixels before morphology:",
        int(
            np.count_nonzero(mask)
        )
    )

    # --------------------------------------------------------
    # MORPHOLOGY
    # --------------------------------------------------------

    kernel = np.ones(
        (
            JEWAR_MORPHOLOGY_KERNEL_SIZE,
            JEWAR_MORPHOLOGY_KERNEL_SIZE
        ),
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

    print(
        "Pixels after morphology:",
        int(
            np.count_nonzero(mask)
        )
    )

    # --------------------------------------------------------
    # REGION ANALYSIS
    # --------------------------------------------------------

    mask, regions = analyze_regions(
        mask,
        difference,
        JEWAR_MIN_REGION_AREA
    )

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    classified_regions = classify_regions(
        regions,
        before_image=before,
        after_image=after
    )

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    changed_pixels = int(
        np.count_nonzero(mask)
    )

    total_pixels = int(
        mask.shape[0]
        * mask.shape[1]
    )

    change_percentage = (
        changed_pixels
        / total_pixels
    ) * 100

    if changed_pixels > 0:

        mean_change_intensity = float(
            np.mean(
                difference[
                    mask > 0
                ]
            )
        )

    else:

        mean_change_intensity = 0.0

    largest_region = (
        classified_regions[0]
        if classified_regions
        else None
    )

    # --------------------------------------------------------
    # SAVE MASK
    # --------------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    cv2.imwrite(
        str(output_path),
        mask
    )

    return {
        "width": mask.shape[1],

        "height": mask.shape[0],

        "estimated_shift": {
            "x": round(
                float(dx),
                3
            ),
            "y": round(
                float(dy),
                3
            )
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

        "change_percentile": (
            JEWAR_CHANGE_PERCENTILE
        ),

        "minimum_region_area": (
            JEWAR_MIN_REGION_AREA
        ),

        "morphology_kernel_size": (
            JEWAR_MORPHOLOGY_KERNEL_SIZE
        ),

        "change_regions": len(
            classified_regions
        ),

        "changed_pixels": (
            changed_pixels
        ),

        "total_pixels": (
            total_pixels
        ),

        "change_percentage": round(
            change_percentage,
            3
        ),

        "mean_change_intensity": round(
            mean_change_intensity,
            4
        ),

        "largest_region": (
            largest_region
        ),

        "regions": (
            classified_regions
        ),

        "change_mask": str(
            output_path
        )
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("ORION JEWAR TEMPORAL CHANGE ANALYSIS")
    print("=" * 70)

    print()
    print("BEFORE: 2022-12-10")
    print("AFTER : 2023-10-06")

    print()
    print(
        "This is a Jewar-specific sensitivity "
        "configuration."
    )

    print(
        "The global Prayagraj detector is "
        "NOT modified."
    )

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    required = [
        BEFORE_B04,
        BEFORE_B03,
        BEFORE_B02,
        AFTER_B04,
        AFTER_B03,
        AFTER_B02
    ]

    missing = [
        str(path)
        for path in required
        if not path.exists()
    ]

    if missing:

        raise FileNotFoundError(
            "Missing required files:\n"
            + "\n".join(missing)
        )

    # --------------------------------------------------------
    # OUTPUT DIRECTORIES
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    RGB_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # RGB CREATION
    # --------------------------------------------------------

    before_info = build_rgb_geotiff(
        BEFORE_B04,
        BEFORE_B03,
        BEFORE_B02,
        BEFORE_RGB
    )

    after_info = build_rgb_geotiff(
        AFTER_B04,
        AFTER_B03,
        AFTER_B02,
        AFTER_RGB
    )

    # --------------------------------------------------------
    # GRID CHECK
    # --------------------------------------------------------

    before_grid = read_band(
        BEFORE_B04
    )

    after_grid = read_band(
        AFTER_B04
    )

    verify_same_grid(
        before_grid,
        after_grid,
        "BEFORE",
        "AFTER"
    )

    print()
    print(
        "Before/after spatial grid verified."
    )

    # --------------------------------------------------------
    # DETECT
    # --------------------------------------------------------

    result = detect_jewar_change(
        BEFORE_RGB,
        AFTER_RGB,
        CHANGE_MASK
    )

    # --------------------------------------------------------
    # DOMINANT CLASS
    # --------------------------------------------------------

    regions = result["regions"]

    if regions:

        dominant_type = regions[0].get(
            "change_type",
            "OTHER CHANGE"
        )

        classification_score = regions[0].get(
            "classification_score",
            0.0
        )

    else:

        dominant_type = (
            "NO QUALIFYING CHANGE"
        )

        classification_score = 0.0

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    report = {

        "dataset": (
            "jewar_airport_best"
        ),

        "scene_id": (
            "jewar_airport"
        ),

        "location": (
            "Noida International Airport "
            "area, Jewar, Uttar Pradesh"
        ),

        "before_date": (
            "2022-12-10"
        ),

        "after_date": (
            "2023-10-06"
        ),

        "sensor": (
            "Copernicus Sentinel-2"
        ),

        "platform": (
            "Sentinel-2"
        ),

        "product": (
            "Sentinel-2 Level-2A "
            "Surface Reflectance"
        ),

        "mgrs_tile": (
            "43RGM"
        ),

        "source_crs": (
            str(before_info[3])
        ),

        "pixel_size_m": 10,

        "before_bands": {
            "B04": str(BEFORE_B04),
            "B03": str(BEFORE_B03),
            "B02": str(BEFORE_B02)
        },

        "after_bands": {
            "B04": str(AFTER_B04),
            "B03": str(AFTER_B03),
            "B02": str(AFTER_B02)
        },

        "before_rgb": str(
            BEFORE_RGB.relative_to(
                PROJECT_ROOT
            )
        ),

        "after_rgb": str(
            AFTER_RGB.relative_to(
                PROJECT_ROOT
            )
        ),

        "change_mask": str(
            CHANGE_MASK.relative_to(
                PROJECT_ROOT
            )
        ),

        "detector": {
            "change_percentile": (
                JEWAR_CHANGE_PERCENTILE
            ),

            "minimum_region_area": (
                JEWAR_MIN_REGION_AREA
            ),

            "morphology_kernel_size": (
                JEWAR_MORPHOLOGY_KERNEL_SIZE
            )
        },

        "dominant_change_type": (
            dominant_type
        ),

        "classification_score": (
            classification_score
        ),

        "change_result": result
    }

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=2
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("JEWAR CHANGE ANALYSIS COMPLETE")
    print("=" * 70)

    print(
        "Change percentage:",
        result["change_percentage"],
        "%"
    )

    print(
        "Changed pixels:",
        result["changed_pixels"]
    )

    print(
        "Total pixels:",
        result["total_pixels"]
    )

    print(
        "Change regions:",
        result["change_regions"]
    )

    print(
        "Mean change intensity:",
        result["mean_change_intensity"]
    )

    print(
        "Dominant change type:",
        dominant_type
    )

    print(
        "Classification score:",
        classification_score
    )

    print()

    for region in regions:

        print(
            f"Region {region.get('region_id')}: "
            f"area={region.get('area_pixels')} "
            f"pixels | "
            f"type={region.get('change_type', 'OTHER CHANGE')} | "
            f"bbox={region.get('bounding_box')} | "
            f"centroid={region.get('centroid')}"
        )

    print()
    print(
        "MASK:"
    )

    print(
        CHANGE_MASK
    )

    print()
    print(
        "REPORT:"
    )

    print(
        REPORT_PATH
    )

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()