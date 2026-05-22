"""FastAPI routes for local handoff custody decisions."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Query

from glassbox.core import HandoffIntent
from glassbox.web.app import RuntimeContextDep
from glassbox.web.handoff_api import HandoffAcceptRequest
from glassbox.web.handoff_api import HandoffArchiveRequest
from glassbox.web.handoff_api import HandoffDecisionResponse
from glassbox.web.handoff_api import HandoffExportRequest
from glassbox.web.handoff_api import HandoffExportResponse
from glassbox.web.handoff_api import HandoffGuidanceResponse
from glassbox.web.handoff_api import HandoffImportResponse
from glassbox.web.handoff_api import HandoffImportTriageResponse
from glassbox.web.handoff_api import HandoffListResponse
from glassbox.web.handoff_api import HandoffPackageInspectResponse
from glassbox.web.handoff_api import HandoffPackagePathRequest
from glassbox.web.handoff_api import HandoffPreparePreviewRequest
from glassbox.web.handoff_api import HandoffPreparePreviewResponse
from glassbox.web.handoff_api import HandoffReadinessUnifiedResponse
from glassbox.web.handoff_api import HandoffRecordResponse
from glassbox.web.handoff_api import HandoffRejectRequest
from glassbox.web.routes.handoff_route_actions import accept_handoff_response
from glassbox.web.routes.handoff_route_actions import archive_handoff_response
from glassbox.web.routes.handoff_route_actions import export_handoff_response
from glassbox.web.routes.handoff_route_actions import import_handoff_package_response
from glassbox.web.routes.handoff_route_actions import inspect_handoff_package_response
from glassbox.web.routes.handoff_route_actions import prepare_handoff_preview_response
from glassbox.web.routes.handoff_route_actions import reject_handoff_response
from glassbox.web.routes.handoff_route_actions import (
    triage_handoff_package_import_response,
)
from glassbox.web.routes.handoff_route_queries import get_handoff_guidance_response
from glassbox.web.routes.handoff_route_queries import get_handoff_readiness_response
from glassbox.web.routes.handoff_route_queries import get_handoff_record_response
from glassbox.web.routes.handoff_route_queries import list_handoff_records_response
from glassbox.web.session_api import ErrorDetailResponse

router = APIRouter(prefix="/handoffs")

PageLimitParam = Annotated[int | None, Query(ge=1, le=500)]


@router.get("", response_model=HandoffListResponse)
async def list_handoffs(
    context: RuntimeContextDep,
    session_id: UUID | None = None,
    include_archived: bool = False,
    limit: PageLimitParam = None,
) -> HandoffListResponse:
    """Return projected handoff records for local custody inspection."""

    return list_handoff_records_response(
        context,
        session_id=session_id,
        include_archived=include_archived,
        limit=limit,
    )


@router.post(
    "/prepare-preview",
    response_model=HandoffPreparePreviewResponse,
    responses={
        400: {"model": ErrorDetailResponse},
        404: {"model": ErrorDetailResponse},
    },
)
async def prepare_handoff_preview(
    request: HandoffPreparePreviewRequest,
    context: RuntimeContextDep,
) -> HandoffPreparePreviewResponse:
    """Preview redaction and local-only posture before exporting a handoff."""

    return prepare_handoff_preview_response(request, context)


@router.post(
    "/exports",
    response_model=HandoffExportResponse,
    responses={
        400: {"model": ErrorDetailResponse},
        404: {"model": ErrorDetailResponse},
    },
)
async def export_handoff(
    request: HandoffExportRequest,
    context: RuntimeContextDep,
) -> HandoffExportResponse:
    """Write a redacted handoff package from a session or changeset source."""

    return export_handoff_response(request, context)


@router.post(
    "/inspect",
    response_model=HandoffPackageInspectResponse,
    responses={400: {"model": ErrorDetailResponse}},
)
async def inspect_handoff_package(
    request: HandoffPackagePathRequest,
    context: RuntimeContextDep,
) -> HandoffPackageInspectResponse:
    """Inspect a local handoff package without importing or mutating state."""

    return inspect_handoff_package_response(request, context)


@router.post(
    "/import-triage",
    response_model=HandoffImportTriageResponse,
    responses={400: {"model": ErrorDetailResponse}},
)
async def triage_handoff_package_import(
    request: HandoffPackagePathRequest,
    context: RuntimeContextDep,
) -> HandoffImportTriageResponse:
    """Inspect package import compatibility without mutating local state."""

    return triage_handoff_package_import_response(request, context)


@router.post(
    "/imports",
    response_model=HandoffImportResponse,
    responses={400: {"model": ErrorDetailResponse}},
)
async def import_handoff_package(
    request: HandoffPackagePathRequest,
    context: RuntimeContextDep,
) -> HandoffImportResponse:
    """Import a supported session handoff package as inspection-only state."""

    return import_handoff_package_response(request, context)


@router.get(
    "/readiness",
    response_model=HandoffReadinessUnifiedResponse,
    responses={
        400: {"model": ErrorDetailResponse},
        404: {"model": ErrorDetailResponse},
    },
)
async def get_handoff_readiness(
    context: RuntimeContextDep,
    source_kind: str = Query(default="workspace"),
    source_id: str | None = None,
    intent: HandoffIntent | None = None,
) -> HandoffReadinessUnifiedResponse:
    """Return shared v17 handoff readiness for a local source."""

    return get_handoff_readiness_response(
        context,
        source_kind=source_kind,
        source_id=source_id,
        intent=intent,
    )


@router.get(
    "/{session_id}/{package_id}",
    response_model=HandoffRecordResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_handoff(
    session_id: UUID,
    package_id: str,
    context: RuntimeContextDep,
) -> HandoffRecordResponse:
    """Return one projected handoff record."""

    return get_handoff_record_response(context, session_id, package_id)


@router.get(
    "/{session_id}/{package_id}/guidance",
    response_model=HandoffGuidanceResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_handoff_guidance(
    session_id: UUID,
    package_id: str,
    context: RuntimeContextDep,
) -> HandoffGuidanceResponse:
    """Return advisory fork-or-continue guidance for one imported handoff."""

    return get_handoff_guidance_response(context, session_id, package_id)


@router.post(
    "/{session_id}/{package_id}/accept",
    response_model=HandoffDecisionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def accept_handoff(
    session_id: UUID,
    package_id: str,
    request: HandoffAcceptRequest,
    context: RuntimeContextDep,
) -> HandoffDecisionResponse:
    """Accept local handoff custody or imported follow-up intent."""

    return accept_handoff_response(session_id, package_id, request, context)


@router.post(
    "/{session_id}/{package_id}/reject",
    response_model=HandoffDecisionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def reject_handoff(
    session_id: UUID,
    package_id: str,
    request: HandoffRejectRequest,
    context: RuntimeContextDep,
) -> HandoffDecisionResponse:
    """Reject local handoff custody with a retained reason."""

    return reject_handoff_response(session_id, package_id, request, context)


@router.post(
    "/{session_id}/{package_id}/archive",
    response_model=HandoffDecisionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def archive_handoff_record(
    session_id: UUID,
    package_id: str,
    request: HandoffArchiveRequest,
    context: RuntimeContextDep,
) -> HandoffDecisionResponse:
    """Archive a handoff as historical local workflow evidence."""

    return archive_handoff_response(session_id, package_id, request, context)


__all__ = ["router"]
