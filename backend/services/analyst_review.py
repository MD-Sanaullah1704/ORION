from pathlib import Path
from datetime import datetime, timezone
import json


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent.parent
)

AUDIT_FILE = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "analyst_review_audit.json"
)


# ============================================================
# LOAD AUDIT
# ============================================================

def load_audit():
    """
    Load the persistent analyst review audit trail.
    """

    if not AUDIT_FILE.exists():
        return {
            "scene_id": "prayagraj",
            "reviews": []
        }

    with open(
        AUDIT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


# ============================================================
# SAVE AUDIT
# ============================================================

def save_audit(audit):
    """
    Persist the analyst review audit trail.
    """

    AUDIT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        AUDIT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            audit,
            file,
            indent=2
        )


# ============================================================
# FIND REVIEW
# ============================================================

def get_review(tile_id):
    """
    Return the most recent review for a tile.
    """

    audit = load_audit()

    reviews = [
        review
        for review in audit.get(
            "reviews",
            []
        )
        if int(
            review.get(
                "tile_id",
                -1
            )
        ) == int(tile_id)
    ]

    if not reviews:
        return None

    return reviews[-1]


# ============================================================
# ADD REVIEW
# ============================================================

def add_review(
    tile_id,
    decision,
    note=""
):
    """
    Add an analyst review to the persistent audit trail.

    decision must be CONFIRMED or REJECTED.
    """

    decision = decision.upper().strip()

    if decision not in {
        "CONFIRMED",
        "REJECTED"
    }:
        raise ValueError(
            "Decision must be CONFIRMED or REJECTED"
        )

    audit = load_audit()

    review = {
        "review_id": (
            len(
                audit.get(
                    "reviews",
                    []
                )
            ) + 1
        ),

        "tile_id": int(
            tile_id
        ),

        "decision": decision,

        "note": note.strip(),

        "reviewed_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
    }

    audit.setdefault(
        "reviews",
        []
    ).append(
        review
    )

    save_audit(
        audit
    )

    return review


# ============================================================
# ALL REVIEWS
# ============================================================

def get_all_reviews():
    """
    Return the complete analyst audit trail.
    """

    audit = load_audit()

    return audit.get(
        "reviews",
        []
    )