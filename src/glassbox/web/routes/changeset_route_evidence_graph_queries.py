"""HTTP-local evidence graph query helpers for changeset routes."""

from uuid import UUID

from glassbox.core import ClaimSupport
from glassbox.core import EvidenceGraph
from glassbox.core import EvidenceGraphNode
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.evidence_graph import EvidenceGraphSummary
from glassbox.web.changeset_api_builders_evidence_graph import (
    build_changeset_evidence_graph_claim_response,
)
from glassbox.web.changeset_api_builders_evidence_graph import (
    build_changeset_evidence_graph_neighborhood_response,
)
from glassbox.web.changeset_api_builders_evidence_graph import (
    build_changeset_evidence_graph_node_response,
)
from glassbox.web.changeset_api_builders_evidence_graph import (
    build_changeset_evidence_graph_response,
)
from glassbox.web.changeset_api_builders_evidence_graph import (
    build_changeset_evidence_graph_summary_response,
)
from glassbox.web.routes.changeset_route_errors import raise_not_found_from_value_error
from glassbox.web.routes.changeset_route_services import changeset_query_service
from glassbox.web.routes.changeset_route_services import changeset_repository
from glassbox.web.routes.changeset_route_services import changeset_verification_service
from glassbox.web.routes.changeset_route_services import workspace_root_for_changeset


def get_changeset_evidence_graph(
    *,
    changeset_id: UUID,
    context: RuntimeContext,
    reviewer_safe: bool = False,
) -> EvidenceGraph:
    repository = changeset_repository(context)
    try:
        workspace_root = workspace_root_for_changeset(repository, changeset_id)
        detail = changeset_query_service(repository).get_detail(
            changeset_id,
            workspace_root=workspace_root,
        )
        verification_plan = changeset_verification_service(
            context,
            repository,
        ).preview_plan(changeset_id, workspace_root)
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_changeset_evidence_graph_response(
        detail,
        verification_plan=verification_plan,
        reviewer_safe=reviewer_safe,
    )


def get_changeset_evidence_graph_summary(
    *,
    changeset_id: UUID,
    context: RuntimeContext,
    reviewer_safe: bool = False,
) -> EvidenceGraphSummary:
    return build_changeset_evidence_graph_summary_response(
        get_changeset_evidence_graph(
            changeset_id=changeset_id,
            context=context,
            reviewer_safe=reviewer_safe,
        )
    )


def get_changeset_evidence_graph_claim(
    *,
    changeset_id: UUID,
    claim_id: str,
    context: RuntimeContext,
    reviewer_safe: bool = False,
) -> ClaimSupport:
    graph = get_changeset_evidence_graph(
        changeset_id=changeset_id,
        context=context,
        reviewer_safe=reviewer_safe,
    )
    support = build_changeset_evidence_graph_claim_response(graph, claim_id)
    if support is None:
        raise_not_found_from_value_error(
            ValueError(f"unknown evidence graph claim: {claim_id}")
        )
    return support


def get_changeset_evidence_graph_node(
    *,
    changeset_id: UUID,
    node_id: str,
    context: RuntimeContext,
    reviewer_safe: bool = False,
) -> EvidenceGraphNode:
    graph = get_changeset_evidence_graph(
        changeset_id=changeset_id,
        context=context,
        reviewer_safe=reviewer_safe,
    )
    node = build_changeset_evidence_graph_node_response(graph, node_id)
    if node is not None:
        return node
    raise_not_found_from_value_error(
        ValueError(f"unknown evidence graph node: {node_id}")
    )


def get_changeset_evidence_graph_neighborhood(
    *,
    changeset_id: UUID,
    node_id: str,
    depth: int,
    context: RuntimeContext,
    reviewer_safe: bool = False,
) -> EvidenceGraph:
    graph = get_changeset_evidence_graph(
        changeset_id=changeset_id,
        context=context,
        reviewer_safe=reviewer_safe,
    )
    return build_changeset_evidence_graph_neighborhood_response(
        graph,
        node_id=node_id,
        depth=depth,
    )


__all__ = [
    "get_changeset_evidence_graph",
    "get_changeset_evidence_graph_claim",
    "get_changeset_evidence_graph_neighborhood",
    "get_changeset_evidence_graph_node",
    "get_changeset_evidence_graph_summary",
]
