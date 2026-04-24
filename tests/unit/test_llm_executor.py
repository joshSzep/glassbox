"""Unit tests for the pydantic-ai executor layer."""

import asyncio

from pydantic_ai.messages import FinalResultEvent
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import PartDeltaEvent
from pydantic_ai.messages import PartStartEvent
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import TextPartDelta
from pydantic_ai.models import ModelRequestParameters

from glassbox.llm import ModelFinalResult
from glassbox.llm import ModelProviderConfig
from glassbox.llm import ModelTextDelta
from glassbox.llm import PreparedModelTurn
from glassbox.llm import PydanticAIModelAdapter
from glassbox.llm import PydanticAIModelExecutor
from glassbox.llm import executor as llm_executor


def test_build_openai_model_executor_uses_provider_runtime_config(
    monkeypatch,
) -> None:
    captured: dict[str, object | None] = {}
    fake_model = object()

    def fake_openai_provider(*, api_key=None, base_url=None):
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return "openai-provider"

    def fake_openai_chat_model(model_name, *, provider):
        captured["model_name"] = model_name
        captured["provider"] = provider
        return fake_model

    monkeypatch.setattr(llm_executor, "OpenAIProvider", fake_openai_provider)
    monkeypatch.setattr(llm_executor, "OpenAIChatModel", fake_openai_chat_model)
    monkeypatch.setattr(llm_executor, "infer_model", lambda model: model)

    executor = llm_executor.build_openai_model_executor(
        "gpt-5.4",
        api_key="openai-key",
        base_url="https://api.openai.example/v1",
    )

    assert isinstance(executor, PydanticAIModelExecutor)
    assert executor._model is fake_model
    assert captured == {
        "api_key": "openai-key",
        "base_url": "https://api.openai.example/v1",
        "model_name": "gpt-5.4",
        "provider": "openai-provider",
    }


def test_build_anthropic_model_executor_uses_provider_runtime_config(
    monkeypatch,
) -> None:
    captured: dict[str, object | None] = {}
    fake_model = object()

    def fake_anthropic_provider(*, api_key=None, base_url=None):
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return "anthropic-provider"

    def fake_anthropic_model(model_name, *, provider):
        captured["model_name"] = model_name
        captured["provider"] = provider
        return fake_model

    monkeypatch.setattr(llm_executor, "AnthropicProvider", fake_anthropic_provider)
    monkeypatch.setattr(llm_executor, "AnthropicModel", fake_anthropic_model)
    monkeypatch.setattr(llm_executor, "infer_model", lambda model: model)

    executor = llm_executor.build_anthropic_model_executor(
        "claude-sonnet-4",
        api_key="anthropic-key",
        base_url="https://anthropic.example",
    )

    assert isinstance(executor, PydanticAIModelExecutor)
    assert executor._model is fake_model
    assert captured == {
        "api_key": "anthropic-key",
        "base_url": "https://anthropic.example",
        "model_name": "claude-sonnet-4",
        "provider": "anthropic-provider",
    }


def test_execute_stream_emits_stream_events_without_network(monkeypatch) -> None:
    stream_model = _FakeStreamingModel()
    monkeypatch.setattr(llm_executor, "infer_model", lambda model: stream_model)
    executor = PydanticAIModelExecutor("openai:gpt-5.4")
    prepared_turn = _prepared_turn()
    stream_translator = PydanticAIModelAdapter(
        ModelProviderConfig(model_name="openai:gpt-5.4")
    ).new_stream_translator()
    streamed_events = []

    result = asyncio.run(
        executor.execute_stream(
            prepared_turn,
            stream_translator=stream_translator,
            on_event=streamed_events.append,
        )
    )

    assert result.assistant_text == "Provider stream complete."
    assert streamed_events == [
        ModelTextDelta(text="Provider stream "),
        ModelTextDelta(text="complete."),
        ModelFinalResult(tool_name=None, tool_call_id=None),
    ]
    assert stream_model.request_calls == 0
    assert stream_model.request_stream_calls == 1


def test_execute_stream_falls_back_to_execute_without_network(monkeypatch) -> None:
    fallback_model = _FakeFallbackModel()
    monkeypatch.setattr(llm_executor, "infer_model", lambda model: fallback_model)
    executor = PydanticAIModelExecutor("openai:gpt-5.4")
    prepared_turn = _prepared_turn()
    stream_translator = PydanticAIModelAdapter(
        ModelProviderConfig(model_name="openai:gpt-5.4")
    ).new_stream_translator()
    streamed_events = []

    result = asyncio.run(
        executor.execute_stream(
            prepared_turn,
            stream_translator=stream_translator,
            on_event=streamed_events.append,
        )
    )

    assert result.assistant_text == "Provider fallback complete."
    assert streamed_events == []
    assert fallback_model.request_calls == 1
    assert fallback_model.request_stream_calls == 1


def _prepared_turn() -> PreparedModelTurn:
    return PreparedModelTurn(
        model_name="openai:gpt-5.4",
        message_history=(),
        user_prompt="Inspect the repository",
        request_parameters=ModelRequestParameters(
            function_tools=[],
            allow_text_output=True,
            allow_image_output=False,
        ),
        model_settings={},
    )


class _FakeStreamingModel:
    def __init__(self) -> None:
        self.request_calls = 0
        self.request_stream_calls = 0

    async def request(self, *_args):
        self.request_calls += 1
        return ModelResponse(parts=[TextPart(content="unexpected fallback")])

    def request_stream(self, *_args):
        self.request_stream_calls += 1
        return _FakeStreamResponse(
            events=[
                PartStartEvent(
                    index=0,
                    part=TextPart(content="Provider stream "),
                    previous_part_kind=None,
                ),
                PartDeltaEvent(
                    index=0,
                    delta=TextPartDelta(content_delta="complete."),
                ),
                FinalResultEvent(tool_name=None, tool_call_id=None),
            ],
            response=ModelResponse(
                parts=[TextPart(content="Provider stream complete.")]
            ),
        )


class _FakeFallbackModel:
    def __init__(self) -> None:
        self.request_calls = 0
        self.request_stream_calls = 0

    async def request(self, *_args):
        self.request_calls += 1
        return ModelResponse(parts=[TextPart(content="Provider fallback complete.")])

    def request_stream(self, *_args):
        self.request_stream_calls += 1
        raise AssertionError("model does not support streamed requests")


class _FakeStreamResponse:
    def __init__(self, *, events, response: ModelResponse) -> None:
        self._events = list(events)
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._events):
            raise StopAsyncIteration
        event = self._events[self._index]
        self._index += 1
        return event

    def get(self) -> ModelResponse:
        return self._response
