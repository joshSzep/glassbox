"""Session-family handoff redaction preview builders."""

from pathlib import Path

from glassbox.core import HandoffIntent
from glassbox.core import HandoffLocalOnlySummary
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffRedactionSummary
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.core import SessionId
from glassbox.runtime.handoff_local_only_inventory import build_local_only_inventory
from glassbox.runtime.handoff_redaction_preview_models import HandoffRedactionPreview
from glassbox.runtime.handoff_redaction_preview_shared import included_sections
from glassbox.runtime.handoff_redaction_preview_shared import positive_counts
from glassbox.runtime.handoff_redaction_preview_shared import redaction_marker_summary
from glassbox.runtime.handoff_redaction_preview_shared import safe_command
from glassbox.runtime.session_export_package import build_session_export_payload
from glassbox.runtime.session_export_profile import (
    SESSION_EXPORT_OMITTED_RAW_CATEGORIES,
)
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import SessionSnapshotView
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository


def build_session_redaction_preview(
    session_id: SessionId,
    *,
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
    intent: HandoffIntent = HandoffIntent.REVIEW_ONLY,
    recipient: str | None = None,
    exported_by: str | None = None,
    expected_custodian: str | None = None,
    note: str | None = None,
    output_format: str = "json",
) -> HandoffRedactionPreview:
    """Preview a session export using the same in-memory payload builder."""

    payload = build_session_export_payload(
        session_id,
        session_repository=session_repository,
        artifact_repository=artifact_repository,
        workspace_root=workspace_root,
        intent=intent,
        recipient=recipient,
        exported_by=exported_by,
        expected_custodian=expected_custodian,
        note=note,
        output_format=output_format,
    )
    snapshot = SessionQueryService(
        session_repository,
        artifact_repository,
    ).get_session_snapshot(session_id, turn_metrics_limit=25)
    return session_redaction_preview_from_payload(payload, snapshot=snapshot)


def session_redaction_preview_from_payload(
    payload,
    *,
    snapshot: SessionSnapshotView,
) -> HandoffRedactionPreview:
    """Build a redaction preview from a session export payload."""

    payload_dict = payload.model_dump(mode="json", exclude_none=True)
    redacted_field_count, categories = redaction_marker_summary(payload_dict)
    local_only_counts = {
        "artifact_references": len(payload.artifact_references),
        "checkpoint_artifacts": sum(
            1 for item in payload.checkpoint_history if item.artifact_id is not None
        ),
    }
    local_only_counts = positive_counts(local_only_counts)
    local_only_summary = HandoffLocalOnlySummary(
        category_counts=local_only_counts,
        limitations=[
            "artifact contents remain local-only and are referenced by ID",
            "raw tool logs and provider output are summarized, not copied",
        ],
        safe_local_inspection_commands=[
            safe_command(
                f"glassbox session status {payload.metadata.session_id} --cwd .",
                "Inspect the source session before sharing or importing.",
            )
        ],
    )
    source = HandoffSourceRef(
        kind=HandoffSourceKind.SESSION,
        primary_id=str(payload.metadata.session_id),
        label="session",
    )
    return HandoffRedactionPreview(
        source=source,
        intent=payload.handoff.intent,
        profile=payload.profile,
        included_sections=included_sections(payload_dict),
        redaction=HandoffRedactionSummary(
            posture=HandoffRedactionPosture.REVIEWER_SAFE,
            redacted_field_count=redacted_field_count,
            redacted_categories=categories,
            raw_transcript_included=False,
            raw_logs_included=False,
            raw_artifacts_included=False,
            raw_diffs_included=False,
            screenshots_included=False,
            provider_output_included=False,
            limitations=list(payload.redaction_notes),
        ),
        local_only=local_only_summary,
        local_only_inventory=payload.local_only_inventory
        or build_local_only_inventory(
            source=source,
            intent=payload.handoff.intent,
            summary=local_only_summary,
            omitted_raw_categories=SESSION_EXPORT_OMITTED_RAW_CATEGORIES,
        ),
        omitted_raw_categories=SESSION_EXPORT_OMITTED_RAW_CATEGORIES,
        unsupported_evidence=[],
        package_limitations=[
            "session preview is computed from the same payload path as export",
            (
                "preview counts what the package would include; it does not write "
                "the package"
            ),
            *(
                ["session has pending approval local state"]
                if snapshot.pending_approval_id is not None
                else []
            ),
        ],
        safe_inspection_commands=[
            safe_command(
                f"glassbox session handoff-readiness {payload.metadata.session_id} "
                "--cwd .",
                "Inspect session handoff readiness before export.",
            )
        ],
    )


__all__ = [
    "build_session_redaction_preview",
    "session_redaction_preview_from_payload",
]
