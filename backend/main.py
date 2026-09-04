from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.services.retrieval import load_scenes, search_scenes
from backend.services.change_detection import detect_change


app = FastAPI(
    title="ORION API",
    description="Offline Satellite Intelligence Backend",
    version="0.2.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENES_ROOT = PROJECT_ROOT / "data" / "scenes"


class SearchRequest(BaseModel):
    query: str = ""
    sensor: str = "ALL"
    change_type: str = "ALL"
    start_date: str | None = None
    end_date: str | None = None


class ChangeDetectionRequest(BaseModel):
    scene_id: str = "prayagraj"


@app.get("/")
def root():
    return {
        "name": "ORION API",
        "status": "running",
        "version": "0.2.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/scenes")
def get_scenes():
    return load_scenes()


@app.post("/search")
def search(request: SearchRequest):
    results = search_scenes(
        query=request.query,
        sensor=request.sensor,
        change_type=request.change_type,
        start_date=request.start_date,
        end_date=request.end_date
    )

    return {
        "query": request.query,
        "count": len(results),
        "results": results
    }


@app.post("/change-detection")
def change_detection(request: ChangeDetectionRequest):
    scene_directory = SCENES_ROOT / request.scene_id

    before_path = scene_directory / "before.tif"
    after_path = scene_directory / "after.tif"
    output_path = scene_directory / "change_mask.png"

    if not before_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Before image not found for scene: {request.scene_id}"
        )

    if not after_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"After image not found for scene: {request.scene_id}"
        )

    try:
        result = detect_change(
            before_path,
            after_path,
            output_path
        )

        top_regions = result.get("regions", [])[:15]

        return {
            "scene_id": request.scene_id,
            "summary": {
                "change_regions": result.get("change_regions", 0),
                "changed_pixels": result.get("changed_pixels", 0),
                "total_pixels": result.get("total_pixels", 0),
                "change_percentage": result.get("change_percentage", 0),
                "mean_change_intensity": result.get(
                    "mean_change_intensity", 0
                )
            },
            "top_regions": top_regions,
            "change_mask": result.get("change_mask")
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )