from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds, Window


SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"

CENTER_LAT = 28.64691
CENTER_LON = 77.20158
AREA_KM2 = 1.73

# We search a broad period, then prefer pairs separated by at least ~6 months.
START_DATE = "2024-01-01"
END_DATE = "2025-12-31"

MAX_CLOUD = 20.0
MAX_RESULTS = 100

# These are enough for a lightweight change screen.
SCORE_BANDS = {
    "B04": ["red"],
    "B08": ["nir"],
    "B11": ["swir16"],
    "SCL": ["scl"],
}


@dataclass
class Candidate:
    item: dict[str, Any]

    @property
    def item_id(self) -> str:
        return str(self.item.get("id", ""))

    @property
    def properties(self) -> dict[str, Any]:
        return self.item.get("properties", {})

    @property
    def datetime(self) -> str:
        return str(self.properties.get("datetime", ""))

    @property
    def date(self) -> datetime:
        return datetime.fromisoformat(self.datetime.replace("Z", "+00:00"))

    @property
    def cloud_cover(self) -> float:
        try:
            return float(self.properties.get("eo:cloud_cover", 999))
        except (TypeError, ValueError):
            return 999.0

    @property
    def platform(self) -> str:
        return str(self.properties.get("platform", ""))


def make_square_bbox() -> list[float]:
    side_km = math.sqrt(AREA_KM2)
    half_km = side_km / 2
    km_lat = 111.32
    km_lon = 111.32 * math.cos(math.radians(CENTER_LAT))

    dlat = half_km / km_lat
    dlon = half_km / km_lon

    return [
        CENTER_LON - dlon,
        CENTER_LAT - dlat,
        CENTER_LON + dlon,
        CENTER_LAT + dlat,
    ]


def bbox_polygon(bbox: list[float]) -> dict[str, Any]:
    min_lon, min_lat, max_lon, max_lat = bbox
    return {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]],
    }


def stac_post(payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/geo+json, application/json",
            "User-Agent": "ORION-SIH26227/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Earth Search returned HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Could not reach Earth Search. Check internet access."
        ) from exc


def search_candidates(geometry: dict[str, Any]) -> list[Candidate]:
    payload = {
        "collections": [COLLECTION],
        "intersects": geometry,
        "datetime": f"{START_DATE}T00:00:00Z/{END_DATE}T23:59:59Z",
        "limit": MAX_RESULTS,
        "query": {
            "eo:cloud_cover": {"lte": MAX_CLOUD},
        },
    }

    result = stac_post(payload)
    features = result.get("features", [])

    candidates = [Candidate(item=f) for f in features]

    # Keep one scene per acquisition date, preferring lowest cloud.
    by_date: dict[str, Candidate] = {}
    for candidate in candidates:
        day = candidate.datetime[:10]
        current = by_date.get(day)
        if current is None or candidate.cloud_cover < current.cloud_cover:
            by_date[day] = candidate

    return sorted(by_date.values(), key=lambda c: c.date)


def asset_href(candidate: Candidate, names: list[str]) -> str:
    assets = candidate.item.get("assets", {})

    for name in names:
        if name in assets and assets[name].get("href"):
            return str(assets[name]["href"])

    for key, asset in assets.items():
        text = (
            str(key).lower()
            + " "
            + str(asset.get("title", "")).lower()
            + " "
            + " ".join(str(x).lower() for x in asset.get("roles", []))
        )
        if any(name.lower() in text for name in names):
            href = asset.get("href")
            if href:
                return str(href)

    raise KeyError(f"Could not find asset {names}")


def read_aoi_window(
    href: str,
    bbox_wgs84: list[float],
    target_size: int = 160,
) -> tuple[np.ndarray, Any]:
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
    ):
        with rasterio.open(href) as src:
            left, bottom, right, top = transform_bounds(
                "EPSG:4326",
                src.crs,
                *bbox_wgs84,
                densify_pts=21,
            )

            window = from_bounds(
                left,
                bottom,
                right,
                top,
                transform=src.transform,
            ).round_offsets().round_lengths()

            window = window.intersection(
                Window(0, 0, src.width, src.height)
            )

            data = src.read(
                1,
                window=window,
                out_shape=(target_size, target_size),
                resampling=Resampling.bilinear,
            ).astype(np.float32)

            return data, src.crs


def read_scl(href: str, bbox_wgs84: list[float], target_size: int = 160) -> np.ndarray:
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
    ):
        with rasterio.open(href) as src:
            left, bottom, right, top = transform_bounds(
                "EPSG:4326",
                src.crs,
                *bbox_wgs84,
                densify_pts=21,
            )

            window = from_bounds(
                left,
                bottom,
                right,
                top,
                transform=src.transform,
            ).round_offsets().round_lengths()

            window = window.intersection(
                Window(0, 0, src.width, src.height)
            )

            return src.read(
                1,
                window=window,
                out_shape=(target_size, target_size),
                resampling=Resampling.nearest,
            )


