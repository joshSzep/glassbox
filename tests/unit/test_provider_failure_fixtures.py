"""Deterministic provider failure fixture coverage."""

from pathlib import Path

import pytest

from glassbox.core.types import ProviderRecoveryAction
from glassbox.core.types import ProviderRecoveryKind
from glassbox.runtime.provider_failure_fixtures import provider_failure_fixture_ids
from glassbox.runtime.provider_failure_fixtures import run_provider_failure_fixture


def test_provider_failure_fixture_inventory_matches_v11_scope() -> None:
    assert provider_failure_fixture_ids() == [
        "retryable-provider-error",
        "non-retryable-provider-error",
        "lost-stream",
        "malformed-tool-call",
        "stale-canary-evidence",
        "model-fallback-recommendation",
    ]


@pytest.mark.parametrize(
    ("fixture_id", "failure_kind", "action", "recommended_action", "posture"),
    [
        (
            "retryable-provider-error",
            ProviderRecoveryKind.RETRYABLE_ERROR,
            ProviderRecoveryAction.RETRY_SCHEDULED,
            "retry",
            "retryable",
        ),
        (
            "non-retryable-provider-error",
            ProviderRecoveryKind.NON_RETRYABLE_ERROR,
            ProviderRecoveryAction.STOPPED_CHECKPOINT_REQUIRED,
            "pause",
            "blocked",
        ),
        (
            "lost-stream",
            ProviderRecoveryKind.LOST_STREAM,
            ProviderRecoveryAction.RETRY_EXHAUSTED,
            "pause",
            "blocked",
        ),
        (
            "malformed-tool-call",
            ProviderRecoveryKind.MALFORMED_TOOL_CALL,
            ProviderRecoveryAction.STOPPED_CHECKPOINT_REQUIRED,
            "pause",
            "blocked",
        ),
    ],
)
def test_provider_failure_fixtures_build_recovery_history(
    tmp_path: Path,
    fixture_id: str,
    failure_kind: ProviderRecoveryKind,
    action: ProviderRecoveryAction,
    recommended_action: str,
    posture: str,
) -> None:
    result = run_provider_failure_fixture(tmp_path / fixture_id, fixture_id)

    assert result.advisory is True
    assert result.deterministic_release_blocking is False
    assert result.recommendation.advisory is True
    assert result.recommendation.auto_applied is False
    assert len(result.recovery_history) == 1
    [record] = result.recovery_history
    assert record.failure_kind == failure_kind
    assert record.action == action
    assert result.recommendation.failure_posture.state == posture
    assert result.recommendation.recommended_action == recommended_action
    assert result.recommendation.risk_posture in {"medium", "high"}
    assert result.recommendation.next_actions


def test_stale_canary_fixture_recommends_refresh_without_live_credentials(
    tmp_path: Path,
) -> None:
    result = run_provider_failure_fixture(
        tmp_path / "stale-canary",
        "stale-canary-evidence",
    )

    assert result.recovery_history == []
    assert len(result.retained_artifacts) == 1
    assert Path(result.retained_artifacts[0]).exists()
    assert result.recommendation.evidence_freshness == "stale"
    assert result.recommendation.recommended_action == "refresh_evidence"
    assert result.recommendation.posture == "risky"
    assert any(
        "evidence is stale" in warning for warning in result.recommendation.warnings
    )


def test_model_fallback_fixture_is_visible_advice_not_mutation(tmp_path: Path) -> None:
    result = run_provider_failure_fixture(
        tmp_path / "model-fallback",
        "model-fallback-recommendation",
    )

    assert result.recovery_history == []
    assert result.recommendation.recommended_action == "local_fallback"
    assert result.recommendation.auto_applied is False
    assert result.recommendation.posture == "risky"
    assert result.recommendation.credential_readiness == "unsupported"
    assert any("local model" in action for action in result.recommendation.next_actions)


def test_unknown_provider_failure_fixture_names_available_ids(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="retryable-provider-error"):
        run_provider_failure_fixture(tmp_path, "missing-fixture")
