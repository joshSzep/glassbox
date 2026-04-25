"""Session supervisor implementation for top-level runtime lifecycle."""

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.events import RuntimeNoteImported
from glassbox.core.events import RuntimeNoteRecorded
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionResumed
from glassbox.core.events import SessionStarted
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_session_id
from glassbox.core.models import ForkedSession
from glassbox.core.models import SessionConfig
from glassbox.core.models import SessionState
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import SessionStatus
from glassbox.runtime.logging import get_runtime_logger
from glassbox.runtime.logging import runtime_log_extra
from glassbox.runtime.transport import RuntimeEventTransport
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.services import SessionRepository
from glassbox.services import SessionService

logger = get_runtime_logger("supervisor")


class SessionSupervisor(SessionService):
    """Top-level session lifecycle orchestrator backed by repository contracts."""

    def __init__(
        self,
        session_repository: SessionRepository,
        event_bus: RuntimeEventTransport[EventEnvelope],
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
                    parent_session_id=config.parent_session_id,
                    forked_from_turn_id=config.forked_from_turn_id,
                    forked_from_sequence=config.forked_from_sequence,
                    branch_label=config.branch_label,
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

    async def fork_session(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId | None = None,
        branch_label: str | None = None,
    ) -> ForkedSession:
        parent_session = self._session_repository.get_session(session_id)
        if parent_session is None:
            raise ValueError(f"unknown session_id: {session_id}")

        fork_point = self._session_repository.resolve_fork_point(
            session_id,
            turn_id=turn_id,
        )
        child_state = await self.start_session(
            SessionConfig(
                model_name=parent_session.model_name,
                cwd=parent_session.cwd,
                approval_mode=parent_session.approval_mode,
                parent_session_id=parent_session.session_id,
                forked_from_turn_id=fork_point.turn_id,
                forked_from_sequence=fork_point.sequence,
                branch_label=branch_label,
            )
        )
        import_events = self._session_repository.build_imported_transcript_events(
            child_state.session_id,
            fork_point,
        )
        if import_events:
            stored_import_events = self._session_repository.append_events(import_events)
            for event in stored_import_events:
                self._event_bus.publish(event)

        inherited_runtime_note_events = [
            EventEnvelope(
                session_id=child_state.session_id,
                sequence=0,
                payload=RuntimeNoteImported(
                    source_session_id=note.source_session_id,
                    source_sequence=note.source_sequence,
                    category=note.category,
                    message=note.message,
                    source_created_at=note.created_at,
                ),
            )
            for note in self._session_repository.list_runtime_notes(session_id)
        ]
        if inherited_runtime_note_events:
            stored_runtime_note_events = self._session_repository.append_events(
                inherited_runtime_note_events
            )
            for event in stored_runtime_note_events:
                self._event_bus.publish(event)

        current_state = self._require_session_state(child_state.session_id)
        logger.info(
            "session_forked",
            extra=runtime_log_extra(
                runtime_event="session_forked",
                session_id=child_state.session_id,
                parent_session_id=parent_session.session_id,
                forked_from_turn_id=fork_point.turn_id,
                forked_from_sequence=fork_point.sequence,
                inherited_message_count=len(fork_point.inherited_messages),
            ),
        )
        return ForkedSession(
            child_session_id=child_state.session_id,
            parent_session_id=parent_session.session_id,
            forked_from_turn_id=fork_point.turn_id,
            forked_from_sequence=fork_point.sequence,
            branch_label=branch_label,
            inherited_message_count=len(fork_point.inherited_messages),
            last_sequence=current_state.last_sequence,
        )

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

    async def record_runtime_note(
        self,
        session_id: SessionId,
        *,
        category: str,
        message: str,
    ) -> None:
        state = self._require_session_state(session_id)
        self._ensure_session_is_active(state, action="record runtime note for")

        event = self._session_repository.record_runtime_note(
            session_id,
            category=category,
            message=message,
        )
        payload = event.payload
        if not isinstance(payload, RuntimeNoteRecorded):
            raise RuntimeError("record_runtime_note stored an unexpected event payload")
        self._event_bus.publish(event)
        logger.info(
            "runtime_note_recorded",
            extra=runtime_log_extra(
                runtime_event="runtime_note_recorded",
                session_id=session_id,
                event_sequence=event.sequence,
                category=payload.category,
                message_length=len(payload.message),
            ),
        )

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
