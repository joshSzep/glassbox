"""Runtime service for deriving and inspecting reviewable changesets."""

from collections.abc import Iterable
from typing import Literal

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetSourceKind
from glassbox.core import ChangesetSourceRecord
from glassbox.core import ChangesetVerificationPostureRecord
from glassbox.core import ChangesetVerificationState
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ReviewFeedbackRecord
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.changeset_models import ChangesetCommandEvidenceSummary
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.changeset_safe_commands import changeset_brief_command
from glassbox.runtime.changeset_safe_commands import changeset_verification_plan_command
from glassbox.runtime.changeset_safe_commands import show_changeset_command
from glassbox.runtime.review_briefs import ReviewBriefArtifact
from glassbox.runtime.review_briefs import ReviewBriefEvidenceRef
from glassbox.runtime.review_briefs import ReviewBriefLimitationSummary
from glassbox.runtime.review_briefs import ReviewBriefSection
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary

_REVIEW_BRIEF_LIMITATION_CAP = 20
_REVIEW_BRIEF_OVERFLOW_SUMMARY_SLOT = 1


def _review_brief_artifact(
    *,
    changeset: ChangesetRecord,
    sources: list[ChangesetSourceRecord],
    inventory_record: ChangesetInventoryRecord | None,
    inventory: ChangeInventoryArtifact | None,
    inventory_status: ChangesetInventoryStatus,
    verification_posture: ChangesetVerificationPostureRecord | None,
    verification_plan: ChangesetVerificationPlanPreview,
    command_evidence: ChangesetCommandEvidenceSummary,
    review_feedback: list[ReviewFeedbackRecord],
    review_response_summary: ChangesetReviewResponseSummary,
    manual_evidence: list[ManualEvidenceRecord],
    limitations: list[str],
    limitation_summary: ReviewBriefLimitationSummary | None,
) -> ReviewBriefArtifact:
    return ReviewBriefArtifact(
        changeset_id=changeset.changeset_id,
        session_id=changeset.session_id,
        task_id=changeset.task_id,
        branch_search_id=changeset.branch_search_id,
        branch_candidate_id=changeset.branch_candidate_id,
        local_only=_review_brief_local_only(
            sources,
            inventory_record,
            verification_posture,
            command_evidence,
            manual_evidence,
        ),
        objective=changeset.objective,
        change_summary=_review_brief_change_summary(changeset),
        changed_file_inventory=_review_brief_inventory_section(
            inventory_record,
            inventory,
            inventory_status,
        ),
        affected_subsystems=_review_brief_topology_section(verification_plan),
        provenance=_review_brief_provenance_section(sources, inventory),
        lifecycle_summary=_review_brief_lifecycle_section(
            changeset,
            review_response_summary,
            manual_evidence,
            verification_plan,
        ),
        review_feedback=_review_brief_feedback_section(review_feedback),
        review_responses=_review_brief_response_section(review_response_summary),
        manual_evidence=_review_brief_manual_evidence_section(manual_evidence),
        live_review_evidence=_review_brief_live_evidence_section(manual_evidence),
        verification=_review_brief_verification_section(
            verification_posture,
            verification_plan,
        ),
        stale_verification=_review_brief_stale_verification_section(
            review_response_summary,
            verification_plan,
        ),
        command_evidence=_review_brief_command_evidence_section(command_evidence),
        branch_candidate_rationale=_review_brief_branch_candidate_section(
            changeset,
            sources,
        ),
        publication_boundary=_review_brief_publication_boundary_section(changeset),
        risks=_review_brief_risk_section(changeset, inventory),
        non_claims=[
            "review brief is a deterministic lifecycle summary, not proof",
            "raw command output is not included",
            "raw manual evidence, screenshots, and browser traces are not included",
            "raw diffs and file contents are not included",
            "review feedback response does not imply reviewer acceptance",
            "manual evidence is advisory unless retained verification supports it",
            "handoff posture is advisory and does not mean publication occurred",
            "commit, push, PR, and merge remain explicit operator actions",
        ],
        reviewer_checklist=_reviewer_checklist(changeset, verification_plan),
        safe_inspection_commands=_review_brief_safe_commands(
            changeset,
            verification_plan,
        ),
        limitations=limitations,
        limitation_summary=limitation_summary,
    )


