"""Review response and fixup inventory artifact helpers."""

import json
from pathlib import Path

from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetVerificationState
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackFixupPathSummary
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFeedbackScopeRecord
from glassbox.core import ReviewFixupSourceKind
from glassbox.core import ReviewResponseState
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.change_inventory import ChangeInventoryPathEntry
from glassbox.runtime.changeset_safe_commands import show_changeset_command
from glassbox.runtime.review_response_models import REVIEW_FIXUP_INVENTORY_ARTIFACT_KIND
from glassbox.runtime.review_response_models import (
    REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION,
)
from glassbox.runtime.review_response_models import ChangesetReviewResponseSummary
from glassbox.runtime.review_response_models import ReviewFeedbackResponseStatus
from glassbox.runtime.review_response_models import ReviewFixupInventoryArtifact
from glassbox.runtime.review_response_models import ReviewFixupInventoryStatus
from glassbox.runtime.review_response_status import review_feedback_response_status
from glassbox.runtime.review_response_status import review_fixup_inventory_status
from glassbox.runtime.review_response_status import review_response_non_claims


def review_fixup_inventory_from_change_inventory(
    inventory: ChangeInventoryArtifact,
    *,
    feedback: ReviewFeedbackRecord,
    scopes: list[ReviewFeedbackScopeRecord],
    source_kind: ReviewFixupSourceKind,
    source_summary: str,
    source_digest: str | None,
    inventory_freshness: ChangesetInventoryFreshness,
    latest_changeset_inventory_artifact_id: str | None = None,
) -> ReviewFixupInventoryArtifact:
    """Build a bounded response-linked inventory artifact from a change inventory."""

    scope_paths = _feedback_scope_paths(scopes)
    paths = [
        _path_summary(entry, matches_feedback_scope=_matches_scope(entry, scope_paths))
        for entry in inventory.paths[:100]
    ]
    matched_scope_path_count = sum(1 for path in paths if path.matches_feedback_scope)
    limitations = [
        *inventory.limitations,
        (
            "fixup inventory is summary-only and does not include raw diffs or "
            "file contents"
        ),
    ]
    if not scope_paths:
        limitations.append("feedback has no file scope; all changed paths need review")
    elif matched_scope_path_count == 0 and paths:
        limitations.append(
            "no changed path directly matched the feedback file scope; inspect "
            "response context"
        )
    return ReviewFixupInventoryArtifact(
        changeset_id=feedback.changeset_id,
        feedback_id=feedback.feedback_id,
        source_kind=source_kind,
        source_summary=source_summary,
        latest_changeset_inventory_artifact_id=latest_changeset_inventory_artifact_id,
        source_digest=source_digest,
        inventory_freshness=inventory_freshness,
        changed_path_count=inventory.summary.changed_path_count,
        matched_scope_path_count=matched_scope_path_count,
        paths=paths,
        limitations=list(dict.fromkeys(limitations)),
        non_claims=[
            "fixup inventory is response evidence, not reviewer acceptance",
            (
                "manual or external edits remain manual unless retained "
                "instrumentation says otherwise"
            ),
            "Glassbox did not stage, commit, push, open a PR, or merge",
        ],
    )


