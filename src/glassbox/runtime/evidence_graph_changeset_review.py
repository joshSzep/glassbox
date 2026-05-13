"""Changeset review and retained-evidence graph node derivation."""

from glassbox.core import EvidenceGraphConfidence
from glassbox.core import EvidenceGraphEdgeKind
from glassbox.core import EvidenceGraphFreshness
from glassbox.core import EvidenceGraphMissingEvidence
from glassbox.core import EvidenceGraphNode
from glassbox.core import EvidenceGraphNodeKind
from glassbox.core import EvidenceGraphProvenance
from glassbox.core import EvidenceGraphRedactionStatus
from glassbox.core import EvidenceGraphVisibility
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceRedactionStatus
from glassbox.core import NextAction
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSurface
from glassbox.core import NextActionTargetKind
from glassbox.runtime.changeset_models import ChangesetDetailView
from glassbox.runtime.evidence_graph_builder import _add_truncation_limitation
from glassbox.runtime.evidence_graph_builder import _GraphBuilder
from glassbox.runtime.next_actions import next_actions_from_summaries

MAX_CHANGESET_GRAPH_MANUAL_EVIDENCE = 50
MAX_CHANGESET_GRAPH_REVIEW_FEEDBACK = 50
MAX_CHANGESET_GRAPH_RESPONSE_PLAN_ENTRIES = 20
MAX_CHANGESET_GRAPH_COMMAND_EVIDENCE = 50
MAX_CHANGESET_GRAPH_SAFE_NEXT_ACTIONS = 50


def missing_changeset_evidence(
    missing_id: str,
    kind: EvidenceGraphNodeKind,
    summary: str,
    actions: list[str],
    *,
    target_id: str,
) -> EvidenceGraphMissingEvidence:
    """Build a missing-evidence row with changeset safe next actions."""

    return EvidenceGraphMissingEvidence(
        missing_id=missing_id,
        kind=kind,
        summary=summary,
        safe_next_actions=_actions_from_strings(actions, target_id),
    )


def add_manual_evidence_nodes(
    graph: _GraphBuilder,
    detail: ChangesetDetailView,
    *,
    claim_id: str,
    stale_node_ids: list[str],
    supporting_edge_ids: list[str],
) -> None:
    """Add retained manual evidence nodes."""

    _add_truncation_limitation(
        graph,
        label="manual evidence row",
        total=len(detail.manual_evidence),
        limit=MAX_CHANGESET_GRAPH_MANUAL_EVIDENCE,
    )
    for item in detail.manual_evidence[:MAX_CHANGESET_GRAPH_MANUAL_EVIDENCE]:
        node_id = f"manual-evidence:{item.evidence_id}"
        freshness = _manual_freshness(item.freshness)
        if freshness == EvidenceGraphFreshness.STALE:
            stale_node_ids.append(node_id)
        graph.add_node(
            EvidenceGraphNode(
                node_id=node_id,
                kind=EvidenceGraphNodeKind.MANUAL_EVIDENCE,
                title=f"Manual evidence: {item.evidence_kind.value}",
                summary=item.summary,
                provenance=[
                    EvidenceGraphProvenance(
                        source_kind="manual_evidence",
                        source_id=str(item.evidence_id),
                        source_sequence=item.last_sequence,
                        summary=item.source_label,
                    )
                ],
                freshness=freshness,
                confidence=EvidenceGraphConfidence.LOW,
                redaction_status=_manual_redaction(item.redaction_status),
                visibility=(
                    EvidenceGraphVisibility.OPERATOR_ONLY
                    if item.local_only
                    else EvidenceGraphVisibility.REVIEWER_SAFE
                ),
                limitations=item.limitations,
            )
        )
        supporting_edge_ids.append(
            graph.add_edge(
                EvidenceGraphEdgeKind.SUPPORTS,
                node_id,
                claim_id,
                "manual evidence adds advisory review context",
                confidence=EvidenceGraphConfidence.LOW,
            )
        )


