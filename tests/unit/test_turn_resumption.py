"""Focused unit tests for suspended turn resumption helpers."""

from __future__ import annotations

import json

from pydantic_ai.messages import ModelRequest, ModelResponse, ToolReturnPart

from glassbox.core import EventEnvelope
from glassbox.core.events import (
    ApprovalRequested,
    ApprovalResolved,
    AssistantMessageStarted,
    ModelCallStarted,
    ModelToolCallRequested,
    UserAnswerProvided,
    UserQuestionAsked,
)
from glassbox.core.ids import (
    new_approval_id,
    new_message_id,
    new_question_id,
    new_session_id,
    new_tool_call_id,
    new_turn_id,
)
from glassbox.core.types import ApprovalDecision
from glassbox.runtime.turn_resumption import SuspendedTurnResumption


class FakeSessionRepository:
    def __init__(
        self,
        *,
        session_events: list[EventEnvelope],
        turn_events_by_turn_id: dict[object, list[EventEnvelope]],
        approval_events_by_approval_id: dict[object, list[EventEnvelope]],
    ) -> None:
        self._session_events = session_events
        self._turn_events_by_turn_id = turn_events_by_turn_id
        self._approval_events_by_approval_id = approval_events_by_approval_id

    def read_session_events(self, session_id):
        assert session_id
        return list(self._session_events)

    def read_events_by_correlation_id(
        self,
        session_id,
        *,
        turn_id=None,
        approval_id=None,
    ):
        assert session_id
        if turn_id is not None:
            return list(self._turn_events_by_turn_id.get(turn_id, []))
        if approval_id is not None:
            return list(self._approval_events_by_approval_id.get(approval_id, []))
        return []


def test_prepare_user_answer_reconstructs_resume_state() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    question_id = new_question_id()
    tool_call_id = new_tool_call_id()
    assistant_message_id = new_message_id()
    question_event = EventEnvelope(
        session_id=session_id,
        sequence=1,
        payload=UserQuestionAsked(
            question_id=question_id,
            turn_id=turn_id,
            tool_call_id=tool_call_id,
            provider_tool_call_id="provider-ask-1",
            question="What colour should I use?",
        ),
    )
    turn_events = [
        EventEnvelope(
            session_id=session_id,
            sequence=2,
            payload=AssistantMessageStarted(message_id=assistant_message_id),
        ),
        EventEnvelope(
            session_id=session_id,
            sequence=3,
            payload=ModelCallStarted(
                turn_id=turn_id,
                provider="openai",
                model_name="gpt-5.4",
            ),
        ),
    ]
    repository = FakeSessionRepository(
        session_events=[question_event],
        turn_events_by_turn_id={turn_id: turn_events},
        approval_events_by_approval_id={},
    )

    state = SuspendedTurnResumption(repository).prepare_user_answer(
        session_id,
        UserAnswerProvided(question_id=question_id, answer="blue"),
    )

    conversation = []
    state.extend_conversation(conversation)

    assert state.turn_id == turn_id
    assert state.assistant_message_id == assistant_message_id
    assert state.starting_model_call_index == 1
    assert len(conversation) == 2
    assert isinstance(conversation[0], ModelResponse)
    assert isinstance(conversation[1], ModelRequest)
    tool_return = conversation[1].parts[0]
    assert isinstance(tool_return, ToolReturnPart)
    assert tool_return.content == {"answer": "blue"}


def test_prepare_approval_resolution_reconstructs_tool_arguments() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    approval_id = new_approval_id()
    tool_call_id = new_tool_call_id()
    assistant_message_id = new_message_id()
    approval_requested = ApprovalRequested(
        approval_id=approval_id,
        turn_id=turn_id,
        reason="needs approval",
        subject="apply_patch",
        tool_call_id=tool_call_id,
        provider_tool_call_id="provider-call-patch-1",
    )
    repository = FakeSessionRepository(
        session_events=[],
        turn_events_by_turn_id={
            turn_id: [
                EventEnvelope(
                    session_id=session_id,
                    sequence=2,
                    payload=AssistantMessageStarted(message_id=assistant_message_id),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=3,
                    payload=ModelCallStarted(
                        turn_id=turn_id,
                        provider="openai",
                        model_name="gpt-5.4",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=4,
                    payload=ModelCallStarted(
                        turn_id=turn_id,
                        provider="openai",
                        model_name="gpt-5.4",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=5,
                    payload=ModelToolCallRequested(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="apply_patch",
                        arguments_json=json.dumps(
                            {"path": "hello.txt", "new_text": "Hello\n"},
                            sort_keys=True,
                        ),
                    ),
                ),
            ]
        },
        approval_events_by_approval_id={
            approval_id: [
                EventEnvelope(
                    session_id=session_id,
                    sequence=1,
                    payload=approval_requested,
                )
            ]
        },
    )

    state = SuspendedTurnResumption(repository).prepare_approval_resolution(
        session_id,
        ApprovalResolved(
            approval_id=approval_id,
            decision=ApprovalDecision.APPROVED,
            decided_by="operator",
        ),
    )

    conversation = []
    state.extend_conversation(conversation)

    assert state.is_resumable is True
    assert state.turn_id == turn_id
    assert state.assistant_message_id == assistant_message_id
    assert state.starting_model_call_index == 2
    assert state.original_tool_arguments == {
        "path": "hello.txt",
        "new_text": "Hello\n",
    }
    assert len(conversation) == 1
    assert isinstance(conversation[0], ModelResponse)
    assert state.to_model_tool_call().arguments == state.original_tool_arguments
