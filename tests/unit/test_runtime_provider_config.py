"""Unit tests for runtime provider config resolution."""

import json
import os
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

from glassbox.core import new_session_id
from glassbox.core import new_turn_id
from glassbox.core.models import ProviderRecoveryRecord
from glassbox.core.types import AutonomyMode
from glassbox.core.types import ProviderRecoveryAction
from glassbox.core.types import ProviderRecoveryKind
from glassbox.runtime.provider_canary import load_provider_canary_evidence
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
    assert recommendation.recommended_action == "local_fallback"
    assert recommendation.failure_posture.state == "none"
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

    assert recommendation.posture == "usable"
    assert recommendation.recommended_action == "continue"
    assert recommendation.confidence == "medium"
    assert recommendation.capability_fit == "partial"
    assert recommendation.risk_posture == "medium"
    assert recommendation.evidence_freshness == "fresh"
    assert recommendation.credential_readiness == "ready"
    assert recommendation.evidence.relevant_passed == ["streaming-text", "tool-call"]
    assert "verification-loop-interaction" in (
        recommendation.evidence.relevant_preflight
    )
    assert any("preflight-only" in unknown for unknown in recommendation.unknowns)


def test_provider_recommendation_reports_missing_credentials(
    tmp_path: Path,
) -> None:
    recommendation = recommend_provider(
        tmp_path,
        task_kind=ProviderTaskKind.CODING,
        autonomy_mode=AutonomyMode.EDIT_SAFE,
        model_name="openai:gpt-5.4",
    )

    assert recommendation.posture == "risky"
    assert recommendation.confidence == "low"
    assert recommendation.capability_fit == "insufficient"
    assert recommendation.risk_posture == "high"
    assert recommendation.credential_readiness == "missing"
    assert recommendation.recommended_action == "fix_credentials"
    assert recommendation.evidence_freshness == "missing"
    assert any("local_fallback" in unknown for unknown in recommendation.unknowns)


def test_provider_recommendation_reports_unknown_model(
    tmp_path: Path,
) -> None:
    recommendation = recommend_provider(
        tmp_path,
        task_kind=ProviderTaskKind.INSPECTION,
        autonomy_mode=AutonomyMode.INSPECT,
        model_name="other:model",
    )

    assert recommendation.posture == "risky"
    assert recommendation.confidence == "low"
    assert recommendation.capability_fit == "insufficient"
    assert recommendation.risk_posture == "high"
    assert recommendation.credential_readiness == "unsupported"
    assert recommendation.recommended_action == "local_fallback"
    assert any("unsupported_model" in unknown for unknown in recommendation.unknowns)