def _review_brief_change_summary(
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


def _review_brief_inventory_section(
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


def _review_brief_provenance_section(
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


def _review_brief_topology_section(
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


def _review_brief_lifecycle_section(
    changeset: ChangesetRecord,
    response_summary: ChangesetReviewResponseSummary,
    manual_evidence: list[ManualEvidenceRecord],
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection:
    review_loop = verification_plan.review_loop_summary
    body = (
        f"Lifecycle summary for changeset {changeset.changeset_id}: "
        f"{response_summary.total_feedback_count} feedback item(s), "
        f"{response_summary.unresolved_count} unresolved, "
        f"{response_summary.stale_response_count} stale response(s), "
        f"{response_summary.accepted_risk_count} accepted-risk response(s), "
        f"{len(manual_evidence)} manual evidence item(s), and verification "
        f"readiness {verification_plan.readiness.state.value}. "
        "The lifecycle brief summarizes retained local evidence and does not "
        "claim reviewer approval or publication."
    )
    return ReviewBriefSection(
        title="Lifecycle Summary",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="readiness",
                identifier=f"review-loop-{changeset.changeset_id}",
                summary=(
                    f"verification preview has "
                    f"{review_loop.open_feedback_count} open feedback item(s), "
                    f"{review_loop.stale_response_count} stale response(s), and "
                    f"{review_loop.manual_evidence_count} manual evidence item(s)"
                ),
            )
        ],
    )


def _review_brief_feedback_section(
    feedback: list[ReviewFeedbackRecord],
) -> ReviewBriefSection | None:
    if not feedback:
        return None
    disposition_counts = _value_counts(item.disposition.value for item in feedback)
    kind_counts = _value_counts(item.feedback_kind.value for item in feedback)
    body = (
        f"Review feedback includes {len(feedback)} item(s). "
        f"Disposition counts: {_format_counts(disposition_counts)}. "
        f"Kind counts: {_format_counts(kind_counts)}. "
        "Unresolved feedback remains visible even when verification is passing."
    )
    return ReviewBriefSection(
        title="Review Feedback",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="feedback",
                identifier=str(item.feedback_id),
                artifact_id=item.artifact_id,
                verification_id=item.verification_id,
                summary=(
                    f"{item.feedback_kind.value}/{item.disposition.value}: "
                    f"{item.summary}"
                ),
                local_only=item.artifact_id is not None,
            )
            for item in feedback[:8]
        ],
    )


def _review_brief_response_section(
    response_summary: ChangesetReviewResponseSummary,
) -> ReviewBriefSection | None:
    if response_summary.total_feedback_count == 0:
        return None
    body = (
        f"Response posture covers {response_summary.total_feedback_count} feedback "
        f"item(s): {response_summary.responded_count} responded, "
        f"{response_summary.unresolved_count} unresolved, "
        f"{response_summary.stale_response_count} stale, "
        f"{response_summary.blocked_count} blocked, and "
        f"{response_summary.accepted_risk_count} accepted with risk. "
        "Response state is local evidence and does not imply reviewer acceptance."
    )
    return ReviewBriefSection(
        title="Review Responses",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="response",
                identifier=str(item.feedback_id),
                artifact_id=item.latest_fixup_inventory_artifact_id,
                summary=(
                    f"{item.response_state.value}: {item.summary}; "
                    f"{item.changed_path_count} fixup path(s), verification "
                    f"{item.verification_state.value}"
                ),
                local_only=item.latest_fixup_inventory_artifact_id is not None,
            )
            for item in response_summary.items[:8]
        ],
    )


