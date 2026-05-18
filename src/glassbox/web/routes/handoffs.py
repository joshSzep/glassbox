"""FastAPI routes for local handoff custody decisions."""

from typing import Annotated
from typing import Any
from typing import cast
from uuid import UUID

from fastapi import APIRouter
from fastapi import Query

from glassbox.core import HandoffProjectionRecord
from glassbox.runtime.handoff_decisions import HandoffDecisionRepository
from glassbox.runtime.handoff_decisions import HandoffDecisionResult
from glassbox.runtime.handoff_decisions import accept_handoff_custody
from glassbox.runtime.handoff_decisions import archive_handoff
from glassbox.runtime.handoff_decisions import custody_action_state
from glassbox.runtime.handoff_decisions import reject_handoff_custody
from glassbox.runtime.handoff_decisions import safe_next_actions_for_decision
from glassbox.web.app import RuntimeContextDep
from glassbox.web.handoff_api import HandoffAcceptRequest
from glassbox.web.handoff_api import HandoffArchiveRequest
from glassbox.web.handoff_api import HandoffDecisionResponse
from glassbox.web.handoff_api import HandoffListResponse
from glassbox.web.handoff_api import HandoffRecordResponse
from glassbox.web.handoff_api import HandoffRejectRequest
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

    repository = cast(Any, context.repositories.sessions)
    records = repository.list_handoffs(
        session_id=session_id,
        include_archived=include_archived,
        limit=limit,
    )
    return HandoffListResponse(items=[_record_response(record) for record in records])


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

    return _record_response(_require_handoff(context, session_id, package_id))


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

    record = _require_handoff(context, session_id, package_id)
    repository = cast(HandoffDecisionRepository, context.repositories.sessions)
    result = accept_handoff_custody(
        repository,
        session_id=session_id,
        package_id=package_id,
        accepted_by=request.accepted_by,
        reason=request.reason,
        follow_up_intent=request.follow_up_intent,
        safe_next_actions=safe_next_actions_for_decision(record),
    )
    return _decision_response(result)


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

    record = _require_handoff(context, session_id, package_id)
    repository = cast(HandoffDecisionRepository, context.repositories.sessions)
    result = reject_handoff_custody(
        repository,
        session_id=session_id,
        package_id=package_id,
        rejected_by=request.rejected_by,
        reason=request.reason,
        safe_next_actions=safe_next_actions_for_decision(record),
    )
    return _decision_response(result)


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

    _require_handoff(context, session_id, package_id)
    repository = cast(HandoffDecisionRepository, context.repositories.sessions)
    result = archive_handoff(
        repository,
        session_id=session_id,
        package_id=package_id,
        archived_by=request.archived_by,
        reason=request.reason,
    )
    return _decision_response(result)


def _require_handoff(
    context: RuntimeContextDep,
    session_id: UUID,
    package_id: str,
) -> HandoffProjectionRecord:
    repository = cast(Any, context.repositories.sessions)
    record = repository.get_handoff(session_id, package_id)
    if record is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="handoff record not found")
    return record


def _decision_response(result: HandoffDecisionResult) -> HandoffDecisionResponse:
    return HandoffDecisionResponse(
        event_type=result.event_type,
        handoff=_record_response(result.record),
        non_claims=result.non_claims,
    )


def _record_response(record: HandoffProjectionRecord) -> HandoffRecordResponse:
    return HandoffRecordResponse(
        record=record,
        action_state=custody_action_state(record),
    )


__all__ = ["router"]
