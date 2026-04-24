"""Helpers for recording replay manifests during live turn execution."""

from typing import Any
from typing import Literal

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.llm import PreparedModelTurn
from glassbox.runtime.context_builder import TurnContext
from glassbox.runtime.replay_manifests import ReplayManifest
from glassbox.runtime.replay_manifests import build_replay_model_call_manifest
from glassbox.runtime.replay_manifests import build_replay_tool_request_manifest
from glassbox.runtime.replay_manifests import build_replay_tool_result_manifest
from glassbox.runtime.replay_manifests import build_replay_turn_output_manifest
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository
from glassbox.tools import PreparedToolExecution
from glassbox.tools import ToolExecutionResult


class ReplayArtifactRecorder:
    """Persist replay manifests as artifact files linked from session events."""

    def __init__(
        self,
        session_repository: SessionRepository,
        artifact_repository: ArtifactRepository,
    ) -> None:
        self._session_repository = session_repository
        self._artifact_repository = artifact_repository

    def record_model_call(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        *,
        call_index: int,
        turn_context: TurnContext,
        prepared_turn: PreparedModelTurn,
    ) -> EventEnvelope:
        manifest = build_replay_model_call_manifest(
            call_index=call_index,
            turn_context=turn_context,
            prepared_turn=prepared_turn,
        )
        return self._record_manifest(session_id, turn_id, manifest)

    def record_tool_request(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        prepared_tool_call: PreparedToolExecution,
    ) -> EventEnvelope:
        manifest = build_replay_tool_request_manifest(prepared_tool_call)
        return self._record_manifest(
            session_id,
            turn_id,
            manifest,
            tool_call_id=prepared_tool_call.event_tool_call_id,
        )

    def record_tool_result(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        *,
        tool_call_id: ToolCallId,
        provider_tool_call_id: str,
        tool_name: str,
        success: bool,
        summary: str,
        output_payload: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> EventEnvelope:
        manifest = build_replay_tool_result_manifest(
            tool_call_id=tool_call_id,
            provider_tool_call_id=provider_tool_call_id,
            tool_name=tool_name,
            success=success,
            summary=summary,
            output_payload=output_payload,
            error_message=error_message,
        )
        return self._record_manifest(
            session_id,
            turn_id,
            manifest,
            tool_call_id=tool_call_id,
        )

    def record_tool_execution_result(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        execution_result: ToolExecutionResult,
    ) -> EventEnvelope:
        return self.record_tool_result(
            session_id,
            turn_id,
            tool_call_id=execution_result.event_tool_call_id,
            provider_tool_call_id=execution_result.provider_tool_call_id,
            tool_name=execution_result.tool_name,
            success=True,
            output_payload=execution_result.output_payload,
            summary=execution_result.summary,
        )

    def record_turn_output(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        *,
        outcome: Literal[
            "completed",
            "awaiting_approval",
            "awaiting_user_input",
            "failed",
        ],
        assistant_text: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> EventEnvelope:
        manifest = build_replay_turn_output_manifest(
            outcome=outcome,
            assistant_text=assistant_text,
            details=details,
        )
        return self._record_manifest(session_id, turn_id, manifest)

    def _record_manifest(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        manifest: ReplayManifest,
        *,
        tool_call_id: ToolCallId | None = None,
    ) -> EventEnvelope:
        stored_artifact = self._artifact_repository.write_text_artifact(
            session_id,
            manifest.model_dump_json(indent=2),
            suffix=".json",
        )
        stored_events = self._session_repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReplayArtifactRecorded(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        artifact_id=stored_artifact.artifact_id,
                        artifact_kind=manifest.artifact_kind,
                        path=stored_artifact.relative_path.as_posix(),
                    ),
                )
            ]
        )
        return stored_events[0]
