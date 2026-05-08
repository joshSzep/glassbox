"""Artifact helpers for response-linked fixup inventory."""

import json

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFeedbackScopeRecord
from glassbox.core import ReviewFixupSourceKind
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.review_fixup_paths import feedback_scope_paths
from glassbox.runtime.review_fixup_paths import review_fixup_path_matches_scope
from glassbox.runtime.review_fixup_paths import review_fixup_path_summary
from glassbox.runtime.review_response_models import ReviewFixupInventoryArtifact


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

    scope_paths = feedback_scope_paths(scopes)
    paths = [
        review_fixup_path_summary(
            entry,
            matches_feedback_scope=review_fixup_path_matches_scope(entry, scope_paths),
        )
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


__all__ = [
    "review_fixup_inventory_artifact_json",
    "review_fixup_inventory_from_change_inventory",
]
