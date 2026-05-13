"""Derived evidence graph helpers for existing local evidence views."""

from collections import deque
from datetime import UTC
from datetime import datetime

from glassbox.core import ClaimSupport
from glassbox.core import EvidenceGraph
from glassbox.core import EvidenceGraphConfidence
from glassbox.core import EvidenceGraphEdgeKind
from glassbox.core import EvidenceGraphFreshness
from glassbox.core import EvidenceGraphMissingEvidence
from glassbox.core import EvidenceGraphNode
from glassbox.core import EvidenceGraphNodeKind
from glassbox.core import EvidenceGraphProvenance
from glassbox.core import EvidenceGraphRedactionStatus
from glassbox.core import EvidenceGraphVisibility
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.runtime.evidence_graph_builder import _claim_confidence
from glassbox.runtime.evidence_graph_builder import _claim_state
from glassbox.runtime.evidence_graph_builder import _claim_summary
from glassbox.runtime.evidence_graph_builder import _GraphBuilder
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
from glassbox.runtime.next_actions import next_actions_from_summaries
from glassbox.runtime.session_query_models import SessionSnapshotView

MAX_EVIDENCE_NEIGHBORHOOD_NODES = 100


def build_session_evidence_graph(
    snapshot: SessionSnapshotView,
    *,
    generated_at: datetime | None = None,
) -> EvidenceGraph:
    """Derive a sparse graph for an existing session snapshot."""

    session_id = str(snapshot.session_id)
    claim_id = f"claim:session:{session_id}:operator-posture"
    graph = _GraphBuilder(
        graph_id=f"graph:session:{session_id}",
        target=NextActionTarget(
            kind=NextActionTargetKind.SESSION,
            target_id=session_id,
            label=f"Session {session_id}",
        ),
        generated_at=generated_at or datetime.now(UTC),
    )
    graph.add_node(
        EvidenceGraphNode(
            node_id=claim_id,
            kind=EvidenceGraphNodeKind.CLAIM,
            title="Session operator posture",
            summary=f"Session status is {snapshot.status}.",
            freshness=EvidenceGraphFreshness.FRESH,
            redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
            visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
        )
    )
    if snapshot.projection_health.state == "unavailable":
        graph.add_limitation(
            "Session projections are unavailable; this graph uses sparse "
            "canonical session metadata until projections are rebuilt."
        )
    elif not snapshot.transcript and snapshot.last_sequence == 0:
        graph.add_limitation(
            "Session has only sparse startup evidence; older or minimal "
            "sessions may not contain richer v16 evidence families."
        )

    supporting_edge_ids: list[str] = []
    contradicting_edge_ids: list[str] = []
    stale_node_ids: list[str] = []
    missing: list[EvidenceGraphMissingEvidence] = []

    status_node_id = f"event:session:{session_id}:status"
    graph.add_node(
        EvidenceGraphNode(
            node_id=status_node_id,
            kind=EvidenceGraphNodeKind.EVENT,
            title="Session status",
            summary=f"Session status is {snapshot.status}.",
            provenance=[
                EvidenceGraphProvenance(
                    source_kind="session_snapshot",
                    source_id=session_id,
                    source_sequence=snapshot.last_sequence,
                    summary="typed session snapshot",
                )
            ],
            freshness=EvidenceGraphFreshness.FRESH,
            confidence=EvidenceGraphConfidence.HIGH,
            redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
            visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
        )
    )
    edge_kind = (
        EvidenceGraphEdgeKind.CONTRADICTS
        if snapshot.status == "failed"
        else EvidenceGraphEdgeKind.SUPPORTS
    )
    edge_id = graph.add_edge(
        edge_kind,
        status_node_id,
        claim_id,
        "session status shapes operator posture",
        confidence=EvidenceGraphConfidence.HIGH,
    )
    if edge_kind == EvidenceGraphEdgeKind.CONTRADICTS:
        contradicting_edge_ids.append(edge_id)
    else:
        supporting_edge_ids.append(edge_id)

    if snapshot.projection_health.degraded:
        projection_node_id = f"projection:session:{session_id}"
        stale_node_ids.append(projection_node_id)
        graph.add_node(
            EvidenceGraphNode(
                node_id=projection_node_id,
                kind=EvidenceGraphNodeKind.PROJECTION,
                title="Projection health",
                summary=snapshot.projection_health.detail
                or snapshot.projection_health.state,
                freshness=EvidenceGraphFreshness.STALE,
                confidence=EvidenceGraphConfidence.MEDIUM,
                redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
                visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
            )
        )
        graph.add_edge(
            EvidenceGraphEdgeKind.MAKES_STALE,
            projection_node_id,
            claim_id,
            "degraded projections make session posture less trustworthy",
            confidence=EvidenceGraphConfidence.HIGH,
        )

    if snapshot.pending_approval_id is not None:
        missing.append(
            EvidenceGraphMissingEvidence(
                missing_id=f"missing:approval:{snapshot.pending_approval_id}",
                kind=EvidenceGraphNodeKind.EVENT,
                summary="A pending approval still needs an operator decision.",
                safe_next_actions=next_actions_from_summaries(
                    ["Resolve pending approval"],
                    target_kind=NextActionTargetKind.SESSION,
                    target_id=session_id,
                    kind=NextActionKind.APPROVE,
                    priority=NextActionPriority.ACTION_NEEDED,
                ),
            )
        )
    if snapshot.pending_question_id is not None:
        missing.append(
            EvidenceGraphMissingEvidence(
                missing_id=f"missing:question:{snapshot.pending_question_id}",
                kind=EvidenceGraphNodeKind.EVENT,
                summary="A pending question still needs an operator answer.",
                safe_next_actions=next_actions_from_summaries(
                    ["Answer pending question"],
                    target_kind=NextActionTargetKind.SESSION,
                    target_id=session_id,
                    kind=NextActionKind.ANSWER,
                    priority=NextActionPriority.ACTION_NEEDED,
                ),
            )
        )

    claim_state = _claim_state(
        missing=missing,
        stale_node_ids=stale_node_ids,
        contradicting_edge_ids=contradicting_edge_ids,
        accepted_risk_count=0,
        manual_evidence_count=0,
        manual_only_node_count=0,
        deterministic_support_count=1,
    )
    graph.add_claim(
        ClaimSupport(
            claim_id=claim_id,
            title="Session operator posture",
            summary=_claim_summary(claim_state),
            state=claim_state,
            confidence=_claim_confidence(claim_state),
            supporting_edge_ids=supporting_edge_ids,
            contradicting_edge_ids=contradicting_edge_ids,
            stale_node_ids=stale_node_ids,
            missing_evidence=missing,
            visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
        )
    )
    return graph.build()


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
