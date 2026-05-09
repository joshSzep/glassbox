"""Focused orchestration tests for replay bundle loading and result mapping."""

from pathlib import Path

import pytest

from glassbox.core import ChangesetCreated
from glassbox.core import EventEnvelope
from glassbox.core import LongRunPhase
from glassbox.core import LongRunPhaseChanged
from glassbox.core import LongRunPhaseState
from glassbox.core import ReplayArtifactRecorded
from glassbox.core import ReviewFeedbackCreated
from glassbox.core import ReviewFeedbackKind
from glassbox.core import SessionConfig
from glassbox.core import TaskCheckpointCreated
from glassbox.core import ToolAttemptHeartbeat
from glassbox.core import ToolAttemptStatus
from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
from glassbox.core import new_review_feedback_id
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.core import new_tool_attempt_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.runtime.replay_compare import collect_mismatches
from glassbox.runtime.replay_compare import normalize_event_families
from glassbox.runtime.replay_compare import normalize_long_run_events
from glassbox.runtime.replay_failures import ReplayFailure
from glassbox.runtime.replay_fingerprints import build_replay_enriched_context_sources
from glassbox.runtime.replay_fingerprints import (
    fingerprint_replay_enriched_context_payload,
)
from glassbox.runtime.replay_models import ReplayBundle
from glassbox.runtime.replay_models import ReplayFinalStateSnapshot
from glassbox.runtime.replay_models import ReplayLongRunEventSnapshot
from glassbox.runtime.replay_models import ReplayNormalizedSession
from glassbox.runtime.replay_orchestrator import ReplayComparisonOutcome
from glassbox.runtime.replay_orchestrator import ReplayExecutionOutcome
from glassbox.runtime.replay_orchestrator import ReplayExecutionRequest
from glassbox.runtime.replay_orchestrator import ReplayOrchestrator


def _normalized_session(*, status: str = "completed") -> ReplayNormalizedSession:
    return ReplayNormalizedSession(
        transcript=[],
        tool_calls=[],
        approvals=[],
        questions=[],
        event_families=["SessionStarted", "TurnCompleted"],
        final_state=ReplayFinalStateSnapshot(status=status),
    )


def _bundle() -> ReplayBundle:
    return ReplayBundle(
        source_session_id=new_session_id(),
        session_config=SessionConfig(
            model_name="openai:gpt-5.4",
            cwd=Path("/tmp/glassbox"),
            approval_mode="confirm",
        ),
        actions=[],
        model_calls=[],
        tool_requests=[],
        tool_results=[],
        turn_outputs=[],
        baseline=_normalized_session(),
    )


def test_replay_orchestrator_builds_exact_match_result() -> None:
    comparison = ReplayComparisonOutcome(
        source_session_id=new_session_id(),
        baseline=_normalized_session(),
        replay=_normalized_session(),
        mismatches=[],
    )

    result = ReplayOrchestrator()._result_from_comparison(comparison)

    assert result.outcome == "exact_match"
    assert result.message is None
    assert result.triage is not None
    assert result.triage.classification == "exact_match"


def test_replay_orchestrator_builds_behavioral_drift_result() -> None:
    comparison = ReplayComparisonOutcome(
        source_session_id=new_session_id(),
        baseline=_normalized_session(),
        replay=_normalized_session(status="failed"),
        mismatches=["final_state drift"],
    )

    result = ReplayOrchestrator()._result_from_comparison(comparison)

    assert result.outcome == "behavioral_drift"
    assert result.message == "normalized replay drift detected"
    assert result.triage is not None
    assert result.triage.classification == "behavioral_drift"


def test_replay_normalizes_long_run_event_families() -> None:
    session_id = new_session_id()
    task_id = new_task_id()
    turn_id = new_turn_id()
    checkpoint_id = new_task_checkpoint_id()
    normalized = normalize_long_run_events(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=1,
                payload=LongRunPhaseChanged(
                    phase=LongRunPhase.MODEL_CALL,
                    state=LongRunPhaseState.ENTERED,
                    task_id=task_id,
                    turn_id=turn_id,
                    reason="starting provider call",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=2,
                payload=TaskCheckpointCreated(
                    checkpoint_id=checkpoint_id,
                    task_id=task_id,
                    turn_id=turn_id,
                    objective="finish replay normalization",
                    completed_step="added event vocabulary",
                    next_action="compare normalized long-run event",
                    recovery_guidance="resume from checkpoint",
                ),
            ),
        ]
    )

    assert [event.event_type for event in normalized] == [
        "LongRunPhaseChanged",
        "TaskCheckpointCreated",
    ]
    assert normalized[0].phase == "model_call"
    assert normalized[0].status == "entered"
    assert normalized[0].task_id == str(task_id)
    assert normalized[1].checkpoint_id == str(checkpoint_id)
    assert normalized[0].fingerprint != normalized[1].fingerprint


