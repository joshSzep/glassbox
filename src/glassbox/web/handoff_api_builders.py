"""Response builders for local handoff API surfaces."""

from pathlib import Path
from typing import Any
from uuid import UUID

from glassbox.core import HandoffProjectionRecord
from glassbox.core import HandoffReadiness
from glassbox.runtime.handoff_decisions import HandoffDecisionResult
from glassbox.runtime.handoff_decisions import custody_action_state
from glassbox.runtime.handoff_guidance import HandoffGuidance
from glassbox.runtime.handoff_import_triage import HandoffImportTriage
from glassbox.runtime.handoff_redaction_preview import HandoffRedactionPreview
from glassbox.runtime.session_import import SessionImportResult
from glassbox.web.handoff_api_models import HandoffChangesetPackageSummary
from glassbox.web.handoff_api_models import HandoffDecisionResponse
from glassbox.web.handoff_api_models import HandoffExportResponse
from glassbox.web.handoff_api_models import HandoffGuidanceResponse
from glassbox.web.handoff_api_models import HandoffImportResponse
from glassbox.web.handoff_api_models import HandoffImportTriageResponse
from glassbox.web.handoff_api_models import HandoffListResponse
from glassbox.web.handoff_api_models import HandoffPackageInspectResponse
from glassbox.web.handoff_api_models import HandoffPreparePreviewResponse
from glassbox.web.handoff_api_models import HandoffReadinessUnifiedResponse
from glassbox.web.handoff_api_models import HandoffRecordResponse


def build_handoff_record_response(
    record: HandoffProjectionRecord,
) -> HandoffRecordResponse:
    """Build a response for one projected handoff record."""

    return HandoffRecordResponse(
        record=record,
        action_state=custody_action_state(record),
    )


def build_handoff_list_response(
    records: list[HandoffProjectionRecord],
) -> HandoffListResponse:
    """Build a bounded list response for projected handoff records."""

    return HandoffListResponse(
        items=[build_handoff_record_response(record) for record in records]
    )


def build_handoff_decision_response(
    result: HandoffDecisionResult,
) -> HandoffDecisionResponse:
    """Build a response for a retained handoff custody decision."""

    return HandoffDecisionResponse(
        event_type=result.event_type,
        handoff=build_handoff_record_response(result.record),
        non_claims=result.non_claims,
    )


def build_handoff_guidance_response(
    guidance: HandoffGuidance,
) -> HandoffGuidanceResponse:
    """Build a response for fork-or-continue guidance."""

    return HandoffGuidanceResponse(guidance=guidance)


def build_handoff_prepare_preview_response(
    preview: HandoffRedactionPreview,
) -> HandoffPreparePreviewResponse:
    """Build a response for handoff preparation preview."""

    return HandoffPreparePreviewResponse(preview=preview)


def build_handoff_export_response(
    *,
    source_kind: str,
    source_id: UUID,
    output_path: Path,
    markdown_output_path: Path | None = None,
) -> HandoffExportResponse:
    """Build a response for a written handoff export package."""

    return HandoffExportResponse(
        source_kind=source_kind,
        source_id=str(source_id),
        output_path=str(output_path),
        markdown_output_path=(
            str(markdown_output_path) if markdown_output_path is not None else None
        ),
    )


def build_handoff_changeset_package_summary(
    summary: dict[str, Any],
) -> HandoffChangesetPackageSummary:
    """Validate a reviewer-safe changeset package summary."""

    return HandoffChangesetPackageSummary.model_validate(summary)


def build_handoff_package_inspect_response(
    *,
    package_path: Path,
    package_family: str,
    triage: HandoffImportTriage | None = None,
    changeset_summary: HandoffChangesetPackageSummary | None = None,
) -> HandoffPackageInspectResponse:
    """Build a response for a local package inspection."""

    return HandoffPackageInspectResponse(
        package_path=str(package_path),
        package_family=package_family,
        triage=triage,
        changeset_summary=changeset_summary,
    )


def build_handoff_import_triage_response(
    triage: HandoffImportTriage,
) -> HandoffImportTriageResponse:
    """Build a response for import triage without mutation."""

    return HandoffImportTriageResponse(triage=triage)


def build_handoff_import_response(
    result: SessionImportResult,
) -> HandoffImportResponse:
    """Build a response for importing a session handoff."""

    return HandoffImportResponse(result=result)


def build_handoff_readiness_response(
    readiness: HandoffReadiness,
) -> HandoffReadinessUnifiedResponse:
    """Build a response for shared handoff readiness."""

    return HandoffReadinessUnifiedResponse(readiness=readiness)


__all__ = [
    "build_handoff_changeset_package_summary",
    "build_handoff_decision_response",
    "build_handoff_export_response",
    "build_handoff_guidance_response",
    "build_handoff_import_response",
    "build_handoff_import_triage_response",
    "build_handoff_list_response",
    "build_handoff_package_inspect_response",
    "build_handoff_prepare_preview_response",
    "build_handoff_readiness_response",
    "build_handoff_record_response",
]
