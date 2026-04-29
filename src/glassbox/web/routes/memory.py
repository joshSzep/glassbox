"""Workspace-memory inspection API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemoryState
from glassbox.web.app import RuntimeContextDep
from glassbox.web.memory_api import WorkspaceMemoryDetailResponse
from glassbox.web.memory_api import WorkspaceMemoryListPageResponse
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
