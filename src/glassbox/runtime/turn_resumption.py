"""Helpers for reconstructing suspended turns before resumption."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Protocol

from pydantic_ai.messages import ModelMessage
from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.messages import ToolReturnPart

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelCallStarted
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import MessageId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import new_message_id
from glassbox.llm import ModelToolCall


class TurnResumptionRepository(Protocol):
    """Minimal repository surface needed to reconstruct suspended turns."""

    def read_session_events(self, session_id) -> list[EventEnvelope]: ...

    def read_events_by_correlation_id(
        self,
        session_id,
        *,
        turn_id=None,
        approval_id=None,
    ) -> list[EventEnvelope]: ...


@dataclass(frozen=True, slots=True)
class UserAnswerResumeState:
    """Resolved state needed to resume an ask_user suspension."""

    question_payload: UserQuestionAsked
    answer: str
    assistant_message_id: MessageId
    starting_model_call_index: int

    @property
    def turn_id(self):
        return self.question_payload.turn_id

    def extend_conversation(self, conversation: list[ModelMessage]) -> None:
        conversation.append(_make_ask_user_model_response(self.question_payload))
        conversation.append(
            _make_ask_user_tool_return(self.question_payload, self.answer)
        )


@dataclass(frozen=True, slots=True)
class ApprovalResumeState:
    """Resolved state needed to resume an approval-gated tool call."""

    approval_requested: ApprovalRequested
    decision: object
    assistant_message_id: MessageId
    starting_model_call_index: int
    original_tool_arguments: dict[str, object]

    @property
    def turn_id(self):
        return self.approval_requested.turn_id

    @property
    def is_resumable(self) -> bool:
        return (
            self.approval_requested.tool_call_id is not None
            and self.approval_requested.provider_tool_call_id is not None
        )

    def extend_conversation(self, conversation: list[ModelMessage]) -> None:
        conversation.append(
            _make_approval_model_response(
                self.approval_requested,
                self.original_tool_arguments,
            )
        )

    def to_model_tool_call(self) -> ModelToolCall:
        assert self.approval_requested.provider_tool_call_id is not None
        return ModelToolCall(
            tool_name=self.approval_requested.subject,
            arguments=self.original_tool_arguments,
            tool_call_id=self.approval_requested.provider_tool_call_id,
        )

    def make_denial_tool_return(self) -> ModelRequest:
        return _make_denial_tool_return(self.approval_requested)


class SuspendedTurnResumption:
    """Resolve persisted suspension state back into a resumable model loop."""

    def __init__(self, session_repository: TurnResumptionRepository) -> None:
        self._session_repository = session_repository

    def prepare_user_answer(
        self,
        session_id,
        payload: UserAnswerProvided,
    ) -> UserAnswerResumeState:
        question_payload: UserQuestionAsked | None = None
        for event in self._session_repository.read_session_events(session_id):
            if (
                isinstance(event.payload, UserQuestionAsked)
                and event.payload.question_id == payload.question_id
            ):
                question_payload = event.payload
                break

        if question_payload is None:
            raise ValueError(
                "no UserQuestionAsked event found for question_id "
                f"{payload.question_id}"
            )

        turn_events = self._session_repository.read_events_by_correlation_id(
            session_id,
            turn_id=question_payload.turn_id,
        )
        return UserAnswerResumeState(
            question_payload=question_payload,
            answer=payload.answer,
            assistant_message_id=_find_assistant_message_id(turn_events),
            starting_model_call_index=_count_model_calls(turn_events),
        )

    def prepare_approval_resolution(
        self,
        session_id,
        payload: ApprovalResolved,
    ) -> ApprovalResumeState:
        approval_requested: ApprovalRequested | None = None
        for event in self._session_repository.read_events_by_correlation_id(
            session_id,
            approval_id=payload.approval_id,
        ):
            if isinstance(event.payload, ApprovalRequested):
                approval_requested = event.payload
                break

        if approval_requested is None:
            raise ValueError(
                "no ApprovalRequested event found for approval_id "
                f"{payload.approval_id}"
            )

        turn_events = self._session_repository.read_events_by_correlation_id(
            session_id,
            turn_id=approval_requested.turn_id,
        )
        original_tool_arguments = (
            _find_tool_arguments(turn_events, approval_requested.tool_call_id)
            if approval_requested.tool_call_id is not None
            else {}
        )
        return ApprovalResumeState(
            approval_requested=approval_requested,
            decision=payload.decision,
            assistant_message_id=_find_assistant_message_id(turn_events),
            starting_model_call_index=_count_model_calls(turn_events),
            original_tool_arguments=original_tool_arguments,
        )


def _find_assistant_message_id(turn_events: list[EventEnvelope]) -> MessageId:
    for event in turn_events:
        if isinstance(event.payload, AssistantMessageStarted):
            return event.payload.message_id
    return new_message_id()


def _count_model_calls(turn_events: list[EventEnvelope]) -> int:
    return sum(
        1 for event in turn_events if isinstance(event.payload, ModelCallStarted)
    )


def _make_ask_user_model_response(question_payload: UserQuestionAsked) -> ModelResponse:
    timestamp = datetime.now(tz=UTC)
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="ask_user",
                tool_call_id=question_payload.provider_tool_call_id,
                args={"question": question_payload.question},
            )
        ],
        timestamp=timestamp,
    )


def _make_ask_user_tool_return(
    question_payload: UserQuestionAsked,
    answer: str,
) -> ModelRequest:
    timestamp = datetime.now(tz=UTC)
    return ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name="ask_user",
                tool_call_id=question_payload.provider_tool_call_id,
                content={"answer": answer},
                timestamp=timestamp,
            )
        ],
        timestamp=timestamp,
    )


def _make_approval_model_response(
    approval_requested: ApprovalRequested,
    arguments: dict[str, object] | None = None,
) -> ModelResponse:
    assert approval_requested.provider_tool_call_id is not None
    timestamp = datetime.now(tz=UTC)
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name=approval_requested.subject,
                tool_call_id=approval_requested.provider_tool_call_id,
                args=arguments or {},
            )
        ],
        timestamp=timestamp,
    )


def _make_denial_tool_return(approval_requested: ApprovalRequested) -> ModelRequest:
    assert approval_requested.provider_tool_call_id is not None
    timestamp = datetime.now(tz=UTC)
    return ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name=approval_requested.subject,
                tool_call_id=approval_requested.provider_tool_call_id,
                content={
                    "error": f"Action denied by operator: {approval_requested.reason}"
                },
                timestamp=timestamp,
            )
        ],
        timestamp=timestamp,
    )


def _find_tool_arguments(
    turn_events: list[EventEnvelope],
    tool_call_id: ToolCallId,
) -> dict[str, object]:
    for event in turn_events:
        if (
            isinstance(event.payload, ModelToolCallRequested)
            and event.payload.tool_call_id == tool_call_id
        ):
            raw: object = json.loads(event.payload.arguments_json)
            if isinstance(raw, dict):
                return {str(key): value for key, value in raw.items()}
    return {}