def add_review_feedback_nodes(
    graph: _GraphBuilder,
    detail: ChangesetDetailView,
    *,
    claim_id: str,
    stale_node_ids: list[str],
    manual_only_node_ids: list[str],
    accepted_risk_node_ids: list[str],
    supporting_edge_ids: list[str],
    contradicting_edge_ids: list[str],
) -> int:
    """Add review feedback, fixup inventory, and response-plan link nodes."""

    response_plan_accepted_risk_count = 0
    response_status_by_feedback = {
        str(item.feedback_id): item for item in detail.review_response_summary.items
    }
    _add_truncation_limitation(
        graph,
        label="review feedback row",
        total=len(detail.review_feedback),
        limit=MAX_CHANGESET_GRAPH_REVIEW_FEEDBACK,
    )
    for item in detail.review_feedback[:MAX_CHANGESET_GRAPH_REVIEW_FEEDBACK]:
        node_id = f"review-feedback:{item.feedback_id}"
        graph.add_node(
            EvidenceGraphNode(
                node_id=node_id,
                kind=EvidenceGraphNodeKind.REVIEW_FEEDBACK,
                title=f"Review feedback: {item.feedback_kind.value}",
                summary=item.summary,
                provenance=[
                    EvidenceGraphProvenance(
                        source_kind="review_feedback",
                        source_id=str(item.feedback_id),
                        source_sequence=item.last_sequence,
                        summary=item.source_label or item.provenance.value,
                    )
                ],
                freshness=EvidenceGraphFreshness.FRESH,
                confidence=EvidenceGraphConfidence.MEDIUM,
                redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
                visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
            )
        )
        edge_kind = (
            EvidenceGraphEdgeKind.CONTRADICTS
            if item.disposition.value in {"open", "reopened"}
            else EvidenceGraphEdgeKind.SUPPORTS
        )
        edge_id = graph.add_edge(
            edge_kind,
            node_id,
            claim_id,
            "review feedback disposition shapes review posture",
            confidence=EvidenceGraphConfidence.MEDIUM,
        )
        if edge_kind == EvidenceGraphEdgeKind.CONTRADICTS:
            contradicting_edge_ids.append(edge_id)
        else:
            supporting_edge_ids.append(edge_id)

        response_status = response_status_by_feedback.get(str(item.feedback_id))
        if response_status is None:
            continue
        if response_status.latest_fixup_inventory_artifact_id is not None:
            _add_response_fixup_inventory_node(
                graph,
                response_status=response_status,
                feedback_node_id=node_id,
                claim_id=claim_id,
                stale_node_ids=stale_node_ids,
                supporting_edge_ids=supporting_edge_ids,
            )
        response_plan_accepted_risk_count += _add_response_plan_link_nodes(
            graph,
            response_status=response_status,
            feedback_node_id=node_id,
            claim_id=claim_id,
            stale_node_ids=stale_node_ids,
            manual_only_node_ids=manual_only_node_ids,
            accepted_risk_node_ids=accepted_risk_node_ids,
            supporting_edge_ids=supporting_edge_ids,
            contradicting_edge_ids=contradicting_edge_ids,
        )
    return response_plan_accepted_risk_count


def add_command_evidence_nodes(
    graph: _GraphBuilder,
    detail: ChangesetDetailView,
    *,
    claim_id: str,
    supporting_edge_ids: list[str],
) -> None:
    """Add retained command evidence nodes."""

    _add_truncation_limitation(
        graph,
        label="command evidence row",
        total=len(detail.command_evidence.items),
        limit=MAX_CHANGESET_GRAPH_COMMAND_EVIDENCE,
    )
    for item in detail.command_evidence.items[:MAX_CHANGESET_GRAPH_COMMAND_EVIDENCE]:
        node_id = f"command:{item.tool_attempt_id}"
        graph.add_node(
            EvidenceGraphNode(
                node_id=node_id,
                kind=EvidenceGraphNodeKind.COMMAND,
                title=f"Command evidence: {item.purpose}",
                summary=item.summary,
                provenance=[
                    EvidenceGraphProvenance(
                        source_kind="tool_attempt",
                        source_id=item.tool_attempt_id,
                        summary=item.tool_name,
                    )
                ],
                freshness=EvidenceGraphFreshness.FRESH,
                confidence=(
                    EvidenceGraphConfidence.HIGH
                    if item.supports_verification
                    else EvidenceGraphConfidence.MEDIUM
                ),
                redaction_status=(
                    EvidenceGraphRedactionStatus.LOCAL_ONLY
                    if item.local_only
                    else EvidenceGraphRedactionStatus.SAFE_SUMMARY
                ),
                visibility=(
                    EvidenceGraphVisibility.OPERATOR_ONLY
                    if item.local_only
                    else EvidenceGraphVisibility.REVIEWER_SAFE
                ),
                limitations=item.redaction_notes,
            )
        )
        supporting_edge_ids.append(
            graph.add_edge(
                EvidenceGraphEdgeKind.VERIFIES
                if item.supports_verification
                else EvidenceGraphEdgeKind.SUPPORTS,
                node_id,
                claim_id,
                "retained command evidence informs review posture",
                confidence=(
                    EvidenceGraphConfidence.HIGH
                    if item.supports_verification
                    else EvidenceGraphConfidence.MEDIUM
                ),
            )
        )


