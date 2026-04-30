"""Recommended action and next-step helpers for provider recommendations."""

from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.runtime.provider_recommendation_models import ProviderCredentialReadiness
from glassbox.runtime.provider_recommendation_models import ProviderFailurePosture
from glassbox.runtime.provider_recommendation_models import (
    ProviderRecommendationEvidence,
)
from glassbox.runtime.provider_recommendation_models import ProviderRecommendedAction


def provider_recommended_action(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    failure_posture: ProviderFailurePosture,
    credential_readiness: ProviderCredentialReadiness,
) -> ProviderRecommendedAction:
    """Select the concrete advisory action for the provider recommendation."""

    if credential_readiness == ProviderCredentialReadiness.MISSING:
        return ProviderRecommendedAction.FIX_CREDENTIALS
    if diagnostics.state == "unsupported_model":
        return ProviderRecommendedAction.LOCAL_FALLBACK
    if diagnostics.runtime_mode == "local":
        return ProviderRecommendedAction.LOCAL_FALLBACK
    if failure_posture.state == "retryable":
        return ProviderRecommendedAction.RETRY
    if failure_posture.state in {"degraded", "repeated_failure"}:
        return ProviderRecommendedAction.SWITCH_PROVIDER
    if failure_posture.state == "blocked":
        return ProviderRecommendedAction.PAUSE
    if evidence.freshness_status in {"missing", "stale", "incompatible", "failed"}:
        return ProviderRecommendedAction.REFRESH_EVIDENCE
    return ProviderRecommendedAction.CONTINUE


def provider_action_next_steps(
    action: ProviderRecommendedAction,
    failure_posture: ProviderFailurePosture,
) -> list[str]:
    """Return stable operator next steps for the selected advisory action."""

    if action == ProviderRecommendedAction.RETRY:
        return [
            "retry the provider call only within the configured autonomy "
            "and retry budget"
        ]
    if action == ProviderRecommendedAction.PAUSE:
        return [
            "pause long-running work and inspect the latest checkpoint before retrying"
        ]
    if action == ProviderRecommendedAction.SWITCH_PROVIDER:
        return [
            "pause work, run provider diagnostics, then choose an operator-approved "
            "provider switch or model switch"
        ]
    if action == ProviderRecommendedAction.LOCAL_FALLBACK:
        return [
            "use an unprefixed local model only for deterministic local work "
            "that does not require live-provider capabilities"
        ]
    if action == ProviderRecommendedAction.FIX_CREDENTIALS:
        return ["fix provider credentials, then rerun provider diagnostics"]
    if action == ProviderRecommendedAction.REFRESH_EVIDENCE:
        return ["refresh provider canary evidence before relying on provider advice"]
    if failure_posture.operator_next_action is not None:
        return [failure_posture.operator_next_action]
    return ["continue with the selected provider; advice remains advisory"]
