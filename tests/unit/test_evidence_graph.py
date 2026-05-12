"""Unit tests for derived evidence graph helpers."""

from datetime import UTC
from datetime import datetime

from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetRiskLevel
from glassbox.core import ChangesetVerificationState
from glassbox.core import ClaimSupportState
from glassbox.core import EvidenceGraphFreshness
from glassbox.core import EvidenceGraphVisibility
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ManualEvidenceRedactionStatus
from glassbox.core import ManualEvidenceState
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewResponseState
from glassbox.core import SessionId
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanSource
from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
from glassbox.core import new_manual_evidence_id
from glassbox.core import new_review_feedback_id
from glassbox.core import new_session_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.changeset_models import ChangesetCommandEvidenceSummary
from glassbox.runtime.changeset_models import ChangesetDetailView
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.changeset_models import ChangesetVerificationReviewLoopSummary
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationRequirement,
)
from glassbox.runtime.evidence_graph import build_changeset_evidence_graph
from glassbox.runtime.evidence_graph import claim_support
from glassbox.runtime.evidence_graph import evidence_neighborhood
from glassbox.runtime.evidence_graph import reviewer_safe_graph_slice
from glassbox.runtime.evidence_graph import summarize_evidence_graph
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.review_responses import ReviewFeedbackResponseStatus
from glassbox.runtime.review_responses import ReviewFeedbackVerificationPlanEntryStatus


def test_changeset_evidence_graph_derives_supported_claim() -> None:
    detail = _detail()
    plan = _plan(detail.changeset.changeset_id, detail.changeset.session_id)

    graph = build_changeset_evidence_graph(
        detail,
        verification_plan=plan,
        generated_at=_now(),
    )
    summary = summarize_evidence_graph(graph)
    claim = graph.claims[0]

    assert claim.state == ClaimSupportState.SUPPORTED
    assert summary.claim_count == 1
    assert summary.stale_claim_count == 0
    assert claim_support(graph, claim.claim_id) == claim


def test_changeset_evidence_graph_marks_stale_evidence() -> None:
    detail = _detail(inventory_stale=True)
    plan = _plan(
        detail.changeset.changeset_id,
        detail.changeset.session_id,
        requirement_state=ChangesetVerificationState.STALE,
    )

    graph = build_changeset_evidence_graph(
        detail,
        verification_plan=plan,
        generated_at=_now(),
    )

    assert graph.claims[0].state == ClaimSupportState.STALE
    assert any(node.freshness == EvidenceGraphFreshness.STALE for node in graph.nodes)
    assert summarize_evidence_graph(graph).stale_claim_count == 1


def test_changeset_evidence_graph_exposes_missing_evidence() -> None:
    detail = _detail(inventory=False)

    graph = build_changeset_evidence_graph(detail, generated_at=_now())

    assert graph.claims[0].state == ClaimSupportState.MISSING
    assert {item.missing_id for item in graph.claims[0].missing_evidence} == {
        "missing:changeset-inventory",
        "missing:verification-plan",
    }
    assert any("legacy or sparse changesets" in item for item in graph.limitations)
    assert any(
        "verification-plan support is missing" in item for item in graph.limitations
    )


def test_changeset_evidence_graph_marks_skipped_as_manual_only() -> None:
    detail = _detail()
    plan = _plan(
        detail.changeset.changeset_id,
        detail.changeset.session_id,
        requirement_state=ChangesetVerificationState.SKIPPED,
    )

    graph = build_changeset_evidence_graph(
        detail,
        verification_plan=plan,
        generated_at=_now(),
    )

    assert graph.claims[0].state == ClaimSupportState.MANUAL_ONLY
    assert any(
        node.freshness == EvidenceGraphFreshness.MANUAL_ONLY for node in graph.nodes
    )


def test_changeset_evidence_graph_marks_manual_only_evidence() -> None:
    detail = _detail(manual=True)
    plan = _plan(
        detail.changeset.changeset_id,
        detail.changeset.session_id,
        requirement_state=ChangesetVerificationState.NOT_APPLICABLE,
    )

    graph = build_changeset_evidence_graph(
        detail,
        verification_plan=plan,
        generated_at=_now(),
    )

    assert graph.claims[0].state == ClaimSupportState.MANUAL_ONLY
    assert graph.claims[0].supporting_edge_ids


def test_changeset_evidence_graph_marks_accepted_risk() -> None:
    detail = _detail(accepted_risk_count=1)
    plan = _plan(
        detail.changeset.changeset_id,
        detail.changeset.session_id,
        requirement_state=ChangesetVerificationState.ACCEPTED_WITH_RISK,
    )

    graph = build_changeset_evidence_graph(
        detail,
        verification_plan=plan,
        generated_at=_now(),
    )

    assert graph.claims[0].state == ClaimSupportState.ACCEPTED_WITH_RISK
    assert summarize_evidence_graph(graph).accepted_risk_claim_count == 1


