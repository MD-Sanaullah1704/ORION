from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer

from backend.incremental_ingest import (
    load_remoteclip,
    encode_image,
)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)


MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "remoteclip"
    / "RemoteCLIP-ViT-B-32.pt"
)


# ============================================================
# EXISTING PRAYAGRAJ INDEXES
# ============================================================

PRAYAGRAJ_BEFORE_INDEX = (
    PROJECT_ROOT
    / "data"
    / "indexes"
    / "prayagraj"
    / "before"
)


PRAYAGRAJ_AFTER_INDEX = (
    PROJECT_ROOT
    / "data"
    / "indexes"
    / "prayagraj"
    / "after"
)


# ============================================================
# COMBINED INDEX
# ============================================================

COMBINED_INDEX_DIR = (
    PROJECT_ROOT
    / "data"
    / "indexes"
    / "orion_combined"
)


COMBINED_INDEX_PATH = (
    COMBINED_INDEX_DIR
    / "index.faiss"
)


COMBINED_METADATA_PATH = (
    COMBINED_INDEX_DIR
    / "metadata.json"
)


COMBINED_MANIFEST_PATH = (
    COMBINED_INDEX_DIR
    / "manifest.json"
)


# ============================================================
# JEWAR DATASET
# ============================================================

JEWAR_DATASET_DIR = (
    PROJECT_ROOT
    / "data"
    / "datasets"
    / "jewar_airport_best"
)


JEWAR_TILES_DIR = (
    PROJECT_ROOT
    / "data"
    / "tiles"
    / "jewar_airport"
)


JEWAR_BEFORE_IMAGE = (
    JEWAR_TILES_DIR
    / "before"
    / "jewar_airport_before.png"
)


JEWAR_AFTER_IMAGE = (
    JEWAR_TILES_DIR
    / "after"
    / "jewar_airport_after.png"
)


JEWAR_BEFORE_B04 = (
    JEWAR_DATASET_DIR
    / "before"
    / "B04.tif"
)


JEWAR_AFTER_B04 = (
    JEWAR_DATASET_DIR
    / "after"
    / "B04.tif"
)


EMBEDDING_DIMENSION = 512


# ============================================================
# HELPERS
# ============================================================

def find_band(
    root: Path,
    band_name: str,
) -> Path | None:
    """
    Find a Sentinel-2 band TIFF recursively.

    Supports:

        B02.tif
        B03.tif
        B04.tif

    and names such as:

        *_B02.tif
        *_B03.tif
        *_B04.tif
    """

    if not root.exists():
        return None

    candidates: list[Path] = []

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".tif",
            ".tiff",
        }:
            continue

        stem = path.stem.lower()

        if (
            stem == band_name.lower()
            or stem.endswith(
                "_" + band_name.lower()
            )
            or stem.endswith(
                "-" + band_name.lower()
            )
        ):
            candidates.append(path)

    if not candidates:
        return None

    candidates.sort(
        key=lambda path: (
            len(path.name),
            str(path),
        )
    )

    return candidates[0]


# ============================================================
# ROBUST NORMALIZATION
# ============================================================

def robust_normalize(
    array: np.ndarray,
) -> np.ndarray:
    """
    Convert Sentinel-2 uint16 data into
    display RGB values.
    """

    array = array.astype(
        np.float32
    )

    valid = np.isfinite(
        array
    )

    if not np.any(valid):

        return np.zeros_like(
            array,
            dtype=np.float32,
        )

    values = array[valid]

    low, high = np.percentile(
        values,
        [2, 98],
    )

    if high <= low:

        return np.zeros_like(
            array,
            dtype=np.float32,
        )

    normalized = (
        (array - low)
        / (high - low)
    )

    normalized = np.clip(
        normalized,
        0.0,
        1.0,
    )

    return normalized


# ============================================================
# READ REAL GEOSPATIAL INFORMATION
# ============================================================

