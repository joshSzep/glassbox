"""Unit tests for runtime bootstrap model executor selection."""

from datetime import UTC, datetime
from pathlib import Path

from glassbox.core import SessionRecord, SessionStatus, new_session_id
from glassbox.runtime import bootstrap as runtime_bootstrap
from glassbox.runtime.provider_config import ProviderSecretConfig, RuntimeProviderConfig


def _session_record(model_name: str) -> SessionRecord:
    timestamp = datetime.now(UTC)
    return SessionRecord(
        session_id=new_session_id(),
        status=SessionStatus.IDLE,
        created_at=timestamp,
        updated_at=timestamp,
        cwd=Path("/tmp/glassbox"),
        model_name=model_name,
        approval_mode="confirm",
        last_sequence=0,
    )


def test_model_executor_factory_uses_openai_provider_builder_when_configured(
    monkeypatch,
) -> None:
    provider_config = RuntimeProviderConfig(
        openai=ProviderSecretConfig(api_key="openai-key")
    )
    captured: dict[str, str | None] = {}

    def fake_build_openai_model_executor(
        model_name: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        captured["model_name"] = model_name
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return "openai-executor"

    monkeypatch.setattr(
        runtime_bootstrap,
        "build_openai_model_executor",
        fake_build_openai_model_executor,
    )

    executor_factory = runtime_bootstrap._build_model_executor_factory(provider_config)

    executor = executor_factory(_session_record("openai:gpt-5.4"))

    assert executor == "openai-executor"
    assert captured == {
        "model_name": "gpt-5.4",
        "api_key": "openai-key",
        "base_url": None,
    }


def test_model_executor_factory_uses_anthropic_provider_builder_when_configured(
    monkeypatch,
) -> None:
    provider_config = RuntimeProviderConfig(
        anthropic=ProviderSecretConfig(base_url="https://anthropic.example")
    )
    captured: dict[str, str | None] = {}

    def fake_build_anthropic_model_executor(
        model_name: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        captured["model_name"] = model_name
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return "anthropic-executor"

    monkeypatch.setattr(
        runtime_bootstrap,
        "build_anthropic_model_executor",
        fake_build_anthropic_model_executor,
    )

    executor_factory = runtime_bootstrap._build_model_executor_factory(provider_config)

    executor = executor_factory(_session_record("anthropic:claude-sonnet-4"))

    assert executor == "anthropic-executor"
    assert captured == {
        "model_name": "claude-sonnet-4",
        "api_key": None,
        "base_url": "https://anthropic.example",
    }


def test_model_executor_factory_falls_back_to_local_executor_without_provider_config(
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}

    def fake_build_local_text_model_executor(model_name: str):
        captured["model_name"] = model_name
        return "local-executor"

    monkeypatch.setattr(
        runtime_bootstrap,
        "build_local_text_model_executor",
        fake_build_local_text_model_executor,
    )

    executor_factory = runtime_bootstrap._build_model_executor_factory(
        RuntimeProviderConfig()
    )

    executor = executor_factory(_session_record("openai:gpt-5.4"))

    assert executor == "local-executor"
    assert captured == {"model_name": "openai:gpt-5.4"}


def test_model_executor_factory_falls_back_to_local_executor_for_unknown_provider(
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}

    def fake_build_local_text_model_executor(model_name: str):
        captured["model_name"] = model_name
        return "local-executor"

    monkeypatch.setattr(
        runtime_bootstrap,
        "build_local_text_model_executor",
        fake_build_local_text_model_executor,
    )

    executor_factory = runtime_bootstrap._build_model_executor_factory(
        RuntimeProviderConfig(
            openai=ProviderSecretConfig(api_key="openai-key"),
            anthropic=ProviderSecretConfig(api_key="anthropic-key"),
        )
    )

    executor = executor_factory(_session_record("other:model"))

    assert executor == "local-executor"
    assert captured == {"model_name": "other:model"}
