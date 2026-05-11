"""Tests for advisory changeset handoff readiness."""

from datetime import UTC
from datetime import datetime

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ChangesetRiskLevel
from glassbox.core import ChangesetVerificationState
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ManualEvidenceRedactionStatus
from glassbox.core import ManualEvidenceState
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
from glassbox.core import new_manual_evidence_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.changesets import ChangesetInventoryStatus
from glassbox.runtime.changesets import ChangesetVerificationPlanLifecycleSummary
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.runtime.commit_readiness import CommitReadinessGitSummary
from glassbox.runtime.handoff_readiness import HandoffReadinessSignal
from glassbox.runtime.handoff_readiness import derive_handoff_readiness
from glassbox.runtime.review_readiness_signals import first_blocking_state
from glassbox.runtime.review_readiness_signals import limitations_for_signal_ids
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary


def test_handoff_readiness_commit_prep_ready_without_claiming_publication() -> None:
    fixture = _fixture()

    assessment = derive_handoff_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture,
            state=ChangesetVerificationState.PASSED,
        ),
        review_briefs=[_review_brief(fixture)],
        review_response_summary=_response_summary(fixture),
        manual_evidence=[],
        readiness=[_readiness(fixture, ChangesetReadinessState.READY)],
        commit_readiness=_commit_readiness(fixture, ChangesetReadinessState.READY),
    )

    assert assessment.state == "commit_prep_ready"
    assert assessment.blockers == []
    assert assessment.verification_plan_summary.passed_count == 1
    assert "not publication" in assessment.non_claims[0]
    assert any("commit-prep" in action for action in assessment.safe_next_actions)
    assert any(
        "no retained review feedback" in limitation
        for limitation in assessment.limitations
    )


def test_handoff_readiness_blocks_unresolved_review_feedback() -> None:
    fixture = _fixture()

    assessment = derive_handoff_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture,
            state=ChangesetVerificationState.PASSED,
        ),
        review_briefs=[_review_brief(fixture)],
        review_response_summary=_response_summary(
            fixture,
            total_feedback_count=2,
            unresolved_count=1,
        ),
        manual_evidence=[],
        readiness=[_readiness(fixture, ChangesetReadinessState.READY)],
        commit_readiness=_commit_readiness(fixture, ChangesetReadinessState.READY),
    )

    assert assessment.state == "needs_review_response"
    assert assessment.blockers == ["1 review feedback item still need response"]
    assert any("feedback status" in action for action in assessment.safe_next_actions)


def test_handoff_readiness_prioritizes_stale_inventory() -> None:
    fixture = _fixture()

    assessment = derive_handoff_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=ChangesetInventoryStatus(
            freshness=ChangesetInventoryFreshness.STALE,
            stale=True,
            reason="workspace diff changed after inventory",
        ),
        verification_plan=_verification_plan(
            fixture,
            state=ChangesetVerificationState.PASSED,
        ),
        review_briefs=[_review_brief(fixture)],
        review_response_summary=_response_summary(
            fixture,
            total_feedback_count=1,
            unresolved_count=1,
        ),
        manual_evidence=[],
        readiness=[_readiness(fixture, ChangesetReadinessState.READY)],
        commit_readiness=_commit_readiness(fixture, ChangesetReadinessState.READY),
    )

    assert assessment.state == "stale_inventory"
    assert assessment.reason.startswith("stale inventory: workspace diff changed")
    assert "git status --short" in assessment.safe_next_actions


def test_handoff_readiness_surfaces_local_only_accepted_risk() -> None:
    fixture = _fixture(accepted_risk_count=1)

    assessment = derive_handoff_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture,
            state=ChangesetVerificationState.PASSED,
        ),
        review_briefs=[_review_brief(fixture)],
        review_response_summary=_response_summary(fixture, accepted_risk_count=1),
        manual_evidence=[_manual_evidence(fixture)],
        readiness=[_readiness(fixture, ChangesetReadinessState.READY)],
        commit_readiness=_commit_readiness(fixture, ChangesetReadinessState.READY),
    )

    assert assessment.state == "accepted_with_risk"
    assert assessment.evidence.accepted_risk_count == 2
    assert assessment.evidence.local_only_evidence_count == 1
    assert "local-only evidence" in assessment.limitations[0]
    assert any(signal.signal_id == "accepted-risk" for signal in assessment.signals)


