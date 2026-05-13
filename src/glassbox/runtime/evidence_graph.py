"""Derived evidence graph facade for existing local evidence views."""

from collections import deque

from glassbox.core import ClaimSupport
from glassbox.core import EvidenceGraph
from glassbox.core import EvidenceGraphRedactionStatus
from glassbox.core import EvidenceGraphVisibility
from glassbox.runtime.evidence_graph_builder import _with_limitation
from glassbox.runtime.evidence_graph_builder import summarize_evidence_graph
from glassbox.runtime.evidence_graph_changeset import (
    MAX_CHANGESET_GRAPH_COMMAND_EVIDENCE,
)
from glassbox.runtime.evidence_graph_changeset import (
    MAX_CHANGESET_GRAPH_MANUAL_EVIDENCE,
)
from glassbox.runtime.evidence_graph_changeset import MAX_CHANGESET_GRAPH_REQUIREMENTS
from glassbox.runtime.evidence_graph_changeset import (
    MAX_CHANGESET_GRAPH_RESPONSE_PLAN_ENTRIES,
)
from glassbox.runtime.evidence_graph_changeset import (
    MAX_CHANGESET_GRAPH_REVIEW_FEEDBACK,
)
from glassbox.runtime.evidence_graph_changeset import (
    MAX_CHANGESET_GRAPH_SAFE_NEXT_ACTIONS,
)
from glassbox.runtime.evidence_graph_changeset import build_changeset_evidence_graph
from glassbox.runtime.evidence_graph_models import EvidenceGraphSummary
from glassbox.runtime.evidence_graph_session import build_session_evidence_graph

MAX_EVIDENCE_NEIGHBORHOOD_NODES = 100


def claim_support(graph: EvidenceGraph, claim_id: str) -> ClaimSupport | None:
    """Return one claim support record by ID."""

    return next((claim for claim in graph.claims if claim.claim_id == claim_id), None)


def evidence_neighborhood(
    graph: EvidenceGraph,
    node_id: str,
    *,
    depth: int = 1,
    max_nodes: int = MAX_EVIDENCE_NEIGHBORHOOD_NODES,
) -> EvidenceGraph:
    """Return a bounded undirected graph neighborhood around one node."""

    if depth < 0:
        raise ValueError("depth must be non-negative")
    if max_nodes < 1:
        raise ValueError("max_nodes must be positive")
    node_ids = {node.node_id for node in graph.nodes}
    if node_id not in node_ids:
        return graph.model_copy(update={"nodes": [], "edges": [], "claims": []})

    adjacency: dict[str, set[str]] = {node.node_id: set() for node in graph.nodes}
    for edge in graph.edges:
        adjacency.setdefault(edge.from_node_id, set()).add(edge.to_node_id)
        adjacency.setdefault(edge.to_node_id, set()).add(edge.from_node_id)

    selected = {node_id}
    queue: deque[tuple[str, int]] = deque([(node_id, 0)])
    truncated = False
    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for neighbor in adjacency.get(current, set()):
            if neighbor in selected:
                continue
            if len(selected) >= max_nodes:
                truncated = True
                continue
            selected.add(neighbor)
            queue.append((neighbor, current_depth + 1))

    edges = [
        edge
        for edge in graph.edges
        if edge.from_node_id in selected and edge.to_node_id in selected
    ]
    edge_ids = {edge.edge_id for edge in edges}
    claims = [
        claim
        for claim in graph.claims
        if claim.claim_id in selected
        or set(claim.supporting_edge_ids).intersection(edge_ids)
        or set(claim.contradicting_edge_ids).intersection(edge_ids)
    ]
    return graph.model_copy(
        update={
            "nodes": [node for node in graph.nodes if node.node_id in selected],
            "edges": edges,
            "claims": claims,
            "limitations": _with_limitation(
                graph.limitations,
                (
                    f"Evidence neighborhood truncated to {max_nodes} node(s); "
                    "inspect a narrower node or depth for additional relationships."
                ),
            )
            if truncated
            else graph.limitations,
        }
    )


def reviewer_safe_graph_slice(graph: EvidenceGraph) -> EvidenceGraph:
    """Return a graph slice that omits operator-only nodes and local-only edges."""

    allowed_nodes = {
        node.node_id
        for node in graph.nodes
        if node.visibility
        in {EvidenceGraphVisibility.REVIEWER_SAFE, EvidenceGraphVisibility.RELEASE_SAFE}
        and node.redaction_status
        not in {
            EvidenceGraphRedactionStatus.LOCAL_ONLY,
            EvidenceGraphRedactionStatus.BLOCKED,
        }
    }
    edges = [
        edge
        for edge in graph.edges
        if edge.from_node_id in allowed_nodes and edge.to_node_id in allowed_nodes
    ]
    edge_ids = {edge.edge_id for edge in edges}
    claims = [
        claim
        for claim in graph.claims
        if claim.visibility
        in {EvidenceGraphVisibility.REVIEWER_SAFE, EvidenceGraphVisibility.RELEASE_SAFE}
    ]
    claims = [
        claim.model_copy(
            update={
                "supporting_edge_ids": [
                    edge_id
                    for edge_id in claim.supporting_edge_ids
                    if edge_id in edge_ids
                ],
                "contradicting_edge_ids": [
                    edge_id
                    for edge_id in claim.contradicting_edge_ids
                    if edge_id in edge_ids
                ],
                "stale_node_ids": [
                    node_id
                    for node_id in claim.stale_node_ids
                    if node_id in allowed_nodes
                ],
                "accepted_risk_node_ids": [
                    node_id
                    for node_id in claim.accepted_risk_node_ids
                    if node_id in allowed_nodes
                ],
            }
        )
        for claim in claims
    ]
    return graph.model_copy(
        update={
            "nodes": [node for node in graph.nodes if node.node_id in allowed_nodes],
            "edges": edges,
            "claims": claims,
        }
    )


__all__ = [
    "EvidenceGraphSummary",
    "build_changeset_evidence_graph",
    "build_session_evidence_graph",
    "claim_support",
    "evidence_neighborhood",
    "reviewer_safe_graph_slice",
    "summarize_evidence_graph",
    "MAX_CHANGESET_GRAPH_COMMAND_EVIDENCE",
    "MAX_CHANGESET_GRAPH_MANUAL_EVIDENCE",
    "MAX_CHANGESET_GRAPH_REQUIREMENTS",
    "MAX_CHANGESET_GRAPH_RESPONSE_PLAN_ENTRIES",
    "MAX_CHANGESET_GRAPH_REVIEW_FEEDBACK",
    "MAX_CHANGESET_GRAPH_SAFE_NEXT_ACTIONS",
    "MAX_EVIDENCE_NEIGHBORHOOD_NODES",
]