def read_raster_geospatial(
    raster_path: Path,
) -> dict[str, Any]:
    """
    Read the real geospatial information directly
    from the Sentinel-2 GeoTIFF.

    This function does NOT invent coordinates.

    It reads:

        CRS
        transform
        bounds
        raster size
        pixel size
        projected center
        WGS84 latitude
        WGS84 longitude
    """

    if not raster_path.exists():

        raise FileNotFoundError(
            "Raster not found:\n"
            f"{raster_path}"
        )

    with rasterio.open(
        raster_path
    ) as src:

        width = src.width
        height = src.height
        count = src.count

        dtype = (
            src.dtypes[0]
            if src.count > 0
            else "unknown"
        )

        # ----------------------------------------------------
        # CRS
        # ----------------------------------------------------

        crs = (
            src.crs.to_string()
            if src.crs
            else None
        )

        # ----------------------------------------------------
        # Transform
        # ----------------------------------------------------

        transform = (
            src.transform
        )

        # ----------------------------------------------------
        # Bounds
        # ----------------------------------------------------

        bounds = src.bounds

        # ----------------------------------------------------
        # Center in source CRS
        # ----------------------------------------------------

        center_x = (
            bounds.left
            + bounds.right
        ) / 2.0

        center_y = (
            bounds.bottom
            + bounds.top
        ) / 2.0

        # ----------------------------------------------------
        # Pixel size
        # ----------------------------------------------------

        pixel_size_x = float(
            transform.a
        )

        pixel_size_y = float(
            transform.e
        )

        # ----------------------------------------------------
        # WGS84 conversion
        # ----------------------------------------------------

        latitude = None
        longitude = None

        if crs:

            try:

                transformer = (
                    Transformer.from_crs(
                        crs,
                        "EPSG:4326",
                        always_xy=True,
                    )
                )

                longitude, latitude = (
                    transformer.transform(
                        center_x,
                        center_y,
                    )
                )

            except Exception as error:

                print(
                    "WARNING: Could not "
                    "convert coordinates "
                    "to WGS84."
                )

                print(error)

        return {

            "path": str(
                raster_path
            ),

            "width": int(
                width
            ),

            "height": int(
                height
            ),

            "count": int(
                count
            ),

            "dtype": str(
                dtype
            ),

            "crs": crs,

            "transform": [
                float(value)
                for value in transform
            ],

            "bounds": {

                "left": float(
                    bounds.left
                ),

                "bottom": float(
                    bounds.bottom
                ),

                "right": float(
                    bounds.right
                ),

                "top": float(
                    bounds.top
                ),

            },

            "center": {

                "x": float(
                    center_x
                ),

                "y": float(
                    center_y
                ),

            },

            "center_wgs84": {

                "longitude": (
                    float(longitude)
                    if longitude is not None
                    else None
                ),

                "latitude": (
                    float(latitude)
                    if latitude is not None
                    else None
                ),

            },

            "pixel_size": {

                "x": float(
                    pixel_size_x
                ),

                "y": float(
                    pixel_size_y
                ),

            },

        }


# ============================================================
# CREATE JEWAR RGB PREVIEW
# ============================================================