def _review_brief_manual_evidence_section(
    manual_evidence: list[ManualEvidenceRecord],
) -> ReviewBriefSection | None:
    if not manual_evidence:
        return None
    kind_counts = _value_counts(item.evidence_kind.value for item in manual_evidence)
    state_counts = _value_counts(item.state.value for item in manual_evidence)
    local_only_count = sum(1 for item in manual_evidence if item.local_only)
    body = (
        f"Manual evidence includes {len(manual_evidence)} item(s), "
        f"{local_only_count} local-only. Kind counts: "
        f"{_format_counts(kind_counts)}. State counts: {_format_counts(state_counts)}. "
        "Manual evidence remains advisory and is not retained command evidence."
    )
    return ReviewBriefSection(
        title="Manual Evidence",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind=_manual_evidence_ref_kind(item),
                identifier=str(item.evidence_id),
                artifact_id=item.artifact_id,
                verification_id=item.verification_id,
                summary=(
                    f"{item.evidence_kind.value}/{item.state.value}: {item.summary}"
                ),
                local_only=item.local_only,
            )
            for item in manual_evidence[:8]
        ],
    )


def _review_brief_live_evidence_section(
    manual_evidence: list[ManualEvidenceRecord],
) -> ReviewBriefSection | None:
    live_evidence = [
        item
        for item in manual_evidence
        if item.evidence_kind
        in {
            ManualEvidenceKind.BROWSER_OBSERVATION,
            ManualEvidenceKind.SCREENSHOT,
            ManualEvidenceKind.ACCESSIBILITY_NOTE,
        }
    ]
    if not live_evidence:
        return None
    kind_counts = _value_counts(item.evidence_kind.value for item in live_evidence)
    body = (
        f"Live review evidence includes {len(live_evidence)} browser, dashboard, "
        f"screenshot, or accessibility item(s). Kind counts: "
        f"{_format_counts(kind_counts)}. These observations are advisory unless a "
        "deterministic fixture-backed gate separately promotes them."
    )
    return ReviewBriefSection(
        title="Live Review Evidence",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind=_manual_evidence_ref_kind(item),
                identifier=str(item.evidence_id),
                artifact_id=item.artifact_id,
                summary=f"{item.evidence_kind.value}: {item.summary}",
                local_only=item.local_only,
            )
            for item in live_evidence[:8]
        ],
    )


def _review_brief_verification_section(
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


def _review_brief_stale_verification_section(
    response_summary: ChangesetReviewResponseSummary,
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection | None:
    stale_responses = [
        item
        for item in response_summary.items
        if item.stale or item.verification_state == ChangesetVerificationState.STALE
    ]
    if (
        not stale_responses
        and verification_plan.readiness.state != ChangesetVerificationState.STALE
    ):
        return None
    body = (
        f"Stale verification posture includes {len(stale_responses)} stale "
        f"response-linked item(s) and changeset readiness "
        f"{verification_plan.readiness.state.value}: "
        f"{verification_plan.readiness.summary}. Rerun focused checks before "
        "handoff when response-linked fixups changed after retained passes."
    )
    return ReviewBriefSection(
        title="Stale Verification",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="verification",
                identifier=str(item.feedback_id),
                artifact_id=item.latest_fixup_inventory_artifact_id,
                summary=(
                    f"{item.response_state.value}: "
                    f"{item.verification_reason or item.stale_reason or item.summary}"
                ),
                local_only=item.latest_fixup_inventory_artifact_id is not None,
            )
            for item in stale_responses[:8]
        ],
    )


def _review_brief_command_evidence_section(
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


def _review_brief_publication_boundary_section(
    changeset: ChangesetRecord,
) -> ReviewBriefSection:
    body = (
        "Publication boundary posture is advisory in this lifecycle brief. "
        "Glassbox generated local evidence only; it did not stage, commit, push, "
        "open a pull request, merge, deploy, or publish. Final handoff and "
        "publication require explicit operator action."
    )
    return ReviewBriefSection(
        title="Publication Boundary",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="publication_boundary",
                identifier=str(changeset.changeset_id),
                summary=(
                    "local lifecycle brief records non-publication posture for "
                    "this changeset"
                ),
            )
        ],
    )


