"""Unit tests for review response fixup inventory helpers."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetVerificationState
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackFixupInventoryRecord
from glassbox.core import ReviewFeedbackFixupPathRecord
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFeedbackScopeKind
from glassbox.core import ReviewFeedbackScopeRecord
from glassbox.core import ReviewFixupSourceKind
from glassbox.core import ReviewResponseState
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import TaskVerificationStatus
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanSource
from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
from glassbox.core import new_review_feedback_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.change_inventory import ChangeInventoryLimits
from glassbox.runtime.change_inventory import ChangeInventoryPathEntry
from glassbox.runtime.change_inventory import ChangeInventoryRiskLevel
from glassbox.runtime.change_inventory import ChangeInventorySummary
from glassbox.runtime.review_fixup_artifacts import (
    review_fixup_inventory_from_change_inventory,
)
from glassbox.runtime.review_responses import changeset_review_response_summary
from glassbox.runtime.review_responses import review_feedback_response_status
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


def test_response_status_marks_stale_fixup_blocked() -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    artifact_id = new_artifact_id()
    feedback = _feedback_record(session_id, changeset_id, feedback_id).model_copy(
        update={"disposition": ReviewFeedbackDisposition.RESOLVED_LOCALLY}
    )
    inventory = ReviewFeedbackFixupInventoryRecord(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        artifact_schema_version=1,
        source_kind=ReviewFixupSourceKind.MANUAL_WORKSPACE_EDIT,
        source_summary="operator recorded response inventory",
        source_digest="sha256:before",
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        changed_path_count=2,
        matched_scope_path_count=1,
        stale=False,
        recorded_by="operator",
        created_at=datetime.now(UTC),
        last_sequence=5,
    )
    path = ReviewFeedbackFixupPathRecord(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        path="app.py",
        change_kind="modified",
        generated=False,
        test_file=False,
        docs_file=False,
        policy_sensitive=False,
        risk_level="low",
        provenance_confidence="unknown",
        matches_feedback_scope=True,
        summary="app.py: matches feedback scope",
        last_sequence=5,
    )
    freshness = review_fixup_inventory_status(
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        recorded_source_digest="sha256:before",
        current_source_digest="sha256:after",
    )

    status = review_feedback_response_status(
        feedback=feedback,
        inventories=[inventory],
        paths=[path],
        freshness_status=freshness,
    )
    summary = changeset_review_response_summary(
        changeset_id=changeset_id,
        items=[status],
    )

    assert status.response_state == ReviewResponseState.BLOCKED
    assert status.stale is True
    assert status.path_summaries == ["app.py: matches feedback scope"]
    assert "source digest changed" in status.blockers[0]
    assert summary.blocked_count == 1
    assert summary.stale_response_count == 1
    assert summary.unresolved_count == 1


def test_response_status_marks_passed_verification_stale_after_fixup() -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    artifact_id = new_artifact_id()
    verification_id = new_task_verification_id()
    feedback = _feedback_record(session_id, changeset_id, feedback_id).model_copy(
        update={"disposition": ReviewFeedbackDisposition.RESOLVED_LOCALLY}
    )
    inventory = _fixup_inventory_record(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        last_sequence=12,
    )
    path = _fixup_path_record(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        path="app.py",
        last_sequence=12,
    )
    ledger = [
        _ledger(
            session_id=session_id,
            verification_id=verification_id,
            status=TaskVerificationStatus.PASSED,
            changed_paths=["app.py"],
            last_success_sequence=8,
            last_sequence=9,
        )
    ]

    status = review_feedback_response_status(
        feedback=feedback,
        inventories=[inventory],
        paths=[path],
        task_ledger=ledger,
    )

    assert status.response_state == ReviewResponseState.BLOCKED
    assert status.verification_state == ChangesetVerificationState.STALE
    assert "passed before response-linked fixup" in (status.verification_reason or "")
    assert str(verification_id) in status.verification_requirement_ids
    assert "rerun uv run pytest" in status.verification_safe_next_actions[0]
    assert "predates response-linked fixups" in status.safe_next_actions[-1]


def test_response_status_marks_fresh_response_verification_passed() -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    artifact_id = new_artifact_id()
    feedback = _feedback_record(session_id, changeset_id, feedback_id).model_copy(
        update={"disposition": ReviewFeedbackDisposition.RESOLVED_LOCALLY}
    )
    inventory = _fixup_inventory_record(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        last_sequence=10,
    )
    path = _fixup_path_record(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        path="app.py",
        last_sequence=10,
    )
    ledger = [
        _ledger(
            session_id=session_id,
            status=TaskVerificationStatus.PASSED,
            changed_paths=["app.py"],
            last_success_sequence=12,
            last_sequence=12,
        )
    ]

    status = review_feedback_response_status(
        feedback=feedback,
        inventories=[inventory],
        paths=[path],
        task_ledger=ledger,
    )

    assert status.response_state == ReviewResponseState.READY_FOR_HANDOFF
    assert status.verification_state == ChangesetVerificationState.PASSED
    assert "fresh" in (status.verification_reason or "")
    assert status.verification_safe_next_actions == []
    assert status.safe_next_actions[-1].startswith(
        "glassbox changeset handoff-readiness"
    )


def test_response_status_does_not_invent_staleness_without_path_mapping() -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    artifact_id = new_artifact_id()
    feedback = _feedback_record(session_id, changeset_id, feedback_id)
    inventory = _fixup_inventory_record(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        last_sequence=10,
    )

    status = review_feedback_response_status(
        feedback=feedback,
        inventories=[inventory],
        paths=[],
        task_ledger=[],
    )

    assert status.verification_state == ChangesetVerificationState.MISSING
    assert "cannot be mapped" in (status.verification_reason or "")
    assert status.response_state == ReviewResponseState.RESPONDED


def test_response_status_keeps_reopened_feedback_unresolved_with_prior_fixup() -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    artifact_id = new_artifact_id()
    feedback = _feedback_record(session_id, changeset_id, feedback_id).model_copy(
        update={"disposition": ReviewFeedbackDisposition.OPEN, "reopened_count": 1}
    )
    inventory = _fixup_inventory_record(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        last_sequence=10,
    )
    path = _fixup_path_record(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        path="app.py",
        last_sequence=10,
    )

    status = review_feedback_response_status(
        feedback=feedback,
        inventories=[inventory],
        paths=[path],
        task_ledger=[],
    )
    summary = changeset_review_response_summary(
        changeset_id=changeset_id,
        items=[status],
    )

    assert status.response_state == ReviewResponseState.REOPENED
    assert summary.unresolved_count == 1
    assert summary.responded_count == 0


def test_response_status_blocks_mismatched_fixup_inventory_scope() -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    artifact_id = new_artifact_id()
    feedback = _feedback_record(session_id, changeset_id, feedback_id).model_copy(
        update={"disposition": ReviewFeedbackDisposition.RESOLVED_LOCALLY}
    )
    inventory = _fixup_inventory_record(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        last_sequence=10,
    ).model_copy(update={"matched_scope_path_count": 0})
    path = _fixup_path_record(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        path="other.py",
        last_sequence=10,
    ).model_copy(update={"matches_feedback_scope": False})
    ledger = [
        _ledger(
            session_id=session_id,
            status=TaskVerificationStatus.PASSED,
            changed_paths=["other.py"],
            last_success_sequence=12,
            last_sequence=12,
        )
    ]

    status = review_feedback_response_status(
        feedback=feedback,
        inventories=[inventory],
        paths=[path],
        task_ledger=ledger,
    )

    assert status.response_state == ReviewResponseState.BLOCKED
    assert status.verification_state == ChangesetVerificationState.MISSING
    assert "no path records matching feedback scope" in (
        status.verification_reason or ""
    )


def test_response_summary_keeps_accepted_risk_local_and_non_approving() -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    feedback = _feedback_record(session_id, changeset_id, feedback_id).model_copy(
        update={"disposition": ReviewFeedbackDisposition.ACCEPTED_WITH_RISK}
    )

    status = review_feedback_response_status(
        feedback=feedback,
        inventories=[],
        paths=[],
        task_ledger=[],
    )
    summary = changeset_review_response_summary(
        changeset_id=changeset_id,
        items=[status],
    )

    assert status.response_state == ReviewResponseState.ACCEPTED_WITH_RISK
    assert status.verification_state == ChangesetVerificationState.ACCEPTED_WITH_RISK
    assert status.blockers == []
    assert "accepted with local risk" in (status.verification_reason or "")
    assert any("not reviewer acceptance" in claim for claim in status.non_claims)
    assert any("did not stage, commit, push" in claim for claim in status.non_claims)
    assert summary.accepted_risk_count == 1
    assert summary.unresolved_count == 0
    assert summary.safe_next_actions == [
        f"glassbox changeset feedback list --changeset {changeset_id} --cwd .",
        f"glassbox changeset show {changeset_id} --cwd .",
    ]
    assert any("not reviewer acceptance" in claim for claim in summary.non_claims)


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


def _fixup_inventory_record(
    *,
    session_id,
    feedback_id,
    changeset_id,
    artifact_id,
    last_sequence: int,
) -> ReviewFeedbackFixupInventoryRecord:
    return ReviewFeedbackFixupInventoryRecord(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        artifact_schema_version=1,
        source_kind=ReviewFixupSourceKind.MANUAL_WORKSPACE_EDIT,
        source_summary="operator recorded response inventory",
        source_digest="sha256:before",
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        changed_path_count=1,
        matched_scope_path_count=1,
        stale=False,
        recorded_by="operator",
        created_at=datetime.now(UTC),
        last_sequence=last_sequence,
    )


def _fixup_path_record(
    *,
    session_id,
    feedback_id,
    changeset_id,
    artifact_id,
    path: str,
    last_sequence: int,
) -> ReviewFeedbackFixupPathRecord:
    return ReviewFeedbackFixupPathRecord(
        session_id=session_id,
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        artifact_id=artifact_id,
        path=path,
        change_kind="modified",
        generated=False,
        test_file=False,
        docs_file=False,
        policy_sensitive=False,
        risk_level="low",
        provenance_confidence="unknown",
        matches_feedback_scope=True,
        summary=f"{path}: matches feedback scope",
        last_sequence=last_sequence,
    )


def _ledger(
    *,
    session_id,
    status: TaskVerificationStatus,
    verification_id=None,
    changed_paths: list[str] | None = None,
    last_success_sequence: int | None = None,
    last_sequence: int = 10,
) -> TaskVerificationLedgerRecord:
    return TaskVerificationLedgerRecord(
        session_id=session_id,
        task_id=new_task_id(),
        verification_id=verification_id or new_task_verification_id(),
        status=status,
        check_name="focused response check",
        kind=VerificationCheckKind.COMMAND,
        source=VerificationPlanSource.EVAL_RECOMMENDATION,
        command=["uv", "run", "pytest", "tests/test_app.py"],
        changed_paths=[Path(path) for path in changed_paths or []],
        last_success_sequence=last_success_sequence,
        updated_at=datetime.now(UTC),
        last_sequence=last_sequence,
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
