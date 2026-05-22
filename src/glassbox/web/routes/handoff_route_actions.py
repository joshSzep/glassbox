"""Mutation/action orchestration for handoff routes."""

from typing import cast
from uuid import UUID

from glassbox.runtime.changeset_export import CHANGESET_EXPORT_KIND
from glassbox.runtime.changeset_export import export_changeset_package
from glassbox.runtime.changeset_export import inspect_changeset_export_package
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.handoff_decisions import HandoffDecisionRepository
from glassbox.runtime.handoff_decisions import accept_handoff_custody
from glassbox.runtime.handoff_decisions import archive_handoff
from glassbox.runtime.handoff_decisions import reject_handoff_custody
from glassbox.runtime.handoff_decisions import safe_next_actions_for_decision
from glassbox.runtime.handoff_import_triage import triage_handoff_import
from glassbox.runtime.handoff_markdown import build_session_export_markdown
from glassbox.runtime.handoff_redaction_preview import build_changeset_redaction_preview
from glassbox.runtime.handoff_redaction_preview import build_session_redaction_preview
from glassbox.runtime.session_export import SESSION_EXPORT_KIND
from glassbox.runtime.session_export_models import SessionExportPayload
from glassbox.runtime.session_export_package import export_session_package
from glassbox.runtime.session_import import import_session_package
from glassbox.web.handoff_api import HandoffAcceptRequest
from glassbox.web.handoff_api import HandoffArchiveRequest
from glassbox.web.handoff_api import HandoffDecisionResponse
from glassbox.web.handoff_api import HandoffExportRequest
from glassbox.web.handoff_api import HandoffExportResponse
from glassbox.web.handoff_api import HandoffImportResponse
from glassbox.web.handoff_api import HandoffImportTriageResponse
from glassbox.web.handoff_api import HandoffPackageInspectResponse
from glassbox.web.handoff_api import HandoffPackagePathRequest
from glassbox.web.handoff_api import HandoffPreparePreviewRequest
from glassbox.web.handoff_api import HandoffPreparePreviewResponse
from glassbox.web.handoff_api import HandoffRejectRequest
from glassbox.web.handoff_api import build_handoff_changeset_package_summary
from glassbox.web.handoff_api import build_handoff_decision_response
from glassbox.web.handoff_api import build_handoff_export_response
from glassbox.web.handoff_api import build_handoff_import_response
from glassbox.web.handoff_api import build_handoff_import_triage_response
from glassbox.web.handoff_api import build_handoff_package_inspect_response
from glassbox.web.handoff_api import build_handoff_prepare_preview_response
from glassbox.web.routes.handoff_route_errors import handoff_bad_request
from glassbox.web.routes.handoff_route_errors import require_handoff_record
from glassbox.web.routes.handoff_route_paths import package_export_kind
from glassbox.web.routes.handoff_route_paths import resolve_local_package_path


def prepare_handoff_preview_response(
    request: HandoffPreparePreviewRequest,
    context: RuntimeContext,
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
            raise handoff_bad_request("unsupported handoff source")
    except ValueError as exc:
        raise handoff_bad_request(str(exc)) from exc
    return build_handoff_prepare_preview_response(preview)


def export_handoff_response(
    request: HandoffExportRequest,
    context: RuntimeContext,
) -> HandoffExportResponse:
    """Write a redacted handoff package from a session or changeset source."""

    workspace_root = context.infrastructure.artifacts_root
    try:
        source_id = UUID(request.source_id)
        output_path = resolve_local_package_path(
            workspace_root,
            request.output_path,
            default_name=f"glassbox-{request.source_kind}-{source_id}.json",
        )
        markdown_output_path = (
            resolve_local_package_path(workspace_root, request.markdown_output_path)
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
            raise handoff_bad_request("unsupported handoff source")
    except ValueError as exc:
        raise handoff_bad_request(str(exc)) from exc

    return build_handoff_export_response(
        source_kind=request.source_kind,
        source_id=source_id,
        output_path=resolved_output,
        markdown_output_path=markdown_output_path,
    )


def inspect_handoff_package_response(
    request: HandoffPackagePathRequest,
    context: RuntimeContext,
) -> HandoffPackageInspectResponse:
    """Inspect a local handoff package without importing or mutating state."""

    package_path = resolve_local_package_path(
        context.infrastructure.artifacts_root,
        request.package_path,
    )
    package_kind = package_export_kind(package_path)
    if package_kind == CHANGESET_EXPORT_KIND:
        summary = build_handoff_changeset_package_summary(
            inspect_changeset_export_package(package_path)
        )
        return build_handoff_package_inspect_response(
            package_path=package_path,
            package_family="changeset-export",
            changeset_summary=summary,
        )

    triage = triage_handoff_import(package_path)
    return build_handoff_package_inspect_response(
        package_path=package_path,
        package_family=(
            "session-export"
            if package_kind == SESSION_EXPORT_KIND
            else "handoff-package"
        ),
        triage=triage,
    )


def triage_handoff_package_import_response(
    request: HandoffPackagePathRequest,
    context: RuntimeContext,
) -> HandoffImportTriageResponse:
    """Inspect package import compatibility without mutating local state."""

    package_path = resolve_local_package_path(
        context.infrastructure.artifacts_root,
        request.package_path,
    )
    return build_handoff_import_triage_response(triage_handoff_import(package_path))


def import_handoff_package_response(
    request: HandoffPackagePathRequest,
    context: RuntimeContext,
) -> HandoffImportResponse:
    """Import a supported session handoff package as inspection-only state."""

    package_path = resolve_local_package_path(
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
        raise handoff_bad_request(str(exc)) from exc
    return build_handoff_import_response(result)


def accept_handoff_response(
    session_id: UUID,
    package_id: str,
    request: HandoffAcceptRequest,
    context: RuntimeContext,
) -> HandoffDecisionResponse:
    """Accept local handoff custody or imported follow-up intent."""

    record = require_handoff_record(context, session_id, package_id)
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
    return build_handoff_decision_response(result)


def reject_handoff_response(
    session_id: UUID,
    package_id: str,
    request: HandoffRejectRequest,
    context: RuntimeContext,
) -> HandoffDecisionResponse:
    """Reject local handoff custody with a retained reason."""

    record = require_handoff_record(context, session_id, package_id)
    repository = cast(HandoffDecisionRepository, context.repositories.sessions)
    result = reject_handoff_custody(
        repository,
        session_id=session_id,
        package_id=package_id,
        rejected_by=request.rejected_by,
        reason=request.reason,
        safe_next_actions=safe_next_actions_for_decision(record),
    )
    return build_handoff_decision_response(result)


def archive_handoff_response(
    session_id: UUID,
    package_id: str,
    request: HandoffArchiveRequest,
    context: RuntimeContext,
) -> HandoffDecisionResponse:
    """Archive a handoff as historical local workflow evidence."""

    require_handoff_record(context, session_id, package_id)
    repository = cast(HandoffDecisionRepository, context.repositories.sessions)
    result = archive_handoff(
        repository,
        session_id=session_id,
        package_id=package_id,
        archived_by=request.archived_by,
        reason=request.reason,
    )
    return build_handoff_decision_response(result)


__all__ = [
    "accept_handoff_response",
    "archive_handoff_response",
    "export_handoff_response",
    "import_handoff_package_response",
    "inspect_handoff_package_response",
    "prepare_handoff_preview_response",
    "reject_handoff_response",
    "triage_handoff_package_import_response",
]
