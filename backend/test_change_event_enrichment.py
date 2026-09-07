from pathlib import Path

from backend.services.change_event_enrichment import (
    load_ranked_events,
    enrich_change_events,
    save_enriched_events
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


INPUT_REPORT = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "ranked_change_events.json"
)


OUTPUT_REPORT = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "enriched_change_events.json"
)


def main():
    print("=== ORION Change Event Enrichment Test ===")

    print(
        f"\nLoading ranked events:\n{INPUT_REPORT}"
    )

    events = load_ranked_events(
        INPUT_REPORT
    )

    print(
        f"Ranked events loaded: {len(events)}"
    )

    enriched_events = enrich_change_events(
        events
    )

    save_enriched_events(
        enriched_events,
        OUTPUT_REPORT
    )

    print(
        f"\nEnriched report saved to:\n"
        f"{OUTPUT_REPORT}"
    )

    print("\n=== TOP 10 ENRICHED EVENTS ===")

    for rank, event in enumerate(
        enriched_events[:10],
        start=1
    ):
        print(
            f"{rank}. "
            f"tile={event['tile_id']} "
            f"priority={event['priority']} "
            f"severity={event['severity_score']:.4f} "
            f"type={event['dominant_change_type']} "
            f"classification="
            f"{event['classification_score']:.4f}"
        )

    print(
        "\n=== ENRICHMENT TEST COMPLETE ==="
    )


if __name__ == "__main__":
    main()