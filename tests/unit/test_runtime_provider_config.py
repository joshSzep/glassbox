"""Unit tests for runtime provider config resolution."""

import json
from pathlib import Path

import pytest

from glassbox.core.types import AutonomyMode
from glassbox.runtime.provider_capability_matrix import ProviderCapabilityResult
from glassbox.runtime.provider_capability_matrix import build_provider_capability_matrix
from glassbox.runtime.provider_config import load_runtime_provider_config
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report
from glassbox.runtime.provider_recommendations import ProviderTaskKind
from glassbox.runtime.provider_recommendations import recommend_provider

AGENTIC_CANARY_SCENARIOS = [
    "streaming-text",
    "tool-call",
    "approval",
    "ask-user",
    "cancellation",
    "dashboard",
    "daemon-attach",
    "malformed-tool-call",
    "long-context-continuity",
    "retry-behavior",
    "rate-limit-handling",
    "tool-call-streaming",
    "cancellation-during-retry",
    "multi-step-plan-following",
    "verification-loop-interaction",
]


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
    assert report.capability_preflight.credential_source == "not_applicable"
    assert report.capability_preflight.streaming_assumption == "unsupported"
    assert report.capability_preflight.known_unsupported_scenarios == (
        AGENTIC_CANARY_SCENARIOS
    )
    assert any("dashboard URL" in step for step in report.onboarding_steps)
    assert any("glassbox.profile.json" in step for step in report.onboarding_steps)
    assert any("commit-smoke" in step for step in report.onboarding_steps)


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
    assert report.capability_preflight.provider_family == "openai"
    assert report.capability_preflight.credential_source == "process-env"
    assert report.capability_preflight.base_url_posture == "default"
    assert report.capability_preflight.streaming_assumption == "supported"
    assert report.capability_preflight.tool_call_assumption == "assumed"
    assert report.capability_preflight.scenario_preflight[0].scenario_id == (
        "streaming-text"
    )
    assert report.capability_preflight.scenario_preflight[0].status == "ready"
    assert report.capability_preflight.scenario_preflight[1].status == "not_automated"


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
    assert "process environment or .env" in report.next_actions[0]
    assert {item.status for item in report.capability_preflight.scenario_preflight} == {
        "skip"
    }


def test_provider_diagnostics_reports_unsupported_model_prefix(tmp_path: Path) -> None:
    report = build_provider_diagnostics_report(
        tmp_path,
        explicit_model_name="other:model",
        environ={},
    )

    assert report.state == "unsupported_model"
    assert report.selected_provider == "other"
    assert "unsupported model provider" in report.problems[0]
    assert "rerun provider diagnostics" in report.next_actions[0]
    assert {item.status for item in report.capability_preflight.scenario_preflight} == {
        "unsupported"
    }


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
    assert payload["entries"][0]["scenario_confidence"] == "observed"
    assert payload["entries"][0]["observed_limits"] == ["text streaming only"]
    assert payload["entries"][0]["redaction_status"] == "redacted"
    assert payload["entries"][1]["approval_behavior"] == "supported"
    assert payload["entries"][1]["scenario_confidence"] == "skipped"
    assert payload["entries"][1]["tool_call_reliability"] == "assumed"
    assert payload["entries"][1]["retry_posture"] == "not_applicable"
    assert payload["entries"][1]["skipped_reason"] == (
        "approval scenario not automated yet"
    )
    assert "secret-openai" not in str(payload)


def test_provider_capability_matrix_includes_agentic_workflow_fields(
    tmp_path: Path,
) -> None:
    report = build_provider_diagnostics_report(
        tmp_path,
        explicit_model_name="openai:gpt-5.4",
        environ={"OPENAI_API_KEY": "secret-openai"},
    )

    results: dict[str, ProviderCapabilityResult] = {
        "malformed-tool-call": "skipped",
        "retry-behavior": "skipped",
        "rate-limit-handling": "skipped",
        "tool-call-streaming": "skipped",
        "verification-loop-interaction": "skipped",
    }
    matrix = build_provider_capability_matrix(
        report,
        scenario_ids=[
            "malformed-tool-call",
            "retry-behavior",
            "rate-limit-handling",
            "tool-call-streaming",
            "verification-loop-interaction",
        ],
        results=results,
    )
    rows = {entry.scenario_id: entry for entry in matrix.entries}

    assert rows["malformed-tool-call"].tool_call_reliability == "unknown"
    assert rows["retry-behavior"].retry_posture == "not_evaluated"
    assert rows["rate-limit-handling"].retry_posture == "rate_limit_unknown"
    assert rows["tool-call-streaming"].streaming_support == "supported"
    assert rows["tool-call-streaming"].tool_call_support == "supported"
    assert rows["verification-loop-interaction"].tool_call_reliability == "assumed"
    assert all(row.scenario_confidence == "preflight" for row in rows.values())


def test_provider_recommendation_keeps_local_fallback_advisory(
    tmp_path: Path,
) -> None:
    recommendation = recommend_provider(
        tmp_path,
        task_kind=ProviderTaskKind.CODING,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
        model_name="local-test-model",
    )

    assert recommendation.advisory is True
    assert recommendation.auto_applied is False
    assert recommendation.posture == "local_fallback"
    assert recommendation.confidence == "low"
    assert recommendation.provider == "local"
    assert "reliable tool calls" in recommendation.required_capabilities
    assert any("local fallback" in warning for warning in recommendation.warnings)


def test_provider_recommendation_uses_retained_canary_evidence(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret-openai\n")
    output_dir = tmp_path / ".glassbox" / "provider-canary"
    output_dir.mkdir(parents=True)
    report = build_provider_diagnostics_report(
        tmp_path,
        explicit_model_name="openai:gpt-5.4",
        environ={"OPENAI_API_KEY": "secret-openai"},
    )
    results: dict[str, ProviderCapabilityResult] = {
        "streaming-text": "passed",
        "tool-call": "passed",
        "verification-loop-interaction": "skipped",
    }
    matrix = build_provider_capability_matrix(
        report,
        scenario_ids=AGENTIC_CANARY_SCENARIOS,
        results=results,
    )
    (output_dir / "provider-canary-summary.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-29T00:00:00+00:00",
                "advisory": True,
                "provider": "openai",
                "model_name": "openai:gpt-5.4",
                "diagnostics_state": "ready",
                "output_path": str(output_dir / "provider-canary-summary.json"),
                "scenario_definitions": [],
                "scenarios": [],
                "capability_matrix": matrix.model_dump(mode="json"),
                "skipped_reason": None,
                "next_actions": [],
            }
        ),
        encoding="utf-8",
    )

    recommendation = recommend_provider(
        tmp_path,
        task_kind=ProviderTaskKind.VERIFICATION,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
        model_name="openai:gpt-5.4",
    )

    assert recommendation.posture == "recommended"
    assert recommendation.confidence == "high"
    assert recommendation.evidence.relevant_passed == ["tool-call"]
    assert "verification-loop-interaction" in (
        recommendation.evidence.relevant_preflight
    )
