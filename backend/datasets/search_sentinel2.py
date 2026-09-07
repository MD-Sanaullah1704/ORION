from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds, Window


EARTH_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"

DEFAULT_CENTER_LAT = 28.64691
DEFAULT_CENTER_LON = 77.20158
DEFAULT_AREA_KM2 = 1.73

DEFAULT_BEFORE_START = "2024-11-20"
DEFAULT_BEFORE_END = "2024-12-15"
DEFAULT_AFTER_START = "2025-12-15"
DEFAULT_AFTER_END = "2025-12-31"

REQUIRED_ASSETS = {
    "B02": ["blue"],
    "B03": ["green"],
    "B04": ["red"],
    "B08": ["nir"],
    "B05": ["rededge1"],
    "B06": ["rededge2"],
    "B07": ["rededge3"],
    "B8A": ["nir08"],
    "B11": ["swir16"],
    "B12": ["swir22"],
    "SCL": ["scl"],
    "AOT": ["aot"],
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
    def cloud_cover(self) -> float:
        value = self.properties.get("eo:cloud_cover")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 999.0

    @property
    def platform(self) -> str:
        return str(self.properties.get("platform", ""))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Search public Sentinel-2 L2A imagery through Earth Search STAC, "
            "select a before/after pair, crop only the ORION AOI from COG assets, "
            "and write provenance metadata."
        )
    )
    parser.add_argument(
        "--output-root",
        default="data/datasets/delhi_sentinel2",
        help="Output directory relative to the ORION project root.",
    )
    parser.add_argument(
        "--aoi-geojson",
        default=None,
        help=(
            "Optional GeoJSON Polygon/Feature file in EPSG:4326. "
            "If omitted, a square AOI of --area-km2 is generated around the centre."
        ),
    )
    parser.add_argument("--center-lat", type=float, default=DEFAULT_CENTER_LAT)
    parser.add_argument("--center-lon", type=float, default=DEFAULT_CENTER_LON)
    parser.add_argument("--area-km2", type=float, default=DEFAULT_AREA_KM2)
    parser.add_argument("--before-start", default=DEFAULT_BEFORE_START)
    parser.add_argument("--before-end", default=DEFAULT_BEFORE_END)
    parser.add_argument("--after-start", default=DEFAULT_AFTER_START)
    parser.add_argument("--after-end", default=DEFAULT_AFTER_END)
    parser.add_argument(
        "--max-cloud",
        type=float,
        default=35.0,
        help="Maximum scene-level eo:cloud_cover used by the STAC search.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum STAC results requested per temporal window.",
    )
    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Only search/select scenes and write selection metadata; do not crop bands.",
    )
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_square_bbox(center_lat: float, center_lon: float, area_km2: float) -> list[float]:
    if area_km2 <= 0:
        raise ValueError("area_km2 must be greater than zero.")

    side_km = math.sqrt(area_km2)
    half_km = side_km / 2.0
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * math.cos(math.radians(center_lat))
    dlat = half_km / km_per_deg_lat
    dlon = half_km / km_per_deg_lon

    return [
        center_lon - dlon,
        center_lat - dlat,
        center_lon + dlon,
        center_lat + dlat,
    ]


def geometry_bbox(geometry: dict[str, Any]) -> list[float]:
    coords: list[tuple[float, float]] = []

    def walk(value: Any) -> None:
        if (
            isinstance(value, list)
            and len(value) >= 2
            and all(isinstance(v, (int, float)) for v in value[:2])
        ):
            coords.append((float(value[0]), float(value[1])))
            return
        if isinstance(value, list):
            for child in value:
                walk(child)

    walk(geometry.get("coordinates", []))
    if not coords:
        raise ValueError("Could not extract coordinates from AOI geometry.")

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def load_aoi_geojson(path: Path) -> tuple[dict[str, Any], list[float]]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if data.get("type") == "Feature":
        geometry = data.get("geometry")
    elif data.get("type") in ("Polygon", "MultiPolygon"):
        geometry = data
    elif data.get("type") == "FeatureCollection":
        features = data.get("features", [])
        if not features:
            raise ValueError("AOI FeatureCollection contains no features.")
        geometry = features[0].get("geometry")
    else:
        raise ValueError(
            "AOI GeoJSON must be a Polygon, MultiPolygon, Feature, or FeatureCollection."
        )

    if not geometry:
        raise ValueError("AOI GeoJSON does not contain a geometry.")

    return geometry, geometry_bbox(geometry)


