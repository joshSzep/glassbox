"""Unit tests for runtime bootstrap model executor selection."""

import sqlite3
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

import pytest

from glassbox.core import SessionRecord
from glassbox.core import SessionStatus
from glassbox.core import new_session_id
from glassbox.runtime import bootstrap as runtime_bootstrap
from glassbox.runtime.errors import ProviderRuntimeConfigFailure
from glassbox.runtime.provider_config import ProviderSecretConfig
from glassbox.runtime.provider_config import RuntimeProviderConfig
from glassbox.runtime.supervisor import SessionSupervisor


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
        anthropic=ProviderSecretConfig(
            api_key="anthropic-key",
            base_url="https://anthropic.example",
        )
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
        "api_key": "anthropic-key",
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


def test_model_executor_factory_rejects_unsupported_provider() -> None:
    executor_factory = runtime_bootstrap._build_model_executor_factory(
        RuntimeProviderConfig()
    )

    with pytest.raises(
        ProviderRuntimeConfigFailure,
        match="unsupported model provider configured for session: other",
    ):
        executor_factory(_session_record("other:model"))


def test_model_executor_factory_rejects_missing_api_key_for_partial_config() -> None:
    executor_factory = runtime_bootstrap._build_model_executor_factory(
        RuntimeProviderConfig(
            openai=ProviderSecretConfig(base_url="https://api.openai.example")
        )
    )

    with pytest.raises(
        ProviderRuntimeConfigFailure,
        match="missing OpenAI API key for configured provider runtime",
    ):
        executor_factory(_session_record("openai:gpt-5.4"))


def test_model_executor_factory_redacts_secret_on_invalid_provider_base_url() -> None:
    secret = "super-secret-openai-key"
    executor_factory = runtime_bootstrap._build_model_executor_factory(
        RuntimeProviderConfig(
            openai=ProviderSecretConfig(api_key=secret, base_url="not-a-url")
        )
    )

    with pytest.raises(
        ProviderRuntimeConfigFailure,
        match="invalid OpenAI base URL runtime config",
    ) as exc_info:
        executor_factory(_session_record("openai:gpt-5.4"))

    assert secret not in str(exc_info.value)


def test_open_runtime_context_initializes_database_at_default_path(
    tmp_path: Path,
) -> None:
    with runtime_bootstrap.open_runtime_context(tmp_path) as runtime_context:
        repository = runtime_context.repositories.sessions

        assert runtime_bootstrap.default_database_path(tmp_path.resolve()).exists()
        assert repository.list_sessions() == []
        assert runtime_context.infrastructure.artifacts_root == tmp_path.resolve()


def test_build_runtime_context_keeps_bootstrap_executor_factory_patchable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = sqlite3.connect(":memory:")
    monkeypatch.setattr(
        runtime_bootstrap,
        "_build_model_executor",
        lambda session: f"patched:{session.model_name}",
    )

    try:
        runtime_context = runtime_bootstrap._build_runtime_context(connection, tmp_path)
        session_service = cast(
            SessionSupervisor,
            runtime_context.services.session_service,
        )
        assert session_service._turn_engine is not None
        build_executor = session_service._turn_engine._model_executor_factory
        executor = build_executor(_session_record("openai:gpt-5.4"))

        assert executor == "patched:openai:gpt-5.4"
    finally:
        connection.close()
