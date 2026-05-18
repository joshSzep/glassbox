"""Recipient-safe local-only evidence inventory helpers."""

from collections.abc import Mapping
from collections.abc import Sequence

from glassbox.core import HandoffIntent
from glassbox.core import HandoffLocalOnlyEvidenceItem
from glassbox.core import HandoffLocalOnlyInventory
from glassbox.core import HandoffLocalOnlySummary
from glassbox.core import HandoffReadiness
from glassbox.core import HandoffReadinessReasonKind
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.core import ManualEvidenceKind
from glassbox.runtime.changeset_models import ChangesetDetailView
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.session_export_models import SessionExportPayload


def build_local_only_inventory(
    *,
    source: HandoffSourceRef,
    intent: HandoffIntent,
    summary: HandoffLocalOnlySummary,
    omitted_raw_categories: Sequence[str] = (),
    unsupported_evidence: Sequence[str] = (),
    affected_claim_ids_by_category: Mapping[str, Sequence[str]] | None = None,
    limitations: Sequence[str] = (),
) -> HandoffLocalOnlyInventory:
    """Build an itemized inventory without copying local-only contents."""

    claim_map = affected_claim_ids_by_category or {}
    items: list[HandoffLocalOnlyEvidenceItem] = []
    for category, count in summary.category_counts.items():
        if count <= 0:
            continue
        items.append(
            _inventory_item(
                category=category,
                count=count,
                reason=_reason_for_category(category),
                summary=_category_summary(category, count),
                affected_claim_ids=[
                    *summary.affected_claim_ids,
                    *claim_map.get(category, ()),
                ],
                recipient_limitation=_recipient_limitation(category),
                safe_commands=summary.safe_local_inspection_commands,
            )
        )
    for category in omitted_raw_categories:
        if category in summary.category_counts:
            continue
        items.append(
            _inventory_item(
                category=category,
                reason=HandoffReadinessReasonKind.REDACTED_EVIDENCE,
                summary=f"{category} stay local and are not copied into the package.",
                affected_claim_ids=claim_map.get(category, ()),
                recipient_limitation=(
                    "Recipient can see that this evidence exists, but cannot verify "
                    "its raw contents from the portable package alone."
                ),
                safe_commands=summary.safe_local_inspection_commands,
            )
        )
    for category in unsupported_evidence:
        items.append(
            _inventory_item(
                category=category,
                reason=HandoffReadinessReasonKind.UNSUPPORTED_EVIDENCE,
                summary=f"{category} is not supported by this handoff package shape.",
                affected_claim_ids=claim_map.get(category, ()),
                recipient_limitation=(
                    "Recipient must inspect the source workspace or request a "
                    "different handoff profile before relying on this evidence."
                ),
                safe_commands=summary.safe_local_inspection_commands,
            )
        )

    return HandoffLocalOnlyInventory(
        source=source,
        intent=intent,
        items=_dedupe_items(items),
        limitations=list(dict.fromkeys([*summary.limitations, *limitations]))[:50],
        safe_local_inspection_commands=summary.safe_local_inspection_commands,
    )


def build_readiness_local_only_inventory(
    readiness: HandoffReadiness,
) -> HandoffLocalOnlyInventory:
    """Inventory local-only readiness reasons with affected claim links."""

    counts: dict[str, int] = {}
    affected_claims: dict[str, list[str]] = {}
    limitations: list[str] = []
    for reason in readiness.local_only_evidence:
        category = reason.kind.value
        counts[category] = counts.get(category, 0) + 1
        affected_claims.setdefault(category, []).extend(reason.affected_claim_ids)
        if reason.limitation is not None:
            limitations.append(reason.limitation)

    return build_local_only_inventory(
        source=readiness.source,
        intent=readiness.intent,
        summary=HandoffLocalOnlySummary(
            category_counts=_positive_counts(counts),
            limitations=[*readiness.limitations, *limitations],
            safe_local_inspection_commands=readiness.safe_first_commands,
        ),
        affected_claim_ids_by_category=affected_claims,
    )


