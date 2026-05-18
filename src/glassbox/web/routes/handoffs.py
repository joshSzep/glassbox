"""FastAPI routes for local handoff custody decisions."""

import json
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import cast
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.core import HandoffIntent
from glassbox.core import HandoffProjectionRecord
from glassbox.runtime.changeset_export import CHANGESET_EXPORT_KIND
from glassbox.runtime.changeset_export import export_changeset_package
from glassbox.runtime.changeset_export import inspect_changeset_export_package
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.handoff_decisions import HandoffDecisionRepository
from glassbox.runtime.handoff_decisions import HandoffDecisionResult
from glassbox.runtime.handoff_decisions import accept_handoff_custody
from glassbox.runtime.handoff_decisions import archive_handoff
from glassbox.runtime.handoff_decisions import custody_action_state
from glassbox.runtime.handoff_decisions import reject_handoff_custody
from glassbox.runtime.handoff_decisions import safe_next_actions_for_decision
from glassbox.runtime.handoff_guidance import load_handoff_guidance
from glassbox.runtime.handoff_import_triage import triage_handoff_import
from glassbox.runtime.handoff_readiness import ChangesetHandoffReadinessService
from glassbox.runtime.handoff_readiness import preview_handoff_readiness
from glassbox.runtime.handoff_redaction_preview import build_changeset_redaction_preview
from glassbox.runtime.handoff_redaction_preview import build_session_redaction_preview
from glassbox.runtime.observability import build_workspace_observability_report
from glassbox.runtime.session_export import SESSION_EXPORT_KIND
from glassbox.runtime.session_export_package import export_session_package
from glassbox.runtime.session_handoff_readiness import SessionHandoffReadinessService
from glassbox.runtime.session_import import import_session_package
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.task_handoff_readiness import TaskHandoffReadinessService
from glassbox.runtime.task_queries import TaskQueryService
from glassbox.runtime.workspace_handoff_readiness import (
    derive_release_handoff_readiness,
)
from glassbox.runtime.workspace_handoff_readiness import (
    derive_workspace_handoff_readiness,
)
from glassbox.web.app import RuntimeContextDep
from glassbox.web.handoff_api import HandoffAcceptRequest
from glassbox.web.handoff_api import HandoffArchiveRequest
from glassbox.web.handoff_api import HandoffChangesetPackageSummary
from glassbox.web.handoff_api import HandoffDecisionResponse
from glassbox.web.handoff_api import HandoffExportRequest
from glassbox.web.handoff_api import HandoffExportResponse
from glassbox.web.handoff_api import HandoffGuidanceResponse
from glassbox.web.handoff_api import HandoffImportResponse
from glassbox.web.handoff_api import HandoffImportTriageResponse
from glassbox.web.handoff_api import HandoffListResponse
from glassbox.web.handoff_api import HandoffPackageInspectResponse
from glassbox.web.handoff_api import HandoffPackagePathRequest
from glassbox.web.handoff_api import HandoffPreparePreviewRequest
from glassbox.web.handoff_api import HandoffPreparePreviewResponse
from glassbox.web.handoff_api import HandoffReadinessUnifiedResponse
from glassbox.web.handoff_api import HandoffRecordResponse
from glassbox.web.handoff_api import HandoffRejectRequest
from glassbox.web.session_api import ErrorDetailResponse

router = APIRouter(prefix="/handoffs")

PageLimitParam = Annotated[int | None, Query(ge=1, le=500)]


@router.get("", response_model=HandoffListResponse)
async def list_handoffs(
    context: RuntimeContextDep,
    session_id: UUID | None = None,
    include_archived: bool = False,
    limit: PageLimitParam = None,
) -> HandoffListResponse:
    """Return projected handoff records for local custody inspection."""

    repository = cast(Any, context.repositories.sessions)
    records = repository.list_handoffs(
        session_id=session_id,
        include_archived=include_archived,
        limit=limit,
    )
    return HandoffListResponse(items=[_record_response(record) for record in records])


