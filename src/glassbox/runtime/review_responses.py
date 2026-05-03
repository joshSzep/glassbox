"""Review response and fixup inventory artifact helpers."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ReviewFeedbackFixupPathSummary
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFeedbackScopeRecord
from glassbox.core import ReviewFixupSourceKind
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.change_inventory import ChangeInventoryPathEntry

REVIEW_FIXUP_INVENTORY_ARTIFACT_KIND = "review_feedback_fixup_inventory"
REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION = 1


class ReviewFixupInventoryStatus(BaseModel):
    """Freshness posture for response-linked fixup inventory."""

    model_config = ConfigDict(extra="forbid")

    freshness: ChangesetInventoryFreshness
    stale: bool = False
    reason: str | None = Field(default=None, max_length=2000)
    recorded_source_digest: str | None = Field(default=None, max_length=256)
    current_source_digest: str | None = Field(default=None, max_length=256)
    safe_next_actions: list[str] = Field(default_factory=list)


class ReviewFixupInventoryArtifact(BaseModel):
    """Artifact describing bounded fixup paths linked to one feedback item."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["review_feedback_fixup_inventory"] = (
        REVIEW_FIXUP_INVENTORY_ARTIFACT_KIND
    )
    schema_version: Literal[1] = REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION
    changeset_id: ChangesetId
    feedback_id: ReviewFeedbackId
    source_kind: ReviewFixupSourceKind
    source_summary: str = Field(min_length=1, max_length=2000)
    latest_changeset_inventory_artifact_id: str | None = None
    source_digest: str | None = Field(default=None, max_length=256)
    inventory_freshness: ChangesetInventoryFreshness
    changed_path_count: int = Field(ge=0)
    matched_scope_path_count: int = Field(ge=0)
    paths: list[ReviewFeedbackFixupPathSummary] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


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


def review_fixup_inventory_status(
    *,
    feedback_id: ReviewFeedbackId,
    changeset_id: ChangesetId,
    recorded_source_digest: str | None,
    current_source_digest: str | None,
    current_error: str | None = None,
) -> ReviewFixupInventoryStatus:
    """Compare response-linked inventory evidence against current workspace state."""

    safe_next_actions = [
        f"glassbox changeset feedback show {feedback_id} --cwd .",
        f"glassbox changeset verification-plan {changeset_id} --cwd .",
    ]
    if current_error is not None:
        return ReviewFixupInventoryStatus(
            freshness=ChangesetInventoryFreshness.UNKNOWN,
            stale=False,
            reason=f"workspace source digest unavailable: {current_error}",
            recorded_source_digest=recorded_source_digest,
            current_source_digest=current_source_digest,
            safe_next_actions=safe_next_actions,
        )
    if recorded_source_digest is None:
        return ReviewFixupInventoryStatus(
            freshness=ChangesetInventoryFreshness.UNKNOWN,
            stale=False,
            reason="fixup inventory has no recorded workspace source digest",
            recorded_source_digest=recorded_source_digest,
            current_source_digest=current_source_digest,
            safe_next_actions=safe_next_actions,
        )
    if recorded_source_digest != current_source_digest:
        return ReviewFixupInventoryStatus(
            freshness=ChangesetInventoryFreshness.STALE,
            stale=True,
            reason=(
                "workspace diff source digest changed since fixup inventory "
                "was recorded"
            ),
            recorded_source_digest=recorded_source_digest,
            current_source_digest=current_source_digest,
            safe_next_actions=safe_next_actions,
        )
    return ReviewFixupInventoryStatus(
        freshness=ChangesetInventoryFreshness.FRESH,
        stale=False,
        recorded_source_digest=recorded_source_digest,
        current_source_digest=current_source_digest,
        safe_next_actions=safe_next_actions,
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
    "review_fixup_inventory_artifact_json",
    "review_fixup_inventory_from_change_inventory",
    "review_fixup_inventory_status",
]
