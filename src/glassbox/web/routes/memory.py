"""Workspace-memory inspection API routes."""

from typing import Annotated
from typing import cast
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemoryState
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureRepository
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureService
from glassbox.web.app import RuntimeContextDep
from glassbox.web.memory_api import WorkspaceMemoryActionRequest
from glassbox.web.memory_api import WorkspaceMemoryAddRequest
from glassbox.web.memory_api import WorkspaceMemoryCandidateDecisionRequest
from glassbox.web.memory_api import WorkspaceMemoryCandidateListPageResponse
from glassbox.web.memory_api import WorkspaceMemoryCandidateRejectedResponse
from glassbox.web.memory_api import WorkspaceMemoryDetailResponse
from glassbox.web.memory_api import WorkspaceMemoryListPageResponse
from glassbox.web.memory_api import WorkspaceMemoryPrunePreviewResponse
from glassbox.web.memory_api import build_workspace_memory_candidate_response
from glassbox.web.memory_api import build_workspace_memory_candidate_responses
from glassbox.web.memory_api import build_workspace_memory_entry_response
from glassbox.web.memory_api import build_workspace_memory_entry_responses
from glassbox.web.session_api import ErrorDetailResponse
from glassbox.web.session_api import PageInfoResponse

router = APIRouter(prefix="/memory")

PageCursorParam = Annotated[int, Query(ge=0)]
PageLimitParam = Annotated[int, Query(ge=1, le=500)]
MemoryStateParam = Annotated[WorkspaceMemoryState | None, Query()]
MemoryKindParam = Annotated[WorkspaceMemoryKind | None, Query()]


