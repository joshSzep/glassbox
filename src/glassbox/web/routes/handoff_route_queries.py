"""Read-only query orchestration for handoff routes."""

from typing import Any
from typing import cast
from uuid import UUID

from glassbox.core import HandoffIntent
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.handoff_guidance import load_handoff_guidance
from glassbox.runtime.handoff_readiness import ChangesetHandoffReadinessService
from glassbox.runtime.handoff_readiness import preview_handoff_readiness
from glassbox.runtime.handoff_source_resolution import resolve_handoff_source
from glassbox.runtime.observability import build_workspace_observability_report
from glassbox.runtime.session_handoff_readiness import SessionHandoffReadinessService
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.task_handoff_readiness import TaskHandoffReadinessService
from glassbox.runtime.task_queries import TaskQueryService
from glassbox.runtime.workspace_handoff_readiness import (
    derive_release_handoff_readiness,
)
from glassbox.runtime.workspace_handoff_readiness import (
    derive_workspace_handoff_readiness,
)
from glassbox.web.handoff_api import HandoffGuidanceResponse
from glassbox.web.handoff_api import HandoffListResponse
from glassbox.web.handoff_api import HandoffReadinessUnifiedResponse
from glassbox.web.handoff_api import HandoffRecordResponse
from glassbox.web.handoff_api import build_handoff_guidance_response
from glassbox.web.handoff_api import build_handoff_list_response
from glassbox.web.handoff_api import build_handoff_readiness_response
from glassbox.web.handoff_api import build_handoff_record_response
from glassbox.web.routes.handoff_route_errors import handoff_bad_request
from glassbox.web.routes.handoff_route_errors import handoff_not_found
from glassbox.web.routes.handoff_route_errors import require_handoff_record


def list_handoff_records_response(
    context: RuntimeContext,
    *,
    session_id: UUID | None,
    include_archived: bool,
    limit: int | None,
) -> HandoffListResponse:
    """Return projected handoff records for local custody inspection."""

    repository = cast(Any, context.repositories.sessions)
    records = repository.list_handoffs(
        session_id=session_id,
        include_archived=include_archived,
        limit=limit,
    )
    return build_handoff_list_response(records)


def handoff_record_response(record) -> HandoffRecordResponse:
    """Build the route response for one projected handoff record."""

    return build_handoff_record_response(record)


def get_handoff_record_response(
    context: RuntimeContext,
    session_id: UUID,
    package_id: str,
) -> HandoffRecordResponse:
    """Return one projected handoff record."""

    return handoff_record_response(
        require_handoff_record(context, session_id, package_id)
    )


def get_handoff_guidance_response(
    context: RuntimeContext,
    session_id: UUID,
    package_id: str,
) -> HandoffGuidanceResponse:
    """Return advisory fork-or-continue guidance for one imported handoff."""

    repository = cast(Any, context.repositories.sessions)
    try:
        guidance = load_handoff_guidance(repository, session_id, package_id)
    except ValueError as exc:
        raise handoff_not_found() from exc
    return build_handoff_guidance_response(guidance)


def get_handoff_readiness_response(
    context: RuntimeContext,
    *,
    source_kind: str,
    source_id: str | None,
    intent: HandoffIntent | None,
) -> HandoffReadinessUnifiedResponse:
    """Return shared v17 handoff readiness for a local source."""

    workspace_root = context.infrastructure.artifacts_root
    try:
        source = resolve_handoff_source(source_kind, source_id)
        if source.source_kind == "session":
            readiness = SessionHandoffReadinessService(
                SessionQueryService(
                    context.repositories.sessions,
                    context.repositories.artifacts,
                )
            ).preview(
                UUID(source.require_source_id()),
                intent=intent or HandoffIntent.REVIEW_ONLY,
            )
        elif source.source_kind == "task":
            readiness = TaskHandoffReadinessService(
                TaskQueryService(
                    cast(Any, context.repositories.sessions),
                    workspace_root=workspace_root,
                )
            ).preview(
                UUID(source.require_source_id()),
                intent=intent or HandoffIntent.CONTINUE_WORK,
            )
        elif source.source_kind == "changeset":
            assessment = preview_handoff_readiness(
                ChangesetHandoffReadinessService(
                    cast(ChangesetRepository, context.repositories.sessions),
                    context.repositories.artifacts,
                ),
                UUID(source.require_source_id()),
                workspace_root,
            )
            readiness = assessment.shared_readiness
        elif source.source_kind in {"workspace", "release"}:
            report = build_workspace_observability_report(
                workspace_root=workspace_root,
                runtime_status=inspect_runtime_owner(workspace_root),
                session_repository=context.repositories.sessions,
                event_transport_stats=context.infrastructure.event_transport.stats(),
            )
            if source.source_kind == "release":
                readiness = derive_release_handoff_readiness(
                    report,
                    intent=intent or HandoffIntent.RELEASE_SIGNOFF,
                )
            else:
                readiness = derive_workspace_handoff_readiness(
                    report,
                    intent=intent or HandoffIntent.FUTURE_SELF,
                )
    except ValueError as exc:
        raise handoff_bad_request(str(exc)) from exc

    return build_handoff_readiness_response(readiness)


__all__ = [
    "get_handoff_guidance_response",
    "get_handoff_readiness_response",
    "get_handoff_record_response",
    "handoff_record_response",
    "list_handoff_records_response",
]
