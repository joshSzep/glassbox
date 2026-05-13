"""Evidence graph response helpers for changeset HTTP routes."""

from glassbox.core import ClaimSupport
from glassbox.core import EvidenceGraph
from glassbox.core import EvidenceGraphNode
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.evidence_graph import EvidenceGraphSummary
from glassbox.runtime.evidence_graph import build_changeset_evidence_graph
from glassbox.runtime.evidence_graph import claim_support
from glassbox.runtime.evidence_graph import evidence_neighborhood
from glassbox.runtime.evidence_graph import evidence_node
from glassbox.runtime.evidence_graph import reviewer_safe_graph_slice
from glassbox.runtime.evidence_graph import summarize_evidence_graph


def build_changeset_evidence_graph_response(
    detail: ChangesetDetailView,
    *,
    verification_plan: ChangesetVerificationPlanPreview,
    reviewer_safe: bool = False,
) -> EvidenceGraph:
    graph = build_changeset_evidence_graph(detail, verification_plan=verification_plan)
    return reviewer_safe_graph_slice(graph) if reviewer_safe else graph


def build_changeset_evidence_graph_summary_response(
    graph: EvidenceGraph,
) -> EvidenceGraphSummary:
    return summarize_evidence_graph(graph)


def build_changeset_evidence_graph_claim_response(
    graph: EvidenceGraph,
    claim_id: str,
) -> ClaimSupport | None:
    return claim_support(graph, claim_id)


def build_changeset_evidence_graph_node_response(
    graph: EvidenceGraph,
    node_id: str,
) -> EvidenceGraphNode | None:
    return evidence_node(graph, node_id)


def build_changeset_evidence_graph_neighborhood_response(
    graph: EvidenceGraph,
    *,
    node_id: str,
    depth: int,
) -> EvidenceGraph:
    return evidence_neighborhood(graph, node_id, depth=depth)


__all__ = [
    "build_changeset_evidence_graph_claim_response",
    "build_changeset_evidence_graph_neighborhood_response",
    "build_changeset_evidence_graph_node_response",
    "build_changeset_evidence_graph_response",
    "build_changeset_evidence_graph_summary_response",
]