@router.post(
    "/prepare-preview",
    response_model=HandoffPreparePreviewResponse,
    responses={
        400: {"model": ErrorDetailResponse},
        404: {"model": ErrorDetailResponse},
    },
)
async def prepare_handoff_preview(
    request: HandoffPreparePreviewRequest,
    context: RuntimeContextDep,
) -> HandoffPreparePreviewResponse:
    """Preview redaction and local-only posture before exporting a handoff."""

    workspace_root = context.infrastructure.artifacts_root
    intent = request.intent
    try:
        if request.source_kind == "session":
            preview = build_session_redaction_preview(
                UUID(request.source_id),
                session_repository=context.repositories.sessions,
                artifact_repository=context.repositories.artifacts,
                workspace_root=workspace_root,
                intent=intent,
                recipient=request.recipient,
                exported_by=request.exported_by,
                expected_custodian=request.expected_custodian,
                note=request.note,
                output_format=request.output_format,
            )
        elif request.source_kind == "changeset":
            preview = build_changeset_redaction_preview(
                UUID(request.source_id),
                repository=cast(ChangesetRepository, context.repositories.sessions),
                artifact_repository=context.repositories.artifacts,
                workspace_root=workspace_root,
                intent=intent,
                recipient=request.recipient,
                expected_custodian=request.expected_custodian,
                exported_by=request.exported_by,
                note=request.note,
                output_format=request.output_format,
            )
        else:
            raise HTTPException(status_code=400, detail="unsupported handoff source")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HandoffPreparePreviewResponse(preview=preview)


@router.post(
    "/exports",
    response_model=HandoffExportResponse,
    responses={
        400: {"model": ErrorDetailResponse},
        404: {"model": ErrorDetailResponse},
    },
)
async def export_handoff(
    request: HandoffExportRequest,
    context: RuntimeContextDep,
) -> HandoffExportResponse:
    """Write a redacted handoff package from a session or changeset source."""

    workspace_root = context.infrastructure.artifacts_root
    try:
        source_id = UUID(request.source_id)
        output_path = _resolve_local_path(
            workspace_root,
            request.output_path,
            default_name=f"glassbox-{request.source_kind}-{source_id}.json",
        )
        markdown_output_path = (
            _resolve_local_path(workspace_root, request.markdown_output_path)
            if request.markdown_output_path is not None
            else None
        )
        if request.source_kind == "session":
            resolved_output = export_session_package(
                source_id,
                output_path,
                session_repository=context.repositories.sessions,
                artifact_repository=context.repositories.artifacts,
                workspace_root=workspace_root,
                intent=request.intent,
                recipient=request.recipient,
                exported_by=request.exported_by,
                expected_custodian=request.expected_custodian,
                note=request.note,
                output_format=request.output_format,
            )
            if markdown_output_path is not None:
                from glassbox.runtime.handoff_markdown import (
                    build_session_export_markdown,
                )
                from glassbox.runtime.session_export_models import SessionExportPayload

                payload = SessionExportPayload.model_validate_json(
                    resolved_output.read_text(encoding="utf-8")
                )
                markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
                markdown_output_path.write_text(
                    build_session_export_markdown(payload),
                    encoding="utf-8",
                )
        elif request.source_kind == "changeset":
            resolved_output = export_changeset_package(
                source_id,
                output_path,
                repository=cast(ChangesetRepository, context.repositories.sessions),
                artifact_repository=context.repositories.artifacts,
                workspace_root=workspace_root,
                intent=request.intent,
                recipient=request.recipient,
                expected_custodian=request.expected_custodian,
                exported_by=request.exported_by,
                note=request.note,
                output_format=request.output_format,
                markdown_output_path=markdown_output_path,
            )
        else:
            raise HTTPException(status_code=400, detail="unsupported handoff source")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return HandoffExportResponse(
        source_kind=request.source_kind,
        source_id=str(source_id),
        output_path=str(resolved_output),
        markdown_output_path=(
            str(markdown_output_path) if markdown_output_path is not None else None
        ),
    )


