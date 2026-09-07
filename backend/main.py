from backend.services.semantic_search import load_semantic_search
from backend.incremental_ingest import incremental_ingest
from pathlib import Path
import json
import mimetypes

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.services.retrieval import load_scenes
from backend.services.semantic_search import load_semantic_search
from backend.services.change_detection import detect_change
from backend.services.geospatial import (
    get_event_geospatial_info,
    get_raster_geospatial_info
)

from backend.services.analyst_review import (
    add_review,
    get_review,
    get_all_reviews
)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

EVALUATED_EVENTS_FILE = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "evaluated_change_events.json"
)


# ============================================================
# REAL DATASET PATHS
# ============================================================

DATASETS_ROOT = (
    PROJECT_ROOT
    / "data"
    / "datasets"
)

DELHI_DATASET_ROOT = (
    DATASETS_ROOT
    / "delhi_sentinel2"
)

DELHI_BEFORE_B04 = (
    DELHI_DATASET_ROOT
    / "before"
    / "B04.tif"
)

DELHI_AFTER_B04 = (
    DELHI_DATASET_ROOT
    / "after"
    / "B04.tif"
)

DELHI_SELECTED_PAIR_FILE = (
    DELHI_DATASET_ROOT
    / "selected_pair.json"
)

DELHI_PROVENANCE_FILE = (
    DELHI_DATASET_ROOT
    / "provenance.json"
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="ORION",
    description=(
        "Semantic Retrieval and Multi-Temporal "
        "Change Analysis of Satellite Imagery"
    ),
    version="0.7.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# GLOBAL SEMANTIC SEARCH SERVICE
# ============================================================

semantic_search = None


# ============================================================
# REQUEST MODELS
# ============================================================

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    sensor: str | None = None
    change_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ReviewRequest(BaseModel):
    decision: str
    note: str = ""

class IncrementalIngestRequest(BaseModel):
    input_path: str
    scene_id: str
    observation: str
    index_dir: str
    model_path: str | None = None
    reload_search: bool = True

# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():

    global semantic_search

    print("=== ORION STARTUP ===")

    print(
        "Loading semantic search engine..."
    )

    semantic_search = load_semantic_search()

    print(
        "=== ORION READY ==="
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "name": "ORION",

        "description": (
            "Semantic Retrieval and "
            "Multi-Temporal Change Analysis "
            "of Satellite Imagery"
        ),

        "version": "0.7.0",

        "status": "running"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",

        "semantic_search": (
            semantic_search is not None
        ),

        "change_events": (
            EVALUATED_EVENTS_FILE.exists()
        )
    }


# ============================================================
# SCENES
# ============================================================

@app.get("/scenes")
def scenes():

    return load_scenes()
# ============================================================
# INCREMENTAL SEMANTIC INDEX INGESTION
# ============================================================

@app.post("/ingest/incremental")
def ingest_incremental(
    request: IncrementalIngestRequest
):
    """
    Incrementally add new satellite tiles to an existing
    RemoteCLIP + FAISS semantic-search index.

    Existing tiles are skipped automatically.

    After successful ingestion, the semantic-search service
    can optionally be reloaded so the newly added vectors
    become immediately searchable.
    """

    global semantic_search

    # --------------------------------------------------------
    # INPUT DIRECTORY
    # --------------------------------------------------------

    input_path = Path(
        request.input_path
    )

    if not input_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Input directory not found: "
                f"{input_path}"
            )
        )

    if not input_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Input path is not a directory: "
                f"{input_path}"
            )
        )

    # --------------------------------------------------------
    # SCENE ID
    # --------------------------------------------------------

    scene_id = (
        request.scene_id
        .strip()
    )

    if not scene_id:
        raise HTTPException(
            status_code=400,
            detail="scene_id cannot be empty."
        )

    # --------------------------------------------------------
    # OBSERVATION
    # --------------------------------------------------------

    observation = (
        request.observation
        .strip()
        .lower()
    )

    if observation not in {
        "before",
        "after"
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "observation must be either "
                "'before' or 'after'."
            )
        )

    # --------------------------------------------------------
    # INDEX DIRECTORY
    # --------------------------------------------------------

    index_dir = Path(
        request.index_dir
    )

    if not index_dir.is_absolute():
        index_dir = (
            PROJECT_ROOT
            / index_dir
        )

    # --------------------------------------------------------
    # REMOTECLIP MODEL
    # --------------------------------------------------------

    if request.model_path:
        model_path = Path(
            request.model_path
        )
    else:
        model_path = (
            PROJECT_ROOT
            / "models"
            / "remoteclip"
            / "RemoteCLIP-ViT-B-32.pt"
        )

    if not model_path.is_absolute():
        model_path = (
            PROJECT_ROOT
            / model_path
        )

    if not model_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"RemoteCLIP model not found: "
                f"{model_path}"
            )
        )

    # --------------------------------------------------------
    # RUN INCREMENTAL INGESTION
    # --------------------------------------------------------

    try:

        result = incremental_ingest(
            image_directory=input_path,
            scene_id=scene_id,
            observation=observation,
            index_directory=index_dir,
            model_path=model_path
        )

    except (
        FileNotFoundError,
        RuntimeError,
        ValueError
    ) as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Incremental ingestion failed: "
                f"{error}"
            )
        )

    # --------------------------------------------------------
    # RELOAD SEMANTIC SEARCH
    # --------------------------------------------------------

    search_reloaded = False

    if request.reload_search:

        try:

            semantic_search = (
                load_semantic_search(
                    index_dir=index_dir
                )
            )

            search_reloaded = True

        except Exception as error:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Incremental ingestion completed, "
                    "but the updated index could not be "
                    "loaded for semantic search: "
                    f"{error}"
                )
            )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "status": result.get(
            "status",
            "success"
        ),

        "ingestion": result,

        "semantic_search_reloaded":
            search_reloaded,

        "active_index_dir": (
            str(index_dir)
            if search_reloaded
            else None
        )
    }

