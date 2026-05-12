"""Derived evidence graph helpers for existing local evidence views."""

from collections import deque
from datetime import UTC
from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ClaimSupport
from glassbox.core import ClaimSupportState
from glassbox.core import EvidenceGraph
from glassbox.core import EvidenceGraphConfidence
from glassbox.core import EvidenceGraphEdge
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
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.runtime.changeset_models import ChangesetDetailView
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.next_actions import next_actions_from_summaries
from glassbox.runtime.session_query_models import SessionSnapshotView

MAX_CHANGESET_GRAPH_REQUIREMENTS = 50
MAX_CHANGESET_GRAPH_MANUAL_EVIDENCE = 50
MAX_CHANGESET_GRAPH_REVIEW_FEEDBACK = 50
MAX_CHANGESET_GRAPH_RESPONSE_PLAN_ENTRIES = 20
MAX_CHANGESET_GRAPH_COMMAND_EVIDENCE = 50
MAX_CHANGESET_GRAPH_SAFE_NEXT_ACTIONS = 50
MAX_EVIDENCE_NEIGHBORHOOD_NODES = 100


class EvidenceGraphSummary(BaseModel):
    """Compact count summary for a derived evidence graph."""

    model_config = ConfigDict(extra="forbid")

    graph_id: str
    target_kind: NextActionTargetKind
    target_id: str | None = None
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    claim_count: int = Field(ge=0)
    stale_claim_count: int = Field(ge=0)
    missing_claim_count: int = Field(ge=0)
    contradicted_claim_count: int = Field(ge=0)
    manual_only_claim_count: int = Field(ge=0)
    accepted_risk_claim_count: int = Field(ge=0)
    limitation_count: int = Field(ge=0)


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
    response_plan_accepted_risk_count = 0

    if detail.inventory is None:
        missing.append(
            _missing(
                "missing:changeset-inventory",
                EvidenceGraphNodeKind.ARTIFACT,
                "No structured changeset inventory is attached.",
                detail.safe_next_actions,
                target_id=changeset_id,
            )
        )
    else:
        inventory_node_id = f"artifact:{detail.inventory.artifact_id}"
        inventory_freshness = _inventory_freshness(detail.inventory_status.stale)
        if detail.inventory_status.stale:
            stale_node_ids.append(inventory_node_id)
        graph.add_node(
            EvidenceGraphNode(
                node_id=inventory_node_id,
                kind=EvidenceGraphNodeKind.ARTIFACT,
                title="Changeset inventory",
                summary=(
                    f"{detail.inventory.changed_path_count} changed path(s); "
                    f"{detail.inventory_status.freshness.value}"
                ),
                provenance=[
                    EvidenceGraphProvenance(
                        source_kind="changeset_inventory",
                        source_id=str(detail.inventory.artifact_id),
                        source_sequence=detail.inventory.last_sequence,
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

    if verification_plan is None:
        graph.add_limitation(
            "No verification plan preview was supplied; this graph remains "
            "compatible with older changesets, but verification-plan support "
            "is missing."
        )
        missing.append(
            _missing(
                "missing:verification-plan",
                EvidenceGraphNodeKind.VERIFICATION_CHECK,
                "No verification plan preview was supplied to this graph.",
                detail.safe_next_actions,
                target_id=changeset_id,
            )
        )
    else:
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
            fixup_node_id = (
                f"artifact:{response_status.latest_fixup_inventory_artifact_id}"
            )
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
                            source_id=str(
                                response_status.latest_fixup_inventory_artifact_id
                            ),
                            source_sequence=(
                                response_status.latest_fixup_inventory_sequence
                            ),
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
                node_id,
                "fixup inventory was recorded for this feedback item",
                confidence=EvidenceGraphConfidence.MEDIUM,
            )
        _add_truncation_limitation(
            graph,
            label=f"verification plan link for feedback {item.feedback_id}",
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
                response_plan_accepted_risk_count += 1
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
                            summary=(
                                "verification overlaps response-linked fixup paths"
                            ),
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
                node_id,
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
                confidence=EvidenceGraphConfidence.HIGH
                if item.supports_verification
                else EvidenceGraphConfidence.MEDIUM,
                redaction_status=EvidenceGraphRedactionStatus.LOCAL_ONLY
                if item.local_only
                else EvidenceGraphRedactionStatus.SAFE_SUMMARY,
                visibility=EvidenceGraphVisibility.OPERATOR_ONLY
                if item.local_only
                else EvidenceGraphVisibility.REVIEWER_SAFE,
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
                confidence=EvidenceGraphConfidence.HIGH
                if item.supports_verification
                else EvidenceGraphConfidence.MEDIUM,
            )
        )

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


class _GraphBuilder:
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


def _actions_from_strings(actions: list[str], target_id: str) -> list[NextAction]:
    return next_actions_from_summaries(
        actions,
        target_kind=NextActionTargetKind.CHANGESET,
        target_id=target_id,
        kind=NextActionKind.INSPECT,
        priority=NextActionPriority.RECOMMENDED,
        recommended_surfaces=[NextActionSurface.CLI, NextActionSurface.DASHBOARD],
    )


def _missing(
    missing_id: str,
    kind: EvidenceGraphNodeKind,
    summary: str,
    actions: list[str],
    *,
    target_id: str,
) -> EvidenceGraphMissingEvidence:
    return EvidenceGraphMissingEvidence(
        missing_id=missing_id,
        kind=kind,
        summary=summary,
        safe_next_actions=_actions_from_strings(actions, target_id),
    )


def _inventory_freshness(stale: bool) -> EvidenceGraphFreshness:
    return EvidenceGraphFreshness.STALE if stale else EvidenceGraphFreshness.FRESH


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


def _claim_state(
    *,
    missing: list[EvidenceGraphMissingEvidence],
    stale_node_ids: list[str],
    contradicting_edge_ids: list[str],
    accepted_risk_count: int,
    manual_evidence_count: int,
    manual_only_node_count: int,
    deterministic_support_count: int,
) -> ClaimSupportState:
    if contradicting_edge_ids:
        return ClaimSupportState.CONTRADICTED
    if accepted_risk_count:
        return ClaimSupportState.ACCEPTED_WITH_RISK
    if stale_node_ids:
        return ClaimSupportState.STALE
    if missing:
        return ClaimSupportState.MISSING
    if manual_only_node_count or (
        manual_evidence_count and deterministic_support_count == 0
    ):
        return ClaimSupportState.MANUAL_ONLY
    return ClaimSupportState.SUPPORTED


def _claim_confidence(state: ClaimSupportState) -> EvidenceGraphConfidence:
    if state == ClaimSupportState.SUPPORTED:
        return EvidenceGraphConfidence.HIGH
    if state in {ClaimSupportState.STALE, ClaimSupportState.ACCEPTED_WITH_RISK}:
        return EvidenceGraphConfidence.MEDIUM
    if state in {ClaimSupportState.MANUAL_ONLY, ClaimSupportState.MISSING}:
        return EvidenceGraphConfidence.LOW
    return EvidenceGraphConfidence.UNKNOWN


def _claim_summary(state: ClaimSupportState) -> str:
    if state == ClaimSupportState.SUPPORTED:
        return "Local evidence supports the current changeset review posture."
    if state == ClaimSupportState.STALE:
        return "Some local evidence is stale and should be refreshed before trust."
    if state == ClaimSupportState.MISSING:
        return "Expected local evidence is missing for this changeset."
    if state == ClaimSupportState.CONTRADICTED:
        return "Local evidence contradicts the current review posture."
    if state == ClaimSupportState.MANUAL_ONLY:
        return "Support depends on manual or advisory evidence."
    if state == ClaimSupportState.ACCEPTED_WITH_RISK:
        return "The posture includes explicitly accepted residual risk."
    return "Local evidence does not support the current claim."


def _count_claims(graph: EvidenceGraph, state: ClaimSupportState) -> int:
    return sum(1 for claim in graph.claims if claim.state == state)


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
