"""Review-loop section builders for changeset review briefs."""

from collections.abc import Iterable
from typing import Literal

from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetVerificationState
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ReviewFeedbackRecord
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.review_briefs import ReviewBriefEvidenceRef
from glassbox.runtime.review_briefs import ReviewBriefSection
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.skipped_evidence import is_skipped_live_evidence
from glassbox.runtime.skipped_evidence import skipped_evidence_label
from glassbox.runtime.skipped_evidence import skipped_evidence_reason
from glassbox.runtime.skipped_evidence import skipped_live_evidence_summary


def review_brief_lifecycle_section(
    changeset: ChangesetRecord,
    response_summary: ChangesetReviewResponseSummary,
    manual_evidence: list[ManualEvidenceRecord],
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection:
    review_loop = verification_plan.review_loop_summary
    skipped_live_count = review_loop.skipped_live_evidence_count
    skipped_sentence = (
        f" {skipped_live_count} live evidence item(s) were explicitly skipped "
        "and remain limitations, not passes."
        if skipped_live_count
        else ""
    )
    body = (
        f"Lifecycle summary for changeset {changeset.changeset_id}: "
        f"{response_summary.total_feedback_count} feedback item(s), "
        f"{response_summary.unresolved_count} unresolved, "
        f"{response_summary.stale_response_count} stale response(s), "
        f"{response_summary.accepted_risk_count} accepted-risk response(s), "
        f"{len(manual_evidence)} manual evidence item(s), and verification "
        f"readiness {verification_plan.readiness.state.value}.{skipped_sentence} "
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


def review_brief_feedback_section(
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


def review_brief_response_section(
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


def review_brief_manual_evidence_section(
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


def review_brief_live_evidence_section(
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
    skipped_evidence = [
        item for item in live_evidence if is_skipped_live_evidence(item)
    ]
    skipped_sentence = (
        f" {len(skipped_evidence)} item(s) are explicitly skipped/not applicable "
        "and must remain visible as limitations, not passes."
        if skipped_evidence
        else ""
    )
    body = (
        f"Live review evidence includes {len(live_evidence)} browser, dashboard, "
        f"screenshot, or accessibility item(s). Kind counts: "
        f"{_format_counts(kind_counts)}. These observations are advisory unless a "
        f"deterministic fixture-backed gate separately promotes them.{skipped_sentence}"
    )
    if skipped_evidence:
        skipped_summaries = [
            skipped_live_evidence_summary(item) for item in skipped_evidence[:5]
        ]
        body = f"{body} Skipped live evidence: {'; '.join(skipped_summaries)}."
    return ReviewBriefSection(
        title="Live Review Evidence",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind=_manual_evidence_ref_kind(item),
                identifier=str(item.evidence_id),
                artifact_id=item.artifact_id,
                summary=_live_evidence_ref_summary(item),
                local_only=item.local_only,
            )
            for item in live_evidence[:8]
        ],
    )


def review_brief_stale_verification_section(
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


def review_brief_publication_boundary_section(
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


def _live_evidence_ref_summary(evidence: ManualEvidenceRecord) -> str:
    if not is_skipped_live_evidence(evidence):
        return f"{evidence.evidence_kind.value}: {evidence.summary}"
    reason = skipped_evidence_reason(evidence)
    reason_suffix = f"; reason: {reason}" if reason else ""
    return (
        f"{evidence.evidence_kind.value}/{skipped_evidence_label(evidence)}: "
        f"{evidence.summary}{reason_suffix}"
    )


def _value_counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key} {value}" for key, value in sorted(counts.items()))


__all__ = [
    "review_brief_feedback_section",
    "review_brief_lifecycle_section",
    "review_brief_live_evidence_section",
    "review_brief_manual_evidence_section",
    "review_brief_publication_boundary_section",
    "review_brief_response_section",
    "review_brief_stale_verification_section",
]