@router.post(
    "/inspect",
    response_model=HandoffPackageInspectResponse,
    responses={400: {"model": ErrorDetailResponse}},
)
async def inspect_handoff_package(
    request: HandoffPackagePathRequest,
    context: RuntimeContextDep,
) -> HandoffPackageInspectResponse:
    """Inspect a local handoff package without importing or mutating state."""

    package_path = _resolve_local_path(
        context.infrastructure.artifacts_root,
        request.package_path,
    )
    package_kind = _package_export_kind(package_path)
    if package_kind == CHANGESET_EXPORT_KIND:
        summary = HandoffChangesetPackageSummary.model_validate(
            inspect_changeset_export_package(package_path)
        )
        return HandoffPackageInspectResponse(
            package_path=str(package_path),
            package_family="changeset-export",
            changeset_summary=summary,
        )

    triage = triage_handoff_import(package_path)
    return HandoffPackageInspectResponse(
        package_path=str(package_path),
        package_family=(
            "session-export"
            if package_kind == SESSION_EXPORT_KIND
            else "handoff-package"
        ),
        triage=triage,
    )


@router.post(
    "/import-triage",
    response_model=HandoffImportTriageResponse,
    responses={400: {"model": ErrorDetailResponse}},
)
async def triage_handoff_package_import(
    request: HandoffPackagePathRequest,
    context: RuntimeContextDep,
) -> HandoffImportTriageResponse:
    """Inspect package import compatibility without mutating local state."""

    package_path = _resolve_local_path(
        context.infrastructure.artifacts_root,
        request.package_path,
    )
    return HandoffImportTriageResponse(triage=triage_handoff_import(package_path))


