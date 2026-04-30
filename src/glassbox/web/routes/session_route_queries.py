"""HTTP-local read helpers for session routes."""

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException

from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import ToolArtifactRecorded
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.daemon import RuntimeOwnerStatus
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.observability import build_background_job_observability
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.runtime.session_queries import OPERATOR_SORT_PRIORITY
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import WorkspaceRuntimeSummaryView
from glassbox.services import SessionRepository
from glassbox.web.routes.pagination import page_info
from glassbox.web.session_api import ArtifactDetailResponse
from glassbox.web.session_api import ContextCompactionResponse
from glassbox.web.session_api import EventLogEntryResponse
from glassbox.web.session_api import SessionAggregateResponse
from glassbox.web.session_api import SessionArtifactPageResponse
from glassbox.web.session_api import SessionCheckpointPageResponse
from glassbox.web.session_api import SessionCompactionPageResponse
from glassbox.web.session_api import SessionEventLogPageResponse
from glassbox.web.session_api import SessionSnapshotResponse
from glassbox.web.session_api import SessionSummaryResponse
from glassbox.web.session_api import SessionToolCallPageResponse
from glassbox.web.session_api import SessionTranscriptPageResponse
from glassbox.web.session_api import SessionTurnMetricsPageResponse
from glassbox.web.session_api import TaskCheckpointResponse
from glassbox.web.session_api import ToolCallResponse
from glassbox.web.session_api import TranscriptMessageResponse
from glassbox.web.session_api import TurnMetricsResponse
from glassbox.web.session_api import build_provider_evidence_summary_response
from glassbox.web.session_api import build_session_aggregate_response
from glassbox.web.session_api import build_session_snapshot_response
from glassbox.web.session_api import build_session_summary_responses


def session_query_service(context: RuntimeContext) -> SessionQueryService:
    return SessionQueryService(
        context.repositories.sessions,
        context.repositories.artifacts,
    )


def ensure_session_exists(session_id: UUID, context: RuntimeContext) -> None:
    if context.repositories.sessions.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")


def list_session_summary_responses(
    context: RuntimeContext,
) -> list[SessionSummaryResponse]:
    query_service = session_query_service(context)
    return build_session_summary_responses(query_service.list_session_summaries())


def get_session_aggregate_response(
    context: RuntimeContext,
    *,
    queue: str | None,
    status: str | None,
    sort: str = OPERATOR_SORT_PRIORITY,
    limit: int | None = None,
    owner_status: RuntimeOwnerStatus | None = None,
) -> SessionAggregateResponse:
    query_service = session_query_service(context)
    workspace_root = context.infrastructure.artifacts_root
    owner_status = owner_status or inspect_runtime_owner(workspace_root)
    aggregate = query_service.get_session_aggregate(
        runtime=build_workspace_runtime_summary(
            workspace_root,
            owner_status,
            context.repositories.sessions,
        ),
        queue=queue,
        status=status,
        sort=sort,
        limit=limit,
    )
    response = build_session_aggregate_response(aggregate)
    response.provider_evidence = build_provider_evidence_summary_response(
        load_provider_canary_evidence(workspace_root)
    )
    return response


def get_session_transcript_response(
    session_id: UUID,
    context: RuntimeContext,
    *,
    cursor: int,
    limit: int,
) -> SessionTranscriptPageResponse:
    ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.list_transcript_messages(
        session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return SessionTranscriptPageResponse(
        session_id=str(session_id),
        page=page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            TranscriptMessageResponse.model_validate(item.model_dump(mode="json"))
            for item in items
        ],
    )


def get_session_event_log_response(
    session_id: UUID,
    context: RuntimeContext,
    *,
    cursor: int,
    limit: int,
) -> SessionEventLogPageResponse:
    ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.read_session_events_after(
        session_id,
        cursor,
        limit=limit + 1,
    )
    items = rows[:limit]
    next_cursor = items[-1].sequence if len(rows) > limit and items else None
    return SessionEventLogPageResponse(
        session_id=str(session_id),
        page=page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            EventLogEntryResponse(
                event_id=str(event.event_id),
                session_id=str(event.session_id),
                sequence=event.sequence,
                event_type=event.event_type,
                event_version=event.event_version,
                created_at=event.created_at,
                payload=event.payload.model_dump(mode="json"),
            )
            for event in items
        ],
    )