def test_changeset_evidence_graph_links_feedback_fixups_to_verification() -> None:
    detail = _detail(feedback_plan_link=True)
    plan = _plan(detail.changeset.changeset_id, detail.changeset.session_id)

    graph = build_changeset_evidence_graph(
        detail,
        verification_plan=plan,
        generated_at=_now(),
    )

    assert graph.claims[0].state == ClaimSupportState.CONTRADICTED
    assert any(
        node.title == "Response-linked fixup inventory"
        and node.freshness == EvidenceGraphFreshness.FRESH
        for node in graph.nodes
    )
    assert any(
        node.title == "focused response check"
        and node.freshness == EvidenceGraphFreshness.STALE
        for node in graph.nodes
    )


def test_evidence_graph_neighborhood_and_reviewer_safe_slice() -> None:
    detail = _detail(manual=True, manual_local_only=True)
    plan = _plan(detail.changeset.changeset_id, detail.changeset.session_id)
    graph = build_changeset_evidence_graph(
        detail,
        verification_plan=plan,
        generated_at=_now(),
    )
    claim_id = graph.claims[0].claim_id

    neighborhood = evidence_neighborhood(graph, claim_id, depth=1)
    safe = reviewer_safe_graph_slice(graph)

    assert neighborhood.nodes
    assert all(
        node.visibility != EvidenceGraphVisibility.OPERATOR_ONLY for node in safe.nodes
    )


def _detail(
    *,
    inventory: bool = True,
    inventory_stale: bool = False,
    manual: bool = False,
    manual_local_only: bool = False,
    accepted_risk_count: int = 0,
    feedback_plan_link: bool = False,
) -> ChangesetDetailView:
    now = _now()
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    changeset = ChangesetRecord(
        session_id=session_id,
        changeset_id=changeset_id,
        objective="Review local changes",
        summary="Review local changes",
        status="open",
        created_by="operator",
        risk_level=ChangesetRiskLevel.LOW,
        accepted_risk_count=accepted_risk_count,
        created_at=now,
        updated_at=now,
        last_sequence=1,
    )
    inventory_record = (
        ChangesetInventoryRecord(
            session_id=session_id,
            changeset_id=changeset_id,
            artifact_id=new_artifact_id(),
            artifact_schema_version=1,
            freshness=(
                ChangesetInventoryFreshness.STALE
                if inventory_stale
                else ChangesetInventoryFreshness.FRESH
            ),
            changed_path_count=2,
            refreshed_by="operator",
            risk_level=ChangesetRiskLevel.LOW,
            updated_at=now,
            last_sequence=2,
        )
        if inventory
        else None
    )
    review_feedback = (
        [_review_feedback(session_id, changeset_id)] if feedback_plan_link else []
    )
    review_response_summary = (
        _review_response_summary_with_plan_link(
            changeset_id,
            review_feedback[0].feedback_id,
        )
        if review_feedback
        else _review_response_summary(
            changeset_id,
            stale_response_count=1 if inventory_stale else 0,
            accepted_risk_count=accepted_risk_count,
        )
    )
    return ChangesetDetailView(
        changeset=changeset,
        inventory=inventory_record,
        inventory_status=ChangesetInventoryStatus(
            freshness=(
                ChangesetInventoryFreshness.STALE
                if inventory_stale
                else ChangesetInventoryFreshness.FRESH
            ),
            stale=inventory_stale,
            reason="workspace changed" if inventory_stale else None,
            safe_next_actions=["glassbox changeset refresh CHANGESET --cwd ."],
        ),
        review_response_summary=review_response_summary,
        manual_evidence=[
            _manual_evidence(
                session_id,
                changeset_id,
                local_only=manual_local_only,
            )
        ]
        if manual
        else [],
        review_feedback=review_feedback,
        readiness=[],
        command_evidence=ChangesetCommandEvidenceSummary(),
        limitations=["detail limitation"] if inventory_stale else [],
        safe_next_actions=["glassbox changeset show CHANGESET --cwd ."],
    )


def _plan(
    changeset_id: ChangesetId,
    session_id: SessionId,
    *,
    requirement_state: ChangesetVerificationState = ChangesetVerificationState.PASSED,
) -> ChangesetVerificationPlanPreview:
    requirement = ChangesetVerificationRequirement(
        requirement_id="pytest",
        state=requirement_state,
        check_name="pytest",
        reason=f"pytest is {requirement_state.value}",
        source=VerificationPlanSource.CHANGED_PATHS,
        kind=VerificationCheckKind.TEST,
        blocking=requirement_state != ChangesetVerificationState.NOT_APPLICABLE,
    )
    readiness = ChangesetVerificationReadiness(
        state=requirement_state,
        summary=f"verification is {requirement_state.value}",
        requirements=[requirement],
        stale_count=1 if requirement_state == ChangesetVerificationState.STALE else 0,
        missing_count=(
            1 if requirement_state == ChangesetVerificationState.MISSING else 0
        ),
        failed_count=1 if requirement_state == ChangesetVerificationState.FAILED else 0,
        accepted_risk_count=(
            1
            if requirement_state == ChangesetVerificationState.ACCEPTED_WITH_RISK
            else 0
        ),
    )
    return ChangesetVerificationPlanPreview(
        changeset_id=changeset_id,
        session_id=session_id,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        review_loop_summary=ChangesetVerificationReviewLoopSummary(
            retained_verification_state=requirement_state
        ),
        readiness=readiness,
    )


