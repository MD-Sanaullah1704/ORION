import json
from pathlib import Path
from datetime import datetime


DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "scenes.json"
)


def load_scenes():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def _parse_date(date_string):
    if not date_string:
        return None

    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        return None


def search_scenes(
    query="",
    sensor="ALL",
    change_type="ALL",
    start_date=None,
    end_date=None
):
    scenes = load_scenes()

    query_words = query.lower().split()

    start = _parse_date(start_date)
    end = _parse_date(end_date)

    results = []

    for scene in scenes:

        # -----------------------------
        # Sensor filter
        # -----------------------------
        if sensor and sensor.upper() != "ALL":
            if scene["sensor"].lower() != sensor.lower():
                continue

        # -----------------------------
        # Change type filter
        # -----------------------------
        if change_type and change_type.upper() != "ALL":
            if scene["changeType"].lower() != change_type.lower():
                continue

        # -----------------------------
        # Date filter
        # -----------------------------
        scene_date = _parse_date(scene.get("date"))

        if start and scene_date and scene_date < start:
            continue

        if end and scene_date and scene_date > end:
            continue

        # -----------------------------
        # Text relevance
        # -----------------------------
        searchable_text = " ".join(
            [
                scene.get("title", ""),
                scene.get("changeType", ""),
                scene.get("description", ""),
                scene.get("sensor", ""),
                scene.get("location", "")
            ]
        ).lower()

        score = 0

        for word in query_words:
            if word in searchable_text:
                score += 1

        # Empty query means return all scenes
        if query_words and score == 0:
            continue

        # -----------------------------
        # Ranking
        # -----------------------------
        retrieval_score = score

        # Slightly favor higher-confidence detections
        confidence_bonus = scene.get("confidence", 0) / 1000

        final_score = retrieval_score + confidence_bonus

        scene_copy = scene.copy()

        scene_copy["retrieval_score"] = round(final_score, 3)

        results.append(scene_copy)

    # Highest relevance first
    results.sort(
        key=lambda scene: scene["retrieval_score"],
        reverse=True
    )

    return results