# ============================================================
# REAL DATASET GEOSPATIAL INFORMATION
# ============================================================

@app.get("/datasets/{dataset_id}/geospatial")
def get_dataset_geospatial(dataset_id: str):

    dataset_id = dataset_id.strip().lower()

    # --------------------------------------------------------
    # Currently supported staged dataset
    # --------------------------------------------------------

    if dataset_id != "delhi_sentinel2":

        raise HTTPException(
            status_code=404,
            detail=(
                f"Dataset '{dataset_id}' is not available "
                "in the staged dataset registry."
            )
        )

    # --------------------------------------------------------
    # Verify dataset directory
    # --------------------------------------------------------

    if not DELHI_DATASET_ROOT.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Delhi Sentinel-2 dataset directory "
                "was not found."
            )
        )

    # --------------------------------------------------------
    # Load selected pair metadata
    # --------------------------------------------------------

    selected_pair = {}

    if DELHI_SELECTED_PAIR_FILE.exists():

        try:

            with open(
                DELHI_SELECTED_PAIR_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                selected_pair = json.load(file)

        except json.JSONDecodeError as error:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Delhi selected_pair.json is invalid: "
                    f"{error}"
                )
            )

    # --------------------------------------------------------
    # Extract actual BEFORE metadata
    #
    # selected_pair.json uses:
    #
    # "before": {
    #     "id": ...,
    #     "datetime": ...,
    #     ...
    # }
    # --------------------------------------------------------

    before_scene = selected_pair.get(
        "before",
        {}
    )

    # --------------------------------------------------------
    # Extract actual AFTER metadata
    # --------------------------------------------------------

    after_scene = selected_pair.get(
        "after",
        {}
    )

    # --------------------------------------------------------
    # Build BEFORE raster geospatial information
    # --------------------------------------------------------

    if DELHI_BEFORE_B04.exists():

        try:

            before_geospatial = (
                get_raster_geospatial_info(
                    DELHI_BEFORE_B04
                )
            )

        except Exception as error:

            before_geospatial = {
                "status": "unavailable",
                "reason": (
                    "Before raster geospatial "
                    f"processing failed: {error}"
                )
            }

    else:

        before_geospatial = {
            "status": "unavailable",
            "reason": (
                "Before B04 raster was not found."
            )
        }

    # --------------------------------------------------------
    # Build AFTER raster geospatial information
    # --------------------------------------------------------

    if DELHI_AFTER_B04.exists():

        try:

            after_geospatial = (
                get_raster_geospatial_info(
                    DELHI_AFTER_B04
                )
            )

        except Exception as error:

            after_geospatial = {
                "status": "unavailable",
                "reason": (
                    "After raster geospatial "
                    f"processing failed: {error}"
                )
            }

    else:

        after_geospatial = {
            "status": "unavailable",
            "reason": (
                "After B04 raster was not found."
            )
        }

    # --------------------------------------------------------
    # Dataset availability
    # --------------------------------------------------------

    dataset_status = (
        "available"
        if (
            before_geospatial
            and before_geospatial.get(
                "status"
            ) == "available"
            and after_geospatial
            and after_geospatial.get(
                "status"
            ) == "available"
        )
        else "partially_available"
    )

    # --------------------------------------------------------
    # Return dataset information
    # --------------------------------------------------------

    return {

        "dataset_id": "delhi_sentinel2",

        "status": dataset_status,

        "sensor": selected_pair.get(
            "source_mission",
            "Copernicus Sentinel-2"
        ),

        "product": selected_pair.get(
            "source_product",
            "Sentinel-2 Level-2A Surface Reflectance"
        ),

        "distribution": selected_pair.get(
            "distribution"
        ),

        "stac_collection": selected_pair.get(
            "stac_collection"
        ),

        "before": {

            "date": before_scene.get(
                "datetime"
            ),

            "scene_id": before_scene.get(
                "id"
            ),

            "platform": before_scene.get(
                "platform"
            ),

            "mgrs_tile": before_scene.get(
                "mgrs_tile"
            ),

            "cloud_cover": before_scene.get(
                "cloud_cover"
            ),

            "processing_baseline": before_scene.get(
                "processing_baseline"
            ),

            "product_uri": before_scene.get(
                "product_uri"
            ),

            "raster": before_geospatial

        },

        "after": {

            "date": after_scene.get(
                "datetime"
            ),

            "scene_id": after_scene.get(
                "id"
            ),

            "platform": after_scene.get(
                "platform"
            ),

            "mgrs_tile": after_scene.get(
                "mgrs_tile"
            ),

            "cloud_cover": after_scene.get(
                "cloud_cover"
            ),

            "processing_baseline": after_scene.get(
                "processing_baseline"
            ),

            "product_uri": after_scene.get(
                "product_uri"
            ),

            "raster": after_geospatial

        },

        "aoi_bbox_epsg4326": selected_pair.get(
            "aoi_bbox_epsg4326"
        ),

        "before_search_window": selected_pair.get(
            "before_search_window"
        ),

        "after_search_window": selected_pair.get(
            "after_search_window"
        ),

        "offline_ready": True,

        "offline_note": selected_pair.get(
            "offline_note"
        ),

        "source": selected_pair.get(
            "distribution",
            "AWS Open Data / Element 84 Earth Search"
        )

    }


# ============================================================
# SEMANTIC SEARCH
# ============================================================

@app.post("/search")
def search(
    request: SearchRequest
):

    if semantic_search is None:

        raise HTTPException(
            status_code=503,
            detail=(
                "Semantic search service "
                "is not ready"
            )
        )

    if not request.query.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "Search query cannot be empty"
            )
        )

    results = semantic_search.search_text(
        request.query,
        top_k=request.top_k
    )

    return {
        "query": request.query,

        "query_type": "text",

        "count": len(results),

        "filters": {
            "sensor": request.sensor,
            "change_type": request.change_type,
            "start_date": request.start_date,
            "end_date": request.end_date
        },

        "results": results
    }


# ============================================================
# FULL-SCENE CHANGE DETECTION
# ============================================================

@app.post("/change-detection")
def change_detection(
    before_path: str,
    after_path: str,
    output_path: str
):

    before = Path(
        before_path
    )

    after = Path(
        after_path
    )

    output = Path(
        output_path
    )

    if not before.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Before image not found: "
                f"{before}"
            )
        )

    if not after.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"After image not found: "
                f"{after}"
            )
        )

    result = detect_change(
        before,
        after,
        output
    )

    return result


# ============================================================
# LOAD EVALUATED CHANGE EVENTS
# ============================================================

def load_evaluated_events():

    if not EVALUATED_EVENTS_FILE.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Evaluated change event report "
                "has not been generated yet."
            )
        )

    try:

        with open(
            EVALUATED_EVENTS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            report = json.load(
                file
            )

    except json.JSONDecodeError as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Evaluated change event report "
                f"is invalid JSON: {error}"
            )
        )

    return report


# ============================================================
# CHANGE EVENTS
# ============================================================

