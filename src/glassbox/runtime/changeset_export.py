"""Reviewer-safe changeset export packages."""

import json
from collections.abc import Iterable
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
from glassbox.core import HandoffIntent
from glassbox.core import HandoffLocalOnlyInventory
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ReviewFeedbackRecord
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.changesets import ChangesetVerificationService
from glassbox.runtime.evidence_graph import build_changeset_evidence_graph
from glassbox.runtime.evidence_graph import reviewer_safe_graph_slice
from glassbox.runtime.evidence_graph import summarize_evidence_graph
from glassbox.runtime.handoff_export_profiles import HandoffExportProfile
from glassbox.runtime.handoff_export_profiles import build_handoff_export_profile
from glassbox.runtime.handoff_local_only_inventory import (
    build_changeset_local_only_inventory,
)
from glassbox.runtime.handoff_markdown import (
    build_changeset_export_markdown as render_changeset_export_markdown,
)
from glassbox.runtime.handoff_readiness import ChangesetHandoffReadinessService
from glassbox.runtime.handoff_readiness import preview_handoff_readiness
from glassbox.runtime.session_export_redaction import RedactionContext
from glassbox.runtime.session_export_redaction import redact_optional_text
from glassbox.runtime.skipped_evidence import is_skipped_live_evidence
from glassbox.runtime.skipped_evidence import skipped_evidence_reason
from glassbox.runtime.skipped_evidence import skipped_evidence_state
from glassbox.runtime.skipped_evidence import skipped_live_evidence_counts
from glassbox.services import ArtifactRepository

CHANGESET_EXPORT_KIND = "changeset_review_export"
CHANGESET_EXPORT_VERSION = 1
CHANGESET_EXPORT_OMITTED_RAW_CATEGORIES = [
    "raw .glassbox database",
    "raw command output",
    "raw provider transcripts",
    "raw manual evidence text",
    "raw external logs",
    "raw diffs",
    "raw file contents",
    "raw screenshots",
    "browser traces",
    "accessibility transcripts",
]


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
    evidence_graph: dict[str, Any]
    verification: dict[str, Any]
    repository_intelligence_limitations: list[str] = Field(default_factory=list)
    handoff_readiness: dict[str, Any]
    review_brief: dict[str, Any] | None = None
    review_feedback: dict[str, Any]
    review_responses: dict[str, Any]
    manual_evidence: dict[str, Any]
    live_review_evidence: dict[str, Any]
    readiness: list[dict[str, Any]] = Field(default_factory=list)
    artifact_references: list[ChangesetExportArtifactReference] = Field(
        default_factory=list
    )
    profile: HandoffExportProfile | None = None
    recipient: str | None = None
    expected_custodian: str | None = None
    exported_by: str | None = None
    note: str | None = None
    local_only_inventory: HandoffLocalOnlyInventory
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
    intent: HandoffIntent = HandoffIntent.REVIEW_ONLY,
    recipient: str | None = None,
    expected_custodian: str | None = None,
    exported_by: str | None = None,
    note: str | None = None,
    output_format: str = "json",
    markdown_output_path: Path | None = None,
) -> Path:
    """Write one reviewer-safe changeset export package."""

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
    if markdown_output_path is not None:
        resolved_markdown_output = markdown_output_path.resolve()
        resolved_markdown_output.parent.mkdir(parents=True, exist_ok=True)
        resolved_markdown_output.write_text(
            build_changeset_export_markdown(payload),
            encoding="utf-8",
        )
    return resolved_output


