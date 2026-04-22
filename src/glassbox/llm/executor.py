"""Model execution helpers built on top of pydantic-ai models."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponseStreamEvent,
    TextContent,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models import Model, infer_model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from glassbox.llm.adapters import (
    ModelAdapterStreamEvent,
    ModelToolCall,
    PreparedModelTurn,
    PydanticAIStreamTranslator,
)


@dataclass(frozen=True, slots=True)
class ModelExecutionResult:
    """Normalized result from one model invocation."""

    assistant_text: str
    tool_calls: tuple[ModelToolCall, ...]
    model_response: ModelResponse
    input_tokens: int | None = None
    output_tokens: int | None = None


class ModelExecutor(Protocol):
    """Stable interface for executing one prepared model turn."""

    async def execute(self, prepared_turn: PreparedModelTurn) -> ModelExecutionResult:
        """Execute one prepared turn and return a normalized result."""

    async def execute_stream(
        self,
        prepared_turn: PreparedModelTurn,
        *,
        stream_translator: PydanticAIStreamTranslator,
        on_event: Callable[[ModelAdapterStreamEvent], None],
    ) -> ModelExecutionResult:
        """Execute one prepared turn with streamed internal events when available."""


class PydanticAIModelExecutor:
    """Execute prepared turns against a pydantic-ai model."""

    def __init__(self, model: Model | str) -> None:
        self._model = infer_model(model)

    async def execute(self, prepared_turn: PreparedModelTurn) -> ModelExecutionResult:
        messages = _request_messages(prepared_turn)

        model_response = await self._model.request(
            messages,
            cast(Any, prepared_turn.model_settings or None),
            prepared_turn.request_parameters,
        )
        return _normalize_model_response(model_response)

    async def execute_stream(
        self,
        prepared_turn: PreparedModelTurn,
        *,
        stream_translator: PydanticAIStreamTranslator,
        on_event: Callable[[ModelAdapterStreamEvent], None],
    ) -> ModelExecutionResult:
        messages = _request_messages(prepared_turn)

        try:
            async with self._model.request_stream(
                messages,
                cast(Any, prepared_turn.model_settings or None),
                prepared_turn.request_parameters,
            ) as streamed_response:
                async for event in streamed_response:
                    _emit_translated_events(
                        event,
                        stream_translator=stream_translator,
                        on_event=on_event,
                    )
                return _normalize_model_response(streamed_response.get())
        except AssertionError as exc:
            if "support streamed requests" not in str(exc):
                raise
            return await self.execute(prepared_turn)


def build_local_text_model_executor(model_name: str) -> PydanticAIModelExecutor:
    """Build a deterministic local executor for runtime bootstrap and tests."""

    def _respond(
        messages: list[ModelMessage],
        _agent_info: object,
    ) -> ModelResponse:
        user_prompt = _latest_user_prompt(messages)
        response_text = (
            "I received your request."
            if user_prompt is None
            else f"I received your request: {user_prompt}"
        )
        return ModelResponse(parts=[TextPart(content=response_text)])

    async def _stream_respond(
        messages: list[ModelMessage],
        _agent_info: object,
    ):
        user_prompt = _latest_user_prompt(messages)
        response_text = (
            "I received your request."
            if user_prompt is None
            else f"I received your request: {user_prompt}"
        )
        for chunk in _chunk_text(response_text):
            yield chunk

    return PydanticAIModelExecutor(
        FunctionModel(
            function=_respond,
            stream_function=_stream_respond,
            model_name=model_name,
        )
    )


def build_openai_model_executor(
    model_name: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> PydanticAIModelExecutor:
    """Build a real OpenAI-backed executor."""

    provider = OpenAIProvider(api_key=api_key, base_url=base_url)
    return PydanticAIModelExecutor(OpenAIChatModel(model_name, provider=provider))


def build_anthropic_model_executor(
    model_name: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> PydanticAIModelExecutor:
    """Build a real Anthropic-backed executor."""

    provider = AnthropicProvider(api_key=api_key, base_url=base_url)
    return PydanticAIModelExecutor(AnthropicModel(model_name, provider=provider))


def _normalize_model_response(model_response: ModelResponse) -> ModelExecutionResult:
    assistant_text = "".join(
        part.content for part in model_response.parts if isinstance(part, TextPart)
    )
    tool_calls = tuple(
        ModelToolCall(
            tool_name=part.tool_name,
            arguments=part.args,
            tool_call_id=part.tool_call_id,
        )
        for part in model_response.parts
        if isinstance(part, ToolCallPart)
    )
    if assistant_text == "" and not tool_calls:
        raise ValueError("model response did not contain assistant text or tool calls")

    usage = model_response.usage
    return ModelExecutionResult(
        assistant_text=assistant_text,
        tool_calls=tool_calls,
        model_response=model_response,
        input_tokens=usage.input_tokens or None,
        output_tokens=usage.output_tokens or None,
    )


def _latest_user_prompt(messages: list[ModelMessage]) -> str | None:
    for message in reversed(messages):
        if not isinstance(message, ModelRequest):
            continue
        for part in reversed(message.parts):
            if isinstance(part, UserPromptPart):
                content = part.content
                if isinstance(content, str):
                    return content
                return "".join(_user_content_text(item) for item in content)
    return None


def _user_content_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, TextContent):
        return content.content
    return ""


def _request_messages(prepared_turn: PreparedModelTurn) -> list[ModelMessage]:
    messages = list(prepared_turn.message_history)
    if prepared_turn.user_prompt is None:
        return messages

    timestamp = datetime.now(tz=UTC)
    messages.append(
        ModelRequest(
            parts=[
                UserPromptPart(
                    content=prepared_turn.user_prompt,
                    timestamp=timestamp,
                )
            ],
            timestamp=timestamp,
        )
    )
    return messages


def _emit_translated_events(
    event: ModelResponseStreamEvent,
    *,
    stream_translator: PydanticAIStreamTranslator,
    on_event: Callable[[ModelAdapterStreamEvent], None],
) -> None:
    for translated_event in stream_translator.translate(event):
        on_event(translated_event)


def _chunk_text(text: str) -> tuple[str, ...]:
    words = text.split()
    if len(words) < 2:
        return (text,)

    midpoint = max(1, len(words) // 2)
    leading = " ".join(words[:midpoint]).strip()
    trailing = " ".join(words[midpoint:]).strip()
    if not trailing:
        return (leading,)
    return (f"{leading} ", trailing)