def add_safe_next_action_nodes(
    graph: _GraphBuilder,
    detail: ChangesetDetailView,
    *,
    changeset_id: str,
    claim_id: str,
) -> None:
    """Add advisory safe next action nodes for the changeset claim."""

    _add_truncation_limitation(
        graph,
        label="safe next action",
        total=len(detail.safe_next_actions),
        limit=MAX_CHANGESET_GRAPH_SAFE_NEXT_ACTIONS,
    )
    for action in _actions_from_strings(
        detail.safe_next_actions[:MAX_CHANGESET_GRAPH_SAFE_NEXT_ACTIONS],
        changeset_id,
    ):
        node_id = f"next-action:{action.action_id}"
        graph.add_node(
            EvidenceGraphNode(
                node_id=node_id,
                kind=EvidenceGraphNodeKind.NEXT_ACTION,
                title=action.title,
                summary=action.summary,
                freshness=EvidenceGraphFreshness.FRESH,
                confidence=EvidenceGraphConfidence.MEDIUM,
                redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
                visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
            )
        )
        graph.add_edge(
            EvidenceGraphEdgeKind.SAFE_NEXT_ACTION_FOR,
            node_id,
            claim_id,
            "safe next action is available for this claim",
            confidence=EvidenceGraphConfidence.MEDIUM,
        )


def _add_response_fixup_inventory_node(
    graph: _GraphBuilder,
    *,
    response_status,
    feedback_node_id: str,
    claim_id: str,
    stale_node_ids: list[str],
    supporting_edge_ids: list[str],
) -> None:
    fixup_node_id = f"artifact:{response_status.latest_fixup_inventory_artifact_id}"
    if response_status.stale:
        stale_node_ids.append(fixup_node_id)
    graph.add_node(
        EvidenceGraphNode(
            node_id=fixup_node_id,
            kind=EvidenceGraphNodeKind.ARTIFACT,
            title="Response-linked fixup inventory",
            summary=(
                f"{response_status.changed_path_count} changed path(s); "
                f"{response_status.matched_scope_path_count} scoped match(es)"
            ),
            provenance=[
                EvidenceGraphProvenance(
                    source_kind="review_feedback_fixup_inventory",
                    source_id=str(response_status.latest_fixup_inventory_artifact_id),
                    source_sequence=response_status.latest_fixup_inventory_sequence,
                    summary=response_status.latest_source_summary
                    or "response-linked fixup inventory",
                )
            ],
            freshness=(
                EvidenceGraphFreshness.STALE
                if response_status.stale
                else EvidenceGraphFreshness.FRESH
            ),
            confidence=EvidenceGraphConfidence.MEDIUM,
            redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
            visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
            limitations=response_status.verification_limitations,
        )
    )
    supporting_edge_ids.append(
        graph.add_edge(
            EvidenceGraphEdgeKind.SUPPORTS,
            fixup_node_id,
            claim_id,
            "fixup inventory links feedback to changed paths",
            confidence=EvidenceGraphConfidence.MEDIUM,
        )
    )
    graph.add_edge(
        EvidenceGraphEdgeKind.DERIVED_FROM,
        fixup_node_id,
        feedback_node_id,
        "fixup inventory was recorded for this feedback item",
        confidence=EvidenceGraphConfidence.MEDIUM,
    )


def _add_response_plan_link_nodes(
    graph: _GraphBuilder,
    *,
    response_status,
    feedback_node_id: str,
    claim_id: str,
    stale_node_ids: list[str],
    manual_only_node_ids: list[str],
    accepted_risk_node_ids: list[str],
    supporting_edge_ids: list[str],
    contradicting_edge_ids: list[str],
) -> int:
    accepted_risk_count = 0
    _add_truncation_limitation(
        graph,
        label=f"verification plan link for feedback {response_status.feedback_id}",
        total=len(response_status.verification_plan_entries),
        limit=MAX_CHANGESET_GRAPH_RESPONSE_PLAN_ENTRIES,
    )
    for plan_entry in response_status.verification_plan_entries[
        :MAX_CHANGESET_GRAPH_RESPONSE_PLAN_ENTRIES
    ]:
        verification_node_id = f"verification:{plan_entry.verification_id}"
        freshness = _response_plan_entry_freshness(plan_entry.relationship)
        if freshness == EvidenceGraphFreshness.STALE:
            stale_node_ids.append(verification_node_id)
        if freshness == EvidenceGraphFreshness.MANUAL_ONLY:
            manual_only_node_ids.append(verification_node_id)
        if plan_entry.relationship == "accepted-risk":
            accepted_risk_node_ids.append(verification_node_id)
            accepted_risk_count += 1
        graph.add_node(
            EvidenceGraphNode(
                node_id=verification_node_id,
                kind=EvidenceGraphNodeKind.VERIFICATION_CHECK,
                title=plan_entry.check_name,
                summary=plan_entry.reason,
                provenance=[
                    EvidenceGraphProvenance(
                        source_kind="review_response_verification_plan_link",
                        source_id=str(plan_entry.verification_id),
                        summary="verification overlaps response-linked fixup paths",
                    )
                ],
                freshness=freshness,
                confidence=_response_plan_entry_confidence(plan_entry.relationship),
                redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
                visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
                limitations=plan_entry.safe_next_actions,
            )
        )
        graph.add_edge(
            EvidenceGraphEdgeKind.DERIVED_FROM,
            verification_node_id,
            feedback_node_id,
            "verification plan link was derived from feedback fixup paths",
            confidence=EvidenceGraphConfidence.MEDIUM,
        )
        response_edge_kind = _response_plan_entry_edge_kind(plan_entry.relationship)
        response_edge_id = graph.add_edge(
            response_edge_kind,
            verification_node_id,
            claim_id,
            f"{plan_entry.relationship} response verification shapes claim",
            confidence=_response_plan_entry_confidence(plan_entry.relationship),
        )
        if response_edge_kind == EvidenceGraphEdgeKind.CONTRADICTS:
            contradicting_edge_ids.append(response_edge_id)
        else:
            supporting_edge_ids.append(response_edge_id)
    return accepted_risk_count


