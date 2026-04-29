"""Branch-search observability collector."""

from typing import cast

from glassbox.core.types import BranchCandidateVerificationStatus
from glassbox.core.types import BranchSearchStatus
from glassbox.runtime.branch_search import BranchSearchRepository
from glassbox.runtime.observability_models import BranchSearchObservability
from glassbox.services import SessionRepository


def build_branch_search_observability(
    session_repository: SessionRepository,
) -> BranchSearchObservability:
    branch_repository = cast(BranchSearchRepository, session_repository)
    searches = branch_repository.list_branch_searches()
    active_searches = [
        search
        for search in searches
        if search.status in {BranchSearchStatus.STARTED, BranchSearchStatus.RUNNING}
    ]
    completed_count = sum(
        1 for search in searches if search.status == BranchSearchStatus.COMPLETED
    )
    abandoned_count = sum(
        1 for search in searches if search.status == BranchSearchStatus.ABANDONED
    )
    needs_review_count = 0
    failed_verification_count = 0
    selected_count = 0
    latest_needs_review_search_id: str | None = None
    for search in searches:
        candidates = branch_repository.list_branch_candidates(
            search.session_id,
            search.search_id,
        )
        for candidate in candidates:
            if candidate.status.value == "needs_review":
                needs_review_count += 1
                latest_needs_review_search_id = str(search.search_id)
            if candidate.verification_status in {
                BranchCandidateVerificationStatus.FAILED,
                BranchCandidateVerificationStatus.BLOCKED,
                BranchCandidateVerificationStatus.TIMED_OUT,
            }:
                failed_verification_count += 1
            if candidate.selection_state is not None:
                selected_count += int(candidate.selection_state.value == "selected")

    latest_search = max(searches, key=lambda search: search.updated_at, default=None)
    next_actions: list[str] = []
    if active_searches:
        next_actions.append("glassbox branch-search list")
    if latest_needs_review_search_id is not None:
        next_actions.append(
            f"glassbox branch-search show {latest_needs_review_search_id}"
        )
        next_actions.append(
            "glassbox branch-search reject SEARCH_ID CANDIDATE_ID --reason 'cleanup'"
        )
    if failed_verification_count:
        next_actions.append("glassbox branch-search list")

    return BranchSearchObservability(
        search_count=len(searches),
        active_count=len(active_searches),
        completed_count=completed_count,
        abandoned_count=abandoned_count,
        needs_review_count=needs_review_count,
        failed_verification_count=failed_verification_count,
        selected_count=selected_count,
        latest_search_id=str(latest_search.search_id) if latest_search else None,
        latest_needs_review_search_id=latest_needs_review_search_id,
        next_actions=_dedupe(next_actions),
    )


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


__all__ = ["build_branch_search_observability"]
