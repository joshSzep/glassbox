"""Tests for provider failure recovery classification."""

from datetime import UTC
from datetime import datetime

from glassbox.core import ProviderRecoveryAction
from glassbox.core import ProviderRecoveryKind
from glassbox.llm import ModelProviderConfig
from glassbox.llm import PydanticAIModelAdapter
from glassbox.runtime.provider_recovery import classify_provider_failure


def test_provider_recovery_classifies_rate_limit_with_bounded_backoff() -> None:
    adapter = PydanticAIModelAdapter(
        ModelProviderConfig(provider="openai", model_name="gpt-5.4")
    )

    recovery = classify_provider_failure(
        RuntimeError("rate limit exceeded"),
        model_adapter=adapter,
        attempt=1,
        max_attempts=3,
        now=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
    )

    assert recovery is not None
    assert recovery.failure_kind == ProviderRecoveryKind.RATE_LIMIT
    assert recovery.action == ProviderRecoveryAction.RETRY_SCHEDULED
    assert recovery.retryable is True
    assert recovery.safe_to_continue is True
    assert recovery.backoff_seconds == 2
    assert recovery.next_retry_at == datetime(2026, 4, 30, 12, 0, 2, tzinfo=UTC)


def test_provider_recovery_stops_for_credential_change() -> None:
    adapter = PydanticAIModelAdapter(
        ModelProviderConfig(provider="anthropic", model_name="claude-sonnet")
    )

    recovery = classify_provider_failure(
        RuntimeError("unauthorized api key"),
        model_adapter=adapter,
    )

    assert recovery is not None
    assert recovery.failure_kind == ProviderRecoveryKind.CREDENTIAL_CHANGE
    assert recovery.action == ProviderRecoveryAction.STOPPED_CHECKPOINT_REQUIRED
    assert recovery.retryable is False
    assert recovery.safe_to_continue is False


def test_provider_recovery_ignores_local_model_failures() -> None:
    adapter = PydanticAIModelAdapter(ModelProviderConfig(model_name="local-dev"))

    recovery = classify_provider_failure(
        RuntimeError("local function model failed"),
        model_adapter=adapter,
    )

    assert recovery is None
