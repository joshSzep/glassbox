"""Changeset inventory evidence graph node derivation."""

from glassbox.core import EvidenceGraphConfidence
from glassbox.core import EvidenceGraphEdgeKind
from glassbox.core import EvidenceGraphFreshness
from glassbox.core import EvidenceGraphNode
from glassbox.core import EvidenceGraphNodeKind
from glassbox.core import EvidenceGraphProvenance
from glassbox.core import EvidenceGraphRedactionStatus
from glassbox.core import EvidenceGraphVisibility
from glassbox.runtime.changeset_models import ChangesetDetailView
from glassbox.runtime.evidence_graph_builder import _GraphBuilder


def add_inventory_evidence_nodes(
    graph: _GraphBuilder,
    detail: ChangesetDetailView,
    *,
    claim_id: str,
    stale_node_ids: list[str],
    supporting_edge_ids: list[str],
) -> None:
    """Add structured changeset inventory nodes and freshness edges."""

    inventory = detail.inventory
    if inventory is None:
        return

    inventory_node_id = f"artifact:{inventory.artifact_id}"
    inventory_freshness = _inventory_freshness(detail.inventory_status.stale)
    if detail.inventory_status.stale:
        stale_node_ids.append(inventory_node_id)
    graph.add_node(
        EvidenceGraphNode(
            node_id=inventory_node_id,
            kind=EvidenceGraphNodeKind.ARTIFACT,
            title="Changeset inventory",
            summary=(
                f"{inventory.changed_path_count} changed path(s); "
                f"{detail.inventory_status.freshness.value}"
            ),
            provenance=[
                EvidenceGraphProvenance(
                    source_kind="changeset_inventory",
                    source_id=str(inventory.artifact_id),
                    source_sequence=inventory.last_sequence,
                    summary="projected latest changeset inventory",
                )
            ],
            freshness=inventory_freshness,
            confidence=EvidenceGraphConfidence.HIGH,
            redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
            visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
            limitations=(
                [detail.inventory_status.reason]
                if detail.inventory_status.reason
                else []
            ),
        )
    )
    supporting_edge_ids.append(
        graph.add_edge(
            EvidenceGraphEdgeKind.SUPPORTS,
            inventory_node_id,
            claim_id,
            "changeset inventory scopes review posture",
            confidence=EvidenceGraphConfidence.HIGH,
        )
    )
    if detail.inventory_status.stale:
        graph.add_edge(
            EvidenceGraphEdgeKind.MAKES_STALE,
            inventory_node_id,
            claim_id,
            "stale inventory lowers confidence in review posture",
            confidence=EvidenceGraphConfidence.HIGH,
        )


def _inventory_freshness(stale: bool) -> EvidenceGraphFreshness:
    return EvidenceGraphFreshness.STALE if stale else EvidenceGraphFreshness.FRESH


__all__ = ["add_inventory_evidence_nodes"]