def get_session_tool_call_response(
    session_id: UUID,
    context: RuntimeContext,
    *,
    cursor: int,
    limit: int,
) -> SessionToolCallPageResponse:
    ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.list_tool_calls(
        session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return SessionToolCallPageResponse(
        session_id=str(session_id),
        page=page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            ToolCallResponse.model_validate(item.model_dump(mode="json"))
            for item in items
        ],
    )


def get_session_turn_metrics_response(
    session_id: UUID,
    context: RuntimeContext,
    *,
    cursor: int,
    limit: int,
) -> SessionTurnMetricsPageResponse:
    ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.list_turn_metrics(
        session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return SessionTurnMetricsPageResponse(
        session_id=str(session_id),
        page=page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            TurnMetricsResponse.model_validate(item.model_dump(mode="json"))
            for item in items
        ],
    )


def get_session_checkpoint_response(
    session_id: UUID,
    context: RuntimeContext,
    *,
    cursor: int,
    limit: int,
) -> SessionCheckpointPageResponse:
    ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.list_task_checkpoints(
        session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return SessionCheckpointPageResponse(
        session_id=str(session_id),
        page=page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            TaskCheckpointResponse.model_validate(item.model_dump(mode="json"))
            for item in items
        ],
    )


def get_session_compaction_response(
    session_id: UUID,
    context: RuntimeContext,
    *,
    cursor: int,
    limit: int,
) -> SessionCompactionPageResponse:
    ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.list_context_compactions(
        session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return SessionCompactionPageResponse(
        session_id=str(session_id),
        page=page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            ContextCompactionResponse.model_validate(item.model_dump(mode="json"))
            for item in items
        ],
    )


def get_session_artifact_response(
    session_id: UUID,
    context: RuntimeContext,
    *,
    cursor: int,
    limit: int,
) -> SessionArtifactPageResponse:
    ensure_session_exists(session_id, context)
    artifacts = [
        artifact_detail_from_event(event)
        for event in context.repositories.sessions.read_session_events(session_id)
        if isinstance(event.payload, ToolArtifactRecorded | ReplayArtifactRecorded)
    ]
    items = artifacts[cursor : cursor + limit]
    next_cursor = cursor + len(items) if cursor + limit < len(artifacts) else None
    return SessionArtifactPageResponse(
        session_id=str(session_id),
        page=page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=items,
    )


def get_session_snapshot_response(
    session_id: UUID,
    context: RuntimeContext,
) -> SessionSnapshotResponse:
    query_service = session_query_service(context)
    try:
        snapshot = query_service.get_session_snapshot(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return build_session_snapshot_response(snapshot)


def artifact_detail_from_event(event) -> ArtifactDetailResponse:
    payload = event.payload
    return ArtifactDetailResponse(
        sequence=event.sequence,
        event_type=event.event_type,
        artifact_id=str(payload.artifact_id),
        artifact_kind=payload.artifact_kind,
        path=payload.path,
        tool_call_id=str(payload.tool_call_id) if payload.tool_call_id else None,
        turn_id=str(payload.turn_id),
        content_sha256=payload.content_sha256,
        size_bytes=payload.size_bytes,
    )


def build_workspace_runtime_summary(
    workspace_root: Path,
    owner_status: RuntimeOwnerStatus,
    session_repository: SessionRepository,
) -> WorkspaceRuntimeSummaryView:
    record = owner_status.record
    dashboard_url = record.dashboard_url if record is not None else None
    background_jobs = build_background_job_observability(session_repository)
    return WorkspaceRuntimeSummaryView(
        workspace_root=str(workspace_root),
        state=owner_status.state,
        health=owner_status.health,
        pid=record.pid if record is not None else None,
        dashboard_url=dashboard_url,
        health_url=(dashboard_url.rstrip("/") + "/healthz") if dashboard_url else None,
        session_index_url=dashboard_url,
        started_at=record.started_at if record is not None else None,
        background_job_failed_count=background_jobs.failed_count,
        background_job_retryable_count=background_jobs.retryable_count,
        background_job_abandoned_count=background_jobs.abandoned_count,
    )
