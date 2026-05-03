"""Tests for deterministic changeset commit message suggestions."""

from datetime import UTC
from datetime import datetime

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetRiskLevel
from glassbox.core import ChangesetVerificationState
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewResponseState
from glassbox.core import TaskPlanStatus
from glassbox.core import TaskRecord
from glassbox.core import new_changeset_id
from glassbox.core import new_review_feedback_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.commit_messages import COMMIT_MESSAGE_SUGGESTION_KIND
from glassbox.runtime.commit_messages import build_commit_message_suggestion
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.runtime.commit_readiness import CommitReadinessGitSummary
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.review_responses import ReviewFeedbackResponseStatus


def test_commit_message_suggestion_uses_evidence_and_labels_non_action() -> None:
    fixture = _fixture()

    suggestion = build_commit_message_suggestion(
        changeset=fixture.changeset,
        task=fixture.task,
        verification_plan=_verification_plan(fixture),
        commit_readiness=_commit_readiness(fixture),
        changed_paths=["src/glassbox/runtime/commit_messages.py", "docs/tasks-v12.md"],
    )

    assert suggestion.suggestion_kind == COMMIT_MESSAGE_SUGGESTION_KIND
    assert suggestion.suggestion_label == "suggestion_only_not_committed"
    assert suggestion.subject == "Generate evidence-backed commit message suggestions"
    assert suggestion.message.startswith(
        "Generate evidence-backed commit message suggestions\n\n"
    )
    assert "Task: Commit message task (completed)" in suggestion.message
    assert "Verification: passed - focused tests passed" in suggestion.message
    assert "Commit readiness: ready - evidence is ready" in suggestion.message
    assert "not a commit action" in suggestion.non_claims[0]


def test_commit_message_suggestion_supports_conventional_style_from_docs() -> None:
    fixture = _fixture(objective="Update reviewer docs.")

    suggestion = build_commit_message_suggestion(
        changeset=fixture.changeset,
        task=fixture.task,
        verification_plan=_verification_plan(fixture),
        commit_readiness=_commit_readiness(fixture),
        changed_paths=["docs/commit-readiness.md", "docs/tasks-v12.md"],
        style="conventional",
    )

    assert suggestion.subject == "docs: Update reviewer docs"
    assert suggestion.style == "conventional"
    assert suggestion.limitations == []


def test_commit_message_suggestion_exposes_missing_evidence_limitations() -> None:
    fixture = _fixture(summary=None)

    suggestion = build_commit_message_suggestion(
        changeset=fixture.changeset,
        task=None,
        verification_plan=_verification_plan(fixture),
        commit_readiness=_commit_readiness(fixture),
        changed_paths=[],
    )

    assert suggestion.subject == "Generate evidence-backed commit message suggestions"
    assert "changed-path inventory is missing or empty" in suggestion.limitations
    assert "task record could not be loaded" in suggestion.limitations[0]
    assert "changeset has no separate summary field" in suggestion.limitations


def test_commit_message_suggestion_mentions_review_loop_without_approval_claims() -> (
    None
):
    fixture = _fixture()

    suggestion = build_commit_message_suggestion(
        changeset=fixture.changeset,
        task=fixture.task,
        verification_plan=_verification_plan(fixture),
        commit_readiness=_commit_readiness(
            fixture,
            local_only_evidence_count=1,
        ),
        review_response_summary=_review_response_summary(fixture),
        manual_evidence_count=2,
        changed_paths=["src/glassbox/runtime/commit_messages.py"],
    )

    assert "Review responses: 1 responded, 1 unresolved, 1 stale" in (
        suggestion.message
    )
    assert "not reviewer approval" in suggestion.message
    assert "Manual evidence: 2 item(s); 1 local-only" in suggestion.message
    assert "reviewer approved" not in suggestion.message.lower()
    assert "review response summaries do not claim reviewer approval" in (
        suggestion.non_claims
    )


class _Fixture:
    def __init__(
        self,
        *,
        objective: str = "Generate evidence-backed commit message suggestions.",
        summary: str | None = "Suggestion formatter",
    ) -> None:
        now = datetime.now(UTC)
        self.session_id = new_session_id()
        self.task_id = new_task_id()
        self.changeset = ChangesetRecord(
            session_id=self.session_id,
            changeset_id=new_changeset_id(),
            objective=objective,
            summary=summary,
            status="active",
            created_by="operator",
            task_id=self.task_id,
            risk_level=ChangesetRiskLevel.LOW,
            created_at=now,
            updated_at=now,
            last_sequence=4,
        )
        self.task = TaskRecord(
            task_id=self.task_id,
            session_id=self.session_id,
            title="Commit message task",
            goal="Suggest commit messages from evidence",
            status=TaskPlanStatus.COMPLETED,
            created_at=now,
            updated_at=now,
            last_sequence=5,
        )


def _fixture(
    *,
    objective: str = "Generate evidence-backed commit message suggestions.",
    summary: str | None = "Suggestion formatter",
) -> _Fixture:
    return _Fixture(objective=objective, summary=summary)


def _verification_plan(fixture: _Fixture) -> ChangesetVerificationPlanPreview:
    return ChangesetVerificationPlanPreview(
        changeset_id=fixture.changeset.changeset_id,
        session_id=fixture.session_id,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        changed_paths=["src/glassbox/runtime/commit_messages.py"],
        readiness=ChangesetVerificationReadiness(
            state=ChangesetVerificationState.PASSED,
            summary="focused tests passed",
        ),
    )


def _commit_readiness(
    fixture: _Fixture,
    *,
    local_only_evidence_count: int = 0,
) -> CommitReadinessAssessment:
    return CommitReadinessAssessment(
        changeset_id=fixture.changeset.changeset_id,
        session_id=fixture.session_id,
        state=ChangesetReadinessState.READY,
        reason="evidence is ready",
        manual_evidence_count=local_only_evidence_count,
        local_only_evidence_count=local_only_evidence_count,
        git=CommitReadinessGitSummary(staged_paths=["src/glassbox/runtime/foo.py"]),
    )


def _review_response_summary(
    fixture: _Fixture,
) -> ChangesetReviewResponseSummary:
    item = ReviewFeedbackResponseStatus(
        feedback_id=new_review_feedback_id(),
        changeset_id=fixture.changeset.changeset_id,
        response_state=ReviewResponseState.RESPONDED,
        disposition=ReviewFeedbackDisposition.RESPONDED,
        summary="response cites local fixup evidence",
        fixup_inventory_count=1,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        stale=True,
        verification_state=ChangesetVerificationState.STALE,
    )
    return ChangesetReviewResponseSummary(
        changeset_id=fixture.changeset.changeset_id,
        total_feedback_count=2,
        open_count=1,
        responded_count=1,
        unresolved_count=1,
        stale_response_count=1,
        accepted_risk_count=1,
        blocked_count=0,
        items=[item],
    )
