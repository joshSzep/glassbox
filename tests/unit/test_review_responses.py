"""Unit tests for review response fixup inventory helpers."""

from datetime import UTC
from datetime import datetime

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFeedbackScopeKind
from glassbox.core import ReviewFeedbackScopeRecord
from glassbox.core import ReviewFixupSourceKind
from glassbox.core import new_changeset_id
from glassbox.core import new_review_feedback_id
from glassbox.core import new_session_id
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.change_inventory import ChangeInventoryLimits
from glassbox.runtime.change_inventory import ChangeInventoryPathEntry
from glassbox.runtime.change_inventory import ChangeInventoryRiskLevel
from glassbox.runtime.change_inventory import ChangeInventorySummary
from glassbox.runtime.review_responses import (
    review_fixup_inventory_from_change_inventory,
)
from glassbox.runtime.review_responses import review_fixup_inventory_status


def test_fixup_inventory_summarizes_scoped_paths_and_risks() -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    feedback = _feedback_record(session_id, changeset_id, feedback_id)
    inventory = ChangeInventoryArtifact(
        changeset_id=changeset_id,
        source="workspace_diff_summary",
        truncated=False,
        size_limited=False,
        limits=ChangeInventoryLimits(),
        summary=ChangeInventorySummary(
            changed_path_count=4,
            included_path_count=4,
            omitted_path_count=0,
            insertions=12,
            deletions=2,
            generated_path_count=1,
            test_path_count=1,
            docs_path_count=1,
            binary_path_count=0,
            policy_sensitive_path_count=1,
            untracked_path_count=0,
            provenance_direct_path_count=0,
            provenance_inferred_path_count=0,
            provenance_unknown_path_count=4,
            externally_modified_path_count=4,
            risk_level="high",
            risk_summary="runtime and generated paths changed",
            high_risk_path_count=1,
            medium_risk_path_count=1,
            low_risk_path_count=2,
            unresolved_risk_count=2,
            accepted_risk_count=0,
        ),
        paths=[
            _path("src/glassbox/runtime/changesets.py", risk_level="high"),
            _path(
                "frontend/generated/api-types.ts", generated=True, risk_level="medium"
            ),
            _path("tests/unit/test_review_responses.py", test_file=True),
            _path("docs/review-responses.md", docs_file=True),
        ],
        limitations=["inventory is summary-only"],
    )
    artifact = review_fixup_inventory_from_change_inventory(
        inventory,
        feedback=feedback,
        scopes=[
            ReviewFeedbackScopeRecord(
                session_id=session_id,
                feedback_id=feedback_id,
                changeset_id=changeset_id,
                scope_kind=ReviewFeedbackScopeKind.FILE,
                reason="review feedback points at runtime changes",
                file_path="src/glassbox/runtime/changesets.py",
                created_at=datetime.now(UTC),
                last_sequence=3,
            )
        ],
        source_kind=ReviewFixupSourceKind.MANUAL_WORKSPACE_EDIT,
        source_summary="operator recorded response inventory",
        source_digest="sha256:before",
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
    )

    assert artifact.changed_path_count == 4
    assert artifact.matched_scope_path_count == 1
    assert artifact.paths[0].matches_feedback_scope is True
    assert "high risk" in artifact.paths[0].summary
    assert "generated output" in artifact.paths[1].summary
    assert "test path" in artifact.paths[2].summary
    assert "docs path" in artifact.paths[3].summary
    assert "raw diffs" in " ".join(artifact.limitations)
    assert "not reviewer acceptance" in " ".join(artifact.non_claims)


def test_fixup_inventory_status_marks_workspace_digest_drift_stale() -> None:
    feedback_id = new_review_feedback_id()
    changeset_id = new_changeset_id()

    status = review_fixup_inventory_status(
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        recorded_source_digest="sha256:before",
        current_source_digest="sha256:after",
    )

    assert status.freshness == ChangesetInventoryFreshness.STALE
    assert status.stale is True
    assert "source digest changed" in (status.reason or "")
    assert (
        f"glassbox changeset feedback show {feedback_id}" in status.safe_next_actions[0]
    )


def _feedback_record(session_id, changeset_id, feedback_id) -> ReviewFeedbackRecord:
    now = datetime.now(UTC)
    return ReviewFeedbackRecord(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        feedback_kind=ReviewFeedbackKind.REQUESTED_CHANGE,
        provenance=ReviewFeedbackProvenance.REVIEWER,
        disposition=ReviewFeedbackDisposition.OPEN,
        summary="Please address runtime feedback.",
        created_by="operator",
        created_at=now,
        updated_at=now,
        last_sequence=2,
    )


def _path(
    path: str,
    *,
    generated: bool = False,
    test_file: bool = False,
    docs_file: bool = False,
    policy_sensitive: bool = False,
    risk_level: ChangeInventoryRiskLevel = "low",
) -> ChangeInventoryPathEntry:
    return ChangeInventoryPathEntry(
        path=path,
        change_kind="modified",
        generated=generated,
        test_file=test_file,
        docs_file=docs_file,
        binary_posture="text",
        policy_sensitive=policy_sensitive,
        provenance_confidence="unknown",
        risk_level=risk_level,
        risk_tags=[],
        risk_reasons=[],
    )