def build_changeset_export_payload(
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
    evidence_graph = reviewer_safe_graph_slice(
        build_changeset_evidence_graph(detail, verification_plan=verification_plan)
    )
    handoff_readiness = _handoff_readiness_summary_for_export(
        changeset_id,
        repository=repository,
        artifact_repository=artifact_repository,
        workspace_root=workspace_root,
    )
    latest_brief = detail.review_briefs[0] if detail.review_briefs else None
    redaction_context = RedactionContext(workspace_root=workspace_root.resolve())
    source = HandoffSourceRef(
        kind=HandoffSourceKind.CHANGESET,
        primary_id=str(detail.changeset.changeset_id),
        identifiers={"session_id": str(detail.changeset.session_id)},
        label=detail.changeset.summary or detail.changeset.objective,
    )
    return ChangesetExportPayload(
        exported_at=datetime.now(UTC),
        changeset=_changeset_summary(detail.changeset),
        sources=[_source_summary(source) for source in detail.sources],
        inventory=_inventory_summary(detail),
        evidence_graph=_evidence_graph_summary(evidence_graph),
        verification=_verification_summary(detail, verification_plan),
        repository_intelligence_limitations=_repository_intelligence_limitations(
            verification_plan
        ),
        handoff_readiness=handoff_readiness,
        review_brief=_review_brief_summary(
            latest_brief,
            detail.changeset.session_id,
            artifact_repository,
        ),
        review_feedback=_review_feedback_summary(detail.review_feedback),
        review_responses=detail.review_response_summary.model_dump(mode="json"),
        manual_evidence=_manual_evidence_summary(detail.manual_evidence),
        live_review_evidence=_live_review_evidence_summary(detail.manual_evidence),
        readiness=[item.model_dump(mode="json") for item in detail.readiness],
        artifact_references=_artifact_references(detail, verification_plan),
        profile=build_handoff_export_profile(
            source=source,
            package_kind=HandoffPackageKind.CHANGESET,
            intent=intent,
            output_format=output_format,
            included_sections=[
                "changeset",
                "evidence_graph",
                "verification",
                "handoff_readiness",
                "local_only_inventory",
            ],
        ),
        recipient=redact_optional_text(recipient, redaction_context),
        expected_custodian=redact_optional_text(
            expected_custodian,
            redaction_context,
        ),
        exported_by=redact_optional_text(exported_by, redaction_context),
        note=redact_optional_text(note, redaction_context),
        local_only_inventory=build_changeset_local_only_inventory(
            detail,
            verification_plan,
            source=source,
            intent=intent,
            omitted_raw_categories=CHANGESET_EXPORT_OMITTED_RAW_CATEGORIES,
        ),
        redaction_report=[
            "raw .glassbox database state is not included",
            "raw command output is not included",
            "raw provider transcripts are not included",
            "raw manual evidence text and raw external logs are not included",
            "raw diffs and file contents are not included",
            (
                "raw screenshots, browser traces, and accessibility transcripts "
                "are not included"
            ),
            "artifact paths remain local-only references by artifact ID",
        ],
        non_claims=[
            (
                "export package is a summary index, not proof every changed "
                "line was reviewed"
            ),
            "stale verification is not treated as fresh",
            "review feedback response state is not reviewer approval",
            "manual evidence is not retained Glassbox command evidence",
            "browser, dashboard, and accessibility evidence remains advisory",
            "local-only artifacts are not shareable without separate review",
            "commit, push, PR, and merge remain explicit operator actions",
            "export package does not publish the changeset",
        ],
        safe_inspection_commands=detail.safe_next_actions,
    )


def inspect_changeset_export_package(bundle_path: Path) -> dict[str, Any]:
    """Return an inspect-only summary for a changeset export package."""

    payload = ChangesetExportPayload.model_validate_json(
        bundle_path.read_text(encoding="utf-8")
    )
    return changeset_export_inspection_summary(payload, bundle_path=bundle_path)


def changeset_export_inspection_summary(
    payload: ChangesetExportPayload,
    *,
    bundle_path: Path | None = None,
) -> dict[str, Any]:
    """Build a compact inspection summary without importing local state."""

    evidence_graph = payload.evidence_graph.get("summary", {})
    return {
        "bundle_path": str(bundle_path.resolve()) if bundle_path is not None else None,
        "export_kind": payload.export_kind,
        "schema_version": payload.schema_version,
        "changeset_id": payload.changeset["changeset_id"],
        "status": payload.changeset["status"],
        "verification_state": payload.verification["readiness"]["state"],
        "handoff_state": payload.handoff_readiness["state"],
        "feedback_count": payload.review_feedback["total_count"],
        "manual_evidence_count": payload.manual_evidence["total_count"],
        "profile_id": (
            payload.profile.profile_id.value if payload.profile is not None else None
        ),
        "local_only_evidence_count": payload.local_only_inventory.total_count,
        "evidence_graph_node_count": evidence_graph.get("node_count", 0),
        "evidence_graph_claim_count": evidence_graph.get("claim_count", 0),
        "redaction_report_count": len(payload.redaction_report),
        "non_claims": payload.non_claims,
        "safe_inspection_commands": payload.safe_inspection_commands,
    }


def build_changeset_export_markdown(payload: ChangesetExportPayload) -> str:
    """Render a compact reviewer-safe Markdown summary."""

    return render_changeset_export_markdown(payload)


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
        "recommended_targets": [
            target.model_dump(mode="json")
            for target in verification_plan.recommended_targets
        ],
        "release_surfaces": [
            surface.model_dump(mode="json")
            for surface in verification_plan.release_surfaces
        ],
        "stale_evidence": [
            target.model_dump(mode="json")
            for target in verification_plan.stale_evidence
        ],
        "retained_artifact_ids": [
            str(artifact_id) for artifact_id in verification_plan.retained_artifact_ids
        ],
        "non_claims": verification_plan.non_claims,
    }


