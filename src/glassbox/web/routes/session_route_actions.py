"""HTTP-local mutation helpers for session routes."""

from uuid import UUID

from fastapi import HTTPException

from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.context_compaction_service import invalidate_context_compaction
from glassbox.runtime.context_compaction_service import refresh_context_compaction
from glassbox.runtime.tool_attempt_recovery import ToolAttemptRecoveryError
from glassbox.runtime.tool_attempt_recovery import abandon_tool_attempt
from glassbox.runtime.tool_attempt_recovery import inspect_tool_attempt
from glassbox.runtime.tool_attempt_recovery import retry_tool_attempt
from glassbox.web.routes.session_route_queries import ensure_session_exists
from glassbox.web.session_api import ActionAcceptedResponse
from glassbox.web.session_api import ContextCompactionResponse
from glassbox.web.session_api import ForkSessionResponse
from glassbox.web.session_api import InvalidateContextCompactionResponse
from glassbox.web.session_api import RefreshContextCompactionResponse
from glassbox.web.session_api import ToolAttemptInspectionResponse
from glassbox.web.session_api import ToolAttemptRecoveryResponse
from glassbox.web.session_api import build_fork_session_response


async def fork_session_response(
    session_id: UUID,
    context: RuntimeContext,
    *,
    turn_id: UUID | None,
    branch_label: str | None,
) -> ForkSessionResponse:
    ensure_session_exists(session_id, context)

    try:
        forked_session = await context.services.session_service.fork_session(
            session_id,
            turn_id=turn_id,
            branch_label=branch_label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return build_fork_session_response(forked_session)


async def submit_session_message_response(
    session_id: UUID,
    context: RuntimeContext,
    *,
    text: str,
) -> ActionAcceptedResponse:
    ensure_session_exists(session_id, context)

    try:
        await context.services.session_service.submit_user_message(session_id, text)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ActionAcceptedResponse(status="ok")


async def submit_session_answer_response(
    session_id: UUID,
    question_id: UUID,
    context: RuntimeContext,
    *,
    answer: str,
) -> ActionAcceptedResponse:
    ensure_session_exists(session_id, context)

    try:
        await context.services.session_service.provide_user_answer(
            session_id,
            question_id,
            answer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ActionAcceptedResponse(status="ok")


async def cancel_session_turn_response(
    session_id: UUID,
    context: RuntimeContext,
    *,
    turn_id: UUID | None,
    reason: str | None,
) -> ActionAcceptedResponse:
    ensure_session_exists(session_id, context)

    try:
        await context.services.session_service.cancel_turn(
            session_id,
            turn_id=turn_id,
            requested_by="api",
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ActionAcceptedResponse(status="ok")


def inspect_session_tool_attempt_response(
    session_id: UUID,
    tool_attempt_id: UUID,
    context: RuntimeContext,
) -> ToolAttemptInspectionResponse:
    ensure_session_exists(session_id, context)
    try:
        inspection = inspect_tool_attempt(
            context.repositories.sessions,
            session_id,
            tool_attempt_id,
        )
    except ToolAttemptRecoveryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ToolAttemptInspectionResponse.model_validate(
        inspection.model_dump(mode="json")
    )


async def retry_session_tool_attempt_response(
    session_id: UUID,
    tool_attempt_id: UUID,
    context: RuntimeContext,
    *,
    confirmed: bool,
    actor: str,
    reason: str | None,
) -> ToolAttemptRecoveryResponse:
    ensure_session_exists(session_id, context)
    if not confirmed:
        raise HTTPException(
            status_code=409,
            detail="tool-attempt retry requires confirmed=true",
        )
    try:
        result = await retry_tool_attempt(
            context.repositories.sessions,
            context.repositories.artifacts,
            session_id,
            tool_attempt_id,
            confirmed=confirmed,
            requested_by=actor,
            reason=reason,
        )
    except ToolAttemptRecoveryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ToolAttemptRecoveryResponse.model_validate(result.model_dump(mode="json"))


def abandon_session_tool_attempt_response(
    session_id: UUID,
    tool_attempt_id: UUID,
    context: RuntimeContext,
    *,
    confirmed: bool,
    actor: str,
    reason: str,
) -> ToolAttemptRecoveryResponse:
    ensure_session_exists(session_id, context)
    if not confirmed:
        raise HTTPException(
            status_code=409,
            detail="tool-attempt abandon requires confirmed=true",
        )
    try:
        result = abandon_tool_attempt(
            context.repositories.sessions,
            session_id,
            tool_attempt_id,
            reason=reason,
            abandoned_by=actor,
        )
    except ToolAttemptRecoveryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ToolAttemptRecoveryResponse.model_validate(result.model_dump(mode="json"))


def refresh_session_compaction_response(
    session_id: UUID,
    compaction_id: UUID,
    context: RuntimeContext,
    *,
    confirmed: bool,
    reason: str | None,
) -> RefreshContextCompactionResponse:
    ensure_session_exists(session_id, context)
    if not confirmed:
        raise HTTPException(
            status_code=409,
            detail="refresh requires confirmed=true",
        )
    try:
        refreshed, change = refresh_context_compaction(
            context.repositories.sessions,
            context.repositories.artifacts,
            session_id,
            compaction_id,
            changed_by="api",
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    refreshed_record = context.repositories.sessions.get_context_compaction(
        session_id,
        refreshed.compaction_id,
    )
    if refreshed_record is None:
        raise HTTPException(
            status_code=409,
            detail="refreshed compaction projection is unavailable",
        )
    return RefreshContextCompactionResponse(
        refreshed_compaction=ContextCompactionResponse.model_validate(
            refreshed_record.model_dump(mode="json")
        ),
        previous_compaction_id=str(change.compaction_id),
        previous_freshness=change.freshness.value,
        previous_freshness_reason=change.reason,
        superseded_by_compaction_id=str(refreshed.compaction_id),
    )


def invalidate_session_compaction_response(
    session_id: UUID,
    compaction_id: UUID,
    context: RuntimeContext,
    *,
    confirmed: bool,
    reason: str,
) -> InvalidateContextCompactionResponse:
    ensure_session_exists(session_id, context)
    if not confirmed:
        raise HTTPException(
            status_code=409,
            detail="invalidation requires confirmed=true",
        )
    try:
        change = invalidate_context_compaction(
            context.repositories.sessions,
            session_id,
            compaction_id,
            reason=reason,
            changed_by="api",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return InvalidateContextCompactionResponse(
        compaction_id=str(change.compaction_id),
        freshness=change.freshness.value,
        freshness_reason=change.reason,
    )
