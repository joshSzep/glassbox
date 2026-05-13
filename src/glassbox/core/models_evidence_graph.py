"""Evidence graph Pydantic contracts shared across Glassbox surfaces."""

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from glassbox.core.models_operator_flow import NextAction
from glassbox.core.models_operator_flow import NextActionTarget
from glassbox.core.types_evidence_graph import ClaimSupportState
from glassbox.core.types_evidence_graph import EvidenceGraphConfidence
from glassbox.core.types_evidence_graph import EvidenceGraphEdgeKind
from glassbox.core.types_evidence_graph import EvidenceGraphFreshness
from glassbox.core.types_evidence_graph import EvidenceGraphNodeKind
from glassbox.core.types_evidence_graph import EvidenceGraphRedactionStatus
from glassbox.core.types_evidence_graph import EvidenceGraphVisibility


class EvidenceGraphProvenance(BaseModel):
    """Summary provenance for one evidence graph item."""

    model_config = ConfigDict(extra="forbid")

    source_kind: str = Field(min_length=1, max_length=120)
    source_id: str | None = Field(default=None, min_length=1, max_length=300)
    source_path: str | None = Field(default=None, min_length=1, max_length=500)
    source_sequence: int | None = Field(default=None, ge=0)
    summary: str = Field(min_length=1, max_length=1000)


class EvidenceGraphNode(BaseModel):
    """One local evidence node in a derived graph."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(min_length=1, max_length=300)
    kind: EvidenceGraphNodeKind
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2000)
    provenance: list[EvidenceGraphProvenance] = Field(
        default_factory=list,
        max_length=20,
    )
    freshness: EvidenceGraphFreshness = EvidenceGraphFreshness.UNKNOWN
    confidence: EvidenceGraphConfidence = EvidenceGraphConfidence.UNKNOWN
    redaction_status: EvidenceGraphRedactionStatus = (
        EvidenceGraphRedactionStatus.UNKNOWN
    )
    visibility: EvidenceGraphVisibility = EvidenceGraphVisibility.OPERATOR_ONLY
    limitations: list[str] = Field(default_factory=list, max_length=20)


class EvidenceGraphEdge(BaseModel):
    """One typed relationship between local evidence graph nodes."""

    model_config = ConfigDict(extra="forbid")

    edge_id: str = Field(min_length=1, max_length=300)
    kind: EvidenceGraphEdgeKind
    from_node_id: str = Field(min_length=1, max_length=300)
    to_node_id: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=1000)
    confidence: EvidenceGraphConfidence = EvidenceGraphConfidence.UNKNOWN
    limitations: list[str] = Field(default_factory=list, max_length=20)


class EvidenceGraphMissingEvidence(BaseModel):
    """A missing support item that has no local evidence node yet."""

    model_config = ConfigDict(extra="forbid")

    missing_id: str = Field(min_length=1, max_length=300)
    kind: EvidenceGraphNodeKind
    summary: str = Field(min_length=1, max_length=1000)
    safe_next_actions: list[NextAction] = Field(default_factory=list, max_length=10)


class ClaimSupport(BaseModel):
    """Evidence support posture for one local claim or recommendation."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2000)
    state: ClaimSupportState
    confidence: EvidenceGraphConfidence = EvidenceGraphConfidence.UNKNOWN
    supporting_edge_ids: list[str] = Field(default_factory=list, max_length=100)
    contradicting_edge_ids: list[str] = Field(default_factory=list, max_length=100)
    stale_node_ids: list[str] = Field(default_factory=list, max_length=100)
    missing_evidence: list[EvidenceGraphMissingEvidence] = Field(
        default_factory=list,
        max_length=50,
    )
    accepted_risk_node_ids: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    visibility: EvidenceGraphVisibility = EvidenceGraphVisibility.OPERATOR_ONLY


class EvidenceGraph(BaseModel):
    """Bounded derived graph for explaining claim support."""

    model_config = ConfigDict(extra="forbid")

    graph_id: str = Field(min_length=1, max_length=300)
    target: NextActionTarget
    generated_at: datetime
    nodes: list[EvidenceGraphNode] = Field(default_factory=list, max_length=500)
    edges: list[EvidenceGraphEdge] = Field(default_factory=list, max_length=1000)
    claims: list[ClaimSupport] = Field(default_factory=list, max_length=200)
    limitations: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_graph_references(self) -> EvidenceGraph:
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("evidence graph node_id values must be unique")

        edge_ids = [edge.edge_id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("evidence graph edge_id values must be unique")

        node_id_set = set(node_ids)
        for edge in self.edges:
            if (
                edge.from_node_id not in node_id_set
                or edge.to_node_id not in node_id_set
            ):
                raise ValueError("evidence graph edges must reference existing nodes")

        edge_id_set = set(edge_ids)
        for claim in self.claims:
            unknown_edges = [
                edge_id
                for edge_id in [
                    *claim.supporting_edge_ids,
                    *claim.contradicting_edge_ids,
                ]
                if edge_id not in edge_id_set
            ]
            if unknown_edges:
                raise ValueError("claim support edge ids must exist in graph edges")
            unknown_nodes = [
                node_id
                for node_id in [
                    *claim.stale_node_ids,
                    *claim.accepted_risk_node_ids,
                ]
                if node_id not in node_id_set
            ]
            if unknown_nodes:
                raise ValueError("claim support node ids must exist in graph nodes")
        return self


__all__ = [
    "ClaimSupport",
    "EvidenceGraph",
    "EvidenceGraphEdge",
    "EvidenceGraphMissingEvidence",
    "EvidenceGraphNode",
    "EvidenceGraphProvenance",
]
