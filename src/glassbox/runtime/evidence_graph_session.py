"""Session evidence graph derivation."""

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
from glassbox.runtime.next_actions import next_actions_from_summaries
from glassbox.runtime.session_query_models import SessionSnapshotView


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

    _add_session_status_node(
        graph,
        snapshot,
        claim_id=claim_id,
        supporting_edge_ids=supporting_edge_ids,
        contradicting_edge_ids=contradicting_edge_ids,
    )
    _add_projection_health_node(
        graph,
        snapshot,
        claim_id=claim_id,
        stale_node_ids=stale_node_ids,
    )
    _add_pending_operator_decisions(snapshot, missing=missing)

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


def _add_session_status_node(
    graph: _GraphBuilder,
    snapshot: SessionSnapshotView,
    *,
    claim_id: str,
    supporting_edge_ids: list[str],
    contradicting_edge_ids: list[str],
) -> None:
    session_id = str(snapshot.session_id)
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


def _add_projection_health_node(
    graph: _GraphBuilder,
    snapshot: SessionSnapshotView,
    *,
    claim_id: str,
    stale_node_ids: list[str],
) -> None:
    if not snapshot.projection_health.degraded:
        return

    session_id = str(snapshot.session_id)
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


def _add_pending_operator_decisions(
    snapshot: SessionSnapshotView,
    *,
    missing: list[EvidenceGraphMissingEvidence],
) -> None:
    session_id = str(snapshot.session_id)
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


__all__ = ["build_session_evidence_graph"]
