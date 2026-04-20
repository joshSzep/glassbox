"""Minimal turn engine for non-tool model turns."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from time import perf_counter

from glassbox.core.events import (
    AssistantMessageCompleted,
    EventEnvelope,
    ModelCallCompleted,
    ModelCallStarted,
    TurnCompleted,
    TurnFailed,
    TurnStarted,
    TurnStatusChanged,
    UserMessageReceived,
)
from glassbox.core.ids import new_message_id, new_turn_id
from glassbox.core.models import MessagePart, SessionRecord
from glassbox.core.types import TurnStatus
from glassbox.llm import (
    ModelAdapter,
    ModelExecutor,
    build_system_prompt,
)
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.services import SessionRepository

ModelAdapterFactory = Callable[[SessionRecord], ModelAdapter]
ModelExecutorFactory = Callable[[SessionRecord], ModelExecutor]


class TurnEngine:
    """Run one non-tool model turn from a persisted user message event."""

    def __init__(
        self,
        session_repository: SessionRepository,
        event_bus: EventBus[EventEnvelope],
        context_builder: TurnContextBuilder,
        model_adapter_factory: ModelAdapterFactory,
        model_executor_factory: ModelExecutorFactory,
    ) -> None:
        self._session_repository = session_repository
        self._event_bus = event_bus
        self._context_builder = context_builder
        self._model_adapter_factory = model_adapter_factory
        self._model_executor_factory = model_executor_factory

    async def run_for_user_message(self, event: EventEnvelope) -> None:
        """Process one persisted user message through the non-tool turn flow."""

        payload = event.payload
        if not isinstance(payload, UserMessageReceived):
            raise TypeError("turn engine requires a UserMessageReceived event")

        session = self._session_repository.get_session(event.session_id)
        if session is None:
            raise ValueError(f"unknown session_id: {event.session_id}")

        turn_id = new_turn_id()
        self._append_and_publish(
            event.session_id,
            [
                TurnStarted(
                    turn_id=turn_id,
                    trigger_message_id=payload.message_id,
                ),
                TurnStatusChanged(
                    turn_id=turn_id,
                    status=TurnStatus.BUILDING_CONTEXT,
                ),
            ],
        )

        try:
            turn_context = self._context_builder.build(event.session_id)
            system_prompt = build_system_prompt(turn_context)
            model_adapter = self._model_adapter_factory(session)
            model_executor = self._model_executor_factory(session)
            prepared_turn = model_adapter.build_turn_request(
                turn_context,
                system_prompt=system_prompt,
            )

            self._append_and_publish(
                event.session_id,
                [
                    TurnStatusChanged(
                        turn_id=turn_id,
                        status=TurnStatus.CALLING_MODEL,
                    ),
                    ModelCallStarted(
                        turn_id=turn_id,
                        provider=model_adapter.config.provider or "local",
                        model_name=model_adapter.config.model_name,
                    ),
                ],
            )

            start = perf_counter()
            result = await model_executor.execute(prepared_turn)
            duration_ms = max(0, int((perf_counter() - start) * 1000))
            assistant_text = result.assistant_text.strip()
            if assistant_text == "":
                raise ValueError("assistant response must not be blank")

            self._append_and_publish(
                event.session_id,
                [
                    ModelCallCompleted(
                        turn_id=turn_id,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        duration_ms=duration_ms,
                    ),
                    TurnStatusChanged(
                        turn_id=turn_id,
                        status=TurnStatus.ASSEMBLING_RESPONSE,
                    ),
                    AssistantMessageCompleted(
                        message_id=new_message_id(),
                        parts=[MessagePart(kind="text", text=assistant_text)],
                    ),
                    TurnStatusChanged(
                        turn_id=turn_id,
                        status=TurnStatus.COMPLETED,
                    ),
                    TurnCompleted(turn_id=turn_id, outcome="completed"),
                ],
            )
        except Exception as exc:
            self._append_and_publish(
                event.session_id,
                [
                    TurnStatusChanged(
                        turn_id=turn_id,
                        status=TurnStatus.FAILED,
                    ),
                    TurnFailed(turn_id=turn_id, error_message=str(exc)),
                ],
            )
            raise

    def _append_and_publish(
        self,
        session_id,
        payloads: Sequence[
            TurnStarted
            | TurnStatusChanged
            | ModelCallStarted
            | ModelCallCompleted
            | AssistantMessageCompleted
            | TurnCompleted
            | TurnFailed
        ],
    ) -> list[EventEnvelope]:
        stored_events = self._session_repository.append_events(
            [
                EventEnvelope(session_id=session_id, sequence=0, payload=payload)
                for payload in payloads
            ]
        )
        for stored_event in stored_events:
            self._event_bus.publish(stored_event)
        return stored_events
