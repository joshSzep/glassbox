"""Focused replay comparison and triage regression coverage."""

from glassbox.runtime.replay import ReplayFinalStateSnapshot
from glassbox.runtime.replay import ReplayNormalizedSession
from glassbox.runtime.replay import ReplayResult
from glassbox.runtime.replay import build_replay_triage
from glassbox.runtime.replay_compare import collect_mismatches
from glassbox.runtime.replay_models import ReplayCancellationSnapshot


def _normalized_session(
    *,
    cancellations: list[ReplayCancellationSnapshot] | None = None,
    event_families: list[str] | None = None,
) -> ReplayNormalizedSession:
    return ReplayNormalizedSession(
        transcript=[],
        tool_calls=[],
        approvals=[],
        questions=[],
        cancellations=cancellations or [],
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


def test_collect_mismatches_reports_cancellation_dimension() -> None:
    baseline = _normalized_session(
        cancellations=[
            ReplayCancellationSnapshot(
                turn_id="turn-1",
                event="turn_cancelled",
                reason="operator requested cancellation",
                stage="model_call",
            )
        ]
    )
    replay = _normalized_session()

    assert collect_mismatches(baseline, replay) == ["cancellations drift"]


def test_build_replay_triage_explains_exact_cancelled_replay() -> None:
    baseline = _normalized_session(
        cancellations=[
            ReplayCancellationSnapshot(
                turn_id="turn-1",
                event="turn_cancelled",
                reason="operator requested cancellation",
                stage="tool_execution",
            )
        ]
    )

    triage = build_replay_triage(
        ReplayResult(outcome="exact_match", baseline=baseline, replay=baseline)
    )

    assert triage.classification == "exact_match"
    assert "cancellation" in triage.headline
    assert triage.impacted_dimensions == ["cancellations", "final_state"]


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
