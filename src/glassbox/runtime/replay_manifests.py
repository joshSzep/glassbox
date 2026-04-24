"""Replay manifest models, builders, and loader helpers."""

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic_ai.messages import ModelMessage
from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import SystemPromptPart
from pydantic_ai.messages import TextContent
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.messages import UserPromptPart

from glassbox.core.ids import ToolCallId
from glassbox.llm import PreparedModelTurn
from glassbox.runtime.context_builder import TurnContext
from glassbox.runtime.replay_fingerprints import ReplayEnrichedContextSourceManifest
from glassbox.runtime.replay_fingerprints import (
    build_replay_enriched_context_fingerprint,
)
from glassbox.runtime.replay_fingerprints import build_replay_enriched_context_sources
from glassbox.runtime.replay_fingerprints import fingerprint_replay_payload
from glassbox.tools import PreparedToolExecution

REPLAY_MODEL_CALL_ARTIFACT = "replay_model_call"
REPLAY_TOOL_REQUEST_ARTIFACT = "replay_tool_request"
REPLAY_TOOL_RESULT_ARTIFACT = "replay_tool_result"
REPLAY_TURN_OUTPUT_ARTIFACT = "replay_turn_output"

_REDACTED = "[REDACTED]"
_SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "token",
    "secret",
    "password",
    "authorization",
    "auth",
)


class ReplayMessagePartSnapshot(BaseModel):
    """Normalized representation of one provider-facing message part."""

    model_config = ConfigDict(extra="forbid")

    part_kind: str
    content: Any = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    arguments: Any = None


class ReplayMessageSnapshot(BaseModel):
    """Normalized representation of one provider-facing message."""

    model_config = ConfigDict(extra="forbid")

    message_kind: Literal["request", "response"]
    parts: list[ReplayMessagePartSnapshot]


class ReplayRuntimeConfigSnapshot(BaseModel):
    """Non-secret summary of runtime config relevant to replay."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    model_settings: dict[str, Any] = Field(default_factory=dict)
    allow_text_output: bool
    allow_image_output: bool
    tool_names: list[str] = Field(default_factory=list)
    fingerprint: str


class ReplayPreparedTurnSnapshot(BaseModel):
    """Normalized prepared model input for one model call."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    user_prompt: str | None = None
    message_history: list[ReplayMessageSnapshot]
    request_parameters: dict[str, Any] = Field(default_factory=dict)
    model_settings: dict[str, Any] = Field(default_factory=dict)


class ReplayModelCallManifest(BaseModel):
    """Replay baseline for one model call inside a turn."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = 1
    artifact_kind: Literal["replay_model_call"] = REPLAY_MODEL_CALL_ARTIFACT
    call_index: int = Field(ge=1)
    turn_context: dict[str, Any]
    enriched_context_fingerprint: str | None = None
    enriched_context_sources: list[ReplayEnrichedContextSourceManifest] = Field(
        default_factory=list
    )
    runtime_config: ReplayRuntimeConfigSnapshot
    prepared_turn: ReplayPreparedTurnSnapshot


class ReplayToolRequestManifest(BaseModel):
    """Replay baseline for one validated tool request."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = 1
    artifact_kind: Literal["replay_tool_request"] = REPLAY_TOOL_REQUEST_ARTIFACT
    tool_call_id: ToolCallId
    provider_tool_call_id: str
    tool_name: str
    validated_arguments: dict[str, Any]
    policy_decision: dict[str, Any]


class ReplayToolResultManifest(BaseModel):
    """Replay baseline for one tool execution result."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = 1
    artifact_kind: Literal["replay_tool_result"] = REPLAY_TOOL_RESULT_ARTIFACT
    tool_call_id: ToolCallId
    provider_tool_call_id: str
    tool_name: str
    success: bool
    output_payload: dict[str, Any] | None = None
    summary: str
    error_message: str | None = None


class ReplayTurnOutputManifest(BaseModel):
    """Replay baseline for the observable outcome of one turn."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = 1
    artifact_kind: Literal["replay_turn_output"] = REPLAY_TURN_OUTPUT_ARTIFACT
    outcome: Literal[
        "completed",
        "awaiting_approval",
        "awaiting_user_input",
        "failed",
    ]
    assistant_text: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


type ReplayManifest = (
    ReplayModelCallManifest
    | ReplayToolRequestManifest
    | ReplayToolResultManifest
    | ReplayTurnOutputManifest
)


