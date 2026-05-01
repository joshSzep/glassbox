"""Tests for bounded branch-search coordination."""

import asyncio
from pathlib import Path

from glassbox.core import AutonomyBudget
from glassbox.core import AutonomyMode
from glassbox.core import BranchCandidateExecuted
from glassbox.core import BranchCandidateId
from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchCandidatesCompared
from glassbox.core import BranchCandidateStatus
from glassbox.core import BranchCandidateVerificationStatus
from glassbox.core import BranchCandidateVerified
from glassbox.core import BranchSearchRecord
from glassbox.core import BranchSearchStatus
from glassbox.core import EventPayload
from glassbox.core import new_branch_candidate_id
from glassbox.core import new_branch_search_id
from glassbox.core import new_session_id
from glassbox.runtime.branch_decision_support import (
    derive_branch_search_decision_support,
)
from glassbox.runtime.branch_search import BranchCandidateExecution
from glassbox.runtime.branch_search import BranchSearchStrategy
from glassbox.runtime.branch_search import run_bounded_branch_search


def test_bounded_branch_search_runs_sequential_candidates() -> None:
    events: list[EventPayload] = []

    async def execute(_strategy, _candidate_id: BranchCandidateId):
        return BranchCandidateExecution(
            candidate_session_id=new_session_id(),
            summary="candidate executed",
            verification_status=BranchCandidateVerificationStatus.PASSED,
            verification_summary="verification passed",
        )

    result = asyncio.run(
        run_bounded_branch_search(
            parent_session_id=new_session_id(),
            objective="Compare repairs",
            strategies=[
                BranchSearchStrategy(label="minimal"),
                BranchSearchStrategy(label="broader"),
            ],
            mode=AutonomyMode.AUTONOMOUS_LOCAL,
            budget=_budget(max_branch_attempts=2),
            max_candidates=2,
            event_sink=events.append,
            execute_strategy=execute,
        )
    )

    assert result.executed_candidate_count == 2
    assert sum(isinstance(event, BranchCandidateExecuted) for event in events) == 2
    assert sum(isinstance(event, BranchCandidateVerified) for event in events) == 2
    assert any(isinstance(event, BranchCandidatesCompared) for event in events)


def test_bounded_branch_search_stops_on_candidate_budget() -> None:
    events: list[EventPayload] = []

    result = asyncio.run(
        run_bounded_branch_search(
            parent_session_id=new_session_id(),
            objective="Compare repairs",
            strategies=[
                BranchSearchStrategy(label="minimal"),
                BranchSearchStrategy(label="broader"),
            ],
            mode=AutonomyMode.GUIDED,
            budget=_budget(max_branch_attempts=1),
            max_candidates=2,
            event_sink=events.append,
            execute_strategy=None,
        )
    )

    assert result.executed_candidate_count == 0
    assert result.budget_exhausted is not None
    assert result.budget_exhausted.limit_name == "branch_attempts"


def test_branch_decision_support_derives_candidate_postures() -> None:
    search_id = new_branch_search_id()
    parent_session_id = new_session_id()
    selected_candidate_id = new_branch_candidate_id()
    review_candidate_id = new_branch_candidate_id()
    created_at = _now()
    search = BranchSearchRecord(
        search_id=search_id,
        session_id=parent_session_id,
        parent_session_id=parent_session_id,
        status=BranchSearchStatus.COMPLETED,
        objective="Compare repair approaches",
        selected_candidate_id=selected_candidate_id,
        candidate_count=2,
        created_at=created_at,
        updated_at=created_at,
        last_sequence=7,
    )
    selected_candidate = BranchCandidateRecord(
        search_id=search_id,
        candidate_id=selected_candidate_id,
        parent_session_id=parent_session_id,
        candidate_session_id=new_session_id(),
        strategy_label="minimal repair",
        status=BranchCandidateStatus.SELECTED,
        selection_state=BranchCandidateStatus.SELECTED,
        verification_status=BranchCandidateVerificationStatus.PASSED,
        verification_summary="Focused tests passed.",
        created_at=created_at,
        updated_at=created_at,
        last_sequence=5,
    )
    review_candidate = BranchCandidateRecord(
        search_id=search_id,
        candidate_id=review_candidate_id,
        parent_session_id=parent_session_id,
        strategy_label="broader rewrite",
        status=BranchCandidateStatus.NEEDS_REVIEW,
        selection_state=BranchCandidateStatus.NEEDS_REVIEW,
        verification_status=BranchCandidateVerificationStatus.NOT_RUN,
        created_at=created_at,
        updated_at=created_at,
        last_sequence=6,
    )

    support = derive_branch_search_decision_support(
        search=search,
        candidates=[selected_candidate, review_candidate],
    )

    assert support.automatic_merge is False
    assert "does not automatically merge" in support.non_goal
    assert support.candidates[0].verification_posture == "strong"
    assert support.candidates[0].risk_posture == "strong"
    assert support.candidates[0].cost_estimate == "low"
    assert support.candidates[0].evidence[0].kind == "session"
    assert support.candidates[1].verification_posture == "unknown"
    assert support.candidates[1].risk_posture == "review"
    assert support.candidates[1].accepted_risks == [
        "candidate has no verification evidence yet"
    ]
    assert (
        support.candidates[1].verification_recommendations[0].source
        == "missing-changed-files"
    )
    assert "Changed-file evidence is not captured" in (
        support.candidates[1].changed_files_summary
    )


def test_branch_decision_support_recommends_eval_commands_for_changed_files() -> None:
    search_id = new_branch_search_id()
    parent_session_id = new_session_id()
    candidate_id = new_branch_candidate_id()
    created_at = _now()
    search = BranchSearchRecord(
        search_id=search_id,
        session_id=parent_session_id,
        parent_session_id=parent_session_id,
        status=BranchSearchStatus.RUNNING,
        objective="Compare dashboard fixes",
        candidate_count=1,
        created_at=created_at,
        updated_at=created_at,
        last_sequence=3,
    )
    candidate = BranchCandidateRecord(
        search_id=search_id,
        candidate_id=candidate_id,
        parent_session_id=parent_session_id,
        candidate_session_id=new_session_id(),
        strategy_label="dashboard repair",
        status=BranchCandidateStatus.FORKED,
        verification_status=BranchCandidateVerificationStatus.NOT_RUN,
        created_at=created_at,
        updated_at=created_at,
        last_sequence=4,
    )

    support = derive_branch_search_decision_support(
        search=search,
        candidates=[candidate],
        workspace_root=Path.cwd(),
        changed_files_by_candidate={
            candidate_id: ["frontend/components/console/branch-search-console.tsx"],
        },
    )

    recommendation = support.candidates[0].verification_recommendations[0]
    assert support.candidates[0].changed_files == [
        "frontend/components/console/branch-search-console.tsx"
    ]
    assert recommendation.source == "changed-files"
    assert "frontend-dashboard" in recommendation.recipe_ids
    assert "pnpm --dir frontend test" in recommendation.commands


def _budget(max_branch_attempts: int) -> AutonomyBudget:
    return AutonomyBudget(
        max_steps=5,
        max_tool_calls=5,
        max_write_operations=0,
        max_command_operations=0,
        max_wall_clock_seconds=60,
        max_verification_attempts=0,
        max_branch_attempts=max_branch_attempts,
        max_artifact_bytes=1024,
        allowed_risk_buckets=["read_only"],
    )


def _now():
    from datetime import UTC
    from datetime import datetime

    return datetime(2026, 1, 1, tzinfo=UTC)
