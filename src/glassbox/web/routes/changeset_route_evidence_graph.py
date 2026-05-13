"""Evidence graph routes for changeset dashboard APIs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Query

from glassbox.web.app import RuntimeContextDep
from glassbox.web.changeset_api import ClaimSupport
from glassbox.web.changeset_api import EvidenceGraph
from glassbox.web.changeset_api import EvidenceGraphNode
from glassbox.web.changeset_api import EvidenceGraphSummary
from glassbox.web.routes.changeset_route_evidence_graph_queries import (
    get_changeset_evidence_graph,
)
from glassbox.web.routes.changeset_route_evidence_graph_queries import (
    get_changeset_evidence_graph_claim,
)
from glassbox.web.routes.changeset_route_evidence_graph_queries import (
    get_changeset_evidence_graph_neighborhood,
)
from glassbox.web.routes.changeset_route_evidence_graph_queries import (
    get_changeset_evidence_graph_node,
)
from glassbox.web.routes.changeset_route_evidence_graph_queries import (
    get_changeset_evidence_graph_summary,
)
from glassbox.web.session_api import ErrorDetailResponse

router = APIRouter()


@router.get(
    "/{changeset_id}/evidence-graph",
    response_model=EvidenceGraph,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_changeset_evidence_graph_route(
    changeset_id: UUID,
    context: RuntimeContextDep,
    reviewer_safe: bool = False,
) -> EvidenceGraph:
    """Return a bounded derived evidence graph for one changeset."""

    return get_changeset_evidence_graph(
        changeset_id=changeset_id,
        context=context,
        reviewer_safe=reviewer_safe,
    )


@router.get(
    "/{changeset_id}/evidence-graph/summary",
    response_model=EvidenceGraphSummary,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_changeset_evidence_graph_summary_route(
    changeset_id: UUID,
    context: RuntimeContextDep,
    reviewer_safe: bool = False,
) -> EvidenceGraphSummary:
    """Return evidence graph counts and claim posture for one changeset."""

    return get_changeset_evidence_graph_summary(
        changeset_id=changeset_id,
        context=context,
        reviewer_safe=reviewer_safe,
    )


@router.get(
    "/{changeset_id}/evidence-graph/claims/{claim_id}",
    response_model=ClaimSupport,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_changeset_evidence_graph_claim_route(
    changeset_id: UUID,
    claim_id: str,
    context: RuntimeContextDep,
    reviewer_safe: bool = False,
) -> ClaimSupport:
    """Return one claim support record from a changeset evidence graph."""

    return get_changeset_evidence_graph_claim(
        changeset_id=changeset_id,
        claim_id=claim_id,
        context=context,
        reviewer_safe=reviewer_safe,
    )


@router.get(
    "/{changeset_id}/evidence-graph/nodes/{node_id}",
    response_model=EvidenceGraphNode,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_changeset_evidence_graph_node_route(
    changeset_id: UUID,
    node_id: str,
    context: RuntimeContextDep,
    reviewer_safe: bool = False,
) -> EvidenceGraphNode:
    """Return one node summary from a changeset evidence graph."""

    return get_changeset_evidence_graph_node(
        changeset_id=changeset_id,
        node_id=node_id,
        context=context,
        reviewer_safe=reviewer_safe,
    )


@router.get(
    "/{changeset_id}/evidence-graph/neighborhood",
    response_model=EvidenceGraph,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_changeset_evidence_graph_neighborhood_route(
    changeset_id: UUID,
    node_id: str,
    context: RuntimeContextDep,
    depth: Annotated[int, Query(ge=0, le=4)] = 1,
    reviewer_safe: bool = False,
) -> EvidenceGraph:
    """Return a bounded evidence graph neighborhood around one node."""

    return get_changeset_evidence_graph_neighborhood(
        changeset_id=changeset_id,
        node_id=node_id,
        depth=depth,
        context=context,
        reviewer_safe=reviewer_safe,
    )