def build_replay_runtime_config_snapshot(
    prepared_turn: PreparedModelTurn,
    *,
    tool_names: Sequence[str],
) -> ReplayRuntimeConfigSnapshot:
    """Build the replay snapshot for non-secret runtime configuration."""

    redacted_model_settings = _redact_json(prepared_turn.model_settings)
    runtime_config = {
        "model_name": prepared_turn.model_name,
        "model_settings": redacted_model_settings,
        "allow_text_output": prepared_turn.request_parameters.allow_text_output,
        "allow_image_output": prepared_turn.request_parameters.allow_image_output,
        "tool_names": list(tool_names),
    }
    runtime_config["fingerprint"] = fingerprint_replay_payload(runtime_config)
    return ReplayRuntimeConfigSnapshot.model_validate(runtime_config)


def build_replay_prepared_turn_snapshot(
    prepared_turn: PreparedModelTurn,
    *,
    tool_names: Sequence[str],
    normalize_system_prompt: bool = True,
) -> ReplayPreparedTurnSnapshot:
    """Build the replay snapshot for one prepared model call input."""

    return ReplayPreparedTurnSnapshot(
        model_name=prepared_turn.model_name,
        user_prompt=prepared_turn.user_prompt,
        message_history=[
            _snapshot_model_message(
                message,
                normalize_system_prompt=normalize_system_prompt,
            )
            for message in prepared_turn.message_history
        ],
        request_parameters={
            "allow_text_output": prepared_turn.request_parameters.allow_text_output,
            "allow_image_output": prepared_turn.request_parameters.allow_image_output,
            "tool_names": list(tool_names),
        },
        model_settings=_redact_json(prepared_turn.model_settings),
    )


def build_replay_model_call_manifest(
    *,
    call_index: int,
    turn_context: TurnContext,
    prepared_turn: PreparedModelTurn,
) -> ReplayModelCallManifest:
    """Build the replay manifest for one model call inside a turn."""

    turn_context_payload = _redact_json(turn_context.model_dump(mode="json"))
    return ReplayModelCallManifest(
        call_index=call_index,
        turn_context=turn_context_payload,
        enriched_context_fingerprint=build_replay_enriched_context_fingerprint(
            turn_context
        ),
        enriched_context_sources=build_replay_enriched_context_sources(
            turn_context_payload
        ),
        runtime_config=build_replay_runtime_config_snapshot(
            prepared_turn,
            tool_names=[tool.name for tool in turn_context.available_tools],
        ),
        prepared_turn=build_replay_prepared_turn_snapshot(
            prepared_turn,
            tool_names=[tool.name for tool in turn_context.available_tools],
        ),
    )


def build_replay_tool_request_manifest(
    prepared_tool_call: PreparedToolExecution,
) -> ReplayToolRequestManifest:
    """Build the replay manifest for one validated tool request."""

    return ReplayToolRequestManifest(
        tool_call_id=prepared_tool_call.event_tool_call_id,
        provider_tool_call_id=prepared_tool_call.provider_tool_call_id,
        tool_name=prepared_tool_call.tool_name,
        validated_arguments=_redact_json(
            prepared_tool_call.validated_arguments.model_dump(mode="json")
        ),
        policy_decision=_redact_json(
            prepared_tool_call.policy_decision.model_dump(mode="json")
        ),
    )


