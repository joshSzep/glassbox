"""Replay-capture forwarding hooks for turn execution."""

from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.llm import PreparedModelTurn
from glassbox.runtime.context_builder import TurnContext
from glassbox.runtime.replay_capture import ReplayArtifactRecorder


class TurnReplayHooks:
    """Small adapter around optional replay artifact capture."""

    def __init__(self, replay_recorder: ReplayArtifactRecorder | None) -> None:
        self._replay_recorder = replay_recorder

    def record_model_call(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId,
        turn_context: TurnContext,
        prepared_turn: PreparedModelTurn,
        call_index: int,
    ) -> None:
        if self._replay_recorder is None:
            return
        self._replay_recorder.record_model_call(
            session_id,
            turn_id,
            call_index=call_index,
            turn_context=turn_context,
            prepared_turn=prepared_turn,
        )

    def record_tool_request(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId,
        prepared_tool_call,
    ) -> None:
        if self._replay_recorder is None:
            return
        self._replay_recorder.record_tool_request(
            session_id,
            turn_id,
            prepared_tool_call,
        )

    def record_tool_execution_result(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId,
        execution_result,
    ) -> None:
        if self._replay_recorder is None:
            return
        self._replay_recorder.record_tool_execution_result(
            session_id,
            turn_id,
            execution_result,
        )

    def record_tool_result(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId,
        tool_call_id: ToolCallId,
        provider_tool_call_id: str,
        tool_name: str,
        success: bool,
        summary: str,
        error_message: str | None = None,
    ) -> None:
        if self._replay_recorder is None:
            return
        self._replay_recorder.record_tool_result(
            session_id,
            turn_id,
            tool_call_id=tool_call_id,
            provider_tool_call_id=provider_tool_call_id,
            tool_name=tool_name,
            success=success,
            summary=summary,
            error_message=error_message,
        )

    def record_turn_output(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId,
        outcome,
        assistant_text: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        if self._replay_recorder is None:
            return
        self._replay_recorder.record_turn_output(
            session_id,
            turn_id,
            outcome=outcome,
            assistant_text=assistant_text,
            details=details,
        )


__all__ = ["TurnReplayHooks"]