def test_provider_recommendation_degrades_stale_evidence(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret-openai\n")
    summary_path = _write_provider_canary_summary(
        tmp_path,
        model_name="openai:gpt-5.4",
        environ={"OPENAI_API_KEY": "secret-openai"},
        results={scenario_id: "passed" for scenario_id in AGENTIC_CANARY_SCENARIOS},
    )
    old_mtime = 1_700_000_000
    os.utime(summary_path, (old_mtime, old_mtime))

    recommendation = recommend_provider(
        tmp_path,
        task_kind=ProviderTaskKind.CODING,
        autonomy_mode=AutonomyMode.EDIT_SAFE,
        model_name="openai:gpt-5.4",
    )

    assert recommendation.posture == "risky"
    assert recommendation.confidence == "low"
    assert recommendation.risk_posture == "high"
    assert recommendation.evidence_freshness == "stale"
    assert recommendation.recommended_action == "refresh_evidence"
    assert any("freshness is stale" in warning for warning in recommendation.warnings)


def test_provider_recommendation_switches_after_repeated_provider_failure(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret-openai\n")
    now = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)
    history = [
        _provider_recovery_record(
            reason="stream interrupted after retry budget",
            failure_kind=ProviderRecoveryKind.LOST_STREAM,
            action=ProviderRecoveryAction.RETRY_EXHAUSTED,
            safe_to_continue=False,
            retryable=True,
            sequence=5,
            created_at=now,
        ),
        _provider_recovery_record(
            reason="rate limit exceeded",
            failure_kind=ProviderRecoveryKind.RATE_LIMIT,
            action=ProviderRecoveryAction.RETRY_SCHEDULED,
            safe_to_continue=True,
            retryable=True,
            sequence=4,
            created_at=now,
            backoff_seconds=4,
        ),
    ]

    recommendation = recommend_provider(
        tmp_path,
        task_kind=ProviderTaskKind.CODING,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
        model_name="openai:gpt-5.4",
        provider_recovery_history=history,
    )

    assert recommendation.recommended_action == "switch_provider"
    assert recommendation.failure_posture.state == "repeated_failure"
    assert recommendation.failure_posture.repeated_failure_count == 2
    assert recommendation.risk_posture == "high"
    assert any("provider switch" in action for action in recommendation.next_actions)


def test_provider_recommendation_retries_fresh_retryable_failure(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret-openai\n")
    history = [
        _provider_recovery_record(
            reason="rate limit exceeded",
            failure_kind=ProviderRecoveryKind.RATE_LIMIT,
            action=ProviderRecoveryAction.RETRY_SCHEDULED,
            safe_to_continue=True,
            retryable=True,
            sequence=5,
            created_at=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
            backoff_seconds=4,
        ),
    ]

    recommendation = recommend_provider(
        tmp_path,
        task_kind=ProviderTaskKind.CODING,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
        model_name="openai:gpt-5.4",
        provider_recovery_history=history,
    )

    assert recommendation.recommended_action == "retry"
    assert recommendation.failure_posture.state == "retryable"
    assert recommendation.budget_impact.retry_delay_seconds == 4
    assert recommendation.risk_posture == "medium"


def test_provider_recommendation_degrades_provider_mismatch(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=secret-anthropic\n")
    _write_provider_canary_summary(
        tmp_path,
        model_name="openai:gpt-5.4",
        environ={"OPENAI_API_KEY": "secret-openai"},
        results={scenario_id: "passed" for scenario_id in AGENTIC_CANARY_SCENARIOS},
    )

    recommendation = recommend_provider(
        tmp_path,
        task_kind=ProviderTaskKind.CODING,
        autonomy_mode=AutonomyMode.EDIT_SAFE,
        model_name="anthropic:claude-sonnet-4",
    )

    assert recommendation.posture == "risky"
    assert recommendation.confidence == "low"
    assert recommendation.capability_fit == "unknown"
    assert recommendation.risk_posture == "high"
    assert recommendation.credential_readiness == "ready"
    assert recommendation.evidence.model_identity_matches_config is False
    assert any("different model" in warning for warning in recommendation.warnings)


def test_provider_canary_evidence_reports_stale_retained_summary(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / ".glassbox" / "provider-canary"
    output_dir.mkdir(parents=True)
    summary_path = output_dir / "provider-canary-summary.json"
    report = build_provider_diagnostics_report(
        tmp_path,
        explicit_model_name="openai:gpt-5.4",
        environ={"OPENAI_API_KEY": "secret-openai"},
    )
    results: dict[str, ProviderCapabilityResult] = {
        scenario_id: "passed" for scenario_id in AGENTIC_CANARY_SCENARIOS
    }
    matrix = build_provider_capability_matrix(
        report,
        scenario_ids=AGENTIC_CANARY_SCENARIOS,
        results=results,
    )
    summary_path.write_text(
        json.dumps(
            {
                "schema_version": "provider-canary-summary.v1",
                "generated_at": "2026-04-29T00:00:00+00:00",
                "advisory": True,
                "provider": "openai",
                "model_name": "openai:gpt-5.4",
                "diagnostics_state": "ready",
                "output_path": str(summary_path),
                "scenario_definitions": [],
                "scenarios": [
                    {
                        "scenario_id": scenario_id,
                        "outcome": "passed",
                        "detail": "test evidence",
                        "automation_status": "automated",
                    }
                    for scenario_id in AGENTIC_CANARY_SCENARIOS
                ],
                "capability_matrix": matrix.model_dump(mode="json"),
                "skipped_reason": None,
                "next_actions": [],
            }
        ),
        encoding="utf-8",
    )
    old_mtime = 1_700_000_000
    os.utime(summary_path, (old_mtime, old_mtime))

    evidence = load_provider_canary_evidence(
        tmp_path,
        expected_model_name="openai:gpt-5.4",
    )

    assert evidence.latest_status == "passed"
    assert evidence.freshness_status == "stale"
    assert evidence.stale is True
    assert evidence.identity_matches_current_config is True
    assert any("provider canary run" in action for action in evidence.next_actions)


def test_provider_canary_evidence_reports_incompatible_retained_summary(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / ".glassbox" / "provider-canary"
    output_dir.mkdir(parents=True)
    summary_path = output_dir / "provider-canary-summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "schema_version": "provider-canary-summary.v0",
                "generated_at": "2026-04-29T00:00:00+00:00",
                "advisory": True,
                "provider": "openai",
                "model_name": "openai:gpt-5.4",
                "diagnostics_state": "ready",
                "output_path": str(summary_path),
                "scenarios": [],
                "capability_matrix": {"entries": [{"scenario_id": "tool-call"}]},
                "next_actions": [],
            }
        ),
        encoding="utf-8",
    )

    evidence = load_provider_canary_evidence(
        tmp_path,
        expected_model_name="openai:gpt-5.4",
    )

    assert evidence.latest_status == "warning"
    assert evidence.freshness_status == "incompatible"
    assert evidence.schema_version == "provider-canary-summary.v0"
    assert evidence.matrix_entry_count == 1
    assert evidence.missing_scenarios == AGENTIC_CANARY_SCENARIOS
    assert any("stale or incompatible" in action for action in evidence.next_actions)


def _provider_recovery_record(
    *,
    reason: str,
    failure_kind: ProviderRecoveryKind,
    action: ProviderRecoveryAction,
    safe_to_continue: bool,
    retryable: bool,
    sequence: int,
    created_at: datetime,
    backoff_seconds: int | None = None,
) -> ProviderRecoveryRecord:
    return ProviderRecoveryRecord(
        session_id=new_session_id(),
        turn_id=new_turn_id(),
        provider="openai",
        model_name="gpt-5.4",
        failure_kind=failure_kind,
        action=action,
        reason=reason,
        retryable=retryable,
        safe_to_continue=safe_to_continue,
        operator_next_action="inspect provider recovery",
        attempt=1,
        max_attempts=3,
        backoff_seconds=backoff_seconds,
        created_at=created_at,
        last_sequence=sequence,
    )


def _write_provider_canary_summary(
    workspace_root: Path,
    *,
    model_name: str,
    environ: dict[str, str],
    results: dict[str, ProviderCapabilityResult],
) -> Path:
    output_dir = workspace_root / ".glassbox" / "provider-canary"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "provider-canary-summary.json"
    report = build_provider_diagnostics_report(
        workspace_root,
        explicit_model_name=model_name,
        environ=environ,
    )
    matrix = build_provider_capability_matrix(
        report,
        scenario_ids=AGENTIC_CANARY_SCENARIOS,
        results=results,
    )
    summary_path.write_text(
        json.dumps(
            {
                "schema_version": "provider-canary-summary.v1",
                "generated_at": "2026-04-29T00:00:00+00:00",
                "advisory": True,
                "provider": report.selected_provider,
                "model_name": model_name,
                "diagnostics_state": report.state,
                "output_path": str(summary_path),
                "scenario_definitions": [],
                "scenarios": [
                    {
                        "scenario_id": scenario_id,
                        "outcome": result,
                        "detail": "test evidence",
                        "automation_status": "automated",
                    }
                    for scenario_id, result in results.items()
                ],
                "capability_matrix": matrix.model_dump(mode="json"),
                "skipped_reason": None,
                "next_actions": [],
            }
        ),
        encoding="utf-8",
    )
    return summary_path