def build_session_local_only_inventory(
    payload: SessionExportPayload,
    *,
    intent: HandoffIntent = HandoffIntent.REVIEW_ONLY,
    omitted_raw_categories: Sequence[str],
) -> HandoffLocalOnlyInventory:
    """Inventory local evidence referenced by a portable session export."""

    source = HandoffSourceRef(
        kind=HandoffSourceKind.SESSION,
        primary_id=str(payload.metadata.session_id),
        label="session",
    )
    safe_commands = [
        _safe_command(
            f"glassbox session status {payload.metadata.session_id} --cwd .",
            "Inspect the source session and retained local evidence.",
        )
    ]
    return build_local_only_inventory(
        source=source,
        intent=intent,
        summary=HandoffLocalOnlySummary(
            category_counts=_positive_counts(
                {
                    "artifact_references": len(payload.artifact_references),
                    "checkpoint_artifacts": sum(
                        1
                        for item in payload.checkpoint_history
                        if item.artifact_id is not None
                    ),
                }
            ),
            affected_claim_ids=[
                "session.transcript-summary",
                "session.checkpoint-posture",
            ],
            limitations=[
                "Artifact contents remain local-only and are referenced by ID.",
                "Raw tool logs and provider output are summarized, not copied.",
            ],
            safe_local_inspection_commands=safe_commands,
        ),
        omitted_raw_categories=omitted_raw_categories,
        affected_claim_ids_by_category={
            "artifact_references": ["session.artifacts"],
            "checkpoint_artifacts": ["session.checkpoints"],
        },
    )


def build_changeset_local_only_inventory(
    detail: ChangesetDetailView,
    verification_plan: ChangesetVerificationPlanPreview,
    *,
    source: HandoffSourceRef,
    intent: HandoffIntent,
    omitted_raw_categories: Sequence[str],
) -> HandoffLocalOnlyInventory:
    """Inventory local evidence behind a reviewer-safe changeset export."""

    local_manual = [item for item in detail.manual_evidence if item.local_only]
    live_kinds = {
        ManualEvidenceKind.BROWSER_OBSERVATION,
        ManualEvidenceKind.SCREENSHOT,
        ManualEvidenceKind.ACCESSIBILITY_NOTE,
    }
    local_live = [item for item in local_manual if item.evidence_kind in live_kinds]
    local_command = [item for item in detail.command_evidence.items if item.local_only]
    summary = HandoffLocalOnlySummary(
        category_counts=_positive_counts(
            {
                "artifact_references": _changeset_artifact_reference_count(
                    detail,
                    verification_plan,
                ),
                "manual_evidence": len(local_manual),
                "browser_dashboard_accessibility_evidence": len(local_live),
                "raw_command_logs": len(local_command),
                "repository_intelligence_snapshots": int(
                    detail.verification_plan_summary.total_count > 0
                ),
                "release_evidence": int(bool(verification_plan.eval_profiles)),
            }
        ),
        affected_claim_ids=[
            f"changeset.{detail.changeset.changeset_id}.review",
            f"changeset.{detail.changeset.changeset_id}.verification",
        ],
        limitations=[
            (
                "Reviewer-safe packages summarize raw local evidence instead of "
                "copying it."
            ),
            (
                "Portable confidence is lower when recipient cannot inspect local "
                "artifacts."
            ),
        ],
        safe_local_inspection_commands=[
            _safe_command(
                "glassbox changeset evidence list "
                f"{detail.changeset.changeset_id} --cwd .",
                "Inspect local evidence before relying on the handoff package.",
            )
        ],
    )
    return build_local_only_inventory(
        source=source,
        intent=intent,
        summary=summary,
        omitted_raw_categories=omitted_raw_categories,
        affected_claim_ids_by_category={
            "manual_evidence": ["changeset.manual-evidence"],
            "browser_dashboard_accessibility_evidence": ["changeset.live-evidence"],
            "raw_command_logs": ["changeset.command-evidence"],
            "repository_intelligence_snapshots": ["changeset.repository-intelligence"],
            "release_evidence": ["changeset.release-evidence"],
        },
    )


