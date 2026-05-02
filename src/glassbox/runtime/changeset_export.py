"""Reviewer-safe changeset export packages."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ChangesetSourceRecord
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.changesets import ChangesetVerificationService
from glassbox.services import ArtifactRepository

CHANGESET_EXPORT_KIND = "changeset_review_export"
CHANGESET_EXPORT_VERSION = 1


class ChangesetExportArtifactReference(BaseModel):
    """Portable reference to retained local evidence without raw contents."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: ArtifactId
    artifact_kind: str
    local_only: bool = True
    summary: str


class ChangesetExportPayload(BaseModel):
    """Reviewer-safe package centered on one changeset."""

    model_config = ConfigDict(extra="forbid")

    export_kind: str = CHANGESET_EXPORT_KIND
    schema_version: int = CHANGESET_EXPORT_VERSION
    exported_at: datetime
    changeset: dict[str, Any]
    sources: list[dict[str, Any]]
    inventory: dict[str, Any] | None = None
    verification: dict[str, Any]
    review_brief: dict[str, Any] | None = None
    readiness: list[dict[str, Any]] = Field(default_factory=list)
    artifact_references: list[ChangesetExportArtifactReference] = Field(
        default_factory=list
    )
    redaction_report: list[str]
    non_claims: list[str]
    safe_inspection_commands: list[str]


