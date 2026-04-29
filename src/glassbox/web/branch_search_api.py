"""HTTP transport models for branch-search dashboard APIs."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from glassbox.core.models import BranchCandidateRecord
from glassbox.core.models import BranchSearchRecord


class BranchSearchSummaryResponse(BaseModel):
    search_id: str
    session_id: str
    parent_session_id: str
    status: str
    objective: str
    task_id: str | None = None
    selected_candidate_id: str | None = None
    abandoned_reason: str | None = None
    candidate_count: int
    created_at: datetime
    updated_at: datetime
    last_sequence: int


class BranchCandidateResponse(BaseModel):
    search_id: str
    candidate_id: str
    parent_session_id: str
    candidate_session_id: str | None = None
    strategy_label: str
    status: str
    verification_status: str
    selection_state: str | None = None
    verification_summary: str | None = None
    verification_id: str | None = None
    artifact_id: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    patch_summary: str | None = None
    policy_budget_summary: str | None = None
    residual_risks: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_sequence: int


class BranchSearchListPageResponse(BaseModel):
    items: list[BranchSearchSummaryResponse]


class BranchSearchDetailResponse(BaseModel):
    search: BranchSearchSummaryResponse
    candidates: list[BranchCandidateResponse]


class BranchCandidateActionRequest(BaseModel):
    actor: str = "operator"
    reason: str = Field(min_length=1, max_length=2000)


class BranchCandidateActionResponse(BaseModel):
    status: str
    candidate: BranchCandidateResponse


def build_branch_search_summary_response(
    search: BranchSearchRecord,
) -> BranchSearchSummaryResponse:
    return BranchSearchSummaryResponse(
        search_id=str(search.search_id),
        session_id=str(search.session_id),
        parent_session_id=str(search.parent_session_id),
        status=search.status.value,
        objective=search.objective,
        task_id=str(search.task_id) if search.task_id is not None else None,
        selected_candidate_id=(
            str(search.selected_candidate_id)
            if search.selected_candidate_id is not None
            else None
        ),
        abandoned_reason=search.abandoned_reason,
        candidate_count=search.candidate_count,
        created_at=search.created_at,
        updated_at=search.updated_at,
        last_sequence=search.last_sequence,
    )


def build_branch_search_summary_responses(
    searches: Sequence[BranchSearchRecord],
) -> list[BranchSearchSummaryResponse]:
    return [build_branch_search_summary_response(search) for search in searches]


def build_branch_candidate_response(
    candidate: BranchCandidateRecord,
) -> BranchCandidateResponse:
    return BranchCandidateResponse(
        search_id=str(candidate.search_id),
        candidate_id=str(candidate.candidate_id),
        parent_session_id=str(candidate.parent_session_id),
        candidate_session_id=(
            str(candidate.candidate_session_id)
            if candidate.candidate_session_id is not None
            else None
        ),
        strategy_label=candidate.strategy_label,
        status=candidate.status.value,
        verification_status=candidate.verification_status.value,
        selection_state=(
            candidate.selection_state.value
            if candidate.selection_state is not None
            else None
        ),
        verification_summary=candidate.verification_summary,
        verification_id=(
            str(candidate.verification_id)
            if candidate.verification_id is not None
            else None
        ),
        artifact_id=str(candidate.artifact_id)
        if candidate.artifact_id is not None
        else None,
        changed_files=[],
        patch_summary=None,
        policy_budget_summary=(
            "No candidate-specific policy or budget evidence is retained."
        ),
        residual_risks=_candidate_residual_risks(candidate),
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        last_sequence=candidate.last_sequence,
    )


def build_branch_candidate_responses(
    candidates: Sequence[BranchCandidateRecord],
) -> list[BranchCandidateResponse]:
    return [build_branch_candidate_response(candidate) for candidate in candidates]


def _candidate_residual_risks(candidate: BranchCandidateRecord) -> list[str]:
    if candidate.verification_status.value == "passed":
        return ["Selection is metadata only; review candidate session before merging."]
    if candidate.verification_status.value == "not_run":
        return ["Verification has not run for this candidate."]
    return [f"Verification ended {candidate.verification_status.value}."]