def test_handoff_readiness_surfaces_skipped_live_evidence_as_limitation() -> None:
    fixture = _fixture()

    assessment = derive_handoff_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture,
            state=ChangesetVerificationState.PASSED,
        ),
        review_briefs=[_review_brief(fixture)],
        review_response_summary=_response_summary(fixture),
        manual_evidence=[_skipped_browser_evidence(fixture)],
        readiness=[_readiness(fixture, ChangesetReadinessState.READY)],
        commit_readiness=_commit_readiness(fixture, ChangesetReadinessState.READY),
    )

    assert assessment.evidence.skipped_live_evidence_count == 1
    assert assessment.evidence.skipped_browser_evidence_count == 1
    assert assessment.evidence.skipped_accessibility_evidence_count == 0
    assert any(
        signal.signal_id == "skipped-live-evidence" and not signal.blocking
        for signal in assessment.signals
    )
    assert any("skipped browser" in limitation for limitation in assessment.limitations)
    assert "skipped live evidence" in " ".join(assessment.non_claims)


def test_shared_readiness_signal_helpers_preserve_handoff_signal_semantics() -> None:
    signals = [
        HandoffReadinessSignal(
            signal_id="local-only-evidence",
            state="handoff_ready",
            summary="local-only evidence remains labeled",
            blocking=False,
        ),
        HandoffReadinessSignal(
            signal_id="unresolved-review-feedback",
            state="needs_review_response",
            summary="feedback still needs response",
        ),
        HandoffReadinessSignal(
            signal_id="stale-inventory",
            state="stale_inventory",
            summary="inventory is stale",
        ),
    ]

    assert (
        first_blocking_state(
            signals,
            ("stale_inventory", "needs_review_response"),
        )
        == "stale_inventory"
    )
    assert limitations_for_signal_ids(
        signals,
        (
            ("local-only-evidence", "local evidence must stay labeled"),
            ("skipped-live-evidence", "skipped evidence is advisory"),
        ),
    ) == ["local evidence must stay labeled"]


class _Fixture:
    def __init__(self, *, accepted_risk_count: int = 0) -> None:
        now = datetime.now(UTC)
        self.verification_id = new_task_verification_id()
        self.changeset = ChangesetRecord(
            session_id=new_session_id(),
            changeset_id=new_changeset_id(),
            objective="Prepare handoff readiness",
            summary="Change updates review-loop handoff logic",
            status="active",
            created_by="operator",
            task_id=new_task_id(),
            latest_verification_id=self.verification_id,
            risk_level=ChangesetRiskLevel.LOW,
            accepted_risk_count=accepted_risk_count,
            created_at=now,
            updated_at=now,
            last_sequence=10,
        )
        self.inventory = ChangesetInventoryRecord(
            session_id=self.changeset.session_id,
            changeset_id=self.changeset.changeset_id,
            artifact_id=new_artifact_id(),
            artifact_schema_version=1,
            freshness=ChangesetInventoryFreshness.FRESH,
            changed_path_count=1,
            source_digest="sha256:abc123",
            refreshed_by="operator",
            risk_level=ChangesetRiskLevel.LOW,
            updated_at=now,
            last_sequence=11,
        )


def _fixture(*, accepted_risk_count: int = 0) -> _Fixture:
    return _Fixture(accepted_risk_count=accepted_risk_count)


def _fresh_inventory_status() -> ChangesetInventoryStatus:
    return ChangesetInventoryStatus(
        freshness=ChangesetInventoryFreshness.FRESH,
        stale=False,
        recorded_source_digest="sha256:abc123",
        current_source_digest="sha256:abc123",
    )


def _verification_plan(
    fixture: _Fixture,
    *,
    state: ChangesetVerificationState,
) -> ChangesetVerificationPlanPreview:
    return ChangesetVerificationPlanPreview(
        changeset_id=fixture.changeset.changeset_id,
        session_id=fixture.changeset.session_id,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        changed_paths=["src/app.py"],
        recommended_commands=["uv run pytest tests/unit/test_app.py"],
        readiness=ChangesetVerificationReadiness(
            state=state,
            summary=f"verification is {state.value}",
        ),
        plan_summary=ChangesetVerificationPlanLifecycleSummary(
            total_count=1,
            passed_count=1 if state == ChangesetVerificationState.PASSED else 0,
            failed_count=1 if state == ChangesetVerificationState.FAILED else 0,
            stale_count=1 if state == ChangesetVerificationState.STALE else 0,
            safe_next_actions=["uv run pytest tests/unit/test_app.py"],
        ),
        retained_artifact_ids=[],
        safe_next_actions=["uv run pytest tests/unit/test_app.py"],
    )


