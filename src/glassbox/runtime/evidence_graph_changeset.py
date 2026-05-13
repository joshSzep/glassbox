"""Changeset evidence graph orchestration."""

from datetime import UTC
from datetime import datetime

from glassbox.core import ClaimSupport
from glassbox.core import EvidenceGraph
from glassbox.core import EvidenceGraphConfidence
from glassbox.core import EvidenceGraphFreshness
from glassbox.core import EvidenceGraphMissingEvidence
from glassbox.core import EvidenceGraphNode
from glassbox.core import EvidenceGraphNodeKind
from glassbox.core import EvidenceGraphRedactionStatus
from glassbox.core import EvidenceGraphVisibility
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.runtime.changeset_models import ChangesetDetailView
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.evidence_graph_builder import _claim_confidence
from glassbox.runtime.evidence_graph_builder import _claim_state
from glassbox.runtime.evidence_graph_builder import _claim_summary
from glassbox.runtime.evidence_graph_builder import _GraphBuilder
from glassbox.runtime.evidence_graph_changeset_inventory import (
    add_inventory_evidence_nodes,
)
from glassbox.runtime.evidence_graph_changeset_review import (
    MAX_CHANGESET_GRAPH_COMMAND_EVIDENCE,
)
from glassbox.runtime.evidence_graph_changeset_review import (
    MAX_CHANGESET_GRAPH_MANUAL_EVIDENCE,
)
from glassbox.runtime.evidence_graph_changeset_review import (
    MAX_CHANGESET_GRAPH_RESPONSE_PLAN_ENTRIES,
)
from glassbox.runtime.evidence_graph_changeset_review import (
    MAX_CHANGESET_GRAPH_REVIEW_FEEDBACK,
)
from glassbox.runtime.evidence_graph_changeset_review import (
    MAX_CHANGESET_GRAPH_SAFE_NEXT_ACTIONS,
)
from glassbox.runtime.evidence_graph_changeset_review import add_command_evidence_nodes
from glassbox.runtime.evidence_graph_changeset_review import add_manual_evidence_nodes
from glassbox.runtime.evidence_graph_changeset_review import add_review_feedback_nodes
from glassbox.runtime.evidence_graph_changeset_review import add_safe_next_action_nodes
from glassbox.runtime.evidence_graph_changeset_review import missing_changeset_evidence
from glassbox.runtime.evidence_graph_changeset_verification import (
    MAX_CHANGESET_GRAPH_REQUIREMENTS,
)
from glassbox.runtime.evidence_graph_changeset_verification import (
    add_verification_requirement_nodes,
)


