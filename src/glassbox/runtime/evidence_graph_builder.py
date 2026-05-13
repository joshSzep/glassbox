"""Builder and summary utilities for derived evidence graphs."""

from datetime import datetime

from glassbox.core import ClaimSupport
from glassbox.core import ClaimSupportState
from glassbox.core import EvidenceGraph
from glassbox.core import EvidenceGraphConfidence
from glassbox.core import EvidenceGraphEdge
from glassbox.core import EvidenceGraphEdgeKind
from glassbox.core import EvidenceGraphNode
from glassbox.core import NextActionTarget
from glassbox.runtime.evidence_graph_models import EvidenceGraphSummary


class _GraphBuilder:
    """Small append-only builder for deterministic evidence graph IDs."""

    def __init__(
        self,
        *,
        graph_id: str,
        target: NextActionTarget,
        generated_at: datetime,
    ) -> None:
        self._graph_id = graph_id
        self._target = target
        self._generated_at = generated_at
        self._nodes: list[EvidenceGraphNode] = []
        self._edges: list[EvidenceGraphEdge] = []
        self._claims: list[ClaimSupport] = []
        self._limitations: list[str] = []
        self._edge_counter = 0

    def add_node(self, node: EvidenceGraphNode) -> None:
        self._nodes.append(node)

    def add_edge(
        self,
        kind: EvidenceGraphEdgeKind,
        from_node_id: str,
        to_node_id: str,
        summary: str,
        *,
        confidence: EvidenceGraphConfidence,
    ) -> str:
        self._edge_counter += 1
        edge_id = f"edge:{self._edge_counter}"
        self._edges.append(
            EvidenceGraphEdge(
                edge_id=edge_id,
                kind=kind,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                summary=summary,
                confidence=confidence,
            )
        )
        return edge_id

    def add_claim(self, claim: ClaimSupport) -> None:
        self._claims.append(claim)

    def add_limitation(self, limitation: str) -> None:
        self._limitations = _with_limitation(self._limitations, limitation)

    def build(self) -> EvidenceGraph:
        return EvidenceGraph(
            graph_id=self._graph_id,
            target=self._target,
            generated_at=self._generated_at,
            nodes=self._nodes,
            edges=self._edges,
            claims=self._claims,
            limitations=self._limitations,
        )


def summarize_evidence_graph(graph: EvidenceGraph) -> EvidenceGraphSummary:
    """Return compact counts for queue/API callers."""

    return EvidenceGraphSummary(
        graph_id=graph.graph_id,
        target_kind=graph.target.kind,
        target_id=graph.target.target_id,
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
        claim_count=len(graph.claims),
        stale_claim_count=_count_claims(graph, ClaimSupportState.STALE),
        missing_claim_count=_count_claims(graph, ClaimSupportState.MISSING),
        contradicted_claim_count=_count_claims(graph, ClaimSupportState.CONTRADICTED),
        manual_only_claim_count=_count_claims(graph, ClaimSupportState.MANUAL_ONLY),
        accepted_risk_claim_count=_count_claims(
            graph,
            ClaimSupportState.ACCEPTED_WITH_RISK,
        ),
        limitation_count=len(graph.limitations),
    )


def _add_truncation_limitation(
    graph: _GraphBuilder,
    *,
    label: str,
    total: int,
    limit: int,
) -> None:
    if total > limit:
        graph.add_limitation(
            f"{label.title()} evidence truncated to {limit} of {total} item(s)."
        )


def _with_limitation(limitations: list[str], limitation: str) -> list[str]:
    return list(dict.fromkeys([*limitations, limitation]))[:20]


def _count_claims(graph: EvidenceGraph, state: ClaimSupportState) -> int:
    return sum(1 for claim in graph.claims if claim.state == state)


__all__ = [
    "_GraphBuilder",
    "_add_truncation_limitation",
    "_with_limitation",
    "summarize_evidence_graph",
]