@app.get("/change-events")
def get_change_events(
    priority: str | None = None,
    confidence: str | None = None,
    change_type: str | None = None,
    include_suppressed: bool = False
):

    report = load_evaluated_events()

    events = report.get(
        "events",
        []
    )

    # --------------------------------------------------------
    # SUPPRESSION FILTER
    # --------------------------------------------------------

    if not include_suppressed:

        events = [
            event
            for event in events
            if not event.get(
                "suppressed",
                False
            )
        ]

    # --------------------------------------------------------
    # PRIORITY FILTER
    # --------------------------------------------------------

    if priority:

        priority_value = (
            priority.upper()
        )

        events = [
            event
            for event in events
            if event.get(
                "priority",
                ""
            ).upper()
            == priority_value
        ]

    # --------------------------------------------------------
    # CONFIDENCE FILTER
    # --------------------------------------------------------

    if confidence:

        confidence_value = (
            confidence.upper()
        )

        events = [
            event
            for event in events
            if event.get(
                "evidence_confidence",
                ""
            ).upper()
            == confidence_value
        ]

    # --------------------------------------------------------
    # CHANGE TYPE FILTER
    # --------------------------------------------------------

    if change_type:

        change_type_value = (
            change_type.upper()
        )

        events = [
            event
            for event in events
            if event.get(
                "dominant_change_type",
                ""
            ).upper()
            == change_type_value
        ]

    return {
        "scene_id": report.get(
            "scene_id",
            "prayagraj"
        ),

        "count": len(events),

        "filters": {
            "priority": priority,
            "confidence": confidence,
            "change_type": change_type,
            "include_suppressed": (
                include_suppressed
            )
        },

        "events": events
    }


# ============================================================
# CHANGE EVENT SUMMARY
# ============================================================

@app.get("/change-events/summary")
def get_change_event_summary():

    report = load_evaluated_events()

    events = report.get(
        "events",
        []
    )

    total = len(
        events
    )

    suppressed = sum(
        1
        for event in events
        if event.get(
            "suppressed",
            False
        )
    )

    active_events = [
        event
        for event in events
        if not event.get(
            "suppressed",
            False
        )
    ]

    # --------------------------------------------------------
    # PRIORITY COUNTS
    # --------------------------------------------------------

    high_priority = sum(
        1
        for event in active_events
        if event.get(
            "priority"
        ) == "HIGH"
    )

    medium_priority = sum(
        1
        for event in active_events
        if event.get(
            "priority"
        ) == "MEDIUM"
    )

    low_priority = sum(
        1
        for event in active_events
        if event.get(
            "priority"
        ) == "LOW"
    )

    # --------------------------------------------------------
    # CONFIDENCE COUNTS
    # --------------------------------------------------------

    high_confidence = sum(
        1
        for event in active_events
        if event.get(
            "evidence_confidence"
        ) == "HIGH"
    )

    medium_confidence = sum(
        1
        for event in active_events
        if event.get(
            "evidence_confidence"
        ) == "MEDIUM"
    )

    low_confidence = sum(
        1
        for event in active_events
        if event.get(
            "evidence_confidence"
        ) == "LOW"
    )

    # --------------------------------------------------------
    # CHANGE TYPE COUNTS
    # --------------------------------------------------------

    change_types = {}

    for event in active_events:

        change_type = event.get(
            "dominant_change_type",
            "OTHER CHANGE"
        )

        change_types[change_type] = (
            change_types.get(
                change_type,
                0
            )
            + 1
        )

    return {
        "scene_id": report.get(
            "scene_id",
            "prayagraj"
        ),

        "total_events": total,

        "active_events": len(
            active_events
        ),

        "suppressed_events": suppressed,

        "priority": {
            "HIGH": high_priority,
            "MEDIUM": medium_priority,
            "LOW": low_priority
        },

        "confidence": {
            "HIGH": high_confidence,
            "MEDIUM": medium_confidence,
            "LOW": low_confidence
        },

        "change_types": change_types
    }


# ============================================================
# GEOSPATIAL SOURCE RASTER RESOLUTION
# ============================================================

