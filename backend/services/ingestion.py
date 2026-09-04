import rasterio
from pathlib import Path


def inspect_raster(file_path):
    """
    Inspect a GeoTIFF/COG raster and return its basic
    geospatial and image metadata.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Raster file not found: {file_path}"
        )

    with rasterio.open(file_path) as src:

        bounds = src.bounds

        return {
            "filename": file_path.name,
            "width": src.width,
            "height": src.height,
            "bands": src.count,
            "crs": str(src.crs) if src.crs else None,
            "resolution": {
                "x": src.res[0],
                "y": src.res[1]
            },
            "bounds": {
                "left": bounds.left,
                "bottom": bounds.bottom,
                "right": bounds.right,
                "top": bounds.top
            },
            "dtype": str(src.dtypes[0]),
            "driver": src.driver
        }