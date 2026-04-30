"""Provider failure posture and retry-budget helpers."""

from collections.abc import Sequence

from glassbox.core.models import ProviderRecoveryRecord
from glassbox.runtime.provider_recommendation_models import ProviderBudgetImpact
from glassbox.runtime.provider_recommendation_models import ProviderFailurePosture


def provider_failure_posture(
    recovery_history: Sequence[ProviderRecoveryRecord],
) -> ProviderFailurePosture:
    """Fold provider recovery history into one advisory failure posture."""

    if not recovery_history:
        return ProviderFailurePosture(state="none")
    latest = recovery_history[0]
    repeated_count = sum(
        1 for record in recovery_history if record.provider == latest.provider
    )
    if repeated_count >= 2:
        state = "repeated_failure"
    elif latest.degraded:
        state = "degraded"
    elif latest.retryable and latest.safe_to_continue:
        state = "retryable"
    elif latest.safe_to_continue is False:
        state = "blocked"
    else:
        state = "unknown"
    return ProviderFailurePosture(
        state=state,
        provider=latest.provider,
        model_name=latest.model_name,
        failure_kind=latest.failure_kind.value,
        recovery_action=latest.action.value,
        retryable=latest.retryable,
        safe_to_continue=latest.safe_to_continue,
        degraded=latest.degraded,
        repeated_failure_count=repeated_count,
        latest_reason=latest.reason,
        operator_next_action=latest.operator_next_action,
    )


def provider_budget_impact(
    recovery_history: Sequence[ProviderRecoveryRecord],
) -> ProviderBudgetImpact:
    """Fold provider recovery history into retry budget impact."""

    if not recovery_history:
        return ProviderBudgetImpact()
    latest = recovery_history[0]
    warning = None
    if latest.backoff_seconds is not None:
        warning = "retry delay consumes provider retry budget and wall-clock budget"
    if latest.max_attempts is not None and latest.attempt >= latest.max_attempts:
        warning = "provider retry attempts are exhausted; pause before retrying"
    return ProviderBudgetImpact(
        retry_delay_seconds=latest.backoff_seconds,
        retry_attempt=latest.attempt,
        max_attempts=latest.max_attempts,
        next_retry_at=latest.next_retry_at.isoformat()
        if latest.next_retry_at
        else None,
        budget_warning=warning,
    )
