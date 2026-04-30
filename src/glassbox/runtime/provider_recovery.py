"""Provider failure classification and recovery evidence helpers."""

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from glassbox.core.events import ProviderRecoveryRecorded
from glassbox.core.types import ProviderRecoveryAction
from glassbox.core.types import ProviderRecoveryKind
from glassbox.llm import ModelAdapter


@dataclass(frozen=True, slots=True)
class ProviderFailureRecoveryDecision:
    """Provider failure posture ready to persist as canonical evidence."""

    provider: str
    model_name: str
    failure_kind: ProviderRecoveryKind
    action: ProviderRecoveryAction
    reason: str
    retryable: bool
    safe_to_continue: bool
    operator_next_action: str
    degraded: bool = False
    attempt: int = 1
    max_attempts: int | None = None
    backoff_seconds: int | None = None
    next_retry_at: datetime | None = None

    def to_event(self, *, turn_id) -> ProviderRecoveryRecorded:
        return ProviderRecoveryRecorded(
            provider=self.provider,
            model_name=self.model_name,
            failure_kind=self.failure_kind,
            action=self.action,
            reason=self.reason,
            retryable=self.retryable,
            safe_to_continue=self.safe_to_continue,
            operator_next_action=self.operator_next_action,
            degraded=self.degraded,
            turn_id=turn_id,
            attempt=self.attempt,
            max_attempts=self.max_attempts,
            backoff_seconds=self.backoff_seconds,
            next_retry_at=self.next_retry_at,
        )


def classify_provider_failure(
    error: Exception,
    *,
    model_adapter: ModelAdapter,
    attempt: int = 1,
    max_attempts: int = 1,
    now: datetime | None = None,
) -> ProviderFailureRecoveryDecision | None:
    """Classify a live provider failure without persisting secrets."""

    provider = model_adapter.config.provider or _provider_from_model_name(
        model_adapter.config.model_name
    )
    if provider is None:
        return None

    message = _safe_error_message(error)
    lowered = message.lower()
    if not _looks_like_provider_failure(lowered):
        return None

    retryable = _is_retryable(lowered)
    failure_kind = _failure_kind(lowered, retryable=retryable)
    exhausted = attempt >= max_attempts
    backoff_seconds = None if not retryable or exhausted else min(60, 2**attempt)
    next_retry_at = None
    if backoff_seconds is not None:
        current_time = now or datetime.now(UTC)
        next_retry_at = _aware(current_time) + timedelta(seconds=backoff_seconds)

    if retryable and not exhausted:
        action = ProviderRecoveryAction.RETRY_SCHEDULED
        safe_to_continue = True
        operator_next_action = (
            "Wait for the bounded provider retry, or pause the session before "
            "retrying with a fresh prompt"
        )
    elif failure_kind == ProviderRecoveryKind.DEGRADED_PROVIDER_POSTURE:
        action = ProviderRecoveryAction.DEGRADED
        safe_to_continue = False
        operator_next_action = (
            "Inspect provider diagnostics and retained canary evidence before "
            "continuing long-running work"
        )
    else:
        action = (
            ProviderRecoveryAction.RETRY_EXHAUSTED
            if retryable
            else ProviderRecoveryAction.STOPPED_CHECKPOINT_REQUIRED
        )
        safe_to_continue = False
        operator_next_action = (
            "Review the failure, create or inspect the latest checkpoint, then "
            "retry, switch provider, or fall back to local deterministic work"
        )

    return ProviderFailureRecoveryDecision(
        provider=provider,
        model_name=model_adapter.config.model_name,
        failure_kind=failure_kind,
        action=action,
        reason=message,
        retryable=retryable,
        safe_to_continue=safe_to_continue,
        operator_next_action=operator_next_action,
        degraded=failure_kind == ProviderRecoveryKind.DEGRADED_PROVIDER_POSTURE,
        attempt=attempt,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
        next_retry_at=next_retry_at,
    )


def _failure_kind(
    message: str,
    *,
    retryable: bool,
) -> ProviderRecoveryKind:
    if "rate limit" in message or "429" in message:
        return ProviderRecoveryKind.RATE_LIMIT
    if "stream" in message or "connection reset" in message:
        return ProviderRecoveryKind.LOST_STREAM
    if "tool call" in message or "tool_call" in message or "malformed" in message:
        return ProviderRecoveryKind.MALFORMED_TOOL_CALL
    if (
        "credential" in message
        or "api key" in message
        or "unauthorized" in message
        or "401" in message
    ):
        return ProviderRecoveryKind.CREDENTIAL_CHANGE
    if "degraded" in message or "canary" in message:
        return ProviderRecoveryKind.DEGRADED_PROVIDER_POSTURE
    if retryable:
        return ProviderRecoveryKind.RETRYABLE_ERROR
    return ProviderRecoveryKind.NON_RETRYABLE_ERROR


def _is_retryable(message: str) -> bool:
    retryable_markers = (
        "timeout",
        "timed out",
        "temporar",
        "rate limit",
        "429",
        "503",
        "502",
        "connection reset",
        "lost stream",
        "stream interrupted",
    )
    non_retryable_markers = ("api key", "credential", "unauthorized", "401")
    if any(marker in message for marker in non_retryable_markers):
        return False
    return any(marker in message for marker in retryable_markers)


def _looks_like_provider_failure(message: str) -> bool:
    provider_markers = (
        "api key",
        "bad request",
        "canary",
        "connection",
        "credential",
        "degraded",
        "model",
        "provider",
        "rate limit",
        "stream",
        "timeout",
        "timed out",
        "tool call",
        "tool_call",
        "unauthorized",
        "401",
        "429",
        "500",
        "502",
        "503",
    )
    return any(marker in message for marker in provider_markers)


def _provider_from_model_name(model_name: str) -> str | None:
    if ":" not in model_name:
        return None
    provider, _, _model = model_name.partition(":")
    return provider or None


def _safe_error_message(error: Exception) -> str:
    message = str(error).strip() or error.__class__.__name__
    if len(message) > 2000:
        return message[:1997] + "..."
    return message


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


__all__ = [
    "ProviderFailureRecoveryDecision",
    "classify_provider_failure",
]