def _review_brief(fixture: _Fixture) -> ChangesetReviewBriefRecord:
    now = datetime.now(UTC)
    return ChangesetReviewBriefRecord(
        session_id=fixture.changeset.session_id,
        changeset_id=fixture.changeset.changeset_id,
        artifact_id=new_artifact_id(),
        artifact_schema_version=2,
        render_targets=["markdown", "json"],
        inventory_artifact_id=fixture.inventory.artifact_id,
        verification_id=fixture.verification_id,
        created_by="operator",
        redacted=True,
        local_only=True,
        created_at=now,
        last_sequence=12,
    )


def _readiness(
    fixture: _Fixture,
    state: ChangesetReadinessState,
) -> ChangesetReadinessRecord:
    now = datetime.now(UTC)
    return ChangesetReadinessRecord(
        session_id=fixture.changeset.session_id,
        changeset_id=fixture.changeset.changeset_id,
        readiness_kind=ChangesetReadinessKind.REVIEW,
        state=state,
        reason="review ready",
        accepted_risk_count=0,
        decided_by="operator",
        updated_at=now,
        last_sequence=13,
    )


def _response_summary(
    fixture: _Fixture,
    *,
    total_feedback_count: int = 0,
    unresolved_count: int = 0,
    accepted_risk_count: int = 0,
) -> ChangesetReviewResponseSummary:
    return ChangesetReviewResponseSummary(
        changeset_id=fixture.changeset.changeset_id,
        total_feedback_count=total_feedback_count,
        open_count=unresolved_count,
        responded_count=total_feedback_count - unresolved_count,
        unresolved_count=unresolved_count,
        stale_response_count=0,
        accepted_risk_count=accepted_risk_count,
        blocked_count=0,
        items=[],
        blockers=[],
        safe_next_actions=[
            "glassbox changeset feedback status "
            f"{fixture.changeset.changeset_id} --cwd ."
        ],
        non_claims=["review feedback is local evidence, not approval"],
    )


def _commit_readiness(
    fixture: _Fixture,
    state: ChangesetReadinessState,
) -> CommitReadinessAssessment:
    return CommitReadinessAssessment(
        changeset_id=fixture.changeset.changeset_id,
        session_id=fixture.changeset.session_id,
        state=state,
        reason=f"commit readiness is {state.value}",
        blockers=[],
        safe_next_actions=["git status --short"],
        inventory_artifact_id=fixture.inventory.artifact_id,
        review_brief_artifact_id=new_artifact_id(),
        verification_id=fixture.verification_id,
        accepted_risk_count=0,
        git=CommitReadinessGitSummary(
            branch="main",
            staged_paths=["src/app.py"],
            workspace_path_count=1,
            staged_path_count=1,
        ),
        signals=[],
        non_claims=["this model does not stage files or run git commit"],
    )


def _manual_evidence(fixture: _Fixture) -> ManualEvidenceRecord:
    now = datetime.now(UTC)
    return ManualEvidenceRecord(
        session_id=fixture.changeset.session_id,
        evidence_id=new_manual_evidence_id(),
        evidence_kind=ManualEvidenceKind.EXTERNAL_CHECK,
        state=ManualEvidenceState.ATTACHED,
        target_kind=ManualEvidenceTargetKind.CHANGESET,
        target_id=str(fixture.changeset.changeset_id),
        changeset_id=fixture.changeset.changeset_id,
        artifact_id=new_artifact_id(),
        artifact_schema_version=1,
        summary="external CI reported green",
        source_label="external-ci",
        created_by="operator",
        local_only=True,
        redaction_status=ManualEvidenceRedactionStatus.LOCAL_ONLY,
        freshness=ManualEvidenceFreshness.CURRENT,
        limitations=["manual evidence is summary-first"],
        non_claims=["manual evidence is not retained command evidence"],
        created_at=now,
        updated_at=now,
        last_sequence=15,
    )


def _skipped_browser_evidence(fixture: _Fixture) -> ManualEvidenceRecord:
    evidence = _manual_evidence(fixture)
    return evidence.model_copy(
        update={
            "evidence_kind": ManualEvidenceKind.BROWSER_OBSERVATION,
            "summary": "dashboard walkthrough intentionally skipped",
            "source_label": "dashboard-local",
            "freshness": ManualEvidenceFreshness.NEEDS_INSPECTION,
            "limitations": [
                "browser/dashboard evidence is advisory live evidence",
                "capture state: not_run",
                "skip reason: local dashboard server was not started",
                "skipped browser/dashboard evidence is not a pass",
            ],
            "non_claims": [
                "not deterministic release authority",
                "skipped browser/dashboard evidence is not a pass",
            ],
        }
    )
