"""Approval resolution HTTP endpoint.

Exposes POST /sessions/{session_id}/approvals/{approval_id}.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from glassbox.core.types import ApprovalDecision
from glassbox.web.app import RuntimeContextDep

router = APIRouter(prefix="/sessions")


class ResolveApprovalRequest(BaseModel):
    """Request body for resolving a pending approval."""

    decision: ApprovalDecision


@router.post("/{session_id}/approvals/{approval_id}", status_code=200)
async def resolve_approval(
    session_id: UUID,
    approval_id: UUID,
    body: ResolveApprovalRequest,
    context: RuntimeContextDep,
) -> dict[str, str]:
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

    return {"status": "ok"}