def resolve_geospatial_source_raster(
    scene_id: str,
    event: dict
) -> Path | None:
    """
    Resolve the original georeferenced source raster for a
    change event.

    Resolution order:
    1. Explicit source raster stored at event level.
    2. Source raster stored in BEFORE metadata.
    3. Source raster stored in AFTER metadata.
    4. Known staged dataset paths.
    5. Standard ORION scene structure.

    Evidence PNGs are never used for geospatial calculations.
    """

    possible_keys = [
        "source_raster",
        "source_raster_path",
        "raster_path"
    ]

    # --------------------------------------------------------
    # Helper: resolve a stored path safely
    # --------------------------------------------------------

    def resolve_path(raw_path):
        if not raw_path:
            return None

        try:
            path = Path(str(raw_path))
        except Exception:
            return None

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        if path.exists() and path.is_file():
            return path

        return None

    # --------------------------------------------------------
    # 1. Explicit source raster stored in event
    # --------------------------------------------------------

    for key in possible_keys:

        path = resolve_path(
            event.get(key)
        )

        if path is not None:
            return path

    # --------------------------------------------------------
    # 2. Source raster inside BEFORE metadata
    # --------------------------------------------------------

    before_data = event.get(
        "before",
        {}
    )

    if isinstance(before_data, dict):

        for key in possible_keys:

            path = resolve_path(
                before_data.get(key)
            )

            if path is not None:
                return path

    # --------------------------------------------------------
    # 3. Source raster inside AFTER metadata
    # --------------------------------------------------------

    after_data = event.get(
        "after",
        {}
    )

    if isinstance(after_data, dict):

        for key in possible_keys:

            path = resolve_path(
                after_data.get(key)
            )

            if path is not None:
                return path

    # --------------------------------------------------------
    # 4. Known staged dataset: Jewar Airport
    #
    # Event 1000 uses the Sentinel-2 B04 GeoTIFF directly.
    # This avoids falling back to the non-georeferenced
    # Prayagraj scene when the event report contains a
    # different scene/dataset.
    # --------------------------------------------------------

    dataset_value = str(
        event.get(
            "dataset",
            ""
        )
    ).strip().lower()

    dataset_values = {
        dataset_value,
        str(
            event.get(
                "dataset_id",
                ""
            )
        ).strip().lower(),
        str(
            event.get(
                "scene_id",
                ""
            )
        ).strip().lower()
    }

    if (
        "jewar" in dataset_values
        or "jewar" in dataset_value
        or "jewar" in str(scene_id).lower()
    ):

        jewar_before = (
            DATASETS_ROOT
            / "jewar_airport_best"
            / "before"
            / "B04.tif"
        )

        if jewar_before.exists():
            return jewar_before

    # --------------------------------------------------------
    # 5. Standard ORION scene structure
    # --------------------------------------------------------

    scene_dir = (
        PROJECT_ROOT
        / "data"
        / "scenes"
        / str(scene_id)
    )

    standard_candidates = [
        scene_dir / "before.tif",
        scene_dir / "before.tiff",
        scene_dir / "before.cog.tif"
    ]

    for path in standard_candidates:

        if path.exists() and path.is_file():
            return path

    # --------------------------------------------------------
    # 6. Last-resort TIFF search
    # --------------------------------------------------------

    if scene_dir.exists():

        tiff_candidates = (
            list(
                scene_dir.glob("*.tif")
            )
            +
            list(
                scene_dir.glob("*.tiff")
            )
        )

        if tiff_candidates:
            return tiff_candidates[0]

    return None


# ============================================================
# BUILD EVENT GEOSPATIAL INFORMATION
# ============================================================

def build_event_geospatial_info(
    event: dict,
    tile_id: int
) -> dict:
    """
    Build geospatial information for a change event.

    The function always prefers the event's real source
    GeoTIFF. It never uses the PNG evidence files for
    geospatial calculations.

    For Sentinel-2 datasets such as Jewar, the source raster
    is georeferenced in its native CRS (EPSG:32643) and is
    converted to WGS84 for the map.
    """

    scene_id = str(
        event.get(
            "scene_id",
            "prayagraj"
        )
    )

    x = event.get("x")
    y = event.get("y")

    # --------------------------------------------------------
    # TILE COORDINATES
    # --------------------------------------------------------

    if x is None or y is None:

        # If the event itself already contains geographic
        # coordinates, return them rather than inventing
        # pixel coordinates.
        latitude = event.get("latitude")
        longitude = event.get("longitude")

        if (
            latitude is not None
            and longitude is not None
        ):

            return {
                "status": "available",
                "tile_id": tile_id,
                "scene_id": scene_id,
                "source_raster": event.get(
                    "source_raster"
                ),
                "crs": event.get(
                    "source_crs"
                ),
                "location": {
                    "latitude": float(latitude),
                    "longitude": float(longitude)
                },
                "bounds_wgs84": event.get(
                    "bounds_wgs84"
                ),
                "tile": None,
                "reason": (
                    "Using geographic coordinates stored "
                    "in the event metadata."
                )
            }

        return {
            "status": "unavailable",
            "tile_id": tile_id,
            "scene_id": scene_id,
            "reason": (
                "Change event does not contain "
                "tile pixel coordinates."
            ),
            "tile": None
        }

    # --------------------------------------------------------
    # RESOLVE ORIGINAL GEOTIFF
    # --------------------------------------------------------

    source_raster = resolve_geospatial_source_raster(
        scene_id,
        event
    )

    if source_raster is None:

        # Do not fabricate a location. If the event contains
        # previously calculated WGS84 metadata, it is safe to
        # expose that metadata directly.
        stored_location = event.get(
            "location"
        )

        stored_bounds = event.get(
            "bounds_wgs84"
        )

        if (
            isinstance(stored_location, dict)
            and stored_location.get("latitude") is not None
            and stored_location.get("longitude") is not None
        ):

            return {
                "status": "available",
                "tile_id": tile_id,
                "scene_id": scene_id,
                "source_raster": event.get(
                    "source_raster"
                ),
                "crs": event.get(
                    "source_crs"
                ),
                "location": stored_location,
                "bounds_wgs84": stored_bounds,
                "tile": None,
                "reason": (
                    "Using geographic metadata stored "
                    "with the change event."
                )
            }

        return {
            "status": "unavailable",
            "tile_id": tile_id,
            "scene_id": scene_id,
            "reason": (
                "Original georeferenced source raster "
                "could not be located for this event."
            ),
            "tile": None
        }

    # --------------------------------------------------------
    # READ AND CONVERT GEOSPATIAL INFORMATION
    # --------------------------------------------------------

    try:

        result = get_event_geospatial_info(
            raster_path=source_raster,
            tile_x=int(x),
            tile_y=int(y),
            tile_width=256,
            tile_height=256
        )

        if not isinstance(result, dict):

            return {
                "status": "unavailable",
                "tile_id": tile_id,
                "scene_id": scene_id,
                "source_raster": str(
                    source_raster
                ),
                "reason": (
                    "Geospatial service returned "
                    "an invalid response."
                ),
                "tile": None
            }

        result["tile_id"] = tile_id
        result["scene_id"] = scene_id
        result["source_raster"] = str(
            source_raster
        )

        # ----------------------------------------------------
        # IMPORTANT DATASET METADATA
        # ----------------------------------------------------

        raster_info = result.get(
            "raster",
            {}
        )

        if raster_info.get("status") == "available":

            result["status"] = "available"

            result["crs"] = (
                raster_info.get("crs")
            )

            result["raster_bounds"] = (
                raster_info.get("bounds")
            )

            result["raster_center"] = (
                raster_info.get("center")
            )

        # ----------------------------------------------------
        # TILE LOCATION
        # ----------------------------------------------------

        tile_info = result.get(
            "tile"
        )

        if (
            isinstance(tile_info, dict)
            and tile_info.get("status") == "available"
        ):

            result["location"] = (
                tile_info.get(
                    "center_wgs84"
                )
            )

            result["bounds_wgs84"] = (
                tile_info.get(
                    "bounds_wgs84"
                )
            )

        else:

            result["location"] = None
            result["bounds_wgs84"] = None

        return result

    except Exception as error:

        return {
            "status": "unavailable",
            "tile_id": tile_id,
            "scene_id": scene_id,
            "source_raster": str(
                source_raster
            ),
            "reason": (
                "Geospatial processing failed: "
                f"{error}"
            ),
            "tile": None
        }


# ============================================================
# GEOSPATIAL EVENT INFORMATION
# ============================================================

@app.get(
    "/change-events/{tile_id}/geospatial"
)
def get_change_event_geospatial(
    tile_id: int
):

    event = find_change_event(
        tile_id
    )

    return build_event_geospatial_info(
        event,
        tile_id
    )


# ============================================================
# SINGLE CHANGE EVENT
# ============================================================

