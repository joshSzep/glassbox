"""FastAPI routes for local repository intelligence."""

from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.core.types import BackgroundJobKind
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.repository_index import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.repository_index import get_repository_index_entry
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.repository_index import search_repository_index
from glassbox.web.app import RuntimeContextDep
from glassbox.web.repository_index_api import RepositoryIndexEntryDetailResponse
from glassbox.web.repository_index_api import RepositoryIndexRebuildRequest
from glassbox.web.repository_index_api import RepositoryIndexRebuildResponse
from glassbox.web.repository_index_api import RepositoryIndexSearchPageResponse
from glassbox.web.repository_index_api import RepositoryIndexStatusResponse
from glassbox.web.repository_index_api import build_repository_index_entry_response
from glassbox.web.repository_index_api import build_repository_index_entry_responses
from glassbox.web.repository_index_api import build_repository_index_status_response
from glassbox.web.session_api import PageInfoResponse
from glassbox.web.task_api import build_background_job_response

router = APIRouter(prefix="/repo/index", tags=["repo"])


@router.get("/status", response_model=RepositoryIndexStatusResponse)
def get_repository_index_status(
    context: RuntimeContextDep,
) -> RepositoryIndexStatusResponse:
    """Return repository index freshness and size."""

    workspace_root = context.infrastructure.artifacts_root
    path = repository_index_path(workspace_root)
    try:
        snapshot = load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError:
        return RepositoryIndexStatusResponse(
            status="missing",
            path=str(path),
            entry_count=0,
            detail="repository index has not been built",
        )
    return build_repository_index_status_response(snapshot, path=str(path))


@router.get("/search", response_model=RepositoryIndexSearchPageResponse)
def search_repository_index_entries(
    context: RuntimeContextDep,
    query: str = Query(min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
) -> RepositoryIndexSearchPageResponse:
    """Search repository index entries by text."""

    try:
        entries = search_repository_index(
            context.infrastructure.artifacts_root,
            query,
            limit=limit,
        )
    except RepositoryIndexNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return RepositoryIndexSearchPageResponse(
        query=query,
        page=PageInfoResponse(
            cursor=0,
            limit=limit,
            next_cursor=None,
            has_more=False,
            returned_count=len(entries),
        ),
        items=build_repository_index_entry_responses(entries),
    )


@router.get("/entries/{entry_id}", response_model=RepositoryIndexEntryDetailResponse)
def get_repository_index_entry_detail(
    context: RuntimeContextDep,
    entry_id: str,
) -> RepositoryIndexEntryDetailResponse:
    """Return one repository index entry by stable ID."""

    try:
        entry = get_repository_index_entry(
            context.infrastructure.artifacts_root,
            entry_id,
        )
    except RepositoryIndexNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except KeyError as error:
        raise HTTPException(
            status_code=404, detail=f"unknown repository index entry: {entry_id}"
        ) from error
    return RepositoryIndexEntryDetailResponse(
        entry=build_repository_index_entry_response(entry),
    )


@router.post("/rebuild", response_model=RepositoryIndexRebuildResponse)
def rebuild_repository_index(
    request: RepositoryIndexRebuildRequest,
    context: RuntimeContextDep,
) -> RepositoryIndexRebuildResponse:
    """Refresh repository intelligence directly or queue a daemon job."""

    workspace_root = context.infrastructure.artifacts_root
    owner_status = inspect_runtime_owner(workspace_root)
    if (
        request.background
        and owner_status.state == "running"
        and request.session_id is not None
    ):
        job = context.repositories.sessions.enqueue_background_job(
            UUID(request.session_id),
            kind=BackgroundJobKind.DERIVED_INDEX,
            job_type="repository-index-refresh",
            title="Refresh repository intelligence index",
            payload={"index_path": str(repository_index_path(workspace_root))},
            requested_by=request.requested_by,
        )
        return RepositoryIndexRebuildResponse(
            mode="background",
            status="queued",
            job=build_background_job_response(job),
        )

    snapshot = build_and_write_repository_index(workspace_root)
    return RepositoryIndexRebuildResponse(
        mode="synchronous",
        status=snapshot.status.value,
        index=build_repository_index_status_response(
            snapshot,
            path=str(repository_index_path(workspace_root)),
        ),
        detail=(
            "daemon job not queued because no running daemon session anchor "
            "was supplied"
            if request.background and owner_status.state == "running"
            else None
        ),
    )
