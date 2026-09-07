from pathlib import Path

from backend.services.change_ranking import (
    load_temporal_results,
    rank_change_events,
    save_ranked_events
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


INPUT_REPORT = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "temporal_tile_results.json"
)


OUTPUT_REPORT = (
    PROJECT_ROOT
    / "data"
    / "change_analysis"
    / "prayagraj"
    / "ranked_change_events.json"
)


def main():
    print("=== ORION Change Ranking Test ===")

    print(
        f"\nLoading report:\n{INPUT_REPORT}"
    )

    report = load_temporal_results(
        INPUT_REPORT
    )

    results = report.get(
        "results",
        []
    )

    print(
        f"Total temporal results: "
        f"{len(results)}"
    )

    events = rank_change_events(
        results
    )

    save_ranked_events(
        events,
        OUTPUT_REPORT
    )

    print(
        f"\nRanked events saved to:\n"
        f"{OUTPUT_REPORT}"
    )

    print("\n=== TOP 10 CHANGE EVENTS ===")

    for rank, event in enumerate(
        events[:10],
        start=1
    ):
        print(
            f"{rank}. "
            f"tile={event['tile_id']} "
            f"x={event['x']} "
            f"y={event['y']} "
            f"change="
            f"{event['change_percentage']:.3f}% "
            f"regions="
            f"{event['change_regions']} "
            f"severity="
            f"{event['severity_score']:.4f} "
            f"priority="
            f"{event['priority']}"
        )

    print("\n=== PRIORITY SUMMARY ===")

    high = sum(
        1
        for event in events
        if event["priority"] == "HIGH"
    )

    medium = sum(
        1
        for event in events
        if event["priority"] == "MEDIUM"
    )

    low = sum(
        1
        for event in events
        if event["priority"] == "LOW"
    )

    print(
        f"HIGH: {high}"
    )

    print(
        f"MEDIUM: {medium}"
    )

    print(
        f"LOW: {low}"
    )

    print(
        "\n=== CHANGE RANKING TEST COMPLETE ==="
    )


if __name__ == "__main__":
    main()