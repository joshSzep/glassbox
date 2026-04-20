"""Model execution helpers built on top of pydantic-ai models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextContent,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models import Model, infer_model
from pydantic_ai.models.function import FunctionModel

from glassbox.llm.adapters import PreparedModelTurn


@dataclass(frozen=True, slots=True)
class ModelExecutionResult:
    """Normalized result from one non-streamed model invocation."""

    assistant_text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class ModelExecutor(Protocol):
    """Stable interface for executing one prepared model turn."""

    async def execute(self, prepared_turn: PreparedModelTurn) -> ModelExecutionResult:
        """Execute one prepared turn and return a normalized result."""


class PydanticAIModelExecutor:
    """Execute prepared turns against a pydantic-ai model."""

    def __init__(self, model: Model | str) -> None:
        self._model = infer_model(model)

    async def execute(self, prepared_turn: PreparedModelTurn) -> ModelExecutionResult:
        messages = list(prepared_turn.message_history)
        if prepared_turn.user_prompt is not None:
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

        model_response = await self._model.request(
            messages,
            cast(Any, prepared_turn.model_settings or None),
            prepared_turn.request_parameters,
        )
        return _normalize_model_response(model_response)


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

    return PydanticAIModelExecutor(
        FunctionModel(function=_respond, model_name=model_name)
    )


def _normalize_model_response(model_response: ModelResponse) -> ModelExecutionResult:
    if any(isinstance(part, ToolCallPart) for part in model_response.parts):
        raise ValueError("tool calls are not supported by the turn engine yet")

    assistant_text = "".join(
        part.content for part in model_response.parts if isinstance(part, TextPart)
    )
    if assistant_text == "":
        raise ValueError("model response did not contain assistant text")

    usage = model_response.usage
    return ModelExecutionResult(
        assistant_text=assistant_text,
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
