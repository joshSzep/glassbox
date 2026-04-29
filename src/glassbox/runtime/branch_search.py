"""Read-only branch-search query service."""

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.core import AutonomyBudget
from glassbox.core import AutonomyBudgetUsage
from glassbox.core import AutonomyMode
from glassbox.core import BranchCandidateExecuted
from glassbox.core import BranchCandidateForked
from glassbox.core import BranchCandidateId
from glassbox.core import BranchCandidatePlanned
from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchCandidatesCompared
from glassbox.core import BranchCandidateVerificationStatus
from glassbox.core import BranchCandidateVerified
from glassbox.core import BranchSearchId
from glassbox.core import BranchSearchRecord
from glassbox.core import BranchSearchStarted
from glassbox.core import BudgetExhausted
from glassbox.core import EventPayload
from glassbox.core import SessionId
from glassbox.core import TaskId
from glassbox.core import new_branch_candidate_id
from glassbox.core import new_branch_search_id
from glassbox.runtime.budgeting import evaluate_budget


class BranchSearchRepository(Protocol):
    """Repository methods required by branch-search queries."""

    def list_branch_searches(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
    ) -> list[BranchSearchRecord]: ...

    def get_branch_search(
        self,
        search_id: BranchSearchId,
    ) -> BranchSearchRecord | None: ...

    def list_branch_candidates(
        self,
        session_id: SessionId,
        search_id: BranchSearchId,
    ) -> list[BranchCandidateRecord]: ...


class BranchSearchDetail(BaseModel):
    """Branch search plus candidate comparison rows."""

    model_config = ConfigDict(extra="forbid")

    search: BranchSearchRecord
    candidates: list[BranchCandidateRecord]


@dataclass(frozen=True, slots=True)
class BranchSearchStrategy:
    """One bounded candidate strategy for branch search."""

    label: str


@dataclass(frozen=True, slots=True)
class BranchCandidateExecution:
    """Result produced by one branch-search strategy callback."""

    candidate_session_id: SessionId | None
    summary: str
    verification_status: BranchCandidateVerificationStatus
    verification_summary: str


@dataclass(frozen=True, slots=True)
class BranchSearchRunResult:
    """Summary of one bounded branch-search coordinator run."""

    search_id: BranchSearchId
    planned_candidate_count: int
    executed_candidate_count: int
    usage: AutonomyBudgetUsage
    budget_exhausted: BudgetExhausted | None = None


BranchSearchEventSink = Callable[[EventPayload], None]
BranchStrategyExecutor = Callable[
    [BranchSearchStrategy, BranchCandidateId],
    Awaitable[BranchCandidateExecution],
]


class BranchSearchQueryService:
    """Read-only service for branch-search CLI and API surfaces."""

    def __init__(self, repository: BranchSearchRepository) -> None:
        self._repository = repository

    def list_searches(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
    ) -> list[BranchSearchRecord]:
        return self._repository.list_branch_searches(
            session_id=session_id,
            limit=limit,
        )

    def get_detail(self, search_id: BranchSearchId) -> BranchSearchDetail:
        search = self._repository.get_branch_search(search_id)
        if search is None:
            raise ValueError(f"unknown branch search: {search_id}")
        return BranchSearchDetail(
            search=search,
            candidates=self._repository.list_branch_candidates(
                search.session_id,
                search.search_id,
            ),
        )


async def run_bounded_branch_search(
    *,
    parent_session_id: SessionId,
    objective: str,
    strategies: list[BranchSearchStrategy],
    mode: AutonomyMode,
    budget: AutonomyBudget,
    current_usage: AutonomyBudgetUsage | None = None,
    max_candidates: int = 2,
    task_id: TaskId | None = None,
    search_id: BranchSearchId | None = None,
    event_sink: BranchSearchEventSink | None = None,
    execute_strategy: BranchStrategyExecutor | None = None,
) -> BranchSearchRunResult:
    """Run a sequential bounded branch search without merging candidates."""

    emit = event_sink or _ignore_event
    usage = current_usage or AutonomyBudgetUsage()
    resolved_search_id = search_id or new_branch_search_id()
    selected_strategies = strategies[:max_candidates]
    emit(
        BranchSearchStarted(
            search_id=resolved_search_id,
            parent_session_id=parent_session_id,
            objective=objective,
            task_id=task_id,
            max_candidates=max_candidates,
        )
    )
    executed_count = 0
    for strategy in selected_strategies:
        budget_decision = evaluate_budget(
            budget,
            usage,
            AutonomyBudgetUsage(branch_attempts=1, tool_calls=1),
        )
        emit(
            budget_decision.decision_event(
                scope="task" if task_id is not None else "session",
                mode=mode,
                budget=budget,
                task_id=task_id,
            )
        )
        if not budget_decision.allowed:
            exhausted = budget_decision.exhausted_event(
                scope="task" if task_id is not None else "session",
                task_id=task_id,
            )
            if exhausted is not None:
                emit(exhausted)
            return BranchSearchRunResult(
                search_id=resolved_search_id,
                planned_candidate_count=len(selected_strategies),
                executed_candidate_count=executed_count,
                usage=budget_decision.usage,
                budget_exhausted=exhausted,
            )
        usage = budget_decision.usage
        candidate_id = new_branch_candidate_id()
        emit(
            BranchCandidatePlanned(
                search_id=resolved_search_id,
                candidate_id=candidate_id,
                strategy_label=strategy.label,
            )
        )
        if execute_strategy is None:
            continue
        execution = await execute_strategy(strategy, candidate_id)
        if execution.candidate_session_id is not None:
            emit(
                BranchCandidateForked(
                    search_id=resolved_search_id,
                    candidate_id=candidate_id,
                    candidate_session_id=execution.candidate_session_id,
                )
            )
        emit(
            BranchCandidateExecuted(
                search_id=resolved_search_id,
                candidate_id=candidate_id,
                summary=execution.summary,
            )
        )
        emit(
            BranchCandidateVerified(
                search_id=resolved_search_id,
                candidate_id=candidate_id,
                verification_status=execution.verification_status,
                summary=execution.verification_summary,
            )
        )
        executed_count += 1
    emit(
        BranchCandidatesCompared(
            search_id=resolved_search_id,
            summary=(
                f"Compared {executed_count} executed candidate(s) "
                f"from {len(selected_strategies)} planned strategy/strategies."
            ),
        )
    )
    return BranchSearchRunResult(
        search_id=resolved_search_id,
        planned_candidate_count=len(selected_strategies),
        executed_candidate_count=executed_count,
        usage=usage,
    )


def _ignore_event(_event: EventPayload) -> None:
    return None


__all__ = [
    "BranchCandidateExecution",
    "BranchSearchEventSink",
    "BranchSearchDetail",
    "BranchSearchQueryService",
    "BranchSearchRepository",
    "BranchSearchRunResult",
    "BranchSearchStrategy",
    "BranchStrategyExecutor",
    "run_bounded_branch_search",
]