def create_rgb_preview(
    before: bool,
) -> Path:
    """
    Create a 256x256 RGB preview using:

        B04 = Red
        B03 = Green
        B02 = Blue

    The complete Jewar AOI is represented
    in the preview.
    """

    observation = (
        "before"
        if before
        else "after"
    )

    observation_dir = (
        JEWAR_DATASET_DIR
        / observation
    )

    red_path = find_band(
        observation_dir,
        "B04",
    )

    green_path = find_band(
        observation_dir,
        "B03",
    )

    blue_path = find_band(
        observation_dir,
        "B02",
    )

    if red_path is None:

        raise FileNotFoundError(
            f"B04 was not found in:\n"
            f"{observation_dir}"
        )

    if green_path is None:

        raise FileNotFoundError(
            f"B03 was not found in:\n"
            f"{observation_dir}"
        )

    if blue_path is None:

        raise FileNotFoundError(
            f"B02 was not found in:\n"
            f"{observation_dir}"
        )

    print()
    print("=" * 70)

    print(
        f"CREATING JEWAR "
        f"{observation.upper()} PREVIEW"
    )

    print("=" * 70)

    print(
        f"Red   : {red_path}"
    )

    print(
        f"Green : {green_path}"
    )

    print(
        f"Blue  : {blue_path}"
    )

    with rasterio.open(
        red_path
    ) as red_src:

        red = red_src.read(1)

    with rasterio.open(
        green_path
    ) as green_src:

        green = green_src.read(1)

    with rasterio.open(
        blue_path
    ) as blue_src:

        blue = blue_src.read(1)

    red = robust_normalize(
        red
    )

    green = robust_normalize(
        green
    )

    blue = robust_normalize(
        blue
    )

    rgb = np.stack(
        [
            red,
            green,
            blue,
        ],
        axis=-1,
    )

    rgb = (
        rgb * 255.0
    ).clip(
        0,
        255,
    ).astype(
        np.uint8
    )

    image = Image.fromarray(
        rgb,
        mode="RGB",
    )

    image = image.resize(
        (256, 256),
        Image.Resampling.LANCZOS,
    )

    output_path = (
        JEWAR_BEFORE_IMAGE
        if before
        else JEWAR_AFTER_IMAGE
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image.save(
        output_path,
        format="PNG",
    )

    print(
        f"Saved preview: "
        f"{output_path}"
    )

    print(
        f"Original raster size: "
        f"{rgb.shape[1]} x "
        f"{rgb.shape[0]}"
    )

    print(
        "Search preview size: 256 x 256"
    )

    return output_path


# ============================================================
# LOAD EXISTING METADATA
# ============================================================

def load_metadata(
    directory: Path,
) -> list[dict[str, Any]]:

    metadata_path = (
        directory
        / "metadata.json"
    )

    if not metadata_path.exists():

        raise FileNotFoundError(
            "Metadata file not found:\n"
            f"{metadata_path}"
        )

    with open(
        metadata_path,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(
            file
        )

    if isinstance(
        data,
        list,
    ):

        return data

    if isinstance(
        data,
        dict,
    ):

        if isinstance(
            data.get("metadata"),
            list,
        ):

            return data["metadata"]

        if isinstance(
            data.get("items"),
            list,
        ):

            return data["items"]

    raise RuntimeError(
        f"Unsupported metadata format:\n"
        f"{metadata_path}"
    )


# ============================================================
# LOAD EXISTING FAISS INDEX
# ============================================================

def load_existing_index(
    directory: Path,
) -> tuple[
    faiss.Index,
    list[dict[str, Any]],
]:

    index_path = (
        directory
        / "index.faiss"
    )

    if not index_path.exists():

        raise FileNotFoundError(
            "FAISS index not found:\n"
            f"{index_path}"
        )

    index = faiss.read_index(
        str(index_path)
    )

    metadata = load_metadata(
        directory
    )

    if (
        index.ntotal
        != len(metadata)
    ):

        raise RuntimeError(
            "Existing index and "
            "metadata are not aligned.\n"
            f"Index: {index.ntotal}\n"
            f"Metadata: {len(metadata)}\n"
            f"Directory: {directory}"
        )

    if (
        index.d
        != EMBEDDING_DIMENSION
    ):

        raise RuntimeError(
            "Unexpected FAISS dimension.\n"
            f"Found: {index.d}\n"
            f"Expected: "
            f"{EMBEDDING_DIMENSION}"
        )

    return (
        index,
        metadata,
    )


# ============================================================
# PRAYAGRAJ METADATA
# ============================================================

def make_prayagraj_metadata_unique(
    metadata: list[dict[str, Any]],
    observation: str,
) -> list[dict[str, Any]]:
    """
    Keep original metadata information but make
    IDs unique inside the combined archive.
    """

    output = []

    for item in metadata:

        copied = dict(
            item
        )

        original_id = str(
            copied.get(
                "tile_id",
                copied.get(
                    "filename",
                    "unknown",
                ),
            )
        )

        copied["tile_id"] = (
            f"prayagraj_"
            f"{observation}_"
            f"{original_id}"
        )

        copied["dataset"] = (
            "prayagraj"
        )

        copied["location_label"] = (
            "Prayagraj, "
            "Uttar Pradesh"
        )

        copied["location"] = (
            "Prayagraj, "
            "Uttar Pradesh"
        )

        copied["acquisition_date"] = (
            "2024-12-13"
            if observation == "before"
            else "2025-01-27"
        )

        copied["sensor"] = (
            "RGB satellite imagery"
        )

        copied["platform"] = (
            "Earth-observation imagery"
        )

        copied["archive_observation"] = (
            observation
        )

        output.append(
            copied
        )

    return output


# ============================================================
# JEWAR METADATA
# ============================================================

def make_jewar_metadata(
    image_path: Path,
    observation: str,
    raster_info: dict[str, Any],
) -> dict[str, Any]:

    date = (
        "2022-12-10"
        if observation == "before"
        else "2023-10-06"
    )

    try:

        relative_path = (
            image_path
            .relative_to(
                PROJECT_ROOT
            )
            .as_posix()
        )

    except ValueError:

        relative_path = str(
            image_path
        )

    center = (
        raster_info[
            "center"
        ]
    )

    center_wgs84 = (
        raster_info[
            "center_wgs84"
        ]
    )

    bounds = (
        raster_info[
            "bounds"
        ]
    )

    pixel_size = (
        raster_info[
            "pixel_size"
        ]
    )

    return {

        # ----------------------------------------------------
        # Search identity
        # ----------------------------------------------------

        "tile_id": (
            f"jewar_airport_"
            f"{observation}"
        ),

        "filename": (
            image_path.name
        ),

        "path": relative_path,

        "scene_id": (
            "jewar_airport"
        ),

        "dataset": (
            "jewar_airport_best"
        ),

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        "location_label": (
            "Noida International "
            "Airport area, Jewar, "
            "Uttar Pradesh"
        ),

        "location": (
            "Noida International "
            "Airport area, Jewar, "
            "Uttar Pradesh"
        ),

        # ----------------------------------------------------
        # Temporal information
        # ----------------------------------------------------

        "observation": observation,

        "archive_observation": (
            observation
        ),

        "acquisition_date": date,

        "date": date,

        "before_date": (
            "2022-12-10"
        ),

        "after_date": (
            "2023-10-06"
        ),

        # ----------------------------------------------------
        # Satellite information
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # REAL CRS
        # ----------------------------------------------------

        "source_crs": (
            raster_info["crs"]
        ),

        "coordinate_system": (
            "WGS 84 / UTM Zone 43N"
        ),

        "coordinate_units": (
            "metres"
        ),

        # ----------------------------------------------------
        # REAL PROJECTED CENTER
        #
        # X = Easting
        # Y = Northing
        # ----------------------------------------------------

        "x": round(
            float(
                center["x"]
            ),
            3,
        ),

        "y": round(
            float(
                center["y"]
            ),
            3,
        ),

        # ----------------------------------------------------
        # REAL WGS84 CENTER
        # ----------------------------------------------------

        "latitude": (
            round(
                float(
                    center_wgs84[
                        "latitude"
                    ]
                ),
                7,
            )
            if center_wgs84[
                "latitude"
            ] is not None
            else None
        ),

        "longitude": (
            round(
                float(
                    center_wgs84[
                        "longitude"
                    ]
                ),
                7,
            )
            if center_wgs84[
                "longitude"
            ] is not None
            else None
        ),

        # ----------------------------------------------------
        # REAL PIXEL SIZE
        # ----------------------------------------------------

        "pixel_size_m": (
            abs(
                float(
                    pixel_size["x"]
                )
            )
        ),

        # ----------------------------------------------------
        # REAL RASTER SIZE
        # ----------------------------------------------------

        "raster_width": (
            raster_info["width"]
        ),

        "raster_height": (
            raster_info["height"]
        ),

        "raster_band_count": (
            raster_info["count"]
        ),

        "raster_dtype": (
            raster_info["dtype"]
        ),

        # ----------------------------------------------------
        # REAL RASTER BOUNDS
        # ----------------------------------------------------

        "bounds": {

            "left": round(
                float(
                    bounds["left"]
                ),
                3,
            ),

            "bottom": round(
                float(
                    bounds["bottom"]
                ),
                3,
            ),

            "right": round(
                float(
                    bounds["right"]
                ),
                3,
            ),

            "top": round(
                float(
                    bounds["top"]
                ),
                3,
            ),

        },

        # ----------------------------------------------------
        # REAL TRANSFORM
        # ----------------------------------------------------

        "transform": (
            raster_info["transform"]
        ),

        # ----------------------------------------------------
        # Search representation
        # ----------------------------------------------------

        "tile_size": 256,

        "image_role": (
            "full_aoi_preview"
        ),

        "source_raster": (
            (
                JEWAR_DATASET_DIR
                / observation
                / "B04.tif"
            )
            .relative_to(
                PROJECT_ROOT
            )
            .as_posix()
        ),

        # ----------------------------------------------------
        # Query tags
        # ----------------------------------------------------

        "query_tags": [

            "construction",

            "construction activity",

            "airport construction",

            "infrastructure development",

            "road development",

            "development site",

            "disturbed land",

            "large construction area",

            "urban expansion",

            "infrastructure",

        ],

    }


# ============================================================
# IDENTIFY JEWAR RECORD
# ============================================================

def is_jewar_record(
    record: dict[str, Any],
) -> bool:

    dataset = str(
        record.get(
            "dataset",
            "",
        )
    ).lower()

    scene_id = str(
        record.get(
            "scene_id",
            "",
        )
    ).lower()

    tile_id = str(
        record.get(
            "tile_id",
            "",
        )
    ).lower()

    filename = str(
        record.get(
            "filename",
            "",
        )
    ).lower()

    return (
        dataset
        in {
            "jewar_airport_best",
            "jewar_airport",
        }
        or "jewar_airport"
        in scene_id
        or "jewar_airport"
        in tile_id
        or "jewar_airport"
        in filename
    )


# ============================================================
# UPDATE EXISTING JEWAR METADATA
# ============================================================

def update_existing_jewar_metadata() -> int:
    """
    Update the already-created combined metadata.

    IMPORTANT:

    This function does NOT:

        - rebuild FAISS
        - load RemoteCLIP
        - create new vectors
        - modify Prayagraj indexes

    It only updates the existing Jewar metadata records
    with real geospatial information from the GeoTIFFs.
    """

    print()
    print("=" * 70)
    print(
        "ORION JEWAR GEOSPATIAL METADATA UPDATE"
    )
    print("=" * 70)

    if not COMBINED_INDEX_PATH.exists():

        print()
        print(
            "Combined FAISS index does not exist."
        )

        print(
            "A normal combined-index build "
            "will be performed instead."
        )

        return -1

    if not COMBINED_METADATA_PATH.exists():

        raise FileNotFoundError(
            "Combined metadata not found:\n"
            f"{COMBINED_METADATA_PATH}"
        )

    if not JEWAR_BEFORE_B04.exists():

        raise FileNotFoundError(
            "Jewar BEFORE B04 not found:\n"
            f"{JEWAR_BEFORE_B04}"
        )

    if not JEWAR_AFTER_B04.exists():

        raise FileNotFoundError(
            "Jewar AFTER B04 not found:\n"
            f"{JEWAR_AFTER_B04}"
        )

    # --------------------------------------------------------
    # Load FAISS only for validation.
    # We DO NOT modify it.
    # --------------------------------------------------------

    index = faiss.read_index(
        str(
            COMBINED_INDEX_PATH
        )
    )

    # --------------------------------------------------------
    # Load metadata.
    # --------------------------------------------------------

    with open(
        COMBINED_METADATA_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        metadata = json.load(
            file
        )

    if not isinstance(
        metadata,
        list,
    ):

        raise RuntimeError(
            "Combined metadata must "
            "be a list."
        )

    if (
        index.ntotal
        != len(metadata)
    ):

        raise RuntimeError(
            "FAISS and metadata are "
            "already misaligned.\n"
            f"FAISS vectors: "
            f"{index.ntotal}\n"
            f"Metadata records: "
            f"{len(metadata)}"
        )

    print()
    print(
        f"Existing FAISS vectors: "
        f"{index.ntotal}"
    )

    print(
        f"Existing metadata records: "
        f"{len(metadata)}"
    )

    # --------------------------------------------------------
    # Read BEFORE GeoTIFF.
    # --------------------------------------------------------

    print()
    print(
        "Reading Jewar BEFORE "
        "geospatial information..."
    )

    before_info = (
        read_raster_geospatial(
            JEWAR_BEFORE_B04
        )
    )

    # --------------------------------------------------------
    # Read AFTER GeoTIFF.
    # --------------------------------------------------------

    print(
        "Reading Jewar AFTER "
        "geospatial information..."
    )

    after_info = (
        read_raster_geospatial(
            JEWAR_AFTER_B04
        )
    )

    # --------------------------------------------------------
    # Validate CRS.
    # --------------------------------------------------------

    print()
    print(
        f"BEFORE CRS: "
        f"{before_info['crs']}"
    )

    print(
        f"AFTER CRS: "
        f"{after_info['crs']}"
    )

    if (
        before_info["crs"]
        != "EPSG:32643"
    ):

        raise RuntimeError(
            "Unexpected Jewar BEFORE CRS: "
            f"{before_info['crs']}"
        )

    if (
        after_info["crs"]
        != "EPSG:32643"
    ):

        raise RuntimeError(
            "Unexpected Jewar AFTER CRS: "
            f"{after_info['crs']}"
        )

    # --------------------------------------------------------
    # Show real coordinates.
    # --------------------------------------------------------

    print()

    print(
        "BEFORE CENTER:"
    )

    print(
        f"  X / Easting  : "
        f"{before_info['center']['x']:.3f}"
    )

    print(
        f"  Y / Northing : "
        f"{before_info['center']['y']:.3f}"
    )

    print(
        f"  Latitude     : "
        f"{before_info['center_wgs84']['latitude']:.7f}"
    )

    print(
        f"  Longitude    : "
        f"{before_info['center_wgs84']['longitude']:.7f}"
    )

    print()

    print(
        "AFTER CENTER:"
    )

    print(
        f"  X / Easting  : "
        f"{after_info['center']['x']:.3f}"
    )

    print(
        f"  Y / Northing : "
        f"{after_info['center']['y']:.3f}"
    )

    print(
        f"  Latitude     : "
        f"{after_info['center_wgs84']['latitude']:.7f}"
    )

    print(
        f"  Longitude    : "
        f"{after_info['center_wgs84']['longitude']:.7f}"
    )

    # --------------------------------------------------------
    # Update records.
    # --------------------------------------------------------

    updated_before = 0
    updated_after = 0

    for record in metadata:

        if not is_jewar_record(
            record
        ):
            continue

        tile_id = str(
            record.get(
                "tile_id",
                "",
            )
        ).lower()

        observation = str(
            record.get(
                "observation",
                "",
            )
        ).lower()

        filename = str(
            record.get(
                "filename",
                "",
            )
        ).lower()

        path = str(
            record.get(
                "path",
                "",
            )
        ).lower()

        combined_text = (
            tile_id
            + " "
            + observation
            + " "
            + filename
            + " "
            + path
        )

        if (
            "before"
            in combined_text
        ):

            info = before_info

            observation_value = (
                "before"
            )

            date = (
                "2022-12-10"
            )

            updated_before += 1

        elif (
            "after"
            in combined_text
        ):

            info = after_info

            observation_value = (
                "after"
            )

            date = (
                "2023-10-06"
            )

            updated_after += 1

        else:

            continue

        # ----------------------------------------------------
        # Real geospatial metadata
        # ----------------------------------------------------

        record["dataset"] = (
            "jewar_airport_best"
        )

        record["location_label"] = (
            "Noida International "
            "Airport area, Jewar, "
            "Uttar Pradesh"
        )

        record["location"] = (
            "Noida International "
            "Airport area, Jewar, "
            "Uttar Pradesh"
        )

        record["sensor"] = (
            "Copernicus Sentinel-2"
        )

        record["platform"] = (
            "Sentinel-2"
        )

        record["product"] = (
            "Sentinel-2 Level-2A "
            "Surface Reflectance"
        )

        record["mgrs_tile"] = (
            "43RGM"
        )

        record["observation"] = (
            observation_value
        )

        record["archive_observation"] = (
            observation_value
        )

        record["acquisition_date"] = (
            date
        )

        record["date"] = (
            date
        )

        record["before_date"] = (
            "2022-12-10"
        )

        record["after_date"] = (
            "2023-10-06"
        )

        # ----------------------------------------------------
        # CRS
        # ----------------------------------------------------

        record["source_crs"] = (
            info["crs"]
        )

        record["coordinate_system"] = (
            "WGS 84 / UTM Zone 43N"
        )

        record["coordinate_units"] = (
            "metres"
        )

        # ----------------------------------------------------
        # X / Y
        # ----------------------------------------------------

        record["x"] = round(
            float(
                info["center"]["x"]
            ),
            3,
        )

        record["y"] = round(
            float(
                info["center"]["y"]
            ),
            3,
        )

        # ----------------------------------------------------
        # Latitude / Longitude
        # ----------------------------------------------------

        record["latitude"] = round(
            float(
                info[
                    "center_wgs84"
                ][
                    "latitude"
                ]
            ),
            7,
        )

        record["longitude"] = round(
            float(
                info[
                    "center_wgs84"
                ][
                    "longitude"
                ]
            ),
            7,
        )

        # ----------------------------------------------------
        # Resolution
        # ----------------------------------------------------

        record["pixel_size_m"] = (
            abs(
                float(
                    info[
                        "pixel_size"
                    ]["x"]
                )
            )
        )

        # ----------------------------------------------------
        # Raster information
        # ----------------------------------------------------

        record["raster_width"] = (
            info["width"]
        )

        record["raster_height"] = (
            info["height"]
        )

        record["raster_band_count"] = (
            info["count"]
        )

        record["raster_dtype"] = (
            info["dtype"]
        )

        # ----------------------------------------------------
        # Bounds
        # ----------------------------------------------------

        record["bounds"] = {
            "left": round(
                float(
                    info["bounds"][
                        "left"
                    ]
                ),
                3,
            ),

            "bottom": round(
                float(
                    info["bounds"][
                        "bottom"
                    ]
                ),
                3,
            ),

            "right": round(
                float(
                    info["bounds"][
                        "right"
                    ]
                ),
                3,
            ),

            "top": round(
                float(
                    info["bounds"][
                        "top"
                    ]
                ),
                3,
            ),
        }

        # ----------------------------------------------------
        # Transform
        # ----------------------------------------------------

        record["transform"] = (
            info["transform"]
        )

        # ----------------------------------------------------
        # Search metadata
        # ----------------------------------------------------

        record["image_role"] = (
            "full_aoi_preview"
        )

        record["tile_size"] = (
            256
        )

    # --------------------------------------------------------
    # Validate exactly two records.
    # --------------------------------------------------------

    total_updated = (
        updated_before
        + updated_after
    )

    print()

    print(
        "Updated Jewar records:"
    )

    print(
        f"  BEFORE: {updated_before}"
    )

    print(
        f"  AFTER : {updated_after}"
    )

    print(
        f"  TOTAL : {total_updated}"
    )

    if total_updated != 2:

        raise RuntimeError(
            "Expected exactly 2 Jewar "
            "records, but updated "
            f"{total_updated}."
        )

    # --------------------------------------------------------
    # Save metadata.
    # --------------------------------------------------------

    with open(
        COMBINED_METADATA_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # Verify again.
    # --------------------------------------------------------

    with open(
        COMBINED_METADATA_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        verification = json.load(
            file
        )

    print()
    print("=" * 70)
    print(
        "GEOSPATIAL METADATA VERIFIED"
    )
    print("=" * 70)

    for record in verification:

        if not is_jewar_record(
            record
        ):
            continue

        print()
        print(
            f"Tile        : "
            f"{record.get('tile_id')}"
        )

        print(
            f"Observation : "
            f"{record.get('observation')}"
        )

        print(
            f"CRS         : "
            f"{record.get('source_crs')}"
        )

        print(
            f"X / Easting : "
            f"{record.get('x')}"
        )

        print(
            f"Y / Northing: "
            f"{record.get('y')}"
        )

        print(
            f"Latitude    : "
            f"{record.get('latitude')}"
        )

        print(
            f"Longitude   : "
            f"{record.get('longitude')}"
        )

        print(
            f"Pixel size  : "
            f"{record.get('pixel_size_m')} m"
        )

    # --------------------------------------------------------
    # Confirm FAISS unchanged.
    # --------------------------------------------------------

    index_after = faiss.read_index(
        str(
            COMBINED_INDEX_PATH
        )
    )

    if (
        index_after.ntotal
        != index.ntotal
    ):

        raise RuntimeError(
            "FAISS vector count changed "
            "during metadata update."
        )

    print()
    print(
        f"FAISS vectors remain: "
        f"{index_after.ntotal}"
    )

    print(
        "FAISS index was NOT rebuilt."
    )

    print(
        "Prayagraj indexes were NOT modified."
    )

    print(
        "Only combined metadata was updated."
    )

    print()
    print(
        "GEOSPATIAL UPDATE COMPLETE."
    )

    return 0


# ============================================================
# ADD EMBEDDING
# ============================================================

def add_embedding(
    combined_index: faiss.Index,
    image_path: Path,
    metadata: dict[str, Any],
    model,
    preprocess,
    device,
    torch,
    combined_metadata: list[
        dict[str, Any]
    ],
) -> None:

    print()

    print(
        f"Embedding: "
        f"{image_path.name}"
    )

    embedding = encode_image(
        image_path=image_path,
        model=model,
        preprocess=preprocess,
        device=device,
        torch=torch,
    )

    embedding_matrix = np.asarray(
        [embedding],
        dtype=np.float32,
    )

    combined_index.add(
        embedding_matrix
    )

    combined_metadata.append(
        metadata
    )


# ============================================================
# BUILD NEW COMBINED INDEX
# ============================================================

def build_combined_index() -> int:

    print()
    print("=" * 70)
    print(
        "ORION COMBINED SEMANTIC INDEX BUILDER"
    )
    print("=" * 70)

    print()
    print(
        "Existing Prayagraj indexes "
        "will NOT be modified."
    )

    print()
    print(
        "Combined index will be created at:"
    )

    print(
        COMBINED_INDEX_DIR
    )

    # --------------------------------------------------------
    # Check RemoteCLIP
    # --------------------------------------------------------

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            "RemoteCLIP checkpoint "
            "not found:\n"
            f"{MODEL_PATH}"
        )

    # --------------------------------------------------------
    # Read real Jewar geospatial information
    # BEFORE
    # --------------------------------------------------------

    print()
    print(
        "Reading Jewar BEFORE "
        "geospatial information..."
    )

    before_geo = (
        read_raster_geospatial(
            JEWAR_BEFORE_B04
        )
    )

    # --------------------------------------------------------
    # Read real Jewar geospatial information
    # AFTER
    # --------------------------------------------------------

    print(
        "Reading Jewar AFTER "
        "geospatial information..."
    )

    after_geo = (
        read_raster_geospatial(
            JEWAR_AFTER_B04
        )
    )

    # --------------------------------------------------------
    # Create previews
    # --------------------------------------------------------

    jewar_before = (
        create_rgb_preview(
            before=True
        )
    )

    jewar_after = (
        create_rgb_preview(
            before=False
        )
    )

    # --------------------------------------------------------
    # Load existing Prayagraj indexes
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "LOADING EXISTING PRAYAGRAJ INDEXES"
    )
    print("=" * 70)

    before_index, before_metadata = (
        load_existing_index(
            PRAYAGRAJ_BEFORE_INDEX
        )
    )

    after_index, after_metadata = (
        load_existing_index(
            PRAYAGRAJ_AFTER_INDEX
        )
    )

    print(
        f"Prayagraj BEFORE vectors: "
        f"{before_index.ntotal}"
    )

    print(
        f"Prayagraj AFTER vectors: "
        f"{after_index.ntotal}"
    )

    # --------------------------------------------------------
    # Start combined index
    # --------------------------------------------------------

    combined_index = (
        faiss.IndexFlatIP(
            EMBEDDING_DIMENSION
        )
    )

    combined_metadata: list[
        dict[str, Any]
    ] = []

    # --------------------------------------------------------
    # Add Prayagraj BEFORE
    # --------------------------------------------------------

    print()
    print(
        "Adding Prayagraj BEFORE..."
    )

    before_vectors = (
        before_index.reconstruct_n(
            0,
            before_index.ntotal,
        )
    )

    combined_index.add(
        np.asarray(
            before_vectors,
            dtype=np.float32,
        )
    )

    combined_metadata.extend(
        make_prayagraj_metadata_unique(
            before_metadata,
            "before",
        )
    )

    # --------------------------------------------------------
    # Add Prayagraj AFTER
    # --------------------------------------------------------

    print(
        "Adding Prayagraj AFTER..."
    )

    after_vectors = (
        after_index.reconstruct_n(
            0,
            after_index.ntotal,
        )
    )

    combined_index.add(
        np.asarray(
            after_vectors,
            dtype=np.float32,
        )
    )

    combined_metadata.extend(
        make_prayagraj_metadata_unique(
            after_metadata,
            "after",
        )
    )

    print()

    print(
        f"Vectors after Prayagraj: "
        f"{combined_index.ntotal}"
    )

    # --------------------------------------------------------
    # Load RemoteCLIP
    # --------------------------------------------------------

    print()
    print(
        "Loading RemoteCLIP..."
    )

    (
        model,
        preprocess,
        device,
        torch,
    ) = load_remoteclip(
        MODEL_PATH
    )

    # --------------------------------------------------------
    # Add Jewar BEFORE
    # --------------------------------------------------------

    jewar_before_metadata = (
        make_jewar_metadata(
            jewar_before,
            "before",
            before_geo,
        )
    )

    add_embedding(
        combined_index,
        jewar_before,
        jewar_before_metadata,
        model,
        preprocess,
        device,
        torch,
        combined_metadata,
    )

    # --------------------------------------------------------
    # Add Jewar AFTER
    # --------------------------------------------------------

    jewar_after_metadata = (
        make_jewar_metadata(
            jewar_after,
            "after",
            after_geo,
        )
    )

    add_embedding(
        combined_index,
        jewar_after,
        jewar_after_metadata,
        model,
        preprocess,
        device,
        torch,
        combined_metadata,
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if (
        combined_index.ntotal
        != len(combined_metadata)
    ):

        raise RuntimeError(
            "FINAL INDEX/METADATA "
            "ALIGNMENT FAILED.\n"
            f"Vectors: "
            f"{combined_index.ntotal}\n"
            f"Metadata: "
            f"{len(combined_metadata)}"
        )

    # --------------------------------------------------------
    # Save directory
    # --------------------------------------------------------

    COMBINED_INDEX_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Save FAISS
    # --------------------------------------------------------

    faiss.write_index(
        combined_index,
        str(
            COMBINED_INDEX_PATH
        ),
    )

    # --------------------------------------------------------
    # Save metadata
    # --------------------------------------------------------

    with open(
        COMBINED_METADATA_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            combined_metadata,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # Save manifest
    # --------------------------------------------------------

    manifest = {

        "name":
            "ORION Combined Semantic Archive",

        "version":
            "1.1",

        "index":
            str(
                COMBINED_INDEX_PATH
                .relative_to(
                    PROJECT_ROOT
                )
            ),

        "metadata":
            str(
                COMBINED_METADATA_PATH
                .relative_to(
                    PROJECT_ROOT
                )
            ),

        "embedding_model":
            "RemoteCLIP ViT-B/32",

        "embedding_dimension":
            EMBEDDING_DIMENSION,

        "datasets": {

            "prayagraj": {

                "before_vectors":
                    before_index.ntotal,

                "after_vectors":
                    after_index.ntotal,

            },

            "jewar_airport": {

                "before_vectors":
                    1,

                "after_vectors":
                    1,

                "before_crs":
                    before_geo["crs"],

                "after_crs":
                    after_geo["crs"],

                "before_pixel_size_m":
                    abs(
                        before_geo[
                            "pixel_size"
                        ]["x"]
                    ),

                "after_pixel_size_m":
                    abs(
                        after_geo[
                            "pixel_size"
                        ]["x"]
                    ),

            },

        },

        "total_vectors":
            combined_index.ntotal,

    }

    with open(
        COMBINED_MANIFEST_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            manifest,
            file,
            indent=2,
        )

    # --------------------------------------------------------
    # Final output
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "COMBINED INDEX CREATED SUCCESSFULLY"
    )
    print("=" * 70)

    print()
    print(
        f"Total vectors: "
        f"{combined_index.ntotal}"
    )

    print(
        "Expected: 244"
    )

    print()
    print(
        f"Prayagraj vectors: "
        f"{before_index.ntotal + after_index.ntotal}"
    )

    print(
        "Jewar vectors: 2"
    )

    print()
    print(
        "Jewar BEFORE geospatial:"
    )

    print(
        f"  CRS: "
        f"{before_geo['crs']}"
    )

    print(
        f"  X: "
        f"{before_geo['center']['x']:.3f}"
    )

    print(
        f"  Y: "
        f"{before_geo['center']['y']:.3f}"
    )

    print(
        f"  Latitude: "
        f"{before_geo['center_wgs84']['latitude']:.7f}"
    )

    print(
        f"  Longitude: "
        f"{before_geo['center_wgs84']['longitude']:.7f}"
    )

    print()
    print(
        "Jewar AFTER geospatial:"
    )

    print(
        f"  CRS: "
        f"{after_geo['crs']}"
    )

    print(
        f"  X: "
        f"{after_geo['center']['x']:.3f}"
    )

    print(
        f"  Y: "
        f"{after_geo['center']['y']:.3f}"
    )

    print(
        f"  Latitude: "
        f"{after_geo['center_wgs84']['latitude']:.7f}"
    )

    print(
        f"  Longitude: "
        f"{after_geo['center_wgs84']['longitude']:.7f}"
    )

    print()
    print(
        f"Index:\n"
        f"{COMBINED_INDEX_PATH}"
    )

    print()
    print(
        f"Metadata:\n"
        f"{COMBINED_METADATA_PATH}"
    )

    print()
    print(
        "Existing Prayagraj indexes "
        "were left untouched."
    )

    return 0


# ============================================================
# COMMAND LINE
# ============================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "ORION combined semantic "
            "index builder and Jewar "
            "geospatial metadata updater."
        )
    )

    parser.add_argument(
        "--rebuild",
        action="store_true",
        help=(
            "Force rebuilding the "
            "combined FAISS index."
        ),
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # DEFAULT BEHAVIOR
    #
    # If combined index already exists:
    #
    #     update metadata only
    #
    # This prevents unnecessary FAISS rebuilding.
    # --------------------------------------------------------

    if (
        not args.rebuild
        and COMBINED_INDEX_PATH.exists()
        and COMBINED_METADATA_PATH.exists()
    ):

        result = (
            update_existing_jewar_metadata()
        )

        if result == 0:
            return 0

    # --------------------------------------------------------
    # Build when index doesn't exist,
    # or when --rebuild is explicitly used.
    # --------------------------------------------------------

    return build_combined_index()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )