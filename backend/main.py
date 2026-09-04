from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.services.retrieval import load_scenes, search_scenes


app = FastAPI(
    title="ORION API",
    description="Offline Satellite Intelligence Backend",
    version="0.1.0"
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


class SearchRequest(BaseModel):
    query: str
    sensor: Optional[str] = "ALL"
    change_type: Optional[str] = "ALL"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@app.get("/")
def root():
    return {
        "system": "ORION",
        "status": "online",
        "message": "Offline Satellite Intelligence API"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/scenes")
def scenes():
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