def build_replay_tool_result_manifest(
    *,
    tool_call_id: ToolCallId,
    provider_tool_call_id: str,
    tool_name: str,
    success: bool,
    summary: str,
    output_payload: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> ReplayToolResultManifest:
    """Build the replay manifest for one tool execution result."""

    return ReplayToolResultManifest(
        tool_call_id=tool_call_id,
        provider_tool_call_id=provider_tool_call_id,
        tool_name=tool_name,
        success=success,
        output_payload=(
            _redact_json(output_payload) if output_payload is not None else None
        ),
        summary=summary,
        error_message=error_message,
    )


def build_replay_turn_output_manifest(
    *,
    outcome: Literal[
        "completed",
        "awaiting_approval",
        "awaiting_user_input",
        "failed",
    ],
    assistant_text: str | None = None,
    details: dict[str, Any] | None = None,
) -> ReplayTurnOutputManifest:
    """Build the replay manifest for the observable outcome of one turn."""

    return ReplayTurnOutputManifest(
        outcome=outcome,
        assistant_text=assistant_text,
        details=_redact_json(details or {}),
    )


def load_replay_manifest(raw_text: str) -> ReplayManifest:
    """Decode one persisted replay artifact into its typed manifest."""

    manifest_data = json.loads(raw_text)
    if not isinstance(manifest_data, dict):
        raise ValueError("replay artifact must decode to a JSON object")

    artifact_kind = manifest_data.get("artifact_kind")
    if artifact_kind == REPLAY_MODEL_CALL_ARTIFACT:
        return ReplayModelCallManifest.model_validate(manifest_data)
    if artifact_kind == REPLAY_TOOL_REQUEST_ARTIFACT:
        return ReplayToolRequestManifest.model_validate(manifest_data)
    if artifact_kind == REPLAY_TOOL_RESULT_ARTIFACT:
        return ReplayToolResultManifest.model_validate(manifest_data)
    if artifact_kind == REPLAY_TURN_OUTPUT_ARTIFACT:
        return ReplayTurnOutputManifest.model_validate(manifest_data)
    raise ValueError(f"unsupported replay artifact kind: {artifact_kind!r}")


def _snapshot_model_message(
    message: ModelMessage,
    *,
    normalize_system_prompt: bool = True,
) -> ReplayMessageSnapshot:
    if isinstance(message, ModelRequest):
        return ReplayMessageSnapshot(
            message_kind="request",
            parts=[
                _snapshot_request_part(
                    part,
                    normalize_system_prompt=normalize_system_prompt,
                )
                for part in message.parts
            ],
        )
    if isinstance(message, ModelResponse):
        return ReplayMessageSnapshot(
            message_kind="response",
            parts=[_snapshot_response_part(part) for part in message.parts],
        )
    raise TypeError(f"unsupported model message type: {type(message)!r}")


def _snapshot_request_part(
    part: Any,
    *,
    normalize_system_prompt: bool = True,
) -> ReplayMessagePartSnapshot:
    if isinstance(part, SystemPromptPart):
        return ReplayMessagePartSnapshot(
            part_kind="system_prompt",
            content=(
                _normalize_system_prompt_content(part.content)
                if normalize_system_prompt
                else part.content
            ),
        )
    if isinstance(part, UserPromptPart):
        return ReplayMessagePartSnapshot(
            part_kind="user_prompt",
            content=_normalize_user_prompt_content(part.content),
        )
    if isinstance(part, ToolReturnPart):
        return ReplayMessagePartSnapshot(
            part_kind="tool_return",
            tool_name=part.tool_name,
            tool_call_id=part.tool_call_id,
            content=_redact_json(_json_compatible(part.content)),
        )
    return ReplayMessagePartSnapshot(
        part_kind=type(part).__name__,
        content=_redact_json(_json_compatible(getattr(part, "content", None))),
    )


def _snapshot_response_part(part: Any) -> ReplayMessagePartSnapshot:
    if isinstance(part, TextPart):
        return ReplayMessagePartSnapshot(part_kind="text", content=part.content)
    if isinstance(part, ToolCallPart):
        return ReplayMessagePartSnapshot(
            part_kind="tool_call",
            tool_name=part.tool_name,
            tool_call_id=part.tool_call_id,
            arguments=_redact_json(_json_compatible(part.args)),
        )
    return ReplayMessagePartSnapshot(
        part_kind=type(part).__name__,
        content=_redact_json(_json_compatible(getattr(part, "content", None))),
    )


def _normalize_user_prompt_content(content: Any) -> Any:
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence) and not isinstance(
        content,
        (str, bytes, bytearray),
    ):
        return [_normalize_user_prompt_content(item) for item in content]
    if isinstance(content, TextContent):
        return content.content
    return _redact_json(_json_compatible(content))


def _normalize_system_prompt_content(content: str) -> str:
    sections = [section.strip() for section in content.split("\n\n")]
    filtered_sections = [
        section
        for section in sections
        if section != ""
        and not section.startswith("Repository context:")
        and not section.startswith("Memory notes:")
        and not section.startswith("Working set:")
        and not section.startswith("Artifact-backed context:")
    ]
    return "\n\n".join(filtered_sections)


def _json_compatible(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_compatible(item) for item in value]
    return value


def _redact_json(value: Any) -> Any:
    normalized = _json_compatible(value)
    if isinstance(normalized, dict):
        redacted: dict[str, Any] = {}
        for key, item in normalized.items():
            if _looks_sensitive(key):
                redacted[key] = _REDACTED
            else:
                redacted[key] = _redact_json(item)
        return redacted
    if isinstance(normalized, list):
        return [_redact_json(item) for item in normalized]
    return normalized


def _looks_sensitive(key: str) -> bool:
    normalized_key = key.lower().replace("-", "_")
    return any(fragment in normalized_key for fragment in _SENSITIVE_KEY_FRAGMENTS)