@router.post(
    "/imports",
    response_model=HandoffImportResponse,
    responses={400: {"model": ErrorDetailResponse}},
)
async def import_handoff_package(
    request: HandoffPackagePathRequest,
    context: RuntimeContextDep,
) -> HandoffImportResponse:
    """Import a supported session handoff package as inspection-only state."""

    package_path = _resolve_local_path(
        context.infrastructure.artifacts_root,
        request.package_path,
    )
    try:
        result = import_session_package(
            package_path,
            session_repository=context.repositories.sessions,
            workspace_root=context.infrastructure.artifacts_root,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HandoffImportResponse(result=result)


@router.get(
    "/readiness",
    response_model=HandoffReadinessUnifiedResponse,
    responses={
        400: {"model": ErrorDetailResponse},
        404: {"model": ErrorDetailResponse},
    },
)
async def get_handoff_readiness(
    context: RuntimeContextDep,
    source_kind: str = Query(default="workspace"),
    source_id: str | None = None,
    intent: HandoffIntent | None = None,
) -> HandoffReadinessUnifiedResponse:
    """Return shared v17 handoff readiness for a local source."""

    workspace_root = context.infrastructure.artifacts_root
    try:
        if source_kind == "session":
            if source_id is None:
                raise HTTPException(status_code=400, detail="source_id is required")
            readiness = SessionHandoffReadinessService(
                SessionQueryService(
                    context.repositories.sessions,
                    context.repositories.artifacts,
                )
            ).preview(UUID(source_id), intent=intent or HandoffIntent.REVIEW_ONLY)
        elif source_kind == "task":
            if source_id is None:
                raise HTTPException(status_code=400, detail="source_id is required")
            readiness = TaskHandoffReadinessService(
                TaskQueryService(
                    cast(Any, context.repositories.sessions),
                    workspace_root=workspace_root,
                )
            ).preview(UUID(source_id), intent=intent or HandoffIntent.CONTINUE_WORK)
        elif source_kind == "changeset":
            if source_id is None:
                raise HTTPException(status_code=400, detail="source_id is required")
            assessment = preview_handoff_readiness(
                ChangesetHandoffReadinessService(
                    cast(ChangesetRepository, context.repositories.sessions),
                    context.repositories.artifacts,
                ),
                UUID(source_id),
                workspace_root,
            )
            readiness = assessment.shared_readiness
        elif source_kind in {"workspace", "release"}:
            report = build_workspace_observability_report(
                workspace_root=workspace_root,
                runtime_status=inspect_runtime_owner(workspace_root),
                session_repository=context.repositories.sessions,
                event_transport_stats=context.infrastructure.event_transport.stats(),
            )
            if source_kind == "release":
                readiness = derive_release_handoff_readiness(
                    report,
                    intent=intent or HandoffIntent.RELEASE_SIGNOFF,
                )
            else:
                readiness = derive_workspace_handoff_readiness(
                    report,
                    intent=intent or HandoffIntent.FUTURE_SELF,
                )
        else:
            raise HTTPException(status_code=400, detail="unsupported handoff source")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return HandoffReadinessUnifiedResponse(readiness=readiness)


@router.get(
    "/{session_id}/{package_id}",
    response_model=HandoffRecordResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_handoff(
    session_id: UUID,
    package_id: str,
    context: RuntimeContextDep,
) -> HandoffRecordResponse:
    """Return one projected handoff record."""

    return _record_response(_require_handoff(context, session_id, package_id))


@router.get(
    "/{session_id}/{package_id}/guidance",
    response_model=HandoffGuidanceResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_handoff_guidance(
    session_id: UUID,
    package_id: str,
    context: RuntimeContextDep,
) -> HandoffGuidanceResponse:
    """Return advisory fork-or-continue guidance for one imported handoff."""

    repository = cast(Any, context.repositories.sessions)
    try:
        guidance = load_handoff_guidance(repository, session_id, package_id)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="handoff record not found",
        ) from exc
    return HandoffGuidanceResponse(guidance=guidance)


@router.post(
    "/{session_id}/{package_id}/accept",
    response_model=HandoffDecisionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def accept_handoff(
    session_id: UUID,
    package_id: str,
    request: HandoffAcceptRequest,
    context: RuntimeContextDep,
) -> HandoffDecisionResponse:
    """Accept local handoff custody or imported follow-up intent."""

    record = _require_handoff(context, session_id, package_id)
    repository = cast(HandoffDecisionRepository, context.repositories.sessions)
    result = accept_handoff_custody(
        repository,
        session_id=session_id,
        package_id=package_id,
        accepted_by=request.accepted_by,
        reason=request.reason,
        follow_up_intent=request.follow_up_intent,
        safe_next_actions=safe_next_actions_for_decision(record),
    )
    return _decision_response(result)


@router.post(
    "/{session_id}/{package_id}/reject",
    response_model=HandoffDecisionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def reject_handoff(
    session_id: UUID,
    package_id: str,
    request: HandoffRejectRequest,
    context: RuntimeContextDep,
) -> HandoffDecisionResponse:
    """Reject local handoff custody with a retained reason."""

    record = _require_handoff(context, session_id, package_id)
    repository = cast(HandoffDecisionRepository, context.repositories.sessions)
    result = reject_handoff_custody(
        repository,
        session_id=session_id,
        package_id=package_id,
        rejected_by=request.rejected_by,
        reason=request.reason,
        safe_next_actions=safe_next_actions_for_decision(record),
    )
    return _decision_response(result)


@router.post(
    "/{session_id}/{package_id}/archive",
    response_model=HandoffDecisionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def archive_handoff_record(
    session_id: UUID,
    package_id: str,
    request: HandoffArchiveRequest,
    context: RuntimeContextDep,
) -> HandoffDecisionResponse:
    """Archive a handoff as historical local workflow evidence."""

    _require_handoff(context, session_id, package_id)
    repository = cast(HandoffDecisionRepository, context.repositories.sessions)
    result = archive_handoff(
        repository,
        session_id=session_id,
        package_id=package_id,
        archived_by=request.archived_by,
        reason=request.reason,
    )
    return _decision_response(result)


def _require_handoff(
    context: RuntimeContextDep,
    session_id: UUID,
    package_id: str,
) -> HandoffProjectionRecord:
    repository = cast(Any, context.repositories.sessions)
    record = repository.get_handoff(session_id, package_id)
    if record is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="handoff record not found")
    return record


def _resolve_local_path(
    workspace_root: Path,
    path_text: str | None,
    *,
    default_name: str | None = None,
) -> Path:
    value = path_text or default_name
    if value is None:
        raise HTTPException(status_code=400, detail="package path is required")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve()


def _package_export_kind(package_path: Path) -> str | None:
    try:
        raw_payload = json.loads(package_path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None
    if not isinstance(raw_payload, dict):
        return None
    export_kind = raw_payload.get("export_kind")
    return export_kind if isinstance(export_kind, str) else None


def _decision_response(result: HandoffDecisionResult) -> HandoffDecisionResponse:
    return HandoffDecisionResponse(
        event_type=result.event_type,
        handoff=_record_response(result.record),
        non_claims=result.non_claims,
    )


def _record_response(record: HandoffProjectionRecord) -> HandoffRecordResponse:
    return HandoffRecordResponse(
        record=record,
        action_state=custody_action_state(record),
    )


__all__ = ["router"]