def build_changeset_evidence_graph(
    detail: ChangesetDetailView,
    *,
    verification_plan: ChangesetVerificationPlanPreview | None = None,
    generated_at: datetime | None = None,
) -> EvidenceGraph:
    """Derive a bounded graph for existing changeset evidence."""

    changeset = detail.changeset
    changeset_id = str(changeset.changeset_id)
    claim_id = f"claim:changeset:{changeset_id}:review-posture"
    graph = _GraphBuilder(
        graph_id=f"graph:changeset:{changeset_id}",
        target=NextActionTarget(
            kind=NextActionTargetKind.CHANGESET,
            target_id=changeset_id,
            label=f"Changeset {changeset_id}",
        ),
        generated_at=generated_at or datetime.now(UTC),
    )
    graph.add_node(
        EvidenceGraphNode(
            node_id=claim_id,
            kind=EvidenceGraphNodeKind.CLAIM,
            title="Changeset review posture",
            summary=changeset.summary or changeset.objective,
            freshness=EvidenceGraphFreshness.FRESH,
            confidence=EvidenceGraphConfidence.UNKNOWN,
            redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
            visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
        )
    )
    if detail.inventory is None:
        graph.add_limitation(
            "Changeset has no structured inventory; this graph remains "
            "inspectable for legacy or sparse changesets, but inventory-backed "
            "claim support is missing."
        )

    stale_node_ids: list[str] = []
    manual_only_node_ids: list[str] = []
    missing: list[EvidenceGraphMissingEvidence] = []
    accepted_risk_node_ids: list[str] = []
    supporting_edge_ids: list[str] = []
    contradicting_edge_ids: list[str] = []

    if detail.inventory is None:
        missing.append(
            missing_changeset_evidence(
                "missing:changeset-inventory",
                EvidenceGraphNodeKind.ARTIFACT,
                "No structured changeset inventory is attached.",
                detail.safe_next_actions,
                target_id=changeset_id,
            )
        )
    else:
        add_inventory_evidence_nodes(
            graph,
            detail,
            claim_id=claim_id,
            stale_node_ids=stale_node_ids,
            supporting_edge_ids=supporting_edge_ids,
        )

    if verification_plan is None:
        graph.add_limitation(
            "No verification plan preview was supplied; this graph remains "
            "compatible with older changesets, but verification-plan support "
            "is missing."
        )
        missing.append(
            missing_changeset_evidence(
                "missing:verification-plan",
                EvidenceGraphNodeKind.VERIFICATION_CHECK,
                "No verification plan preview was supplied to this graph.",
                detail.safe_next_actions,
                target_id=changeset_id,
            )
        )
    else:
        add_verification_requirement_nodes(
            graph,
            verification_plan,
            claim_id=claim_id,
            stale_node_ids=stale_node_ids,
            manual_only_node_ids=manual_only_node_ids,
            accepted_risk_node_ids=accepted_risk_node_ids,
            supporting_edge_ids=supporting_edge_ids,
            contradicting_edge_ids=contradicting_edge_ids,
        )

    add_manual_evidence_nodes(
        graph,
        detail,
        claim_id=claim_id,
        stale_node_ids=stale_node_ids,
        supporting_edge_ids=supporting_edge_ids,
    )
    response_plan_accepted_risk_count = add_review_feedback_nodes(
        graph,
        detail,
        claim_id=claim_id,
        stale_node_ids=stale_node_ids,
        manual_only_node_ids=manual_only_node_ids,
        accepted_risk_node_ids=accepted_risk_node_ids,
        supporting_edge_ids=supporting_edge_ids,
        contradicting_edge_ids=contradicting_edge_ids,
    )
    add_command_evidence_nodes(
        graph,
        detail,
        claim_id=claim_id,
        supporting_edge_ids=supporting_edge_ids,
    )
    add_safe_next_action_nodes(
        graph,
        detail,
        changeset_id=changeset_id,
        claim_id=claim_id,
    )

    claim_state = _claim_state(
        missing=missing,
        stale_node_ids=stale_node_ids,
        contradicting_edge_ids=contradicting_edge_ids,
        accepted_risk_count=(
            changeset.accepted_risk_count
            + detail.review_response_summary.accepted_risk_count
            + (
                verification_plan.readiness.accepted_risk_count
                if verification_plan is not None
                else 0
            )
            + response_plan_accepted_risk_count
        ),
        manual_evidence_count=len(detail.manual_evidence),
        manual_only_node_count=len(manual_only_node_ids),
        deterministic_support_count=(
            detail.command_evidence.verification_count
            + (
                1
                if verification_plan is not None
                and verification_plan.readiness.state.value == "passed"
                else 0
            )
        ),
    )
    graph.add_claim(
        ClaimSupport(
            claim_id=claim_id,
            title="Changeset review posture",
            summary=_claim_summary(claim_state),
            state=claim_state,
            confidence=_claim_confidence(claim_state),
            supporting_edge_ids=supporting_edge_ids[:100],
            contradicting_edge_ids=contradicting_edge_ids[:100],
            stale_node_ids=list(dict.fromkeys(stale_node_ids))[:100],
            missing_evidence=missing[:50],
            accepted_risk_node_ids=list(dict.fromkeys(accepted_risk_node_ids))[:100],
            limitations=detail.limitations[:20],
            visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
        )
    )
    return graph.build()


__all__ = [
    "MAX_CHANGESET_GRAPH_COMMAND_EVIDENCE",
    "MAX_CHANGESET_GRAPH_MANUAL_EVIDENCE",
    "MAX_CHANGESET_GRAPH_REQUIREMENTS",
    "MAX_CHANGESET_GRAPH_RESPONSE_PLAN_ENTRIES",
    "MAX_CHANGESET_GRAPH_REVIEW_FEEDBACK",
    "MAX_CHANGESET_GRAPH_SAFE_NEXT_ACTIONS",
    "build_changeset_evidence_graph",
]