def robust_normalize(image: np.ndarray, valid: np.ndarray) -> np.ndarray:
    values = image[valid]
    if values.size < 50:
        return np.zeros_like(image, dtype=np.float32)

    low, high = np.percentile(values, [2, 98])
    if high <= low:
        return np.zeros_like(image, dtype=np.float32)

    return np.clip((image - low) / (high - low), 0, 1)


def scene_signature(candidate: Candidate, bbox: list[float]) -> dict[str, Any]:
    print(
        f"  Screening {candidate.datetime[:10]} | "
        f"{candidate.platform} | cloud={candidate.cloud_cover:.2f}%..."
    )

    red = read_aoi_window(
        asset_href(candidate, SCORE_BANDS["B04"]),
        bbox,
    )[0]

    nir = read_aoi_window(
        asset_href(candidate, SCORE_BANDS["B08"]),
        bbox,
    )[0]

    swir = read_aoi_window(
        asset_href(candidate, SCORE_BANDS["B11"]),
        bbox,
    )[0]

    scl = read_scl(
        asset_href(candidate, SCORE_BANDS["SCL"]),
        bbox,
    )

    # SCL: reject cloud/shadow/snow/no-data classes.
    # Keep vegetation, bare soil, built-up and water for screening.
    valid = np.isfinite(red) & np.isfinite(nir) & np.isfinite(swir)
    invalid_scl = np.isin(scl, [0, 1, 3, 8, 9, 10, 11])
    valid &= ~invalid_scl

    red_n = robust_normalize(red, valid)
    nir_n = robust_normalize(nir, valid)
    swir_n = robust_normalize(swir, valid)

    ndvi = (nir - red) / (nir + red + 1e-6)
    ndbi = (swir - nir) / (swir + nir + 1e-6)

    return {
        "red": red_n,
        "nir": nir_n,
        "swir": swir_n,
        "ndvi": ndvi,
        "ndbi": ndbi,
        "valid": valid,
        "valid_fraction": float(valid.mean()),
    }


def pair_score(a: dict[str, Any], b: dict[str, Any]) -> dict[str, float]:
    """Score a temporal pair for spatially concentrated change.

    This deliberately avoids using only a scene-wide median difference because
    broad illumination, haze, or seasonal effects can produce a large global
    difference without a useful localized change event.
    """
    valid = a["valid"] & b["valid"]

    if valid.sum() < 100:
        return {
            "score": 0.0,
            "spectral_change": 0.0,
            "spectral_p90": 0.0,
            "spectral_p98": 0.0,
            "localized_change": 0.0,
            "change_fraction_top5": 0.0,
            "ndvi_change": 0.0,
            "ndbi_change": 0.0,
            "valid_fraction": float(valid.mean()),
        }

    spectral = np.stack([
        np.abs(a["red"] - b["red"]),
        np.abs(a["nir"] - b["nir"]),
        np.abs(a["swir"] - b["swir"]),
    ], axis=0)

    # Per-pixel multi-band spectral difference.
    spectral_map = np.mean(spectral, axis=0)
    values = spectral_map[valid]

    spectral_change = float(np.median(values))
    spectral_p90 = float(np.percentile(values, 90))
    spectral_p98 = float(np.percentile(values, 98))

    # Localized change should occupy a relatively small part of the scene,
    # while still being substantially stronger than the scene background.
    high_threshold = float(np.percentile(values, 95))
    high_pixels = valid & (spectral_map >= high_threshold)
    change_fraction_top5 = float(high_pixels.sum() / max(valid.sum(), 1))

    # Ratio between the strongest local changes and the scene background.
    # Broad illumination changes tend to make this ratio closer to 1.
    localized_change = float(
        spectral_p98 / (spectral_change + 1e-6)
    )

    ndvi_delta = np.abs(a["ndvi"] - b["ndvi"])
    ndbi_delta = np.abs(a["ndbi"] - b["ndbi"])

    ndvi_change = float(np.median(ndvi_delta[valid]))
    ndbi_change = float(np.median(ndbi_delta[valid]))

    ndvi_p90 = float(np.percentile(ndvi_delta[valid], 90))
    ndbi_p90 = float(np.percentile(ndbi_delta[valid], 90))

    # The final score favours strong tails/localized regions over broad scene
    # differences. It is still only a screening score, never a probability.
    tail_strength = min(spectral_p98, 1.0)
    ndvi_tail = min(ndvi_p90, 1.0)
    ndbi_tail = min(ndbi_p90, 1.0)
    concentration_bonus = min(max(localized_change - 1.0, 0.0) / 3.0, 1.0)

    score = (
        0.35 * tail_strength
        + 0.20 * min(spectral_p90, 1.0)
        + 0.15 * ndvi_tail
        + 0.15 * ndbi_tail
        + 0.15 * concentration_bonus
    )

    return {
        "score": float(score),
        "spectral_change": spectral_change,
        "spectral_p90": spectral_p90,
        "spectral_p98": spectral_p98,
        "localized_change": localized_change,
        "change_fraction_top5": change_fraction_top5,
        "ndvi_change": ndvi_change,
        "ndbi_change": ndbi_change,
        "valid_fraction": float(valid.mean()),
    }


