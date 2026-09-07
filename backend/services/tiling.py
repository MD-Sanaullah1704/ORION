from pathlib import Path

import rasterio
from PIL import Image


def generate_tiles(
    raster_path,
    output_dir,
    tile_size=256,
    stride=256,
):
    """
    Split a raster image into RGB PNG tiles.

    Parameters
    ----------
    raster_path : str or Path
        Input GeoTIFF.

    output_dir : str or Path
        Directory where tiles will be written.

    tile_size : int
        Width/height of each tile.

    stride : int
        Distance between tile starts.

    Returns
    -------
    list[dict]
        Metadata for every generated tile.
    """

    raster_path = Path(raster_path)
    output_dir = Path(output_dir)

    if not raster_path.exists():
        raise FileNotFoundError(
            f"Raster not found: {raster_path}"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    tiles = []

    with rasterio.open(raster_path) as src:

        if src.count < 3:
            raise ValueError(
                "Raster must contain at least 3 bands."
            )

        width = src.width
        height = src.height

        tile_index = 0

        for y in range(0, height, stride):

            for x in range(0, width, stride):

                window_width = min(
                    tile_size,
                    width - x
                )

                window_height = min(
                    tile_size,
                    height - y
                )

                # Ignore incomplete edge tiles for now.
                if (
                    window_width != tile_size
                    or window_height != tile_size
                ):
                    continue

                window = rasterio.windows.Window(
                    x,
                    y,
                    tile_size,
                    tile_size
                )

                data = src.read(
                    [1, 2, 3],
                    window=window
                )

                # Convert from:
                # [bands, height, width]
                #
                # to:
                # [height, width, bands]
                data = data.transpose(1, 2, 0)

                # Normalize uint16 satellite values
                # into displayable 8-bit RGB.
                image = _normalize_rgb(data)

                tile_filename = (
                    f"tile_{tile_index:05d}"
                    f"_x{x}_y{y}.png"
                )

                tile_path = (
                    output_dir
                    / tile_filename
                )

                Image.fromarray(image).save(
                    tile_path
                )

                tiles.append(
                    {
                        "tile_id": tile_path.stem,
                        "filename": tile_filename,
                        "path": str(tile_path),
                        "x": x,
                        "y": y,
                        "width": tile_size,
                        "height": tile_size,
                    }
                )

                tile_index += 1

    return tiles


def _normalize_rgb(data):
    """
    Convert a 3-band uint16/float raster tile
    into an 8-bit RGB image.

    Percentile stretching is performed independently
    for each channel.
    """

    import numpy as np

    data = data.astype(np.float32)

    output = np.zeros_like(
        data,
        dtype=np.uint8
    )

    for band in range(3):

        channel = data[:, :, band]

        low = np.percentile(
            channel,
            2
        )

        high = np.percentile(
            channel,
            98
        )

        if high <= low:
            normalized = np.zeros_like(
                channel,
                dtype=np.float32
            )
        else:
            normalized = (
                (channel - low)
                / (high - low)
            )

        normalized = np.clip(
            normalized,
            0,
            1
        )

        output[:, :, band] = (
            normalized * 255
        ).astype(np.uint8)

    return output