@app.get(
    "/change-events/{tile_id}"
)
def get_change_event(
    tile_id: int
):

    report = load_evaluated_events()

    events = report.get(
        "events",
        []
    )

    for event in events:

        try:

            event_tile_id = int(
                event.get(
                    "tile_id",
                    -1
                )
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        if event_tile_id == tile_id:

            geospatial = (
                build_event_geospatial_info(
                    event,
                    tile_id
                )
            )

            enriched_event = dict(
                event
            )

            enriched_event[
                "geospatial"
            ] = geospatial

            return enriched_event

    raise HTTPException(
        status_code=404,
        detail=(
            f"Change event for tile "
            f"{tile_id} not found"
        )
    )


# ============================================================
# EVIDENCE HELPERS
# ============================================================

def resolve_evidence_path(
    raw_path: str | None
) -> Path:

    if not raw_path:

        raise HTTPException(
            status_code=404,
            detail="Evidence path is missing."
        )

    path = Path(
        raw_path
    )

    # --------------------------------------------------------
    # Absolute path
    # --------------------------------------------------------

    if path.is_absolute():

        if path.exists():

            return path

    # --------------------------------------------------------
    # Path relative to project root
    # --------------------------------------------------------

    project_path = (
        PROJECT_ROOT
        / path
    )

    if project_path.exists():

        return project_path

    # --------------------------------------------------------
    # Path relative to current working directory
    # --------------------------------------------------------

    cwd_path = (
        Path.cwd()
        / path
    )

    if cwd_path.exists():

        return cwd_path

    raise HTTPException(
        status_code=404,
        detail=(
            f"Evidence file not found: "
            f"{raw_path}"
        )
    )


def find_change_event(
    tile_id: int
):

    report = load_evaluated_events()

    events = report.get(
        "events",
        []
    )

    for event in events:

        try:

            event_tile_id = int(
                event.get(
                    "tile_id",
                    -1
                )
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        if event_tile_id == tile_id:

            return event

    raise HTTPException(
        status_code=404,
        detail=(
            f"Change event for tile "
            f"{tile_id} not found"
        )
    )


def evidence_file_response(
    path: Path
):

    media_type, _ = mimetypes.guess_type(
        str(path)
    )

    if media_type is None:

        media_type = (
            "application/octet-stream"
        )

    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=path.name
    )


# ============================================================
# CHANGE EVENT EVIDENCE METADATA
# ============================================================

@app.get(
    "/change-events/{tile_id}/evidence"
)
def get_change_event_evidence(
    tile_id: int
):

    event = find_change_event(
        tile_id
    )

    before_data = event.get(
        "before",
        {}
    )

    after_data = event.get(
        "after",
        {}
    )

    before_path = resolve_evidence_path(
        before_data.get(
            "path"
        )
    )

    after_path = resolve_evidence_path(
        after_data.get(
            "path"
        )
    )

    mask_path = resolve_evidence_path(
        event.get(
            "mask_path"
        )
    )

    # --------------------------------------------------------
    # Acquisition dates
    # --------------------------------------------------------

    before_date = (
        before_data.get(
            "observation"
        )
        or before_data.get(
            "date"
        )
        or event.get(
            "before_date"
        )
        or "2024-12-13"
    )

    after_date = (
        after_data.get(
            "observation"
        )
        or after_data.get(
            "date"
        )
        or event.get(
            "after_date"
        )
        or "2025-01-27"
    )

    # --------------------------------------------------------
    # Severity
    # --------------------------------------------------------

    severity = (
        event.get("severity")
        if event.get("severity") is not None
        else event.get("severity_score")
    )

    if severity is None:

        severity = event.get(
            "change_severity"
        )

    if severity is None:

        ranking = event.get(
            "ranking",
            {}
        )

        if isinstance(
            ranking,
            dict
        ):

            severity = (
                ranking.get(
                    "severity"
                )
                if ranking.get(
                    "severity"
                ) is not None
                else ranking.get(
                    "severity_score"
                )
            )

    return {
        "tile_id": tile_id,

        "scene_id": event.get(
            "scene_id",
            "prayagraj"
        ),

        "coordinates": {
            "x": event.get("x"),
            "y": event.get("y")
        },

        "before": {
            "date": before_date,

            "path": str(
                before_path
            ),

            "url": (
                f"/change-events/"
                f"{tile_id}/evidence/before"
            )
        },

        "after": {
            "date": after_date,

            "path": str(
                after_path
            ),

            "url": (
                f"/change-events/"
                f"{tile_id}/evidence/after"
            )
        },

        "change_mask": {
            "path": str(
                mask_path
            ),

            "url": (
                f"/change-events/"
                f"{tile_id}/evidence/mask"
            )
        },

        "change_percentage": event.get(
            "change_percentage"
        ),

        "dominant_change_type": event.get(
            "dominant_change_type"
        ),

        "classification_score": event.get(
            "classification_score"
        ),

        "severity": severity,

        "priority": event.get(
            "priority"
        ),

        "evidence_confidence": event.get(
            "evidence_confidence"
        ),

        "false_alarm_risk": event.get(
            "false_alarm_risk"
        ),

        "suppressed": event.get(
            "suppressed",
            False
        )
    }


# ============================================================
# BEFORE EVIDENCE IMAGE
# ============================================================

@app.get(
    "/change-events/{tile_id}/evidence/before"
)
def get_before_evidence(
    tile_id: int
):

    event = find_change_event(
        tile_id
    )

    before_data = event.get(
        "before",
        {}
    )

    path = resolve_evidence_path(
        before_data.get(
            "path"
        )
    )

    return evidence_file_response(
        path
    )


# ============================================================
# AFTER EVIDENCE IMAGE
# ============================================================

@app.get(
    "/change-events/{tile_id}/evidence/after"
)
def get_after_evidence(
    tile_id: int
):

    event = find_change_event(
        tile_id
    )

    after_data = event.get(
        "after",
        {}
    )

    path = resolve_evidence_path(
        after_data.get(
            "path"
        )
    )

    return evidence_file_response(
        path
    )


# ============================================================
# CHANGE MASK
# ============================================================

@app.get(
    "/change-events/{tile_id}/evidence/mask"
)
def get_change_mask_evidence(
    tile_id: int
):

    event = find_change_event(
        tile_id
    )

    path = resolve_evidence_path(
        event.get(
            "mask_path"
        )
    )

    return evidence_file_response(
        path
    )


# ============================================================
# ANALYST REVIEW
# ============================================================

@app.post(
    "/change-events/{tile_id}/review"
)
def review_change_event(
    tile_id: int,
    request: ReviewRequest
):

    decision = (
        request.decision
        .upper()
        .strip()
    )

    # --------------------------------------------------------
    # VALIDATE DECISION
    # --------------------------------------------------------

    if decision not in {
        "CONFIRMED",
        "REJECTED"
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "Decision must be "
                "CONFIRMED or REJECTED"
            )
        )

    # --------------------------------------------------------
    # VERIFY EVENT EXISTS
    # --------------------------------------------------------

    report = load_evaluated_events()

    events = report.get(
        "events",
        []
    )

    event_exists = False

    for event in events:

        try:

            event_tile_id = int(
                event.get(
                    "tile_id",
                    -1
                )
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        if event_tile_id == tile_id:

            event_exists = True

            break

    if not event_exists:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Change event for tile "
                f"{tile_id} not found"
            )
        )

    # --------------------------------------------------------
    # SAVE REVIEW
    # --------------------------------------------------------

    try:

        review = add_review(
            tile_id=tile_id,
            decision=decision,
            note=request.note
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    return {
        "status": "review_recorded",

        "tile_id": tile_id,

        "review": review
    }


# ============================================================
# GET REVIEW FOR ONE EVENT
# ============================================================

@app.get(
    "/change-events/{tile_id}/review"
)
def get_change_event_review(
    tile_id: int
):

    # --------------------------------------------------------
    # VERIFY EVENT EXISTS
    # --------------------------------------------------------

    report = load_evaluated_events()

    events = report.get(
        "events",
        []
    )

    event_exists = False

    for event in events:

        try:

            event_tile_id = int(
                event.get(
                    "tile_id",
                    -1
                )
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        if event_tile_id == tile_id:

            event_exists = True

            break

    if not event_exists:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Change event for tile "
                f"{tile_id} not found"
            )
        )

    # --------------------------------------------------------
    # GET REVIEW
    # --------------------------------------------------------

    review = get_review(
        tile_id
    )

    if review is None:

        return {
            "tile_id": tile_id,

            "reviewed": False,

            "review": None
        }

    return {
        "tile_id": tile_id,

        "reviewed": True,

        "review": review
    }


# ============================================================
# COMPLETE REVIEW AUDIT
# ============================================================

@app.get("/review-audit")
def review_audit():

    reviews = get_all_reviews()

    confirmed = sum(
        1
        for review in reviews
        if review.get(
            "decision"
        ) == "CONFIRMED"
    )

    rejected = sum(
        1
        for review in reviews
        if review.get(
            "decision"
        ) == "REJECTED"
    )

    return {
        "scene_id": "prayagraj",

        "total_reviews": len(
            reviews
        ),

        "confirmed": confirmed,

        "rejected": rejected,

        "reviews": reviews
    }