def _actions_from_strings(actions: list[str], target_id: str) -> list[NextAction]:
    return next_actions_from_summaries(
        actions,
        target_kind=NextActionTargetKind.CHANGESET,
        target_id=target_id,
        kind=NextActionKind.INSPECT,
        priority=NextActionPriority.RECOMMENDED,
        recommended_surfaces=[NextActionSurface.CLI, NextActionSurface.DASHBOARD],
    )


def _manual_freshness(freshness: ManualEvidenceFreshness) -> EvidenceGraphFreshness:
    if freshness == ManualEvidenceFreshness.CURRENT:
        return EvidenceGraphFreshness.FRESH
    if freshness in {
        ManualEvidenceFreshness.NEEDS_INSPECTION,
        ManualEvidenceFreshness.STALE,
    }:
        return EvidenceGraphFreshness.STALE
    return EvidenceGraphFreshness.UNKNOWN


def _manual_redaction(
    redaction: ManualEvidenceRedactionStatus,
) -> EvidenceGraphRedactionStatus:
    if redaction == ManualEvidenceRedactionStatus.PASSED:
        return EvidenceGraphRedactionStatus.SAFE_SUMMARY
    if redaction == ManualEvidenceRedactionStatus.LOCAL_ONLY:
        return EvidenceGraphRedactionStatus.LOCAL_ONLY
    if redaction == ManualEvidenceRedactionStatus.REDACTED:
        return EvidenceGraphRedactionStatus.REDACTED
    if redaction in {
        ManualEvidenceRedactionStatus.REJECTED,
        ManualEvidenceRedactionStatus.QUARANTINED,
    }:
        return EvidenceGraphRedactionStatus.BLOCKED
    return EvidenceGraphRedactionStatus.UNKNOWN


def _response_plan_entry_freshness(relationship: str) -> EvidenceGraphFreshness:
    if relationship == "stale":
        return EvidenceGraphFreshness.STALE
    if relationship in {"skipped", "accepted-risk"}:
        return EvidenceGraphFreshness.MANUAL_ONLY
    return EvidenceGraphFreshness.FRESH


def _response_plan_entry_confidence(relationship: str) -> EvidenceGraphConfidence:
    if relationship == "fresh":
        return EvidenceGraphConfidence.HIGH
    if relationship in {"stale", "failed"}:
        return EvidenceGraphConfidence.MEDIUM
    return EvidenceGraphConfidence.LOW


def _response_plan_entry_edge_kind(relationship: str) -> EvidenceGraphEdgeKind:
    if relationship in {"stale", "failed"}:
        return EvidenceGraphEdgeKind.CONTRADICTS
    if relationship == "skipped":
        return EvidenceGraphEdgeKind.SKIPPED_BY
    if relationship == "accepted-risk":
        return EvidenceGraphEdgeKind.ACCEPTED_RISK_FOR
    if relationship == "fresh":
        return EvidenceGraphEdgeKind.VERIFIES
    return EvidenceGraphEdgeKind.SUPPORTS


__all__ = [
    "MAX_CHANGESET_GRAPH_COMMAND_EVIDENCE",
    "MAX_CHANGESET_GRAPH_MANUAL_EVIDENCE",
    "MAX_CHANGESET_GRAPH_RESPONSE_PLAN_ENTRIES",
    "MAX_CHANGESET_GRAPH_REVIEW_FEEDBACK",
    "MAX_CHANGESET_GRAPH_SAFE_NEXT_ACTIONS",
    "add_command_evidence_nodes",
    "add_manual_evidence_nodes",
    "add_review_feedback_nodes",
    "add_safe_next_action_nodes",
    "missing_changeset_evidence",
]
