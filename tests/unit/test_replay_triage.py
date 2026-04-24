"""Focused replay comparison and triage regression coverage."""

from glassbox.runtime.replay import (
    ReplayFinalStateSnapshot,
    ReplayNormalizedSession,
    ReplayResult,
    build_replay_triage,
)
from glassbox.runtime.replay_compare import collect_mismatches


def _normalized_session(
    *,
    event_families: list[str] | None = None,
) -> ReplayNormalizedSession:
    return ReplayNormalizedSession(
        transcript=[],
        tool_calls=[],
        approvals=[],
        questions=[],
        event_families=event_families or ["SessionStarted", "TurnCompleted"],
        final_state=ReplayFinalStateSnapshot(status="completed"),
    )


def test_collect_mismatches_reports_changed_dimensions() -> None:
    baseline = _normalized_session()
    replay = _normalized_session(event_families=["SessionStarted"])
    replay.final_state = ReplayFinalStateSnapshot(status="failed")

    assert collect_mismatches(baseline, replay) == [
        "event_families drift",
        "final_state drift",
    ]


def test_build_replay_triage_classifies_behavioral_drift() -> None:
    triage = build_replay_triage(
        ReplayResult(
            outcome="behavioral_drift",
            mismatches=["event_families drift", "final_state drift"],
        )
    )

    assert triage.classification == "behavioral_drift"
    assert triage.first_relevant_change == "event_families drift"
    assert triage.impacted_dimensions == ["event_families", "final_state"]
    assert triage.recommended_inspection_path is not None
    assert "event stream" in triage.recommended_inspection_path


def test_build_replay_triage_classifies_context_source_drift() -> None:
    triage = build_replay_triage(
        ReplayResult(
            outcome="manifest_drift",
            message="recorded enriched context source drifted: runtime_notes",
        )
    )

    assert triage.classification == "context_source_drift"
    assert triage.drift_sources == ["runtime_notes"]
    assert triage.recommended_inspection_path is not None
    assert "runtime note inputs" in triage.recommended_inspection_path


def test_replay_behavioral_drift_characterization_preserves_ordered_guidance() -> None:
    baseline = _normalized_session()
    replay = _normalized_session(event_families=["SessionStarted"])
    replay.final_state = ReplayFinalStateSnapshot(status="failed")

    mismatches = collect_mismatches(baseline, replay)
    triage = build_replay_triage(
        ReplayResult(
            outcome="behavioral_drift",
            mismatches=mismatches,
            baseline=baseline,
            replay=replay,
        )
    )

    assert mismatches == ["event_families drift", "final_state drift"]
    assert triage.first_relevant_change == "event_families drift"
    assert triage.impacted_dimensions == ["event_families", "final_state"]
    assert triage.recommended_inspection_path is not None
    assert "event stream" in triage.recommended_inspection_path