def review_fixup_inventory_artifact_json(
    artifact: ReviewFixupInventoryArtifact,
) -> str:
    """Serialize a response-linked inventory artifact with stable key ordering."""

    return json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def changeset_review_response_summary(
    *,
    changeset_id: ChangesetId,
    items: list[ReviewFeedbackResponseStatus],
) -> ChangesetReviewResponseSummary:
    """Summarize derived response status rows for one changeset."""

    unresolved_states = {
        ReviewResponseState.PLANNED,
        ReviewResponseState.IN_PROGRESS,
        ReviewResponseState.RESPONDED,
        ReviewResponseState.REOPENED,
        ReviewResponseState.BLOCKED,
    }
    blockers = [
        f"{item.feedback_id}: {blocker}" for item in items for blocker in item.blockers
    ]
    return ChangesetReviewResponseSummary(
        changeset_id=changeset_id,
        total_feedback_count=len(items),
        open_count=sum(
            1
            for item in items
            if item.disposition
            in {
                ReviewFeedbackDisposition.OPEN,
                ReviewFeedbackDisposition.IN_PROGRESS,
            }
        ),
        responded_count=sum(
            1
            for item in items
            if item.response_state
            in {
                ReviewResponseState.RESPONDED,
                ReviewResponseState.RESOLVED,
                ReviewResponseState.READY_FOR_HANDOFF,
            }
        ),
        unresolved_count=sum(
            1 for item in items if item.response_state in unresolved_states
        ),
        stale_response_count=sum(
            1
            for item in items
            if item.stale or item.verification_state == ChangesetVerificationState.STALE
        ),
        accepted_risk_count=sum(
            1
            for item in items
            if item.response_state == ReviewResponseState.ACCEPTED_WITH_RISK
        ),
        blocked_count=sum(
            1 for item in items if item.response_state == ReviewResponseState.BLOCKED
        ),
        items=items,
        blockers=blockers,
        safe_next_actions=[
            f"glassbox changeset feedback list --changeset {changeset_id} --cwd .",
            show_changeset_command(changeset_id),
        ],
        non_claims=review_response_non_claims(),
    )


def _feedback_scope_paths(scopes: list[ReviewFeedbackScopeRecord]) -> set[str]:
    return {
        _normalize_path(scope.file_path)
        for scope in scopes
        if scope.file_path is not None
    }


def _matches_scope(
    entry: ChangeInventoryPathEntry,
    scope_paths: set[str],
) -> bool:
    if not scope_paths:
        return False
    path = _normalize_path(entry.path)
    return path in scope_paths or any(
        path.startswith(f"{scope_path}/") for scope_path in scope_paths
    )


def _path_summary(
    entry: ChangeInventoryPathEntry,
    *,
    matches_feedback_scope: bool,
) -> ReviewFeedbackFixupPathSummary:
    return ReviewFeedbackFixupPathSummary(
        path=entry.path,
        change_kind=entry.change_kind,
        generated=entry.generated,
        test_file=entry.test_file,
        docs_file=entry.docs_file,
        policy_sensitive=entry.policy_sensitive,
        risk_level=entry.risk_level,
        provenance_confidence=entry.provenance_confidence,
        matches_feedback_scope=matches_feedback_scope,
        summary=_safe_path_summary(
            entry, matches_feedback_scope=matches_feedback_scope
        ),
    )


def _safe_path_summary(
    entry: ChangeInventoryPathEntry,
    *,
    matches_feedback_scope: bool,
) -> str:
    labels: list[str] = []
    if matches_feedback_scope:
        labels.append("matches feedback scope")
    if entry.generated:
        labels.append("generated output")
    if entry.test_file:
        labels.append("test path")
    if entry.docs_file:
        labels.append("docs path")
    if entry.policy_sensitive:
        labels.append("policy-sensitive path")
    if entry.risk_level in {"high", "medium"}:
        labels.append(f"{entry.risk_level} risk")
    if entry.provenance_confidence == "unknown":
        labels.append("manual or external provenance")
    if not labels:
        labels.append("changed path")
    return f"{entry.path}: {', '.join(labels)}"


def _normalize_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").strip().lstrip("./")


__all__ = [
    "REVIEW_FIXUP_INVENTORY_ARTIFACT_KIND",
    "REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION",
    "ReviewFixupInventoryArtifact",
    "ReviewFixupInventoryStatus",
    "ReviewFeedbackResponseStatus",
    "ChangesetReviewResponseSummary",
    "changeset_review_response_summary",
    "review_feedback_response_status",
    "review_fixup_inventory_artifact_json",
    "review_fixup_inventory_from_change_inventory",
    "review_fixup_inventory_status",
]
