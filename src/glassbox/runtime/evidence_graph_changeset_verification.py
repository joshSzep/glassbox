"""Changeset verification evidence graph node derivation."""

from glassbox.core import EvidenceGraphConfidence
from glassbox.core import EvidenceGraphEdgeKind
from glassbox.core import EvidenceGraphFreshness
from glassbox.core import EvidenceGraphNode
from glassbox.core import EvidenceGraphNodeKind
from glassbox.core import EvidenceGraphProvenance
from glassbox.core import EvidenceGraphRedactionStatus
from glassbox.core import EvidenceGraphVisibility
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.evidence_graph_builder import _add_truncation_limitation
from glassbox.runtime.evidence_graph_builder import _GraphBuilder

MAX_CHANGESET_GRAPH_REQUIREMENTS = 50


def add_verification_requirement_nodes(
    graph: _GraphBuilder,
    verification_plan: ChangesetVerificationPlanPreview,
    *,
    claim_id: str,
    stale_node_ids: list[str],
    manual_only_node_ids: list[str],
    accepted_risk_node_ids: list[str],
    supporting_edge_ids: list[str],
    contradicting_edge_ids: list[str],
) -> None:
    """Add verification readiness requirement nodes for a changeset graph."""

    _add_truncation_limitation(
        graph,
        label="verification requirement",
        total=len(verification_plan.readiness.requirements),
        limit=MAX_CHANGESET_GRAPH_REQUIREMENTS,
    )
    for requirement in verification_plan.readiness.requirements[
        :MAX_CHANGESET_GRAPH_REQUIREMENTS
    ]:
        node_id = f"verification:{requirement.requirement_id}"
        freshness = _requirement_freshness(requirement.state.value)
        if freshness == EvidenceGraphFreshness.STALE:
            stale_node_ids.append(node_id)
        if freshness == EvidenceGraphFreshness.MANUAL_ONLY:
            manual_only_node_ids.append(node_id)
        if requirement.state.value == "accepted_with_risk":
            accepted_risk_node_ids.append(node_id)
        graph.add_node(
            EvidenceGraphNode(
                node_id=node_id,
                kind=EvidenceGraphNodeKind.VERIFICATION_CHECK,
                title=requirement.check_name,
                summary=requirement.reason,
                provenance=[
                    EvidenceGraphProvenance(
                        source_kind="verification_requirement",
                        source_id=requirement.requirement_id,
                        summary=requirement.evidence_summary
                        or "changeset verification readiness requirement",
                    )
                ],
                freshness=freshness,
                confidence=_requirement_confidence(requirement.state.value),
                redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
                visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
                limitations=requirement.safe_next_actions,
            )
        )
        edge_kind = (
            EvidenceGraphEdgeKind.CONTRADICTS
            if requirement.state.value == "failed"
            else EvidenceGraphEdgeKind.SUPPORTS
        )
        edge_id = graph.add_edge(
            edge_kind,
            node_id,
            claim_id,
            f"{requirement.state.value} verification requirement shapes claim",
            confidence=_requirement_confidence(requirement.state.value),
        )
        if edge_kind == EvidenceGraphEdgeKind.CONTRADICTS:
            contradicting_edge_ids.append(edge_id)
        else:
            supporting_edge_ids.append(edge_id)


def _requirement_freshness(state: str) -> EvidenceGraphFreshness:
    if state == "passed":
        return EvidenceGraphFreshness.FRESH
    if state == "stale":
        return EvidenceGraphFreshness.STALE
    if state == "missing":
        return EvidenceGraphFreshness.MISSING
    if state == "skipped":
        return EvidenceGraphFreshness.MANUAL_ONLY
    return EvidenceGraphFreshness.UNKNOWN


def _requirement_confidence(state: str) -> EvidenceGraphConfidence:
    if state == "passed":
        return EvidenceGraphConfidence.HIGH
    if state in {"failed", "stale", "accepted_with_risk"}:
        return EvidenceGraphConfidence.MEDIUM
    if state in {"missing", "skipped"}:
        return EvidenceGraphConfidence.LOW
    return EvidenceGraphConfidence.UNKNOWN


__all__ = ["MAX_CHANGESET_GRAPH_REQUIREMENTS", "add_verification_requirement_nodes"]