@router.get("", response_model=WorkspaceMemoryListPageResponse)
async def list_workspace_memory_page(
    context: RuntimeContextDep,
    state: MemoryStateParam = None,
    kind: MemoryKindParam = None,
    query: str | None = None,
    include_pruned: bool = False,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> WorkspaceMemoryListPageResponse:
    """Return a bounded page of projected workspace memory entries."""

    rows = context.repositories.sessions.list_workspace_memory(
        state=state,
        kind=kind,
        query_text=query,
        include_pruned=include_pruned,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return WorkspaceMemoryListPageResponse(
        page=PageInfoResponse(
            cursor=cursor,
            limit=limit,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            returned_count=len(items),
        ),
        items=build_workspace_memory_entry_responses(items),
    )


@router.post("", response_model=WorkspaceMemoryDetailResponse)
async def add_workspace_memory(
    request: WorkspaceMemoryAddRequest,
    context: RuntimeContextDep,
) -> WorkspaceMemoryDetailResponse:
    """Create and immediately confirm an operator-provided memory entry."""

    try:
        entry = WorkspaceMemoryCaptureService(
            cast(WorkspaceMemoryCaptureRepository, context.repositories.sessions)
        ).add_operator_memory(
            UUID(request.session_id),
            kind=WorkspaceMemoryKind(request.kind),
            content=request.content,
            summary=request.summary,
            source_label=request.source_label,
            tags=request.tags,
            confirmed_by=request.confirmed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WorkspaceMemoryDetailResponse(
        entry=build_workspace_memory_entry_response(entry)
    )


@router.get("/candidates", response_model=WorkspaceMemoryCandidateListPageResponse)
async def list_workspace_memory_candidates(
    context: RuntimeContextDep,
    session_id: UUID,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> WorkspaceMemoryCandidateListPageResponse:
    """Return operator-reviewable memory candidates for one session."""

    try:
        rows = WorkspaceMemoryCaptureService(
            cast(WorkspaceMemoryCaptureRepository, context.repositories.sessions)
        ).list_candidates(session_id, limit=cursor + limit + 1)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    page_rows = rows[cursor : cursor + limit + 1]
    items = page_rows[:limit]
    next_cursor = cursor + len(items) if len(page_rows) > limit else None
    return WorkspaceMemoryCandidateListPageResponse(
        session_id=str(session_id),
        page=PageInfoResponse(
            cursor=cursor,
            limit=limit,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            returned_count=len(items),
        ),
        items=build_workspace_memory_candidate_responses(items),
    )


@router.post(
    "/candidates/{candidate_id}/confirm",
    response_model=WorkspaceMemoryDetailResponse,
)
async def confirm_workspace_memory_candidate(
    candidate_id: str,
    request: WorkspaceMemoryCandidateDecisionRequest,
    context: RuntimeContextDep,
) -> WorkspaceMemoryDetailResponse:
    """Create confirmed memory from one generated candidate."""

    try:
        entry = WorkspaceMemoryCaptureService(
            cast(WorkspaceMemoryCaptureRepository, context.repositories.sessions)
        ).confirm_candidate(
            UUID(request.session_id),
            candidate_id,
            confirmed_by=request.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WorkspaceMemoryDetailResponse(
        entry=build_workspace_memory_entry_response(entry)
    )


@router.post(
    "/candidates/{candidate_id}/reject",
    response_model=WorkspaceMemoryCandidateRejectedResponse,
)
async def reject_workspace_memory_candidate(
    candidate_id: str,
    request: WorkspaceMemoryCandidateDecisionRequest,
    context: RuntimeContextDep,
) -> WorkspaceMemoryCandidateRejectedResponse:
    """Record explicit operator rejection for one generated candidate."""

    if request.reason is None or not request.reason.strip():
        raise HTTPException(status_code=400, detail="rejection reason is required")
    try:
        candidate = WorkspaceMemoryCaptureService(
            cast(WorkspaceMemoryCaptureRepository, context.repositories.sessions)
        ).reject_candidate(
            UUID(request.session_id),
            candidate_id,
            rejected_by=request.actor,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WorkspaceMemoryCandidateRejectedResponse(
        candidate=build_workspace_memory_candidate_response(candidate),
        rejected_by=request.actor,
        reason=request.reason,
    )


@router.get(
    "/{memory_id}",
    response_model=WorkspaceMemoryDetailResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_workspace_memory_detail(
    memory_id: UUID,
    context: RuntimeContextDep,
) -> WorkspaceMemoryDetailResponse:
    """Return one projected workspace memory entry."""

    entry = context.repositories.sessions.get_workspace_memory(memory_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"workspace memory {memory_id} not found",
        )
    return WorkspaceMemoryDetailResponse(
        entry=build_workspace_memory_entry_response(entry)
    )


@router.post(
    "/{memory_id}/confirm",
    response_model=WorkspaceMemoryDetailResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def confirm_workspace_memory(
    memory_id: UUID,
    request: WorkspaceMemoryActionRequest,
    context: RuntimeContextDep,
) -> WorkspaceMemoryDetailResponse:
    """Confirm or refresh confirmation evidence for one memory entry."""

    try:
        entry = context.repositories.sessions.confirm_workspace_memory(
            memory_id,
            confirmed_by=request.actor,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WorkspaceMemoryDetailResponse(
        entry=build_workspace_memory_entry_response(entry)
    )


@router.post(
    "/{memory_id}/invalidate",
    response_model=WorkspaceMemoryDetailResponse,
    responses={
        400: {"model": ErrorDetailResponse},
        404: {"model": ErrorDetailResponse},
    },
)
async def invalidate_workspace_memory(
    memory_id: UUID,
    request: WorkspaceMemoryActionRequest,
    context: RuntimeContextDep,
) -> WorkspaceMemoryDetailResponse:
    """Invalidate one memory entry while keeping it inspectable."""

    reason = _required_reason(request.reason, "invalidation reason is required")
    try:
        entry = context.repositories.sessions.invalidate_workspace_memory(
            memory_id,
            invalidated_by=request.actor,
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WorkspaceMemoryDetailResponse(
        entry=build_workspace_memory_entry_response(entry)
    )


@router.post(
    "/{memory_id}/prune-preview",
    response_model=WorkspaceMemoryPrunePreviewResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def preview_workspace_memory_prune(
    memory_id: UUID,
    request: WorkspaceMemoryActionRequest,
    context: RuntimeContextDep,
) -> WorkspaceMemoryPrunePreviewResponse:
    """Preview a prune action without mutating canonical memory events."""

    entry = context.repositories.sessions.get_workspace_memory(memory_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"workspace memory {memory_id} not found",
        )
    return WorkspaceMemoryPrunePreviewResponse(
        entry=build_workspace_memory_entry_response(entry),
        would_prune=entry.pruned_at is None,
        reason=request.reason,
    )


@router.post(
    "/{memory_id}/prune",
    response_model=WorkspaceMemoryDetailResponse,
    responses={
        400: {"model": ErrorDetailResponse},
        404: {"model": ErrorDetailResponse},
    },
)
async def prune_workspace_memory(
    memory_id: UUID,
    request: WorkspaceMemoryActionRequest,
    context: RuntimeContextDep,
) -> WorkspaceMemoryDetailResponse:
    """Prune one memory entry from active retrieval while preserving history."""

    reason = _required_reason(request.reason, "prune reason is required")
    try:
        entry = context.repositories.sessions.prune_workspace_memory(
            memory_id,
            pruned_by=request.actor,
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WorkspaceMemoryDetailResponse(
        entry=build_workspace_memory_entry_response(entry)
    )


def _required_reason(value: str | None, message: str) -> str:
    if value is None or not value.strip():
        raise HTTPException(status_code=400, detail=message)
    return value.strip()
