"""Stable internal adapter layer for pydantic-ai integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.messages import (
    FinalResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponseStreamEvent,
    PartDeltaEvent,
    PartEndEvent,
    PartStartEvent,
    SystemPromptPart,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.tools import ToolDefinition

from glassbox.core.models import TranscriptMessage
from glassbox.runtime import ToolSchema, TurnContext


class ModelProviderConfig(BaseModel):
    """Provider and model configuration used by the adapter."""

    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(min_length=1)
    provider: str | None = None
    model_settings: dict[str, object] = Field(default_factory=dict)
    allow_text_output: bool = True
    allow_image_output: bool = False

    @property
    def resolved_model_name(self) -> str:
        """Return the provider-qualified model name expected by pydantic-ai."""

        if self.provider is None or ":" in self.model_name:
            return self.model_name
        return f"{self.provider}:{self.model_name}"


@dataclass(frozen=True, slots=True)
class PreparedModelTurn:
    """Prepared provider-facing model input for one turn."""

    model_name: str
    message_history: tuple[ModelMessage, ...]
    user_prompt: str | None
    request_parameters: ModelRequestParameters
    model_settings: dict[str, object]


@dataclass(frozen=True, slots=True)
class ModelTextDelta:
    """A streamed assistant text delta."""

    text: str
    kind: Literal["text_delta"] = "text_delta"


@dataclass(frozen=True, slots=True)
class ModelToolCallDelta:
    """A streamed tool-call delta from the model provider."""

    tool_name_delta: str | None = None
    arguments_delta: str | dict[str, object] | None = None
    tool_call_id: str | None = None
    kind: Literal["tool_call_delta"] = "tool_call_delta"


@dataclass(frozen=True, slots=True)
class ModelToolCall:
    """A structured tool-call request emitted by the model."""

    tool_name: str
    arguments: str | dict[str, object] | None
    tool_call_id: str
    kind: Literal["tool_call"] = "tool_call"


@dataclass(frozen=True, slots=True)
class ModelFinalResult:
    """Signal that the provider reached a final result boundary."""

    tool_name: str | None
    tool_call_id: str | None
    kind: Literal["final_result"] = "final_result"


ModelAdapterStreamEvent = (
    ModelTextDelta | ModelToolCallDelta | ModelToolCall | ModelFinalResult
)


class ModelAdapter(Protocol):
    """Stable internal interface for model adapters."""

    config: ModelProviderConfig

    def build_turn_request(
        self,
        turn_context: TurnContext,
        *,
        system_prompt: str | None = None,
    ) -> PreparedModelTurn:
        """Translate internal turn context into provider-facing request state."""

    def new_stream_translator(self) -> PydanticAIStreamTranslator:
        """Create a translator for provider stream events."""


class PydanticAIModelAdapter:
    """Translate Glassbox turn state into pydantic-ai request structures."""

    def __init__(self, config: ModelProviderConfig) -> None:
        self.config = config

    def build_turn_request(
        self,
        turn_context: TurnContext,
        *,
        system_prompt: str | None = None,
    ) -> PreparedModelTurn:
        """Build the provider-facing turn input for one model call."""

        history = list(_build_message_history(turn_context.transcript))
        user_prompt = None
        if turn_context.transcript and turn_context.transcript[-1].role == "user":
            latest_user_message = turn_context.transcript[-1]
            history.pop()
            user_prompt = _message_text(latest_user_message)

        if system_prompt is not None:
            history.insert(
                0,
                ModelRequest(
                    parts=[
                        SystemPromptPart(
                            content=system_prompt,
                            timestamp=_default_timestamp(),
                        )
                    ],
                    timestamp=_default_timestamp(),
                ),
            )

        tool_definitions = list(_build_tool_definitions(turn_context.available_tools))
        request_parameters = ModelRequestParameters(
            function_tools=tool_definitions,
            allow_text_output=self.config.allow_text_output,
            allow_image_output=self.config.allow_image_output,
        )

        return PreparedModelTurn(
            model_name=self.config.resolved_model_name,
            message_history=tuple(history),
            user_prompt=user_prompt,
            request_parameters=request_parameters,
            model_settings=dict(self.config.model_settings),
        )

    def new_stream_translator(self) -> PydanticAIStreamTranslator:
        """Create a stateful translator for pydantic-ai stream events."""

        return PydanticAIStreamTranslator()


@dataclass(slots=True)
class PydanticAIStreamTranslator:
    """Translate pydantic-ai stream events into stable internal events."""

    _tool_calls: dict[int, _PendingToolCall] = field(default_factory=dict)

    def translate(
        self, event: ModelResponseStreamEvent
    ) -> tuple[ModelAdapterStreamEvent, ...]:
        """Translate one provider event into zero or more internal events."""

        if isinstance(event, PartStartEvent):
            return self._translate_part_start(event)
        if isinstance(event, PartDeltaEvent):
            return self._translate_part_delta(event)
        if isinstance(event, PartEndEvent):
            return self._translate_part_end(event)
        if isinstance(event, FinalResultEvent):
            return (
                ModelFinalResult(
                    tool_name=event.tool_name,
                    tool_call_id=event.tool_call_id,
                ),
            )
        return ()

    def _translate_part_start(
        self, event: PartStartEvent
    ) -> tuple[ModelAdapterStreamEvent, ...]:
        part = event.part
        if isinstance(part, TextPart):
            if part.content == "":
                return ()
            return (ModelTextDelta(text=part.content),)
        if isinstance(part, ToolCallPart):
            pending = _PendingToolCall(
                tool_name=part.tool_name,
                arguments=_normalize_arguments(part.args),
                tool_call_id=part.tool_call_id,
            )
            self._tool_calls[event.index] = pending
            return (
                ModelToolCallDelta(
                    tool_name_delta=part.tool_name,
                    arguments_delta=_normalize_arguments(part.args),
                    tool_call_id=part.tool_call_id,
                ),
            )
        return ()

    def _translate_part_delta(
        self, event: PartDeltaEvent
    ) -> tuple[ModelAdapterStreamEvent, ...]:
        delta = event.delta
        if isinstance(delta, TextPartDelta):
            if delta.content_delta == "":
                return ()
            return (ModelTextDelta(text=delta.content_delta),)
        if isinstance(delta, ToolCallPartDelta):
            pending = self._tool_calls.setdefault(event.index, _PendingToolCall())
            pending.tool_name = _merge_optional_text(
                pending.tool_name,
                delta.tool_name_delta,
            )
            pending.arguments = _merge_arguments(
                pending.arguments,
                _normalize_arguments(delta.args_delta),
            )
            pending.tool_call_id = delta.tool_call_id or pending.tool_call_id
            return (
                ModelToolCallDelta(
                    tool_name_delta=delta.tool_name_delta,
                    arguments_delta=_normalize_arguments(delta.args_delta),
                    tool_call_id=delta.tool_call_id,
                ),
            )
        return ()

    def _translate_part_end(
        self, event: PartEndEvent
    ) -> tuple[ModelAdapterStreamEvent, ...]:
        part = event.part
        if not isinstance(part, ToolCallPart):
            return ()

        pending = self._tool_calls.pop(event.index, _PendingToolCall())
        tool_name = part.tool_name or pending.tool_name
        tool_call_id = part.tool_call_id or pending.tool_call_id
        if tool_name is None or tool_call_id is None:
            raise ValueError("tool call stream ended without a complete identifier")

        arguments = _normalize_arguments(part.args)
        if arguments is None:
            arguments = pending.arguments
        return (
            ModelToolCall(
                tool_name=tool_name,
                arguments=arguments,
                tool_call_id=tool_call_id,
            ),
        )


@dataclass(slots=True)
class _PendingToolCall:
    tool_name: str | None = None
    arguments: str | dict[str, object] | None = None
    tool_call_id: str | None = None


def _build_message_history(
    transcript: list[TranscriptMessage],
) -> tuple[ModelMessage, ...]:
    history: list[ModelMessage] = []
    for message in transcript:
        message_text = _message_text(message)
        if message.role == "assistant":
            history.append(
                ModelResponse(
                    parts=[TextPart(content=message_text)],
                    timestamp=message.created_at,
                )
            )
            continue

        part = (
            SystemPromptPart(content=message_text, timestamp=message.created_at)
            if message.role == "system"
            else UserPromptPart(content=message_text, timestamp=message.created_at)
        )
        history.append(ModelRequest(parts=[part], timestamp=message.created_at))

    return tuple(history)


def _build_tool_definitions(
    tool_schemas: list[ToolSchema],
) -> tuple[ToolDefinition, ...]:
    return tuple(
        ToolDefinition(
            name=tool.name,
            description=tool.description,
            parameters_json_schema=cast(dict[str, Any], tool.parameters_json_schema),
        )
        for tool in tool_schemas
    )


def _message_text(message: TranscriptMessage) -> str:
    return "\n".join(part.text for part in message.parts)


def _default_timestamp() -> datetime:
    return datetime.now(tz=UTC)


def _normalize_arguments(
    arguments: str | dict[str, Any] | None,
) -> str | dict[str, object] | None:
    if arguments is None:
        return None
    if isinstance(arguments, str):
        return arguments
    return {key: value for key, value in arguments.items()}


def _merge_optional_text(current: str | None, delta: str | None) -> str | None:
    if delta is None:
        return current
    if current is None:
        return delta
    return f"{current}{delta}"


def _merge_arguments(
    current: str | dict[str, object] | None,
    delta: str | dict[str, object] | None,
) -> str | dict[str, object] | None:
    if delta is None:
        return current
    if current is None:
        return delta
    if isinstance(current, str) and isinstance(delta, str):
        return f"{current}{delta}"
    if isinstance(current, dict) and isinstance(delta, dict):
        return {**current, **delta}
    raise ValueError("tool call arguments changed representation mid-stream")