def bbox_to_polygon(bbox: list[float]) -> dict[str, Any]:
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
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        EARTH_SEARCH_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/geo+json, application/json",
            "User-Agent": "ORION-SIH26227/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Earth Search returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Could not reach Earth Search. Check internet access and try again."
        ) from exc


def search_window(
    geometry: dict[str, Any],
    start_date: str,
    end_date: str,
    max_cloud: float,
    limit: int,
) -> list[Candidate]:
    payload = {
        "collections": [COLLECTION],
        "intersects": geometry,
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": limit,
        "query": {"eo:cloud_cover": {"lte": max_cloud}},
    }

    result = stac_post(payload)
    candidates = [Candidate(item=f) for f in result.get("features", [])]
    candidates.sort(key=lambda c: (c.cloud_cover, c.datetime, c.item_id))
    return candidates


def normalise_mgrs(candidate: Candidate) -> str:
    p = candidate.properties
    value = p.get("s2:mgrs_tile")
    if value:
        text = str(value)
        return text[1:] if text.startswith("T") else text

    zone = p.get("mgrs:utm_zone")
    band = p.get("mgrs:latitude_band")
    square = p.get("mgrs:grid_square")
    if zone is not None and band and square:
        return f"{zone}{band}{square}"
    return ""


def select_pair(
    before_candidates: list[Candidate],
    after_candidates: list[Candidate],
) -> tuple[Candidate, Candidate]:
    if not before_candidates:
        raise RuntimeError("No before-scene candidates matched the search.")
    if not after_candidates:
        raise RuntimeError("No after-scene candidates matched the search.")

    best: tuple[float, Candidate, Candidate] | None = None
    for before in before_candidates:
        before_tile = normalise_mgrs(before)
        for after in after_candidates:
            after_tile = normalise_mgrs(after)
            same_tile = bool(before_tile and after_tile and before_tile == after_tile)
            tile_penalty = 0.0 if same_tile else 1000.0
            platform_penalty = 0.0 if before.platform == after.platform else 2.0
            score = tile_penalty + platform_penalty + before.cloud_cover + after.cloud_cover
            if best is None or score < best[0]:
                best = (score, before, after)

    assert best is not None
    return best[1], best[2]


def candidate_summary(candidate: Candidate) -> dict[str, Any]:
    p = candidate.properties
    return {
        "id": candidate.item_id,
        "datetime": candidate.datetime,
        "platform": candidate.platform,
        "cloud_cover": candidate.cloud_cover,
        "mgrs_tile": normalise_mgrs(candidate),
        "processing_level": p.get("processing:level"),
        "processing_baseline": p.get("s2:processing_baseline"),
        "product_uri": p.get("s2:product_uri"),
        "constellation": p.get("constellation"),
        "instruments": p.get("instruments"),
        "bbox": candidate.item.get("bbox"),
        "stac_collection": candidate.item.get("collection"),
    }


def print_candidates(label: str, candidates: list[Candidate], max_rows: int = 10) -> None:
    print(f"\n{label} candidates: {len(candidates)}")
    print("-" * 100)
    for i, c in enumerate(candidates[:max_rows], start=1):
        print(
            f"{i:02d}. {c.datetime[:10]} | "
            f"cloud={c.cloud_cover:6.2f}% | "
            f"tile={normalise_mgrs(c) or 'unknown':8s} | "
            f"platform={c.platform or 'unknown':12s} | "
            f"{c.item_id}"
        )


def resolve_asset(item: dict[str, Any], candidate_keys: list[str]) -> tuple[str, dict[str, Any]]:
    assets = item.get("assets", {})
    for key in candidate_keys:
        if key in assets:
            return key, assets[key]
    raise KeyError(
        f"Could not find any of these STAC asset keys: {candidate_keys}. "
        f"Available keys: {sorted(assets.keys())}"
    )


