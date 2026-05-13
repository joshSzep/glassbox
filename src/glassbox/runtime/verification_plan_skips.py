"""Skipped-check and limit rows for verification-plan previews."""

from glassbox.runtime.changeset_models import ChangesetVerificationSkippedCheckPreview

MAX_VERIFICATION_PLAN_SKIPPED_CHECKS = 50


class VerificationPlanSkippedCollector:
    """Append skipped-check previews while preserving the public cap behavior."""

    def __init__(
        self,
        skipped: list[ChangesetVerificationSkippedCheckPreview],
        *,
        changed_paths: list[str],
        limit: int = MAX_VERIFICATION_PLAN_SKIPPED_CHECKS,
    ) -> None:
        self._skipped = skipped
        self._changed_paths = changed_paths
        self._limit = limit
        self._limit_recorded = False

    def add(self, item: ChangesetVerificationSkippedCheckPreview) -> None:
        """Add one skipped row or replace the final row with the cap marker."""

        if len(self._skipped) >= self._limit:
            if not self._limit_recorded and self._skipped:
                self._skipped[-1] = skipped_check_limit_row(
                    self._changed_paths,
                    limit=self._limit,
                )
                self._limit_recorded = True
            return
        self._skipped.append(item)


def unsafe_command_skipped_row(
    *,
    target_id: str,
    matched_paths: list[str],
) -> ChangesetVerificationSkippedCheckPreview:
    """Build the skipped row for unsafe command recipe recommendations."""

    return skipped_row(
        target_id=target_id,
        target_kind="command-recipe",
        reason="unsafe-command",
        explanation=(
            "verification planning filters publication, upload, push, deploy, "
            "release, and destructive commands"
        ),
        matched_paths=matched_paths,
    )


def operator_selection_required_skipped_row(
    *,
    target_id: str,
    track: str,
    matched_paths: list[str],
    safe_next_actions: list[str],
) -> ChangesetVerificationSkippedCheckPreview:
    """Build the skipped row for advisory eval profiles."""

    return skipped_row(
        target_id=target_id,
        target_kind="eval-profile",
        reason="operator-selection-required",
        explanation=(
            f"{track} profiles remain advisory until the operator explicitly "
            "selects them"
        ),
        matched_paths=matched_paths,
        safe_next_actions=safe_next_actions,
    )


def plan_entry_limit_row(
    matched_paths: list[str],
    *,
    limit: int,
) -> ChangesetVerificationSkippedCheckPreview:
    """Build the skipped row shown when executable plan entries are capped."""

    return skipped_row(
        target_id="verification-plan-entry-limit",
        target_kind="plan-limit",
        reason="plan-entry-limit",
        explanation=(
            f"Verification plan preview is capped at {limit} entry summaries; "
            "inspect repository recommendations for additional candidate checks."
        ),
        matched_paths=matched_paths[:100],
    )


def skipped_check_limit_row(
    matched_paths: list[str],
    *,
    limit: int,
) -> ChangesetVerificationSkippedCheckPreview:
    """Build the skipped row shown when skipped-check previews are capped."""

    return skipped_row(
        target_id="verification-skipped-check-limit",
        target_kind="plan-limit",
        reason="skipped-check-limit",
        explanation=(
            f"Skipped-check preview is capped at {limit} rows; inspect repository "
            "recommendations for additional skipped advisory checks."
        ),
        matched_paths=matched_paths[:100],
    )


def skipped_row(
    *,
    target_id: str,
    target_kind: str,
    reason: str,
    explanation: str,
    matched_paths: list[str],
    safe_next_actions: list[str] | None = None,
) -> ChangesetVerificationSkippedCheckPreview:
    """Build one skipped-check preview row."""

    return ChangesetVerificationSkippedCheckPreview(
        target_id=target_id,
        target_kind=target_kind,
        reason=reason,
        explanation=explanation,
        matched_paths=matched_paths,
        safe_next_actions=safe_next_actions or [],
    )


__all__ = [
    "MAX_VERIFICATION_PLAN_SKIPPED_CHECKS",
    "VerificationPlanSkippedCollector",
    "operator_selection_required_skipped_row",
    "plan_entry_limit_row",
    "skipped_check_limit_row",
    "skipped_row",
    "unsafe_command_skipped_row",
]