def test_replay_normalizes_changeset_event_families() -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()

    families = normalize_event_families(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=1,
                payload=ChangesetCreated(
                    changeset_id=changeset_id,
                    objective="review local workspace changes",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=2,
                payload=ReviewFeedbackCreated(
                    feedback_id=new_review_feedback_id(),
                    changeset_id=changeset_id,
                    feedback_kind=ReviewFeedbackKind.REVIEWER_QUESTION,
                    summary="Clarify stale verification posture.",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=3,
                payload=ReplayArtifactRecorded(
                    turn_id=new_turn_id(),
                    artifact_id=new_artifact_id(),
                    artifact_kind="replay_baseline",
                    path="replay/baseline.json",
                ),
            ),
        ]
    )

    assert families == ["ChangesetCreated", "ReviewFeedbackCreated"]


def test_replay_canonicalizes_tool_attempt_identifiers() -> None:
    first_attempt = new_tool_attempt_id()
    second_attempt = new_tool_attempt_id()
    first_turn = new_turn_id()
    second_turn = new_turn_id()
    first_tool_call = new_tool_call_id()
    second_tool_call = new_tool_call_id()

    normalized = normalize_long_run_events(
        [
            EventEnvelope(
                session_id=new_session_id(),
                sequence=1,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=first_attempt,
                    status=ToolAttemptStatus.STARTED,
                    turn_id=first_turn,
                    tool_call_id=first_tool_call,
                    tool_name="read_file",
                ),
            ),
            EventEnvelope(
                session_id=new_session_id(),
                sequence=2,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=first_attempt,
                    status=ToolAttemptStatus.SUCCEEDED,
                    turn_id=first_turn,
                    tool_call_id=first_tool_call,
                    tool_name="read_file",
                ),
            ),
            EventEnvelope(
                session_id=new_session_id(),
                sequence=3,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=second_attempt,
                    status=ToolAttemptStatus.STARTED,
                    turn_id=second_turn,
                    tool_call_id=second_tool_call,
                    tool_name="write_file",
                ),
            ),
        ]
    )

    assert [event.tool_attempt_id for event in normalized] == [
        "tool_attempt:0",
        "tool_attempt:0",
        "tool_attempt:1",
    ]
    assert [event.tool_call_id for event in normalized] == [
        "tool_call:0",
        "tool_call:0",
        "tool_call:1",
    ]
    assert [event.turn_id for event in normalized] == ["turn:0", "turn:0", "turn:1"]


def test_replay_mismatch_detection_includes_long_run_events() -> None:
    baseline = _normalized_session()
    replay = baseline.model_copy(
        update={
            "long_run_events": [
                ReplayLongRunEventSnapshot(
                    event_type="LongRunPhaseChanged",
                    status="entered",
                    phase="model_call",
                    fingerprint="different",
                )
            ]
        }
    )

    assert collect_mismatches(baseline, replay) == ["long_run_events drift"]


def test_replay_fingerprints_repository_intelligence_context_by_source() -> None:
    payload = {
        "repository_intelligence": {
            "status": "fresh",
            "schema_version": 1,
            "source_digest": "repo-intel:abc123",
            "sources": [
                {
                    "source_name": "path-to-verification",
                    "source_kind": "verification_recommendation",
                    "freshness": "fresh",
                    "confidence": "medium",
                    "included": True,
                    "provenance": "eval recommend",
                }
            ],
            "items": [
                {
                    "item_kind": "likely_test",
                    "title": "context builder tests",
                    "summary": "Run focused context and prompt tests.",
                    "source_names": ["path-to-verification"],
                    "freshness": "fresh",
                    "confidence": "medium",
                }
            ],
            "excluded_sources": [
                {
                    "source_name": "workspace-memory",
                    "source_kind": "memory_reference",
                    "freshness": "stale",
                    "confidence": "low",
                    "included": False,
                    "limitations": ["stale memory excluded from prompt context"],
                }
            ],
            "additional_item_count": 2,
            "limitations": ["bounded context"],
            "safe_next_actions": ["glassbox repo recommend src/glassbox/runtime"],
        }
    }

    sources = build_replay_enriched_context_sources(payload)

    assert [source.source_name for source in sources] == ["repository_intelligence"]
    assert sources[0].schema_version == 1
    assert sources[0].item_count == 1
    assert sources[0].additional_item_count == 2
    assert "repository intelligence fresh" in (sources[0].summary or "")
    assert fingerprint_replay_enriched_context_payload(payload) != (
        fingerprint_replay_enriched_context_payload({})
    )


@pytest.mark.anyio
async def test_replay_orchestrator_maps_execution_failures_to_replay_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ReplayExecutionRequest(bundle=_bundle())

    async def fake_execute(_request: ReplayExecutionRequest) -> ReplayExecutionOutcome:
        raise ReplayFailure("execution exploded")

    orchestrator = ReplayOrchestrator()
    monkeypatch.setattr(orchestrator, "_execute", fake_execute)

    result = await orchestrator.replay_bundle(request.bundle)

    assert result.outcome == "replay_failure"
    assert result.message == "execution exploded"
    assert result.baseline == request.bundle.baseline
