"""Focused orchestration tests for replay bundle loading and result mapping."""

from pathlib import Path

import pytest

from glassbox.core import SessionConfig
from glassbox.core import new_session_id
from glassbox.runtime.replay_failures import ReplayFailure
from glassbox.runtime.replay_models import ReplayBundle
from glassbox.runtime.replay_models import ReplayFinalStateSnapshot
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