def crop_remote_cog(href: str, bbox_wgs84: list[float], output_path: Path) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
    ):
        with rasterio.open(href) as src:
            if src.crs is None:
                raise RuntimeError(f"Remote asset has no CRS: {href}")

            left, bottom, right, top = transform_bounds(
                "EPSG:4326", src.crs, *bbox_wgs84, densify_pts=21
            )
            raw_window = from_bounds(left, bottom, right, top, transform=src.transform)
            window = raw_window.round_offsets().round_lengths()
            full = Window(0, 0, src.width, src.height)
            window = window.intersection(full)

            if window.width <= 0 or window.height <= 0:
                raise RuntimeError(f"AOI does not intersect remote raster asset: {href}")

            data = src.read(
                window=window,
                boundless=False,
                resampling=Resampling.nearest,
            )
            transform = src.window_transform(window)

            profile = src.profile.copy()
            profile.update(
                driver="GTiff",
                width=data.shape[2],
                height=data.shape[1],
                transform=transform,
                compress="deflate",
                tiled=True,
                BIGTIFF="IF_SAFER",
            )

            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(data)
                dst.update_tags(**src.tags())

            bounds = rasterio.windows.bounds(window, src.transform)
            return {
                "source_href": href,
                "output_path": str(output_path.as_posix()),
                "crs": src.crs.to_string(),
                "width": int(data.shape[2]),
                "height": int(data.shape[1]),
                "count": int(data.shape[0]),
                "dtype": str(data.dtype),
                "transform": list(transform)[:6],
                "bounds_native_crs": [float(v) for v in bounds],
                "resolution": [float(abs(src.res[0])), float(abs(src.res[1]))],
                "nodata": src.nodata,
            }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def download_scene(
    role: str,
    candidate: Candidate,
    bbox_wgs84: list[float],
    output_root: Path,
) -> dict[str, Any]:
    scene_dir = output_root / role
    scene_dir.mkdir(parents=True, exist_ok=True)

    scene_record = {
        "role": role,
        "selection": candidate_summary(candidate),
        "assets": {},
    }

    print(f"\nCropping {role.upper()} scene:")
    print(f"  {candidate.item_id}")
    print(f"  Date: {candidate.datetime}")
    print(f"  Cloud: {candidate.cloud_cover:.2f}%")
    print(f"  MGRS: {normalise_mgrs(candidate) or 'unknown'}")

    for band_name, candidate_keys in REQUIRED_ASSETS.items():
        print(f"  -> {band_name}: locating asset...", end="", flush=True)
        try:
            asset_key, asset = resolve_asset(candidate.item, candidate_keys)
        except KeyError as exc:
            print(" MISSING")
            scene_record["assets"][band_name] = {"status": "missing", "error": str(exc)}
            continue

        href = asset.get("href")
        if not href:
            print(" NO HREF")
            scene_record["assets"][band_name] = {
                "status": "missing_href",
                "stac_asset_key": asset_key,
            }
            continue

        output_path = scene_dir / f"{band_name}.tif"
        print(f" {asset_key} -> cropping...", end="", flush=True)
        try:
            raster_info = crop_remote_cog(href, bbox_wgs84, output_path)
            print(
                f" done ({raster_info['width']}x{raster_info['height']}, "
                f"{raster_info['resolution'][0]:g} m)"
            )
            scene_record["assets"][band_name] = {
                "status": "ok",
                "stac_asset_key": asset_key,
                "title": asset.get("title"),
                "roles": asset.get("roles"),
                "type": asset.get("type"),
                **raster_info,
            }
        except Exception as exc:
            print(" FAILED")
            scene_record["assets"][band_name] = {
                "status": "failed",
                "stac_asset_key": asset_key,
                "source_href": href,
                "error": repr(exc),
            }

    return scene_record


