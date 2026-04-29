"""Tests for bounded branch-search coordination."""

import asyncio

from glassbox.core import AutonomyBudget
from glassbox.core import AutonomyMode
from glassbox.core import BranchCandidateExecuted
from glassbox.core import BranchCandidateId
from glassbox.core import BranchCandidatesCompared
from glassbox.core import BranchCandidateVerificationStatus
from glassbox.core import BranchCandidateVerified
from glassbox.core import EventPayload
from glassbox.core import new_session_id
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
