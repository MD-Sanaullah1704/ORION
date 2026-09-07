from pathlib import Path

from backend.services.change_confidence import (
    load_ranked_events,
    evaluate_events,
    save_evaluated_events
)


PROJECT_ROOT = Path(
    __file__
).resolve().parent.parent


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
    / "evaluated_change_events.json"
)


def main():

    print(
        "=== ORION Change Confidence Test ==="
    )

    print(
        f"\nLoading ranked events:\n"
        f"{INPUT_REPORT}"
    )

    report = load_ranked_events(
        INPUT_REPORT
    )

    events = report.get(
        "events",
        []
    )

    print(
        f"Ranked events loaded: "
        f"{len(events)}"
    )

    evaluated_events = evaluate_events(
        events
    )

    save_evaluated_events(
        evaluated_events,
        OUTPUT_REPORT
    )

    print(
        f"\nEvaluated report saved to:\n"
        f"{OUTPUT_REPORT}"
    )

    # --------------------------------------------------------
    # TOP 10
    # --------------------------------------------------------

    print(
        "\n=== TOP 10 EVALUATED EVENTS ==="
    )

    for rank, event in enumerate(
        evaluated_events[:10],
        start=1
    ):

        print(
            f"{rank}. "
            f"tile={event['tile_id']} "
            f"change="
            f"{event['change_percentage']:.3f}% "
            f"type="
            f"{event.get('dominant_change_type', 'OTHER CHANGE')} "
            f"severity="
            f"{event.get('severity_score', 0):.4f} "
            f"evidence="
            f"{event['evidence_score']:.4f} "
            f"confidence="
            f"{event['evidence_confidence']} "
            f"false_alarm="
            f"{event['false_alarm_risk']} "
            f"suppressed="
            f"{event['suppressed']}"
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    high_confidence = sum(
        1
        for event in evaluated_events
        if event["evidence_confidence"]
        == "HIGH"
    )

    medium_confidence = sum(
        1
        for event in evaluated_events
        if event["evidence_confidence"]
        == "MEDIUM"
    )

    low_confidence = sum(
        1
        for event in evaluated_events
        if event["evidence_confidence"]
        == "LOW"
    )

    suppressed = sum(
        1
        for event in evaluated_events
        if event["suppressed"]
    )

    print(
        "\n=== CONFIDENCE SUMMARY ==="
    )

    print(
        f"HIGH confidence: "
        f"{high_confidence}"
    )

    print(
        f"MEDIUM confidence: "
        f"{medium_confidence}"
    )

    print(
        f"LOW confidence: "
        f"{low_confidence}"
    )

    print(
        f"Suppressed as high false-alarm risk: "
        f"{suppressed}"
    )

    print(
        "\n=== CHANGE CONFIDENCE TEST COMPLETE ==="
    )


if __name__ == "__main__":
    main()