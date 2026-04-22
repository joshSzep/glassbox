"""Unit tests for runtime provider config resolution."""

from pathlib import Path

import pytest

from glassbox.runtime.provider_config import load_runtime_provider_config


def test_env_vars_override_dotenv_values(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=dotenv-openai\n"
        "OPENAI_BASE_URL=https://dotenv-openai.example\n"
        "ANTHROPIC_API_KEY=dotenv-anthropic\n"
    )

    config = load_runtime_provider_config(
        tmp_path,
        environ={
            "OPENAI_API_KEY": "env-openai",
            "ANTHROPIC_BASE_URL": "https://env-anthropic.example",
        },
    )

    assert config.openai.api_key == "env-openai"
    assert config.openai.base_url == "https://dotenv-openai.example"
    assert config.anthropic.api_key == "dotenv-anthropic"
    assert config.anthropic.base_url == "https://env-anthropic.example"


def test_load_runtime_provider_config_allows_missing_dotenv(tmp_path: Path) -> None:
    config = load_runtime_provider_config(tmp_path, environ={})

    assert config.openai.api_key is None
    assert config.openai.base_url is None
    assert config.anthropic.api_key is None
    assert config.anthropic.base_url is None


def test_load_runtime_provider_config_supports_export_and_quoted_values(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text(
        'export OPENAI_API_KEY=quoted-openai\nANTHROPIC_API_KEY="quoted-anthropic"\n'
    )

    config = load_runtime_provider_config(tmp_path, environ={})

    assert config.openai.api_key == "quoted-openai"
    assert config.anthropic.api_key == "quoted-anthropic"


def test_load_runtime_provider_config_ignores_comments_and_blank_lines(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text(
        "# comment\n\nOPENAI_API_KEY=dotenv-openai\n   # another comment\n"
    )

    config = load_runtime_provider_config(tmp_path, environ={})

    assert config.openai.api_key == "dotenv-openai"


def test_load_runtime_provider_config_rejects_malformed_dotenv(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("NOT_A_VALID_LINE\n")

    with pytest.raises(ValueError, match=r"invalid \.env line 1"):
        load_runtime_provider_config(tmp_path, environ={})