def main() -> int:
    args = parse_args()
    project_root = Path.cwd()
    output_root = (project_root / args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    if args.aoi_geojson:
        aoi_path = Path(args.aoi_geojson)
        if not aoi_path.is_absolute():
            aoi_path = (project_root / aoi_path).resolve()
        geometry, bbox = load_aoi_geojson(aoi_path)
        aoi_source = {"type": "user_geojson", "path": str(aoi_path)}
    else:
        bbox = make_square_bbox(args.center_lat, args.center_lon, args.area_km2)
        geometry = bbox_to_polygon(bbox)
        aoi_source = {
            "type": "generated_square",
            "center_lat": args.center_lat,
            "center_lon": args.center_lon,
            "target_area_km2": args.area_km2,
            "note": (
                "Approximate square AOI generated around the Delhi centre. "
                "Replace with --aoi-geojson when the exact Copernicus Browser polygon is available."
            ),
        }

    aoi_record = {
        "type": "Feature",
        "properties": {"name": "ORION Delhi AOI", "crs": "EPSG:4326", **aoi_source},
        "geometry": geometry,
        "bbox": bbox,
    }
    write_json(output_root / "aoi.geojson", aoi_record)

    print("=" * 100)
    print("ORION — Sentinel-2 L2A Public Dataset Acquisition")
    print("=" * 100)
    print(f"Earth Search: {EARTH_SEARCH_URL}")
    print(f"Collection:   {COLLECTION}")
    print(f"Output:       {output_root}")
    print(f"AOI bbox:     [{bbox[0]:.6f}, {bbox[1]:.6f}, {bbox[2]:.6f}, {bbox[3]:.6f}]")
    print(f"Before:       {args.before_start} -> {args.before_end} | max cloud {args.max_cloud:.1f}%")
    print(f"After:        {args.after_start} -> {args.after_end} | max cloud {args.max_cloud:.1f}%")
    print("\nSearching public Earth Search STAC catalogue...")

    before_candidates = search_window(
        geometry, args.before_start, args.before_end, args.max_cloud, args.limit
    )
    after_candidates = search_window(
        geometry, args.after_start, args.after_end, args.max_cloud, args.limit
    )

    print_candidates("BEFORE", before_candidates)
    print_candidates("AFTER", after_candidates)
    before, after = select_pair(before_candidates, after_candidates)

    print("\nSELECTED PAIR")
    print("-" * 100)
    print(
        f"BEFORE: {before.datetime[:10]} | cloud={before.cloud_cover:.2f}% | "
        f"tile={normalise_mgrs(before) or 'unknown'} | {before.item_id}"
    )
    print(
        f"AFTER : {after.datetime[:10]} | cloud={after.cloud_cover:.2f}% | "
        f"tile={normalise_mgrs(after) or 'unknown'} | {after.item_id}"
    )

    selection_record = {
        "generated_at_utc": utc_now_iso(),
        "project": "ORION",
        "problem_statement": "SIH26227",
        "purpose": "Semantic retrieval and multi-temporal change analysis",
        "source_mission": "Copernicus Sentinel-2",
        "source_product": "Sentinel-2 Level-2A Surface Reflectance",
        "distribution": "AWS Open Data / Element 84 Earth Search",
        "earth_search_endpoint": EARTH_SEARCH_URL,
        "stac_collection": COLLECTION,
        "aoi_bbox_epsg4326": bbox,
        "before_search_window": [args.before_start, args.before_end],
        "after_search_window": [args.after_start, args.after_end],
        "max_scene_cloud_cover": args.max_cloud,
        "before": candidate_summary(before),
        "after": candidate_summary(after),
        "selection_logic": (
            "Prefer matching MGRS tile, then lower combined scene cloud cover, "
            "with a small preference for the same Sentinel platform."
        ),
        "offline_note": (
            "Network access is used only during dataset staging. "
            "ORION runtime/evaluation should use the locally saved GeoTIFF crops "
            "and provenance files without external APIs."
        ),
    }
    write_json(output_root / "selected_pair.json", selection_record)

    if args.search_only:
        print("\nSearch-only mode complete.")
        print(f"Selection metadata: {output_root / 'selected_pair.json'}")
        return 0

    before_record = download_scene("before", before, bbox, output_root)
    after_record = download_scene("after", after, bbox, output_root)

    provenance = {
        **selection_record,
        "ingested_at_utc": utc_now_iso(),
        "aoi_file": str((output_root / "aoi.geojson").as_posix()),
        "before_scene": before_record,
        "after_scene": after_record,
        "required_assets": list(REQUIRED_ASSETS.keys()),
        "provenance_version": "orion-sentinel2-ingest-v1",
    }
    write_json(output_root / "provenance.json", provenance)

    ok_before = sum(1 for v in before_record["assets"].values() if v.get("status") == "ok")
    ok_after = sum(1 for v in after_record["assets"].values() if v.get("status") == "ok")

    print("\n" + "=" * 100)
    print("DONE")
    print("=" * 100)
    print(f"BEFORE assets cropped successfully: {ok_before}/{len(REQUIRED_ASSETS)}")
    print(f"AFTER assets cropped successfully:  {ok_after}/{len(REQUIRED_ASSETS)}")
    print(f"AOI:        {output_root / 'aoi.geojson'}")
    print(f"Selection:  {output_root / 'selected_pair.json'}")
    print(f"Provenance: {output_root / 'provenance.json'}")

    if ok_before < 4 or ok_after < 4:
        print("\nWARNING: Too few assets were downloaded. Inspect provenance.json for details.")
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
