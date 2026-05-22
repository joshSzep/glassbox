"""Changeset-family handoff redaction preview builders."""

from pathlib import Path

from glassbox.core import ChangesetId
from glassbox.core import HandoffIntent
from glassbox.core import HandoffLocalOnlySummary
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffRedactionSummary
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.runtime.changeset_export import CHANGESET_EXPORT_OMITTED_RAW_CATEGORIES
from glassbox.runtime.changeset_export import ChangesetExportPayload
from glassbox.runtime.changeset_export import build_changeset_export_payload
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.handoff_redaction_preview_models import HandoffRedactionPreview
from glassbox.runtime.handoff_redaction_preview_shared import included_sections
from glassbox.runtime.handoff_redaction_preview_shared import positive_counts
from glassbox.runtime.handoff_redaction_preview_shared import redaction_marker_summary
from glassbox.runtime.handoff_redaction_preview_shared import safe_command
from glassbox.services import ArtifactRepository


def build_changeset_redaction_preview(
    changeset_id: ChangesetId,
    *,
    repository: ChangesetRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
    intent: HandoffIntent = HandoffIntent.REVIEW_ONLY,
    recipient: str | None = None,
    expected_custodian: str | None = None,
    exported_by: str | None = None,
    note: str | None = None,
    output_format: str = "json",
) -> HandoffRedactionPreview:
    """Preview a changeset export using the same reviewer-safe package builder."""

    payload = build_changeset_export_payload(
        changeset_id,
        repository=repository,
        artifact_repository=artifact_repository,
        workspace_root=workspace_root,
        intent=intent,
        recipient=recipient,
        expected_custodian=expected_custodian,
        exported_by=exported_by,
        note=note,
        output_format=output_format,
    )
    return changeset_redaction_preview_from_payload(payload)


def changeset_redaction_preview_from_payload(
    payload: ChangesetExportPayload,
) -> HandoffRedactionPreview:
    """Build a redaction preview from a changeset export payload."""

    payload_dict = payload.model_dump(mode="json", exclude_none=True)
    redacted_field_count, marker_categories = redaction_marker_summary(payload_dict)
    redaction_categories = list(
        dict.fromkeys([*marker_categories, *_redaction_report_categories(payload)])
    )
    manual_evidence = payload.manual_evidence
    live_evidence = payload.live_review_evidence
    local_only_counts = positive_counts(
        {
            "artifact_references": len(payload.artifact_references),
            "manual_evidence": int(manual_evidence.get("local_only_count", 0)),
            "skipped_live_evidence": int(
                live_evidence.get("skipped_live_evidence_count", 0)
            ),
        }
    )
    local_only_summary = HandoffLocalOnlySummary(
        category_counts=local_only_counts,
        limitations=[
            "artifact paths remain local-only references by artifact ID",
            ("manual, browser, dashboard, and accessibility raw evidence stays local"),
        ],
        safe_local_inspection_commands=[
            safe_command(
                "glassbox changeset evidence list "
                f"{payload.changeset['changeset_id']} --cwd .",
                "Inspect local evidence inventory before sharing.",
            )
        ],
    )
    return HandoffRedactionPreview(
        source=HandoffSourceRef(
            kind=HandoffSourceKind.CHANGESET,
            primary_id=str(payload.changeset["changeset_id"]),
            identifiers={"session_id": str(payload.changeset["session_id"])},
            label=payload.changeset.get("summary") or payload.changeset["objective"],
        ),
        intent=(
            payload.profile.profile_id
            if payload.profile is not None
            else HandoffIntent.REVIEW_ONLY
        ),
        profile=payload.profile,
        included_sections=included_sections(payload_dict),
        redaction=HandoffRedactionSummary(
            posture=HandoffRedactionPosture.REVIEWER_SAFE,
            redacted_field_count=max(
                redacted_field_count, len(payload.redaction_report)
            ),
            redacted_categories=redaction_categories,
            raw_transcript_included=False,
            raw_logs_included=False,
            raw_artifacts_included=False,
            raw_diffs_included=False,
            screenshots_included=False,
            provider_output_included=False,
            limitations=list(payload.redaction_report),
        ),
        local_only=local_only_summary,
        local_only_inventory=payload.local_only_inventory,
        omitted_raw_categories=CHANGESET_EXPORT_OMITTED_RAW_CATEGORIES,
        unsupported_evidence=[],
        package_limitations=[
            "changeset preview is computed from the same payload path as export",
            (
                "preview counts what the package would include; it does not write "
                "the package"
            ),
        ],
        safe_inspection_commands=[
            safe_command(
                "glassbox changeset handoff-readiness "
                f"{payload.changeset['changeset_id']} --cwd .",
                "Inspect final handoff posture before export.",
            )
        ],
    )


def _redaction_report_categories(payload: ChangesetExportPayload) -> list[str]:
    categories: list[str] = []
    for item in payload.redaction_report:
        lowered = item.lower()
        if "database" in lowered:
            categories.append("database-state")
        if "command output" in lowered:
            categories.append("command-output")
        if "provider" in lowered:
            categories.append("provider-output")
        if "manual evidence" in lowered or "external logs" in lowered:
            categories.append("manual-evidence")
        if "diff" in lowered or "file contents" in lowered:
            categories.append("diff-and-file-content")
        if "screenshots" in lowered or "browser" in lowered:
            categories.append("browser-and-screenshot-evidence")
        if "artifact" in lowered:
            categories.append("artifact-path")
    return list(dict.fromkeys(categories))


__all__ = [
    "build_changeset_redaction_preview",
    "changeset_redaction_preview_from_payload",
]
