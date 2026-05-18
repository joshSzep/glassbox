"""Redaction preview helpers for local handoff exports."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import computed_field

from glassbox.core import ChangesetId
from glassbox.core import HandoffIntent
from glassbox.core import HandoffLocalOnlyInventory
from glassbox.core import HandoffLocalOnlySummary
from glassbox.core import HandoffReadiness
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffRedactionSummary
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.core import SessionId
from glassbox.core import TaskId
from glassbox.runtime.changeset_export import CHANGESET_EXPORT_OMITTED_RAW_CATEGORIES
from glassbox.runtime.changeset_export import ChangesetExportPayload
from glassbox.runtime.changeset_export import build_changeset_export_payload
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.handoff_local_only_inventory import build_local_only_inventory
from glassbox.runtime.handoff_local_only_inventory import (
    build_readiness_local_only_inventory,
)
from glassbox.runtime.observability import WorkspaceObservabilityReport
from glassbox.runtime.session_export_package import (
    SESSION_EXPORT_OMITTED_RAW_CATEGORIES,
)
from glassbox.runtime.session_export_package import build_session_export_payload
from glassbox.runtime.session_export_redaction import REDACTION_PLACEHOLDER
from glassbox.runtime.session_export_redaction import WORKSPACE_PLACEHOLDER
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import SessionSnapshotView
from glassbox.runtime.task_handoff_readiness import derive_task_handoff_readiness
from glassbox.runtime.task_queries import TaskDetailView
from glassbox.runtime.task_queries import TaskQueryService
from glassbox.runtime.workspace_handoff_readiness import (
    derive_release_handoff_readiness,
)
from glassbox.runtime.workspace_handoff_readiness import (
    derive_workspace_handoff_readiness,
)
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository


class HandoffRedactionPreview(BaseModel):
    """Machine-readable preview for what a handoff export would include."""

    model_config = ConfigDict(extra="forbid")

    preview_kind: str = "handoff_redaction_preview"
    source: HandoffSourceRef
    intent: HandoffIntent
    included_sections: list[str] = Field(default_factory=list, max_length=100)
    redaction: HandoffRedactionSummary
    local_only: HandoffLocalOnlySummary
    local_only_inventory: HandoffLocalOnlyInventory
    omitted_raw_categories: list[str] = Field(default_factory=list, max_length=50)
    unsupported_evidence: list[str] = Field(default_factory=list, max_length=50)
    package_limitations: list[str] = Field(default_factory=list, max_length=50)
    safe_inspection_commands: list[HandoffSafeCommand] = Field(
        default_factory=list,
        max_length=20,
    )

    @computed_field
    @property
    def local_only_evidence_count(self) -> int:
        return sum(self.local_only.category_counts.values())


def build_session_redaction_preview(
    session_id: SessionId,
    *,
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
    exported_by: str | None = None,
    expected_custodian: str | None = None,
    note: str | None = None,
) -> HandoffRedactionPreview:
    """Preview a session export using the same in-memory payload builder."""

    payload = build_session_export_payload(
        session_id,
        session_repository=session_repository,
        artifact_repository=artifact_repository,
        workspace_root=workspace_root,
        exported_by=exported_by,
        expected_custodian=expected_custodian,
        note=note,
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
    redacted_field_count, categories = _redaction_marker_summary(payload_dict)
    local_only_counts = {
        "artifact_references": len(payload.artifact_references),
        "checkpoint_artifacts": sum(
            1 for item in payload.checkpoint_history if item.artifact_id is not None
        ),
    }
    local_only_counts = _positive_counts(local_only_counts)
    local_only_summary = HandoffLocalOnlySummary(
        category_counts=local_only_counts,
        limitations=[
            "artifact contents remain local-only and are referenced by ID",
            "raw tool logs and provider output are summarized, not copied",
        ],
        safe_local_inspection_commands=[
            _safe_command(
                f"glassbox session status {payload.metadata.session_id} --cwd .",
                "Inspect the source session before sharing or importing.",
            )
        ],
    )
    return HandoffRedactionPreview(
        source=HandoffSourceRef(
            kind=HandoffSourceKind.SESSION,
            primary_id=str(payload.metadata.session_id),
            label="session",
        ),
        intent=HandoffIntent.REVIEW_ONLY,
        included_sections=_included_sections(payload_dict),
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
            source=HandoffSourceRef(
                kind=HandoffSourceKind.SESSION,
                primary_id=str(payload.metadata.session_id),
                label="session",
            ),
            intent=HandoffIntent.REVIEW_ONLY,
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
            _safe_command(
                f"glassbox session handoff-readiness {payload.metadata.session_id} "
                "--cwd .",
                "Inspect session handoff readiness before export.",
            )
        ],
    )


def build_changeset_redaction_preview(
    changeset_id: ChangesetId,
    *,
    repository: ChangesetRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
) -> HandoffRedactionPreview:
    """Preview a changeset export using the same reviewer-safe package builder."""

    payload = build_changeset_export_payload(
        changeset_id,
        repository=repository,
        artifact_repository=artifact_repository,
        workspace_root=workspace_root,
    )
    return changeset_redaction_preview_from_payload(payload)


def changeset_redaction_preview_from_payload(
    payload: ChangesetExportPayload,
) -> HandoffRedactionPreview:
    """Build a redaction preview from a changeset export payload."""

    payload_dict = payload.model_dump(mode="json", exclude_none=True)
    redacted_field_count, marker_categories = _redaction_marker_summary(payload_dict)
    redaction_categories = list(
        dict.fromkeys([*marker_categories, *_redaction_report_categories(payload)])
    )
    manual_evidence = payload.manual_evidence
    live_evidence = payload.live_review_evidence
    local_only_counts = _positive_counts(
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
            _safe_command(
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
        intent=HandoffIntent.REVIEW_ONLY,
        included_sections=_included_sections(payload_dict),
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
            _safe_command(
                "glassbox changeset handoff-readiness "
                f"{payload.changeset['changeset_id']} --cwd .",
                "Inspect final handoff posture before export.",
            )
        ],
    )


def build_task_redaction_preview(
    task_id: TaskId,
    *,
    query_service: TaskQueryService,
    intent: HandoffIntent = HandoffIntent.CONTINUE_WORK,
) -> HandoffRedactionPreview:
    """Preview the currently supported task handoff sections."""

    detail = query_service.get_task_detail(task_id)
    readiness = derive_task_handoff_readiness(detail, intent=intent)
    return task_redaction_preview_from_readiness(detail, readiness=readiness)


def task_redaction_preview_from_readiness(
    detail: TaskDetailView,
    *,
    readiness: HandoffReadiness,
) -> HandoffRedactionPreview:
    local_only_counts = _positive_counts(
        {
            "local_only_readiness_reasons": len(readiness.local_only_evidence),
            "verification_artifacts": sum(
                1
                for item in detail.verification_ledger
                if item.latest_artifact_id is not None
            ),
        }
    )
    local_only_summary = HandoffLocalOnlySummary(
        category_counts=local_only_counts,
        limitations=readiness.limitations,
        safe_local_inspection_commands=readiness.safe_first_commands,
    )
    return HandoffRedactionPreview(
        source=readiness.source,
        intent=readiness.intent,
        included_sections=[
            "task",
            "steps",
            "verification_summary",
            "readiness",
            "safe_first_commands",
        ],
        redaction=HandoffRedactionSummary(
            posture=HandoffRedactionPosture.LOCAL_ONLY_OMITTED,
            redacted_field_count=0,
            redacted_categories=[],
            limitations=[
                "task handoff preview currently summarizes readiness sections only"
            ],
        ),
        local_only=local_only_summary,
        local_only_inventory=build_local_only_inventory(
            source=readiness.source,
            intent=readiness.intent,
            summary=local_only_summary,
            omitted_raw_categories=[
                "raw task session transcript",
                "raw verification logs",
                "raw managed artifacts",
            ],
            affected_claim_ids_by_category={
                "verification_artifacts": ["task.verification"],
                "local_only_readiness_reasons": ["task.readiness"],
            },
        ),
        omitted_raw_categories=[
            "raw task session transcript",
            "raw verification logs",
            "raw managed artifacts",
        ],
        unsupported_evidence=[
            "task export packages are not available until recipient profiles land"
        ],
        package_limitations=[
            "task preview is readiness-oriented and does not write a package"
        ],
        safe_inspection_commands=readiness.safe_first_commands,
    )


def workspace_redaction_preview_from_report(
    report: WorkspaceObservabilityReport,
    *,
    intent: HandoffIntent = HandoffIntent.FUTURE_SELF,
) -> HandoffRedactionPreview:
    readiness = derive_workspace_handoff_readiness(report, intent=intent)
    return _observability_preview(
        readiness,
        included_sections=[
            "runtime",
            "projections",
            "operator_queue",
            "repository_intelligence",
            "memory",
            "artifacts",
            "verification",
            "maintenance_cues",
        ],
        omitted_raw_categories=[
            "raw .glassbox database",
            "raw artifacts",
            "raw command logs",
            "raw provider output",
            "screenshots",
        ],
        unsupported_evidence=[],
    )


def release_redaction_preview_from_report(
    report: WorkspaceObservabilityReport,
    *,
    intent: HandoffIntent = HandoffIntent.RELEASE_SIGNOFF,
) -> HandoffRedactionPreview:
    readiness = derive_release_handoff_readiness(report, intent=intent)
    return _observability_preview(
        readiness,
        included_sections=[
            "retained_eval_evidence",
            "release_surface_freshness",
            "package_check_paths",
            "installed_smoke_paths",
            "advisory_provider_evidence",
            "safe_first_commands",
        ],
        omitted_raw_categories=[
            "raw eval logs",
            "raw provider output",
            "raw dashboard evidence",
            "raw browser evidence",
            "raw accessibility evidence",
        ],
        unsupported_evidence=[],
    )


def _observability_preview(
    readiness: HandoffReadiness,
    *,
    included_sections: list[str],
    omitted_raw_categories: list[str],
    unsupported_evidence: list[str],
) -> HandoffRedactionPreview:
    local_only_counts: dict[str, int] = {}
    for reason in readiness.local_only_evidence:
        key = reason.kind.value
        local_only_counts[key] = local_only_counts.get(key, 0) + 1
    local_only_counts = _positive_counts(local_only_counts)
    local_only_summary = HandoffLocalOnlySummary(
        category_counts=local_only_counts,
        limitations=readiness.limitations,
        safe_local_inspection_commands=readiness.safe_first_commands,
    )
    return HandoffRedactionPreview(
        source=readiness.source,
        intent=readiness.intent,
        included_sections=included_sections,
        redaction=HandoffRedactionSummary(
            posture=HandoffRedactionPosture.LOCAL_ONLY_OMITTED,
            redacted_field_count=0,
            redacted_categories=[],
            limitations=readiness.limitations,
        ),
        local_only=local_only_summary,
        local_only_inventory=build_readiness_local_only_inventory(readiness)
        if readiness.local_only_evidence
        else build_local_only_inventory(
            source=readiness.source,
            intent=readiness.intent,
            summary=local_only_summary,
            omitted_raw_categories=omitted_raw_categories,
        ),
        omitted_raw_categories=omitted_raw_categories,
        unsupported_evidence=unsupported_evidence,
        package_limitations=[
            "preview summarizes retained local posture and does not write a package"
        ],
        safe_inspection_commands=readiness.safe_first_commands,
    )


def _included_sections(payload: Mapping[str, Any]) -> list[str]:
    return [
        key
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    ][:100]


def _redaction_marker_summary(value: Any) -> tuple[int, list[str]]:
    categories: list[str] = []
    count = 0
    for item in _walk_values(value):
        if not isinstance(item, str):
            continue
        redacted = REDACTION_PLACEHOLDER in item
        workspace = WORKSPACE_PLACEHOLDER in item
        if redacted or workspace:
            count += 1
        if redacted:
            categories.append("secret-like-token")
        if workspace:
            categories.append("workspace-path")
    return count, list(dict.fromkeys(categories))


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


def _walk_values(value: Any):
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


def _positive_counts(counts: Mapping[str, int]) -> dict[str, int]:
    return {key: value for key, value in counts.items() if value > 0}


def _safe_command(display: str, purpose: str) -> HandoffSafeCommand:
    return HandoffSafeCommand(
        command=display.split(),
        display=display,
        purpose=purpose,
    )


__all__ = [
    "HandoffRedactionPreview",
    "build_changeset_redaction_preview",
    "build_session_redaction_preview",
    "build_task_redaction_preview",
    "changeset_redaction_preview_from_payload",
    "release_redaction_preview_from_report",
    "session_redaction_preview_from_payload",
    "task_redaction_preview_from_readiness",
    "workspace_redaction_preview_from_report",
]