def _changeset_artifact_reference_count(
    detail: ChangesetDetailView,
    verification_plan: ChangesetVerificationPlanPreview,
) -> int:
    count = int(detail.inventory is not None)
    count += len(detail.review_briefs)
    count += sum(
        1
        for item in detail.review_response_summary.items
        if item.latest_fixup_inventory_artifact_id is not None
    )
    count += sum(1 for item in detail.manual_evidence if item.artifact_id is not None)
    count += len(verification_plan.retained_artifact_ids)
    return count


def _inventory_item(
    *,
    category: str,
    reason: HandoffReadinessReasonKind,
    summary: str,
    recipient_limitation: str,
    count: int = 1,
    affected_claim_ids: Sequence[str] = (),
    safe_commands: Sequence[HandoffSafeCommand] = (),
) -> HandoffLocalOnlyEvidenceItem:
    return HandoffLocalOnlyEvidenceItem(
        category=category,
        count=count,
        reason=reason,
        summary=summary,
        affected_claim_ids=list(dict.fromkeys(affected_claim_ids))[:50],
        recipient_limitation=recipient_limitation,
        safe_local_inspection_commands=list(safe_commands)[:10],
    )


def _reason_for_category(category: str) -> HandoffReadinessReasonKind:
    lowered = category.lower()
    if "manual" in lowered or "provider" in lowered:
        return HandoffReadinessReasonKind.MANUAL_ONLY_EVIDENCE
    if "skipped" in lowered:
        return HandoffReadinessReasonKind.SKIPPED_EVIDENCE
    if "unsupported" in lowered:
        return HandoffReadinessReasonKind.UNSUPPORTED_EVIDENCE
    if "raw" in lowered or "redact" in lowered:
        return HandoffReadinessReasonKind.REDACTED_EVIDENCE
    return HandoffReadinessReasonKind.LOCAL_ONLY_EVIDENCE


def _category_summary(category: str, count: int) -> str:
    label = category.replace("_", " ").replace("-", " ")
    suffix = "item" if count == 1 else "items"
    return f"{count} {label} {suffix} remain local-only evidence."


def _recipient_limitation(category: str) -> str:
    label = category.replace("_", " ").replace("-", " ")
    return (
        f"Recipient cannot inspect {label} contents from the package alone; "
        "use the safe local inspection command in the source workspace."
    )


def _dedupe_items(
    items: Sequence[HandoffLocalOnlyEvidenceItem],
) -> list[HandoffLocalOnlyEvidenceItem]:
    deduped: dict[str, HandoffLocalOnlyEvidenceItem] = {}
    for item in items:
        existing = deduped.get(item.category)
        if existing is None:
            deduped[item.category] = item
            continue
        deduped[item.category] = existing.model_copy(
            update={
                "count": existing.count + item.count,
                "affected_claim_ids": list(
                    dict.fromkeys(
                        [*existing.affected_claim_ids, *item.affected_claim_ids]
                    )
                )[:50],
            },
            deep=True,
        )
    return list(deduped.values())[:100]


def _positive_counts(counts: Mapping[str, int]) -> dict[str, int]:
    return {key: value for key, value in counts.items() if value > 0}


def _safe_command(display: str, purpose: str) -> HandoffSafeCommand:
    return HandoffSafeCommand(
        command=display.split(),
        display=display,
        purpose=purpose,
    )


__all__ = [
    "build_changeset_local_only_inventory",
    "build_local_only_inventory",
    "build_readiness_local_only_inventory",
    "build_session_local_only_inventory",
]