def export_changeset_package(
    changeset_id: ChangesetId,
    output_path: Path,
    *,
    repository: ChangesetRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
) -> Path:
    """Write one reviewer-safe changeset export package."""

    payload = build_changeset_export_payload(
        changeset_id,
        repository=repository,
        artifact_repository=artifact_repository,
        workspace_root=workspace_root,
    )
    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(
        json.dumps(
            payload.model_dump(mode="json", exclude_none=True),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return resolved_output


def build_changeset_export_payload(
    changeset_id: ChangesetId,
    *,
    repository: ChangesetRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
) -> ChangesetExportPayload:
    """Build a changeset-centered handoff payload from retained evidence."""

    detail = ChangesetQueryService(repository).get_detail(
        changeset_id,
        workspace_root=workspace_root,
    )
    verification_plan = ChangesetVerificationService(
        repository,
        artifact_repository,
    ).preview_plan(changeset_id, workspace_root)
    latest_brief = detail.review_briefs[0] if detail.review_briefs else None
    return ChangesetExportPayload(
        exported_at=datetime.now(UTC),
        changeset=_changeset_summary(detail.changeset),
        sources=[_source_summary(source) for source in detail.sources],
        inventory=_inventory_summary(detail),
        verification=_verification_summary(detail, verification_plan),
        review_brief=_review_brief_summary(
            latest_brief,
            detail.changeset.session_id,
            artifact_repository,
        ),
        readiness=[item.model_dump(mode="json") for item in detail.readiness],
        artifact_references=_artifact_references(detail, verification_plan),
        redaction_report=[
            "raw .glassbox database state is not included",
            "raw command output is not included",
            "raw provider transcripts are not included",
            "raw diffs and file contents are not included",
            "artifact paths remain local-only references by artifact ID",
        ],
        non_claims=[
            (
                "export package is a summary index, not proof every changed "
                "line was reviewed"
            ),
            "stale verification is not treated as fresh",
            "local-only artifacts are not shareable without separate review",
            "commit, push, PR, and merge remain explicit operator actions",
        ],
        safe_inspection_commands=detail.safe_next_actions,
    )


def _changeset_summary(changeset: ChangesetRecord) -> dict[str, Any]:
    return {
        "session_id": str(changeset.session_id),
        "changeset_id": str(changeset.changeset_id),
        "objective": changeset.objective,
        "summary": changeset.summary,
        "status": changeset.status,
        "task_id": str(changeset.task_id) if changeset.task_id is not None else None,
        "branch_search_id": (
            str(changeset.branch_search_id)
            if changeset.branch_search_id is not None
            else None
        ),
        "branch_candidate_id": (
            str(changeset.branch_candidate_id)
            if changeset.branch_candidate_id is not None
            else None
        ),
        "latest_inventory_artifact_id": (
            str(changeset.latest_inventory_artifact_id)
            if changeset.latest_inventory_artifact_id is not None
            else None
        ),
        "latest_verification_id": (
            str(changeset.latest_verification_id)
            if changeset.latest_verification_id is not None
            else None
        ),
        "latest_review_brief_artifact_id": (
            str(changeset.latest_review_brief_artifact_id)
            if changeset.latest_review_brief_artifact_id is not None
            else None
        ),
        "risk_level": changeset.risk_level.value,
        "risk_summary": changeset.risk_summary,
        "unresolved_risk_count": changeset.unresolved_risk_count,
        "accepted_risk_count": changeset.accepted_risk_count,
    }


def _source_summary(source: ChangesetSourceRecord) -> dict[str, Any]:
    return {
        "source_kind": source.source_kind.value,
        "source_session_id": (
            str(source.source_session_id)
            if source.source_session_id is not None
            else None
        ),
        "task_id": str(source.task_id) if source.task_id is not None else None,
        "branch_search_id": (
            str(source.branch_search_id)
            if source.branch_search_id is not None
            else None
        ),
        "branch_candidate_id": (
            str(source.branch_candidate_id)
            if source.branch_candidate_id is not None
            else None
        ),
        "verification_id": (
            str(source.verification_id) if source.verification_id is not None else None
        ),
        "artifact_id": str(source.artifact_id)
        if source.artifact_id is not None
        else None,
        "reason": source.reason,
        "limitation": source.limitation,
        "last_sequence": source.last_sequence,
    }


def _inventory_summary(detail: ChangesetDetailView) -> dict[str, Any] | None:
    inventory = detail.inventory
    if inventory is None:
        return None
    return {
        "artifact_id": str(inventory.artifact_id),
        "freshness": detail.inventory_status.freshness.value,
        "stale": detail.inventory_status.stale,
        "freshness_reason": detail.inventory_status.reason,
        "changed_path_count": inventory.changed_path_count,
        "risk_level": inventory.risk_level.value,
        "risk_summary": inventory.risk_summary,
        "unresolved_risk_count": inventory.unresolved_risk_count,
        "accepted_risk_count": inventory.accepted_risk_count,
        "source_digest_present": inventory.source_digest is not None,
        "previous_artifact_id": (
            str(inventory.previous_artifact_id)
            if inventory.previous_artifact_id is not None
            else None
        ),
    }


def _verification_summary(
    detail: ChangesetDetailView,
    verification_plan: ChangesetVerificationPlanPreview,
) -> dict[str, Any]:
    posture = detail.verification_posture
    return {
        "posture": posture.model_dump(mode="json") if posture is not None else None,
        "readiness": verification_plan.readiness.model_dump(mode="json"),
        "recommended_commands": verification_plan.recommended_commands,
        "retained_artifact_ids": [
            str(artifact_id) for artifact_id in verification_plan.retained_artifact_ids
        ],
        "non_claims": verification_plan.non_claims,
    }


def _review_brief_summary(
    brief: ChangesetReviewBriefRecord | None,
    session_id,
    artifact_repository: ArtifactRepository,
) -> dict[str, Any] | None:
    if brief is None:
        return None
    summary: dict[str, Any] = brief.model_dump(mode="json")
    try:
        content = artifact_repository.read_text_artifact(
            _review_brief_artifact_path(session_id, brief.artifact_id)
        )
        artifact = json.loads(content)
        summary["objective"] = artifact.get("objective")
        summary["non_claims"] = artifact.get("non_claims", [])
        summary["limitations"] = artifact.get("limitations", [])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        summary["limitations"] = [f"review brief artifact could not be read: {exc}"]
    return summary


def _artifact_references(
    detail: ChangesetDetailView,
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[ChangesetExportArtifactReference]:
    references: list[ChangesetExportArtifactReference] = []
    if detail.inventory is not None:
        references.append(
            ChangesetExportArtifactReference(
                artifact_id=detail.inventory.artifact_id,
                artifact_kind="changeset_change_inventory",
                summary="structured changed-file inventory summary",
            )
        )
    for brief in detail.review_briefs[:3]:
        references.append(
            ChangesetExportArtifactReference(
                artifact_id=brief.artifact_id,
                artifact_kind="changeset_review_brief",
                summary="reviewer-safe brief artifact",
            )
        )
    for artifact_id in verification_plan.retained_artifact_ids:
        references.append(
            ChangesetExportArtifactReference(
                artifact_id=artifact_id,
                artifact_kind="verification_evidence",
                summary="retained verification evidence artifact",
            )
        )
    deduped: dict[str, ChangesetExportArtifactReference] = {}
    for reference in references:
        deduped[str(reference.artifact_id)] = reference
    return list(deduped.values())


def _review_brief_artifact_path(session_id, artifact_id: ArtifactId) -> Path:
    return (
        Path(".glassbox")
        / "sessions"
        / str(session_id)
        / "artifacts"
        / f"{artifact_id}.changeset-review-brief.json"
    )


__all__ = [
    "CHANGESET_EXPORT_KIND",
    "CHANGESET_EXPORT_VERSION",
    "ChangesetExportArtifactReference",
    "ChangesetExportPayload",
    "build_changeset_export_payload",
    "export_changeset_package",
]
