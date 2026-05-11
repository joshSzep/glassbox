"""Core deterministic section builders for changeset review briefs."""

from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetSourceKind
from glassbox.core import ChangesetSourceRecord
from glassbox.core import ChangesetVerificationPostureRecord
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.changeset_models import ChangesetCommandEvidenceSummary
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.review_briefs import ReviewBriefEvidenceRef
from glassbox.runtime.review_briefs import ReviewBriefSection


def review_brief_change_summary(
    changeset: ChangesetRecord,
) -> ReviewBriefSection:
    summary = changeset.summary or "No operator-written changeset summary is attached."
    body = (
        f"{summary} Status is {changeset.status}. Risk is "
        f"{changeset.risk_level.value} with "
        f"{changeset.unresolved_risk_count} unresolved and "
        f"{changeset.accepted_risk_count} accepted risk item(s)."
    )
    return ReviewBriefSection(
        title="Change Summary",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="changeset",
                identifier=str(changeset.changeset_id),
                summary="changeset projection supplied objective, summary, and risk",
            )
        ],
    )


def review_brief_inventory_section(
    inventory_record: ChangesetInventoryRecord | None,
    inventory: ChangeInventoryArtifact | None,
    inventory_status: ChangesetInventoryStatus,
) -> ReviewBriefSection:
    if inventory_record is None:
        return ReviewBriefSection(
            title="Changed-File Inventory",
            body="No structured change inventory is attached yet.",
        )
    if inventory is None:
        body = (
            f"Inventory artifact {inventory_record.artifact_id} is projected with "
            f"{inventory_record.changed_path_count} changed path(s), but the "
            "artifact could not be loaded for path details."
        )
    else:
        paths = ", ".join(entry.path for entry in inventory.paths[:10])
        if len(inventory.paths) > 10:
            paths = f"{paths}, and {len(inventory.paths) - 10} more"
        body = (
            f"Inventory records {inventory.summary.changed_path_count} changed "
            f"path(s), {inventory.summary.test_path_count} test path(s), "
            f"{inventory.summary.docs_path_count} docs path(s), and "
            f"{inventory.summary.policy_sensitive_path_count} policy-sensitive "
            f"path(s). Freshness is {inventory_status.freshness.value}."
        )
        if paths:
            body = f"{body} Included paths: {paths}."
    if inventory_status.reason is not None:
        body = f"{body} Freshness note: {inventory_status.reason}."
    return ReviewBriefSection(
        title="Changed-File Inventory",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="inventory",
                identifier=str(inventory_record.artifact_id),
                artifact_id=inventory_record.artifact_id,
                summary=(
                    f"latest inventory has {inventory_record.changed_path_count} "
                    f"path(s) and freshness {inventory_status.freshness.value}"
                ),
                local_only=True,
            )
        ],
    )


def review_brief_provenance_section(
    sources: list[ChangesetSourceRecord],
    inventory: ChangeInventoryArtifact | None,
) -> ReviewBriefSection:
    source_summary = "; ".join(
        f"{source.source_kind.value}: {source.reason}" for source in sources[:8]
    )
    if not source_summary:
        source_summary = "No changeset source records are attached."
    provenance_body = source_summary
    if inventory is not None:
        provenance_body = (
            f"{provenance_body} Path provenance counts: "
            f"{inventory.summary.provenance_direct_path_count} direct, "
            f"{inventory.summary.provenance_inferred_path_count} inferred, "
            f"{inventory.summary.provenance_unknown_path_count} unknown."
        )
    return ReviewBriefSection(
        title="Provenance",
        body=provenance_body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="provenance",
                identifier=f"source-sequence-{source.last_sequence}",
                summary=f"{source.source_kind.value}: {source.reason}",
                artifact_id=source.artifact_id,
                local_only=source.artifact_id is not None,
            )
            for source in sources[:8]
        ],
    )


