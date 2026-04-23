"""Session supervisor implementation for top-level runtime lifecycle."""

from __future__ import annotations

from glassbox.core.events import (
    ApprovalRequested,
    ApprovalResolved,
    EventEnvelope,
    SessionCompleted,
    SessionResumed,
    SessionStarted,
    UserAnswerProvided,
    UserMessageReceived,
    UserQuestionAsked,
)
from glassbox.core.ids import (
    ApprovalId,
    QuestionId,
    SessionId,
    new_message_id,
    new_session_id,
)
from glassbox.core.models import SessionConfig, SessionState
from glassbox.core.types import ApprovalDecision, SessionStatus
from glassbox.runtime.bus import EventBus
from glassbox.runtime.logging import get_runtime_logger, runtime_log_extra
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.services import SessionRepository, SessionService

logger = get_runtime_logger("supervisor")


class SessionSupervisor(SessionService):
    """Top-level session lifecycle orchestrator backed by repository contracts."""

    def __init__(
        self,
        session_repository: SessionRepository,
        event_bus: EventBus[EventEnvelope],
        turn_engine: TurnEngine | None = None,
    ) -> None:
        self._session_repository = session_repository
        self._event_bus = event_bus
        self._turn_engine = turn_engine

    async def start_session(self, config: SessionConfig) -> SessionState:
        session_id = new_session_id()
        event = self._session_repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(config.cwd),
                    dashboard_url=config.dashboard_url,
                    model_name=config.model_name,
                    approval_mode=config.approval_mode,
                ),
            )
        )
        self._event_bus.publish(event)
        logger.info(
            "session_started",
            extra=runtime_log_extra(
                runtime_event="session_started",
                session_id=session_id,
                event_sequence=event.sequence,
                model_name=config.model_name,
                cwd=config.cwd,
                approval_mode=config.approval_mode,
            ),
        )
        return self._require_session_state(session_id)

    async def resume_session(self, session_id: SessionId) -> SessionState:
        current_state = self._require_session_state(session_id)
        if current_state.status in {
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        }:
            raise ValueError(
                f"cannot resume session {session_id} in status {current_state.status}"
            )

        if (
            current_state.status == SessionStatus.RUNNING
            and current_state.current_turn_id is not None
        ):
            raise ValueError(
                f"session {session_id} has an in-flight turn "
                f"{current_state.current_turn_id}; active turn execution cannot be "
                "resumed after restart"
            )

        event = self._session_repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionResumed(from_sequence=current_state.last_sequence),
            )
        )
        self._event_bus.publish(event)
        logger.info(
            "session_resumed",
            extra=runtime_log_extra(
                runtime_event="session_resumed",
                session_id=session_id,
                event_sequence=event.sequence,
                from_sequence=current_state.last_sequence,
            ),
        )
        return self._require_session_state(session_id)

    async def stop_session(
        self,
        session_id: SessionId,
        reason: str = "stopped",
    ) -> SessionState:
        state = self._require_session_state(session_id)
        self._ensure_session_is_active(state, action="stop")
        event = self._session_repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionCompleted(reason=reason),
            )
        )
        self._event_bus.publish(event)
        logger.info(
            "session_stopped",
            extra=runtime_log_extra(
                runtime_event="session_stopped",
                session_id=session_id,
                event_sequence=event.sequence,
                reason=reason,
            ),
        )
        return self._require_session_state(session_id)

    async def submit_user_message(self, session_id: SessionId, text: str) -> None:
        state = self._require_session_state(session_id)
        self._ensure_session_can_accept_input(state)
        if not text.strip():
            raise ValueError("user message text must not be blank")

        event = self._session_repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=UserMessageReceived(
                    message_id=new_message_id(),
                    text=text,
                ),
            )
        )
        self._event_bus.publish(event)
        logger.info(
            "user_message_submitted",
            extra=runtime_log_extra(
                runtime_event="user_message_submitted",
                session_id=session_id,
                message_id=event.message_id,
                event_sequence=event.sequence,
                text_length=len(text.strip()),
            ),
        )
        if self._turn_engine is not None:
            await self._turn_engine.run_for_user_message(event)

    async def resolve_approval(
        self,
        session_id: SessionId,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None:
        state = self._require_session_state(session_id)
        if state.status != SessionStatus.AWAITING_APPROVAL:
            raise ValueError(
                f"session {session_id} is not awaiting approval resolution"
            )

        approval_events = self._session_repository.read_events_by_correlation_id(
            session_id,
            approval_id=approval_id,
        )
        if not any(
            isinstance(event.payload, ApprovalRequested) for event in approval_events
        ):
            raise ValueError(f"unknown approval_id: {approval_id}")
        if any(
            isinstance(event.payload, ApprovalResolved) for event in approval_events
        ):
            raise ValueError(f"approval {approval_id} has already been resolved")

        event = self._session_repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ApprovalResolved(
                    approval_id=approval_id,
                    decision=decision,
                    decided_by="user",
                ),
            )
        )
        self._event_bus.publish(event)
        logger.info(
            "approval_resolved",
            extra=runtime_log_extra(
                runtime_event="approval_resolved",
                session_id=session_id,
                approval_id=approval_id,
                event_sequence=event.sequence,
                decision=decision,
            ),
        )
        if self._turn_engine is not None:
            await self._turn_engine.run_for_approval_resolution(event)

    async def provide_user_answer(
        self,
        session_id: SessionId,
        question_id: QuestionId,
        answer: str,
    ) -> None:
        state = self._require_session_state(session_id)
        if state.status != SessionStatus.AWAITING_USER_INPUT:
            raise ValueError(f"session {session_id} is not awaiting user input")

        if not any(
            isinstance(event.payload, UserQuestionAsked)
            and event.payload.question_id == question_id
            for event in self._session_repository.read_session_events(session_id)
        ):
            raise ValueError(f"unknown question_id: {question_id}")

        event = self._session_repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=UserAnswerProvided(
                    question_id=question_id,
                    answer=answer,
                ),
            )
        )
        self._event_bus.publish(event)
        logger.info(
            "user_answer_provided",
            extra=runtime_log_extra(
                runtime_event="user_answer_provided",
                session_id=session_id,
                question_id=question_id,
                event_sequence=event.sequence,
                answer_length=len(answer),
            ),
        )
        if self._turn_engine is not None:
            await self._turn_engine.run_for_user_answer(event)

    def _require_session_state(self, session_id: SessionId) -> SessionState:
        session_state = self._session_repository.get_session_state(session_id)
        if session_state is None:
            raise ValueError(f"unknown session_id: {session_id}")
        return session_state

    def _ensure_session_is_active(
        self,
        session_state: SessionState,
        *,
        action: str,
    ) -> None:
        if session_state.status in {
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        }:
            raise ValueError(
                f"cannot {action} session {session_state.session_id} "
                f"in status {session_state.status}"
            )

    def _ensure_session_can_accept_input(self, session_state: SessionState) -> None:
        if session_state.status in {
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
            SessionStatus.AWAITING_APPROVAL,
            SessionStatus.AWAITING_USER_INPUT,
        }:
            raise ValueError(
                "session cannot accept input in its current state: "
                f"{session_state.status}"
            )