def _manual_evidence(
    session_id: SessionId,
    changeset_id: ChangesetId,
    *,
    local_only: bool,
) -> ManualEvidenceRecord:
    now = _now()
    return ManualEvidenceRecord(
        session_id=session_id,
        evidence_id=new_manual_evidence_id(),
        evidence_kind=ManualEvidenceKind.EXTERNAL_CHECK,
        state=ManualEvidenceState.ATTACHED,
        target_kind=ManualEvidenceTargetKind.CHANGESET,
        target_id=str(changeset_id),
        changeset_id=changeset_id,
        artifact_id=new_artifact_id(),
        artifact_schema_version=1,
        summary="External check was inspected manually.",
        source_label="external-check",
        created_by="operator",
        local_only=local_only,
        redaction_status=(
            ManualEvidenceRedactionStatus.LOCAL_ONLY
            if local_only
            else ManualEvidenceRedactionStatus.PASSED
        ),
        freshness=ManualEvidenceFreshness.CURRENT,
        limitations=["manual evidence is advisory"],
        non_claims=["manual evidence is not command evidence"],
        created_at=now,
        updated_at=now,
        last_sequence=3,
    )


def _review_response_summary(
    changeset_id: ChangesetId,
    *,
    stale_response_count: int = 0,
    accepted_risk_count: int = 0,
) -> ChangesetReviewResponseSummary:
    feedback_id = new_review_feedback_id()
    item = ReviewFeedbackResponseStatus(
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        response_state=ReviewResponseState.RESPONDED,
        disposition=ReviewFeedbackDisposition.RESPONDED,
        summary="feedback responded",
        fixup_inventory_count=1,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
    )
    return ChangesetReviewResponseSummary(
        changeset_id=changeset_id,
        total_feedback_count=1,
        open_count=0,
        responded_count=1,
        unresolved_count=0,
        stale_response_count=stale_response_count,
        accepted_risk_count=accepted_risk_count,
        blocked_count=0,
        items=[item],
    )


def _review_response_summary_with_plan_link(
    changeset_id: ChangesetId,
    feedback_id,
) -> ChangesetReviewResponseSummary:
    artifact_id = new_artifact_id()
    verification_id = new_task_verification_id()
    item = ReviewFeedbackResponseStatus(
        feedback_id=feedback_id,
        changeset_id=changeset_id,
        response_state=ReviewResponseState.BLOCKED,
        disposition=ReviewFeedbackDisposition.RESPONDED,
        summary="feedback responded",
        fixup_inventory_count=1,
        latest_fixup_inventory_artifact_id=artifact_id,
        latest_fixup_inventory_sequence=8,
        latest_source_summary="operator recorded response inventory",
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        changed_path_count=1,
        matched_scope_path_count=1,
        verification_state=ChangesetVerificationState.STALE,
        verification_reason="focused response check predates response fixup",
        verification_requirement_ids=[str(verification_id)],
        verification_plan_entries=[
            ReviewFeedbackVerificationPlanEntryStatus(
                verification_id=verification_id,
                check_name="focused response check",
                status="passed",
                relationship="stale",
                reason="focused response check predates response fixup",
                command=["uv", "run", "pytest"],
                changed_paths=["app.py"],
            )
        ],
        stale_plan_entry_count=1,
    )
    return ChangesetReviewResponseSummary(
        changeset_id=changeset_id,
        total_feedback_count=1,
        open_count=0,
        responded_count=0,
        unresolved_count=1,
        stale_response_count=1,
        accepted_risk_count=0,
        blocked_count=1,
        items=[item],
    )


def _review_feedback(
    session_id: SessionId,
    changeset_id: ChangesetId,
) -> ReviewFeedbackRecord:
    now = _now()
    return ReviewFeedbackRecord(
        session_id=session_id,
        feedback_id=new_review_feedback_id(),
        changeset_id=changeset_id,
        feedback_kind=ReviewFeedbackKind.REQUESTED_CHANGE,
        provenance=ReviewFeedbackProvenance.REVIEWER,
        disposition=ReviewFeedbackDisposition.RESPONDED,
        summary="Review feedback was handled.",
        body=None,
        source_label="local-review",
        reviewer_label="reviewer",
        created_by="operator",
        updated_by="operator",
        resolved_by=None,
        archived_by=None,
        accepted_by=None,
        resolution_summary=None,
        residual_risk=None,
        risk_summary=None,
        acceptance_reason=None,
        archived_reason=None,
        replacement_feedback_id=None,
        reopened_count=0,
        created_at=now,
        updated_at=now,
        last_sequence=4,
    )


def _now() -> datetime:
    return datetime(2026, 5, 10, tzinfo=UTC)
