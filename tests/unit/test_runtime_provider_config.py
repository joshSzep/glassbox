"""Unit tests for runtime provider config resolution."""

from pathlib import Path

import pytest

from glassbox.runtime.provider_capability_matrix import ProviderCapabilityResult
from glassbox.runtime.provider_capability_matrix import build_provider_capability_matrix
from glassbox.runtime.provider_config import load_runtime_provider_config
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report


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


def test_provider_diagnostics_reports_local_mode(tmp_path: Path) -> None:
    report = build_provider_diagnostics_report(
        tmp_path,
        explicit_model_name="local-test-model",
        environ={},
    )

    assert report.state == "ready"
    assert report.selected_provider == "local"
    assert report.runtime_mode == "local"
    assert report.selected_model_source == "cli"


def test_provider_diagnostics_reports_openai_configuration(tmp_path: Path) -> None:
    report = build_provider_diagnostics_report(
        tmp_path,
        explicit_model_name="openai:gpt-5.4",
        environ={"OPENAI_API_KEY": "secret-openai"},
    )

    assert report.state == "ready"
    assert report.selected_provider == "openai"
    assert report.runtime_mode == "openai"
    openai = next(item for item in report.diagnostics if item.provider == "openai")
    assert openai.api_key_present is True
    assert openai.api_key_source == "process-env"


def test_provider_diagnostics_reports_anthropic_dotenv_configuration(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=secret-anthropic\n")

    report = build_provider_diagnostics_report(
        tmp_path,
        explicit_model_name="anthropic:claude-sonnet-4",
        environ={},
    )

    assert report.state == "ready"
    assert report.selected_provider == "anthropic"
    assert report.runtime_mode == "anthropic"
    anthropic = next(
        item for item in report.diagnostics if item.provider == "anthropic"
    )
    assert anthropic.api_key_present is True
    assert anthropic.api_key_source == "dotenv"


def test_provider_diagnostics_reports_missing_credentials_for_partial_config(
    tmp_path: Path,
) -> None:
    report = build_provider_diagnostics_report(
        tmp_path,
        explicit_model_name="openai:gpt-5.4",
        environ={"OPENAI_BASE_URL": "https://api.openai.example"},
    )

    assert report.state == "missing_credentials"
    assert report.runtime_mode == "unavailable"
    assert report.problems == ["missing OPENAI_API_KEY"]
    assert "OPENAI_API_KEY" in report.next_actions[0]


def test_provider_diagnostics_reports_unsupported_model_prefix(tmp_path: Path) -> None:
    report = build_provider_diagnostics_report(
        tmp_path,
        explicit_model_name="other:model",
        environ={},
    )

    assert report.state == "unsupported_model"
    assert report.selected_provider == "other"
    assert "unsupported model provider" in report.problems[0]


def test_provider_diagnostics_reports_invalid_workspace_profile(
    tmp_path: Path,
) -> None:
    (tmp_path / "glassbox.profile.json").write_text(
        '{"profile_version": 999}',
        encoding="utf-8",
    )

    report = build_provider_diagnostics_report(tmp_path, environ={})

    assert report.state == "invalid_workspace_profile"
    assert report.runtime_mode == "unavailable"
    assert "invalid workspace profile" in report.problems[0]


def test_provider_capability_matrix_serializes_redacted_evidence(
    tmp_path: Path,
) -> None:
    report = build_provider_diagnostics_report(
        tmp_path,
        explicit_model_name="openai:gpt-5.4",
        environ={"OPENAI_API_KEY": "secret-openai"},
    )

    results: dict[str, ProviderCapabilityResult] = {
        "streaming-text": "passed",
        "approval": "skipped",
    }
    matrix = build_provider_capability_matrix(
        report,
        scenario_ids=["streaming-text", "approval"],
        results=results,
        details={"streaming-text": "provider text turn completed"},
        skipped_reason="approval scenario not automated yet",
    )
    payload = matrix.model_dump(mode="json")

    assert payload["advisory"] is True
    assert payload["deterministic_release_blocking"] is False
    assert payload["provider"] == "openai"
    assert payload["entries"][0]["credential_state"] == "configured"
    assert payload["entries"][0]["streaming_support"] == "supported"
    assert payload["entries"][0]["redaction_status"] == "redacted"
    assert payload["entries"][1]["approval_behavior"] == "supported"
    assert payload["entries"][1]["skipped_reason"] == (
        "approval scenario not automated yet"
    )
    assert "secret-openai" not in str(payload)
