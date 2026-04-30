"""Credential-readiness scoring for provider recommendations."""

from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.runtime.provider_recommendation_models import ProviderCredentialReadiness


def provider_credential_readiness(
    diagnostics: ProviderDiagnosticsReport,
) -> ProviderCredentialReadiness:
    """Score whether the selected provider has usable credentials."""

    if diagnostics.runtime_mode == "local":
        return ProviderCredentialReadiness.NOT_REQUIRED
    if diagnostics.state == "ready":
        return ProviderCredentialReadiness.READY
    if diagnostics.state in {"missing_credentials", "local_fallback"}:
        return ProviderCredentialReadiness.MISSING
    if diagnostics.state == "unsupported_model":
        return ProviderCredentialReadiness.UNSUPPORTED
    if diagnostics.state in {"invalid_workspace_profile", "invalid_provider_config"}:
        return ProviderCredentialReadiness.INVALID
    return ProviderCredentialReadiness.UNKNOWN
