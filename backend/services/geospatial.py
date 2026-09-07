from pathlib import Path

import rasterio
from pyproj import Transformer


def _has_valid_georeferencing(dataset) -> bool:
    """
    Return True only when the raster has a usable CRS and
    a non-identity affine transform.
    """
    if dataset.crs is None:
        return False

    transform = dataset.transform

    if transform == rasterio.Affine.identity():
        return False

    # Guard against transforms that effectively have no spatial scale.
    if transform.a == 0 or transform.e == 0:
        return False

    return True


def get_raster_geospatial_info(raster_path: str | Path) -> dict:
    """
    Read geospatial metadata from a GeoTIFF/COG.

    This function never invents coordinates. If CRS or transform is
    unavailable, it returns status='unavailable'.
    """
    path = Path(raster_path)

    if not path.exists():
        raise FileNotFoundError(f"Raster not found: {path}")

    with rasterio.open(path) as dataset:
        transform = dataset.transform
        crs = dataset.crs

        result = {
            "status": "available" if _has_valid_georeferencing(dataset) else "unavailable",
            "path": str(path),
            "width": dataset.width,
            "height": dataset.height,
            "count": dataset.count,
            "dtype": dataset.dtypes[0] if dataset.dtypes else None,
            "crs": crs.to_string() if crs else None,
            "transform": list(transform),
            "bounds": None,
            "center": None,
            "pixel_size": {
                "x": transform.a,
                "y": transform.e,
            },
        }

        if not _has_valid_georeferencing(dataset):
            result["reason"] = (
                "Source raster does not contain a valid CRS and/or "
                "non-identity geospatial transform."
            )
            return result

        bounds = dataset.bounds

        result["bounds"] = {
            "left": bounds.left,
            "bottom": bounds.bottom,
            "right": bounds.right,
            "top": bounds.top,
        }

        center_x = (bounds.left + bounds.right) / 2.0
        center_y = (bounds.bottom + bounds.top) / 2.0

        result["center"] = {
            "x": center_x,
            "y": center_y,
        }

        return result


def pixel_to_map(
    raster_path: str | Path,
    pixel_x: float,
    pixel_y: float,
) -> dict:
    """
    Convert raster pixel coordinates (column=x, row=y) into
    the raster's native map CRS.

    Pixel coordinates refer to the pixel center.
    """
    path = Path(raster_path)

    if not path.exists():
        raise FileNotFoundError(f"Raster not found: {path}")

    with rasterio.open(path) as dataset:
        if not _has_valid_georeferencing(dataset):
            return {
                "status": "unavailable",
                "reason": (
                    "Cannot convert pixel coordinates because the "
                    "source raster has no valid georeferencing."
                ),
                "pixel": {
                    "x": pixel_x,
                    "y": pixel_y,
                },
            }

        map_x, map_y = rasterio.transform.xy(
            dataset.transform,
            pixel_y,
            pixel_x,
            offset="center",
        )

        return {
            "status": "available",
            "pixel": {
                "x": pixel_x,
                "y": pixel_y,
            },
            "map": {
                "x": map_x,
                "y": map_y,
                "crs": dataset.crs.to_string(),
            },
        }


def pixel_to_wgs84(
    raster_path: str | Path,
    pixel_x: float,
    pixel_y: float,
) -> dict:
    """
    Convert raster pixel coordinates to WGS84 longitude/latitude.

    No conversion is attempted when the raster is not georeferenced.
    """
    map_result = pixel_to_map(
        raster_path,
        pixel_x,
        pixel_y,
    )

    if map_result["status"] != "available":
        return map_result

    source_crs = map_result["map"]["crs"]

    transformer = Transformer.from_crs(
        source_crs,
        "EPSG:4326",
        always_xy=True,
    )

    longitude, latitude = transformer.transform(
        map_result["map"]["x"],
        map_result["map"]["y"],
    )

    return {
        "status": "available",
        "pixel": map_result["pixel"],
        "map": map_result["map"],
        "wgs84": {
            "longitude": longitude,
            "latitude": latitude,
            "crs": "EPSG:4326",
        },
    }


def get_tile_geospatial_info(
    raster_path: str | Path,
    tile_x: int,
    tile_y: int,
    tile_width: int = 256,
    tile_height: int = 256,
) -> dict:
    """
    Calculate geographic information for a tile inside a raster.

    tile_x and tile_y are pixel offsets in the source raster.
    The returned bounds are based on the outer edges of the tile.
    """
    path = Path(raster_path)

    if not path.exists():
        raise FileNotFoundError(f"Raster not found: {path}")

    with rasterio.open(path) as dataset:
        if not _has_valid_georeferencing(dataset):
            return {
                "status": "unavailable",
                "reason": (
                    "Cannot calculate tile geography because the "
                    "source raster has no valid georeferencing."
                ),
                "tile": {
                    "x": tile_x,
                    "y": tile_y,
                    "width": tile_width,
                    "height": tile_height,
                },
            }

        if tile_x < 0 or tile_y < 0:
            raise ValueError("Tile x/y must be non-negative.")

        if tile_x >= dataset.width or tile_y >= dataset.height:
            raise ValueError("Tile origin is outside the raster.")

        actual_width = min(
            tile_width,
            dataset.width - tile_x,
        )
        actual_height = min(
            tile_height,
            dataset.height - tile_y,
        )

        left, top = rasterio.transform.xy(
            dataset.transform,
            tile_y,
            tile_x,
            offset="ul",
        )

        right, bottom = rasterio.transform.xy(
            dataset.transform,
            tile_y + actual_height,
            tile_x + actual_width,
            offset="ul",
        )

        transformer = Transformer.from_crs(
            dataset.crs,
            "EPSG:4326",
            always_xy=True,
        )

        west, north = transformer.transform(left, top)
        east, south = transformer.transform(right, bottom)

        center_x = (west + east) / 2.0
        center_y = (south + north) / 2.0

        return {
            "status": "available",
            "tile": {
                "x": tile_x,
                "y": tile_y,
                "width": actual_width,
                "height": actual_height,
            },
            "source_crs": dataset.crs.to_string(),
            "bounds_wgs84": {
                "west": west,
                "south": south,
                "east": east,
                "north": north,
            },
            "center_wgs84": {
                "longitude": center_x,
                "latitude": center_y,
            },
        }


def get_event_geospatial_info(
    raster_path: str | Path,
    tile_x: int | None,
    tile_y: int | None,
    tile_width: int = 256,
    tile_height: int = 256,
) -> dict:
    """
    Convenience wrapper for ORION change events.

    If tile coordinates are missing, only raster-level metadata is returned.
    """
    raster_info = get_raster_geospatial_info(raster_path)

    result = {
        "raster": raster_info,
        "tile": None,
    }

    if (
        tile_x is not None
        and tile_y is not None
        and raster_info["status"] == "available"
    ):
        result["tile"] = get_tile_geospatial_info(
            raster_path,
            tile_x,
            tile_y,
            tile_width,
            tile_height,
        )

    return result


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Inspect ORION raster geospatial metadata."
    )

    parser.add_argument(
        "raster",
        help="Path to GeoTIFF/COG",
    )

    parser.add_argument(
        "--pixel-x",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--pixel-y",
        type=float,
        default=None,
    )

    args = parser.parse_args()

    info = get_raster_geospatial_info(args.raster)

    if args.pixel_x is not None and args.pixel_y is not None:
        info["pixel_query"] = pixel_to_wgs84(
            args.raster,
            args.pixel_x,
            args.pixel_y,
        )

    print(
        json.dumps(
            info,
            indent=2,
            default=str,
        )
    )