def _review_brief_branch_candidate_section(
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


def _review_brief_risk_section(
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


def _reviewer_checklist(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[str]:
    checklist = [
        "Inspect the changed-file inventory before reviewing implementation details",
        "Review provenance confidence for changed paths with unknown source evidence",
        "Inspect verification readiness and retained evidence references",
    ]
    if verification_plan.readiness.state != ChangesetVerificationState.PASSED:
        checklist.append("Resolve missing, stale, failed, or accepted-risk checks")
    if changeset.unresolved_risk_count > 0:
        checklist.append("Review unresolved risk classification before commit prep")
    return checklist


def _review_brief_safe_commands(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[str]:
    commands = [
        show_changeset_command(changeset.changeset_id),
        changeset_verification_plan_command(changeset.changeset_id),
        changeset_brief_command(changeset.changeset_id, json=True),
    ]
    commands.extend(verification_plan.safe_next_actions)
    return list(dict.fromkeys(commands))


def _manual_evidence_ref_kind(
    evidence: ManualEvidenceRecord,
) -> Literal[
    "manual_evidence",
    "browser_evidence",
    "dashboard_evidence",
    "accessibility_evidence",
]:
    if evidence.evidence_kind == ManualEvidenceKind.ACCESSIBILITY_NOTE:
        return "accessibility_evidence"
    if evidence.evidence_kind == ManualEvidenceKind.BROWSER_OBSERVATION:
        summary = evidence.summary.lower()
        return "dashboard_evidence" if "dashboard" in summary else "browser_evidence"
    if evidence.evidence_kind == ManualEvidenceKind.SCREENSHOT:
        return "browser_evidence"
    return "manual_evidence"


def _value_counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key} {value}" for key, value in sorted(counts.items()))


def _review_brief_local_only(
    sources: list[ChangesetSourceRecord],
    inventory_record: ChangesetInventoryRecord | None,
    verification_posture: ChangesetVerificationPostureRecord | None,
    command_evidence: ChangesetCommandEvidenceSummary,
    manual_evidence: list[ManualEvidenceRecord],
) -> bool:
    return (
        inventory_record is not None
        or verification_posture is not None
        or command_evidence.environment_captured_count > 0
        or command_evidence.artifact_count > 0
        or any(item.local_only for item in manual_evidence)
        or any(source.artifact_id is not None for source in sources)
    )


def _review_brief_limitations(
    *,
    sources: list[ChangesetSourceRecord],
    inventory: ChangeInventoryArtifact | None,
    inventory_status: ChangesetInventoryStatus,
    inventory_limitations: list[str],
    verification_plan: ChangesetVerificationPlanPreview,
    command_evidence: ChangesetCommandEvidenceSummary,
    review_response_summary: ChangesetReviewResponseSummary,
    manual_evidence: list[ManualEvidenceRecord],
) -> tuple[list[str], ReviewBriefLimitationSummary | None]:
    limitations = [
        source.limitation for source in sources if source.limitation is not None
    ]
    limitations.extend(inventory_limitations)
    if inventory_status.reason is not None:
        limitations.append(inventory_status.reason)
    if inventory is not None:
        limitations.extend(inventory.limitations)
    limitations.extend(verification_plan.limitations)
    limitations.extend(command_evidence.limitations)
    limitations.extend(review_response_summary.blockers)
    for evidence in manual_evidence:
        limitations.extend(evidence.limitations)
    if verification_plan.readiness.state != ChangesetVerificationState.PASSED:
        limitations.append(
            f"verification readiness is {verification_plan.readiness.state.value}"
        )
    if review_response_summary.unresolved_count > 0:
        limitations.append(
            f"{review_response_summary.unresolved_count} review feedback item(s) "
            "remain unresolved"
        )
    if review_response_summary.stale_response_count > 0:
        limitations.append(
            f"{review_response_summary.stale_response_count} review response(s) "
            "need fresh verification"
        )
    return _summarize_review_brief_limitations(limitations)


def _summarize_review_brief_limitations(
    limitations: list[str],
) -> tuple[list[str], ReviewBriefLimitationSummary | None]:
    """Keep reviewer-safe limitations within the artifact cap."""

    deduped = list(dict.fromkeys(limitations))
    if len(deduped) <= _REVIEW_BRIEF_LIMITATION_CAP:
        return deduped, None

    visible_limit = _REVIEW_BRIEF_LIMITATION_CAP - _REVIEW_BRIEF_OVERFLOW_SUMMARY_SLOT
    prioritized = sorted(
        enumerate(deduped),
        key=lambda item: (_review_brief_limitation_priority(item[1]), item[0]),
    )
    visible_indexes = {index for index, _limitation in prioritized[:visible_limit]}
    visible = [
        limitation
        for index, limitation in enumerate(deduped)
        if index in visible_indexes
    ]
    overflow_count = len(deduped) - len(visible)
    reason = "rich-evidence limitations exceeded the reviewer-safe 20-item artifact cap"
    visible.append(
        "rich-evidence limitations summarized: "
        f"{overflow_count} additional retained limitation(s) are summarized "
        "to keep the reviewer-safe brief within the 20-item artifact cap; "
        "inspect retained changeset evidence for the full limitation set"
    )
    return visible, ReviewBriefLimitationSummary(
        summarized=True,
        total_count=len(deduped),
        visible_count=len(visible),
        overflow_count=overflow_count,
        reason=reason,
    )


def _review_brief_limitation_priority(limitation: str) -> int:
    lowered = limitation.lower()
    high_priority_terms = (
        "blocker",
        "failed",
        "failure",
        "unresolved",
        "verification readiness",
        "need fresh verification",
        "stale",
        "accepted risk",
    )
    if any(term in lowered for term in high_priority_terms):
        return 0
    return 1


def _review_readiness_state(
    *,
    inventory_status: ChangesetInventoryStatus,
    verification_plan: ChangesetVerificationPlanPreview,
    changeset: ChangesetRecord,
    review_response_summary: ChangesetReviewResponseSummary,
) -> tuple[ChangesetReadinessState, list[str]]:
    blockers: list[str] = []
    if review_response_summary.blockers:
        blockers.extend(review_response_summary.blockers)
    if review_response_summary.stale_response_count > 0:
        blockers.append(
            f"{review_response_summary.stale_response_count} review response(s) "
            "need fresh verification"
        )
        return ChangesetReadinessState.NEEDS_VERIFICATION, blockers
    if review_response_summary.unresolved_count > 0:
        blockers.append(
            f"{review_response_summary.unresolved_count} review feedback item(s) "
            "remain unresolved"
        )
        return ChangesetReadinessState.NEEDS_REVIEW, blockers
    readiness = verification_plan.readiness
    if inventory_status.stale:
        blockers.append(
            inventory_status.reason
            or "structured change inventory is stale against the current workspace"
        )
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if inventory_status.freshness == ChangesetInventoryFreshness.UNKNOWN:
        blockers.append(
            inventory_status.reason
            or "structured change inventory freshness is unknown"
        )
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if readiness.state == ChangesetVerificationState.FAILED:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.FAILED_CHECKS, blockers
    if readiness.state == ChangesetVerificationState.STALE:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if readiness.state in {
        ChangesetVerificationState.MISSING,
        ChangesetVerificationState.PLANNED,
        ChangesetVerificationState.RUNNING,
        ChangesetVerificationState.SKIPPED,
    }:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.NEEDS_VERIFICATION, blockers
    if readiness.state == ChangesetVerificationState.ACCEPTED_WITH_RISK:
        return ChangesetReadinessState.ACCEPTED_WITH_RISK, [readiness.summary]
    return ChangesetReadinessState.READY, blockers


def _review_readiness_reason(
    state: ChangesetReadinessState,
    blockers: list[str],
) -> str:
    if blockers:
        return "; ".join(blockers)
    if state == ChangesetReadinessState.READY:
        return "deterministic changeset evidence is ready for reviewer inspection"
    return f"review readiness is {state.value}"