def review_brief_topology_section(
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection | None:
    impacts = verification_plan.topology_impacts
    if not impacts:
        return None
    lines = []
    refs = []
    for impact in impacts[:8]:
        owners = (
            f"; owners {', '.join(impact.ownership_hints)}"
            if impact.ownership_hints
            else ""
        )
        tests = f"; tests {', '.join(impact.test_roots)}" if impact.test_roots else ""
        deps = (
            f"; dependencies {', '.join(impact.dependency_hints[:4])}"
            if impact.dependency_hints
            else ""
        )
        lines.append(
            f"{impact.name} ({impact.kind}, {impact.root_path}) matched "
            f"{len(impact.matched_paths)} path(s); topology is "
            f"{impact.topology_freshness}{owners}{tests}{deps}."
        )
        refs.append(
            ReviewBriefEvidenceRef(
                kind="provenance",
                identifier=impact.component_id,
                summary=(
                    f"{impact.name} matched {len(impact.matched_paths)} "
                    f"path(s) with {impact.recommendation_posture} topology posture"
                ),
            )
        )
    body = " ".join(lines)
    return ReviewBriefSection(
        title="Affected Subsystems",
        body=body,
        evidence_refs=refs,
    )


def review_brief_verification_section(
    verification_posture: ChangesetVerificationPostureRecord | None,
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection:
    readiness = verification_plan.readiness
    body = (
        f"Readiness is {readiness.state.value}: {readiness.summary}. "
        f"Counts are {readiness.failed_count} failed, {readiness.stale_count} stale, "
        f"{readiness.missing_count} missing, and "
        f"{readiness.accepted_risk_count} accepted risk."
    )
    if verification_posture is None:
        body = f"{body} No retained changeset verification posture is attached yet."
    else:
        body = (
            f"{body} Latest retained posture is "
            f"{verification_posture.state.value}: {verification_posture.summary}."
        )
    if verification_plan.recommended_targets or verification_plan.release_surfaces:
        body = (
            f"{body} Path-to-verification guidance names "
            f"{len(verification_plan.recommended_targets)} recommended target(s), "
            f"{len(verification_plan.recipes)} recipe(s), and "
            f"{len(verification_plan.release_surfaces)} release surface(s)."
        )
    if verification_plan.stale_evidence:
        body = (
            f"{body} Stale evidence guidance names "
            f"{len(verification_plan.stale_evidence)} stale or missing item(s)."
        )
    plan_summary = verification_plan.plan_summary
    if plan_summary.total_count:
        body = (
            f"{body} Plan lifecycle tracks {plan_summary.total_count} check(s): "
            f"{plan_summary.selected_count} selected, "
            f"{plan_summary.passed_count} passed, "
            f"{plan_summary.failed_count} failed, "
            f"{plan_summary.skipped_count} skipped, "
            f"{plan_summary.stale_count} stale, and "
            f"{plan_summary.accepted_risk_count} accepted risk."
        )
    refs = []
    if verification_posture is not None:
        refs.append(
            ReviewBriefEvidenceRef(
                kind="verification",
                identifier=str(
                    verification_posture.verification_id
                    or verification_posture.last_sequence
                ),
                verification_id=verification_posture.verification_id,
                artifact_id=verification_posture.artifact_id,
                summary=verification_posture.summary,
                local_only=verification_posture.artifact_id is not None,
            )
        )
    refs.extend(
        ReviewBriefEvidenceRef(
            kind="verification",
            identifier=requirement.requirement_id,
            verification_id=requirement.verification_id,
            artifact_id=requirement.artifact_id,
            summary=f"{requirement.state.value}: {requirement.reason}",
            local_only=requirement.artifact_id is not None,
        )
        for requirement in readiness.requirements[:8]
    )
    return ReviewBriefSection(title="Verification", body=body, evidence_refs=refs)


def review_brief_command_evidence_section(
    command_evidence: ChangesetCommandEvidenceSummary,
) -> ReviewBriefSection:
    if command_evidence.total_count == 0:
        body = "No retained command evidence matched this changeset."
    else:
        body = (
            f"Command evidence includes {command_evidence.total_count} retained "
            f"attempt(s): {command_evidence.verification_count} verification, "
            f"{command_evidence.failed_count} failed, "
            f"{command_evidence.risky_count} publish/deploy/destructive-risk, "
            f"{command_evidence.environment_captured_count} with redacted "
            "environment posture, and "
            f"{command_evidence.artifact_count} with output artifact references."
        )
    refs = [
        ReviewBriefEvidenceRef(
            kind="command",
            identifier=item.tool_attempt_id,
            artifact_id=item.output_artifact_id,
            summary=(
                f"{item.purpose}/{item.status}: {item.summary}; "
                f"environment captured {item.environment_captured}"
            ),
            local_only=item.local_only,
        )
        for item in command_evidence.items[:8]
    ]
    return ReviewBriefSection(title="Command Evidence", body=body, evidence_refs=refs)


def review_brief_branch_candidate_section(
    changeset: ChangesetRecord,
    sources: list[ChangesetSourceRecord],
) -> ReviewBriefSection | None:
    if changeset.branch_search_id is None and changeset.branch_candidate_id is None:
        return None
    candidate_sources = [
        source
        for source in sources
        if source.source_kind == ChangesetSourceKind.BRANCH_SEARCH_CANDIDATE
    ]
    body = (
        f"Branch search {changeset.branch_search_id} selected candidate "
        f"{changeset.branch_candidate_id}. No workspace mutation is claimed by "
        "this review brief."
    )
    return ReviewBriefSection(
        title="Branch-Candidate Rationale",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="branch_candidate",
                identifier=str(source.branch_candidate_id or source.last_sequence),
                artifact_id=source.artifact_id,
                summary=source.reason,
                local_only=source.artifact_id is not None,
            )
            for source in candidate_sources
        ],
    )


def review_brief_risk_section(
    changeset: ChangesetRecord,
    inventory: ChangeInventoryArtifact | None,
) -> ReviewBriefSection:
    body = (
        f"Changeset risk is {changeset.risk_level.value}. "
        f"{changeset.unresolved_risk_count} unresolved and "
        f"{changeset.accepted_risk_count} accepted risk item(s) are projected."
    )
    if changeset.risk_summary is not None:
        body = f"{body} Summary: {changeset.risk_summary}."
    if inventory is not None:
        body = (
            f"{body} Inventory risk counts: "
            f"{inventory.summary.high_risk_path_count} high, "
            f"{inventory.summary.medium_risk_path_count} medium, "
            f"{inventory.summary.low_risk_path_count} low."
        )
    return ReviewBriefSection(
        title="Risks",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="risk",
                identifier=str(changeset.changeset_id),
                summary=body,
            )
        ],
    )


__all__ = [
    "review_brief_branch_candidate_section",
    "review_brief_change_summary",
    "review_brief_command_evidence_section",
    "review_brief_inventory_section",
    "review_brief_provenance_section",
    "review_brief_risk_section",
    "review_brief_topology_section",
    "review_brief_verification_section",
]
