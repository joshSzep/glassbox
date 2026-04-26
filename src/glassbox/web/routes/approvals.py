"""Approval resolution HTTP endpoint.

Exposes POST /sessions/{session_id}/approvals/{approval_id}.
"""

from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel

from glassbox.core.types import ApprovalDecision
from glassbox.web.app import RuntimeContextDep
from glassbox.web.session_api import ActionAcceptedResponse
from glassbox.web.session_api import ErrorDetailResponse

router = APIRouter(prefix="/sessions")


class ResolveApprovalRequest(BaseModel):
    """Request body for resolving a pending approval."""

    decision: ApprovalDecision


@router.post(
    "/{session_id}/approvals/{approval_id}",
    response_model=ActionAcceptedResponse,
    status_code=200,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def resolve_approval(
    session_id: UUID,
    approval_id: UUID,
    body: ResolveApprovalRequest,
    context: RuntimeContextDep,
) -> ActionAcceptedResponse:
    """Approve or deny a pending tool-call approval.

    Returns ``{"status": "ok"}`` on success.

    Raises:
        404 if the session or approval does not exist.
        409 if the session is not currently awaiting approval, or if the
            approval has already been resolved.
    """
    repo = context.repositories.sessions
    if repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    try:
        await context.services.session_service.resolve_approval(
            session_id,
            approval_id,
            body.decision,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ActionAcceptedResponse(status="ok")