def _evidence_graph_summary(graph) -> dict[str, Any]:
    return {
        "summary": summarize_evidence_graph(graph).model_dump(mode="json"),
        "reviewer_safe_graph": graph.model_dump(mode="json", exclude_none=True),
        "non_claims": [
            "evidence graph is a derived view, not a second source of truth",
            "reviewer-safe graph slices omit operator-only and local-only nodes",
            "graph edges explain evidence relationships but do not approve changes",
        ],
    }


def _repository_intelligence_limitations(
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[str]:
    limitations = [
        limitation
        for limitation in verification_plan.limitations
        if _mentions_repository_intelligence(limitation)
    ]
    for recipe in verification_plan.recipes:
        limitations.extend(
            limitation
            for limitation in recipe.limitations
            if _mentions_repository_intelligence(limitation)
        )
    return list(dict.fromkeys(limitations))


def _mentions_repository_intelligence(value: str) -> bool:
    lowered = value.lower()
    return (
        "repository intelligence" in lowered
        or "repository index" in lowered
        or "topology" in lowered
        or "recipe" in lowered
    )


def _handoff_readiness_summary(handoff) -> dict[str, Any]:
    return {
        "readiness_kind": handoff.readiness_kind,
        "state": handoff.state,
        "reason": handoff.reason,
        "blockers": handoff.blockers,
        "limitations": handoff.limitations,
        "safe_next_actions": handoff.safe_next_actions,
        "verification_plan_summary": handoff.verification_plan_summary.model_dump(
            mode="json"
        ),
        "evidence": handoff.evidence.model_dump(mode="json"),
        "shared_readiness": handoff.shared_readiness.model_dump(mode="json"),
        "non_claims": handoff.non_claims,
    }


def _handoff_readiness_summary_for_export(
    changeset_id: ChangesetId,
    *,
    repository: ChangesetRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
) -> dict[str, Any]:
    try:
        return _handoff_readiness_summary(
            preview_handoff_readiness(
                ChangesetHandoffReadinessService(repository, artifact_repository),
                changeset_id,
                workspace_root,
            )
        )
    except Exception as exc:
        reason = _bounded_text(f"handoff readiness could not be derived: {exc}")
        return {
            "readiness_kind": "handoff",
            "state": "blocked",
            "reason": reason,
            "blockers": [reason],
            "limitations": [
                "handoff readiness is unavailable in this export; inspect locally"
            ],
            "safe_next_actions": [
                f"glassbox changeset handoff-readiness {changeset_id} --cwd ."
            ],
            "verification_plan_summary": None,
            "evidence": None,
            "shared_readiness": None,
            "non_claims": [
                "handoff readiness fallback is local export posture, not publication"
            ],
        }


def _bounded_text(value: str, *, limit: int = 1000) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


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
        summary["schema_version"] = artifact.get("schema_version")
        summary["lifecycle_summary"] = artifact.get("lifecycle_summary")
        summary["review_feedback"] = artifact.get("review_feedback")
        summary["review_responses"] = artifact.get("review_responses")
        summary["manual_evidence"] = artifact.get("manual_evidence")
        summary["live_review_evidence"] = artifact.get("live_review_evidence")
        summary["stale_verification"] = artifact.get("stale_verification")
        summary["publication_boundary"] = artifact.get("publication_boundary")
        summary["non_claims"] = artifact.get("non_claims", [])
        summary["limitations"] = artifact.get("limitations", [])
        summary["limitation_summary"] = artifact.get("limitation_summary")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        summary["limitations"] = [f"review brief artifact could not be read: {exc}"]
    return summary


def _review_feedback_summary(feedback: list[ReviewFeedbackRecord]) -> dict[str, Any]:
    return {
        "total_count": len(feedback),
        "disposition_counts": _value_counts(
            item.disposition.value for item in feedback
        ),
        "kind_counts": _value_counts(item.feedback_kind.value for item in feedback),
        "items": [
            {
                "feedback_id": str(item.feedback_id),
                "feedback_kind": item.feedback_kind.value,
                "provenance": item.provenance.value,
                "disposition": item.disposition.value,
                "summary": item.summary,
                "reviewer_label": item.reviewer_label,
                "artifact_id": (
                    str(item.artifact_id) if item.artifact_id is not None else None
                ),
                "verification_id": (
                    str(item.verification_id)
                    if item.verification_id is not None
                    else None
                ),
                "residual_risk": item.residual_risk,
                "risk_summary": item.risk_summary,
                "last_sequence": item.last_sequence,
            }
            for item in feedback[:20]
        ],
    }


def _manual_evidence_summary(evidence: list[ManualEvidenceRecord]) -> dict[str, Any]:
    return {
        "total_count": len(evidence),
        "local_only_count": sum(1 for item in evidence if item.local_only),
        "kind_counts": _value_counts(item.evidence_kind.value for item in evidence),
        "state_counts": _value_counts(item.state.value for item in evidence),
        "items": [_manual_evidence_item(item) for item in evidence[:20]],
        "non_claims": [
            "manual evidence summaries are not retained command evidence",
            "raw manual evidence text, screenshots, and logs are not included",
        ],
    }


def _live_review_evidence_summary(
    evidence: list[ManualEvidenceRecord],
) -> dict[str, Any]:
    live_evidence = [
        item
        for item in evidence
        if item.evidence_kind
        in {
            ManualEvidenceKind.BROWSER_OBSERVATION,
            ManualEvidenceKind.SCREENSHOT,
            ManualEvidenceKind.ACCESSIBILITY_NOTE,
        }
    ]
    (
        skipped_live_evidence_count,
        skipped_browser_evidence_count,
        skipped_accessibility_evidence_count,
    ) = skipped_live_evidence_counts(live_evidence)
    return {
        "total_count": len(live_evidence),
        "browser_evidence_count": sum(
            1
            for item in live_evidence
            if item.evidence_kind
            in {
                ManualEvidenceKind.BROWSER_OBSERVATION,
                ManualEvidenceKind.SCREENSHOT,
            }
        ),
        "accessibility_evidence_count": sum(
            1
            for item in live_evidence
            if item.evidence_kind == ManualEvidenceKind.ACCESSIBILITY_NOTE
        ),
        "skipped_live_evidence_count": skipped_live_evidence_count,
        "skipped_browser_evidence_count": skipped_browser_evidence_count,
        "skipped_accessibility_evidence_count": skipped_accessibility_evidence_count,
        "kind_counts": _value_counts(
            item.evidence_kind.value for item in live_evidence
        ),
        "skipped_items": [
            _manual_evidence_item(item)
            for item in live_evidence
            if is_skipped_live_evidence(item)
        ][:20],
        "items": [_manual_evidence_item(item) for item in live_evidence[:20]],
        "non_claims": [
            "live browser, dashboard, and accessibility evidence is advisory",
            "skipped live evidence is not a pass or release authority",
            (
                "raw screenshots, browser traces, and accessibility transcripts "
                "are not included"
            ),
        ],
    }


def _manual_evidence_item(item: ManualEvidenceRecord) -> dict[str, Any]:
    return {
        "evidence_id": str(item.evidence_id),
        "evidence_kind": item.evidence_kind.value,
        "state": item.state.value,
        "target_kind": item.target_kind.value,
        "target_id": item.target_id,
        "feedback_id": str(item.feedback_id) if item.feedback_id is not None else None,
        "artifact_id": str(item.artifact_id) if item.artifact_id is not None else None,
        "summary": item.summary,
        "source_label": item.source_label,
        "local_only": item.local_only,
        "redaction_status": item.redaction_status.value,
        "freshness": item.freshness.value,
        "capture_state": skipped_evidence_state(item),
        "skip_reason": skipped_evidence_reason(item),
        "skipped_live_evidence": is_skipped_live_evidence(item),
        "limitations": item.limitations,
        "non_claims": item.non_claims,
        "last_sequence": item.last_sequence,
    }


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
    for item in detail.review_response_summary.items:
        if item.latest_fixup_inventory_artifact_id is not None:
            references.append(
                ChangesetExportArtifactReference(
                    artifact_id=item.latest_fixup_inventory_artifact_id,
                    artifact_kind="review_feedback_fixup_inventory",
                    summary="summary-only review response fixup inventory",
                )
            )
    for item in detail.manual_evidence:
        if item.artifact_id is not None:
            references.append(
                ChangesetExportArtifactReference(
                    artifact_id=item.artifact_id,
                    artifact_kind="manual_evidence",
                    summary=(f"{item.evidence_kind.value} manual evidence summary"),
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


def _value_counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


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
    "build_changeset_export_markdown",
    "build_changeset_export_payload",
    "changeset_export_inspection_summary",
    "export_changeset_package",
    "inspect_changeset_export_package",
]