def temporal_penalty_days(days: int) -> float:
    # We want meaningful multi-temporal comparisons, but avoid very long
    # intervals where unrelated changes accumulate.
    if days < 180:
        return 0.45
    if days > 550:
        return 0.80
    return 1.00


def seasonal_similarity(first: Candidate, second: Candidate) -> float:
    """Return a soft preference for same-season comparisons."""
    day1 = first.date.timetuple().tm_yday
    day2 = second.date.timetuple().tm_yday
    distance = abs(day1 - day2)
    distance = min(distance, 366 - distance)

    if distance <= 30:
        return 1.00
    if distance <= 60:
        return 0.95
    if distance <= 90:
        return 0.85
    if distance <= 150:
        return 0.70
    return 0.55


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find Delhi Sentinel-2 temporal pairs with localized spectral change."
    )
    parser.add_argument(
        "--output",
        default="data/datasets/delhi_sentinel2/change_pair_candidates.json",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top candidate pairs to save.",
    )
    args = parser.parse_args()

    bbox = make_square_bbox()
    geometry = bbox_polygon(bbox)

    print("=" * 100)
    print("ORION — Delhi Sentinel-2 Change-Pair Screening")
    print("=" * 100)
    print(f"AOI bbox: {bbox}")
    print(f"Period: {START_DATE} -> {END_DATE}")
    print(f"Maximum cloud: {MAX_CLOUD}%")
    print("\nSearching STAC catalogue...")

    candidates = search_candidates(geometry)

    print(f"\nUnique acquisition dates found: {len(candidates)}")

    if len(candidates) < 2:
        raise RuntimeError("Not enough candidate scenes were found.")

    signatures: dict[str, dict[str, Any]] = {}

    for candidate in candidates:
        try:
            signatures[candidate.item_id] = scene_signature(candidate, bbox)
        except Exception as exc:
            print(f"  FAILED {candidate.item_id}: {exc}")

    scored: list[dict[str, Any]] = []

    for i, first in enumerate(candidates):
        if first.item_id not in signatures:
            continue

        for second in candidates[i + 1:]:
            if second.item_id not in signatures:
                continue

            days = abs((second.date - first.date).days)

            if days < 180:
                continue

            score_details = pair_score(
                signatures[first.item_id],
                signatures[second.item_id],
            )

            season_factor = seasonal_similarity(first, second)
            time_factor = temporal_penalty_days(days)
            score = score_details["score"] * time_factor * season_factor

            scored.append({
                "score": score,
                "days_between": days,
                "season_similarity": season_factor,
                "temporal_factor": time_factor,
                "before": {
                    "id": first.item_id,
                    "date": first.datetime,
                    "platform": first.platform,
                    "cloud_cover": first.cloud_cover,
                },
                "after": {
                    "id": second.item_id,
                    "date": second.datetime,
                    "platform": second.platform,
                    "cloud_cover": second.cloud_cover,
                },
                "metrics": score_details,
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:args.top]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "purpose": (
            "Screen Delhi Sentinel-2 L2A temporal pairs for strong spectral "
            "differences before full ORION ingestion."
        ),
        "warning": (
            "The score is a screening metric, not a ground-truth change "
            "confidence or probability. Strong scores can still be caused by "
            "seasonality, illumination, residual atmospheric effects, "
            "registration differences, or genuine land-cover change."
        ),
        "aoi_bbox_epsg4326": bbox,
        "search_period": [START_DATE, END_DATE],
        "max_cloud_cover": MAX_CLOUD,
        "candidate_scene_count": len(candidates),
        "screened_scene_count": len(signatures),
        "top_pairs": top,
    }

    output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 100)
    print("TOP CHANGE CANDIDATES")
    print("=" * 100)

    for rank, pair in enumerate(top, start=1):
        print(
            f"{rank:02d}. score={pair['score']:.4f} | "
            f"{pair['before']['date'][:10]} -> {pair['after']['date'][:10]} | "
            f"{pair['days_between']} days | "
            f"season={pair['season_similarity']:.2f} | "
            f"p98={pair['metrics']['spectral_p98']:.4f} | "
            f"local={pair['metrics']['localized_change']:.2f} | "
            f"NDVI={pair['metrics']['ndvi_change']:.4f} | "
            f"NDBI={pair['metrics']['ndbi_change']:.4f}"
        )

    print(f"\nReport: {output}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
