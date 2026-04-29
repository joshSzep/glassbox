"""Provider configuration diagnostics for CLI and canary workflows."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.runtime.bootstrap_provider import split_model_name
from glassbox.runtime.provider_config import load_runtime_provider_config
from glassbox.runtime.workspace_profile import DEFAULT_MODEL_NAME
from glassbox.runtime.workspace_profile import load_workspace_profile

type ProviderConfigSource = Literal["process-env", "dotenv", "unset"]
type ProviderCredentialSource = Literal[
    "process-env",
    "dotenv",
    "unset",
    "not_applicable",
]
type ProviderDiagnosticState = Literal[
    "ready",
    "local_fallback",
    "missing_credentials",
    "unsupported_model",
    "invalid_workspace_profile",
    "invalid_provider_config",
]
type ProviderBaseUrlPosture = Literal[
    "default",
    "custom",
    "not_applicable",
]
type ProviderCapabilityAssumption = Literal[
    "supported",
    "assumed",
    "unsupported",
    "unknown",
]
type ProviderScenarioPreflightStatus = Literal[
    "ready",
    "skip",
    "not_automated",
    "unsupported",
]

_SUPPORTED_PROVIDER_PREFIXES = {"openai", "anthropic"}
_ADVISORY_CANARY_SCENARIOS = (
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
)
_AUTOMATED_CANARY_SCENARIOS = {"streaming-text"}


class ProviderSecretDiagnostic(BaseModel):
    """Secret-preserving diagnostic for one provider family."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    api_key_present: bool
    api_key_source: ProviderConfigSource
    base_url_present: bool
    base_url_source: ProviderConfigSource
    missing_credentials: list[str]


class ProviderScenarioPreflight(BaseModel):
    """Offline expectation for one advisory canary scenario."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    status: ProviderScenarioPreflightStatus
    reason: str


class ProviderCapabilityPreflight(BaseModel):
    """Offline provider capability assumptions used before canary execution."""

    model_config = ConfigDict(extra="forbid")

    provider_family: str
    configured_model: str
    credential_source: ProviderCredentialSource
    base_url_posture: ProviderBaseUrlPosture
    streaming_assumption: ProviderCapabilityAssumption
    tool_call_assumption: ProviderCapabilityAssumption
    known_unsupported_scenarios: list[str]
    scenario_preflight: list[ProviderScenarioPreflight]


class ProviderDiagnosticsReport(BaseModel):
    """Operator-facing provider configuration diagnostic report."""

    model_config = ConfigDict(extra="forbid")

    state: ProviderDiagnosticState
    selected_model_name: str
    selected_model_source: str
    selected_provider: str
    runtime_mode: str
    diagnostics: list[ProviderSecretDiagnostic]
    capability_preflight: ProviderCapabilityPreflight
    problems: list[str]
    next_actions: list[str]
    onboarding_steps: list[str]


def build_provider_diagnostics_report(
    workspace_root: Path,
    *,
    explicit_model_name: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> ProviderDiagnosticsReport:
    """Build a redacted provider configuration diagnostic report."""

    try:
        selected_model_name, selected_model_source = _selected_model_name(
            workspace_root,
            explicit_model_name=explicit_model_name,
        )
    except ValueError as exc:
        return _invalid_report(
            state="invalid_workspace_profile",
            selected_model_name=explicit_model_name or DEFAULT_MODEL_NAME,
            selected_model_source="cli" if explicit_model_name else "unknown",
            problem=str(exc),
            next_action="fix glassbox.profile.json or override --model-name",
        )

    try:
        provider_config = load_runtime_provider_config(
            workspace_root,
            environ=environ,
        )
    except ValueError as exc:
        return _invalid_report(
            state="invalid_provider_config",
            selected_model_name=selected_model_name,
            selected_model_source=selected_model_source,
            problem=str(exc),
            next_action="fix the workspace .env provider configuration",
        )

    source_map = _provider_source_map(workspace_root, environ=environ)
    diagnostics = [
        _provider_diagnostic(
            "openai",
            provider_config.openai.api_key,
            provider_config.openai.base_url,
            api_key_source=source_map.get("OPENAI_API_KEY", "unset"),
            base_url_source=source_map.get("OPENAI_BASE_URL", "unset"),
        ),
        _provider_diagnostic(
            "anthropic",
            provider_config.anthropic.api_key,
            provider_config.anthropic.base_url,
            api_key_source=source_map.get("ANTHROPIC_API_KEY", "unset"),
            base_url_source=source_map.get("ANTHROPIC_BASE_URL", "unset"),
        ),
    ]
    provider, model_name = split_model_name(selected_model_name)
    selected_provider = provider or "local"
    problems: list[str] = []
    next_actions: list[str] = []

    if provider is not None and (
        provider not in _SUPPORTED_PROVIDER_PREFIXES or not model_name
    ):
        problems.append(
            f"unsupported model provider or empty model: {selected_model_name}"
        )
        next_actions.append(
            "choose an unprefixed local model, openai:MODEL, or anthropic:MODEL; "
            "then rerun provider diagnostics before starting a session"
        )
        state: ProviderDiagnosticState = "unsupported_model"
        runtime_mode = "unavailable"
    elif provider is None:
        state = "ready"
        runtime_mode = "local"
    else:
        selected_diagnostic = next(
            diagnostic for diagnostic in diagnostics if diagnostic.provider == provider
        )
        problems.extend(
            f"missing {credential}"
            for credential in selected_diagnostic.missing_credentials
        )
        if selected_diagnostic.missing_credentials:
            next_actions.append(
                f"set {provider.upper()}_API_KEY in the process environment or .env; "
                "otherwise remove the partial provider override"
            )
            state = "missing_credentials"
            runtime_mode = "unavailable"
        elif selected_diagnostic.api_key_present:
            state = "ready"
            runtime_mode = provider
        else:
            next_actions.append(
                f"set {provider.upper()}_API_KEY to use the real provider; "
                "otherwise use an unprefixed local model for deterministic fallback"
            )
            state = "local_fallback"
            runtime_mode = "local_fallback"

    capability_preflight = _capability_preflight(
        state=state,
        selected_model_name=selected_model_name,
        selected_provider=selected_provider,
        runtime_mode=runtime_mode,
        selected_diagnostic=next(
            (
                diagnostic
                for diagnostic in diagnostics
                if diagnostic.provider == selected_provider
            ),
            None,
        ),
    )

    return ProviderDiagnosticsReport(
        state=state,
        selected_model_name=selected_model_name,
        selected_model_source=selected_model_source,
        selected_provider=selected_provider,
        runtime_mode=runtime_mode,
        diagnostics=diagnostics,
        capability_preflight=capability_preflight,
        problems=problems,
        next_actions=next_actions,
        onboarding_steps=_onboarding_steps(
            selected_model_name=selected_model_name,
            selected_model_source=selected_model_source,
        ),
    )


def _onboarding_steps(
    *,
    selected_model_name: str,
    selected_model_source: str,
) -> list[str]:
    return [
        "Run provider diagnostics before the first live-provider session: "
        f"glassbox provider diagnostics --cwd . --model-name {selected_model_name}",
        "Keep provider API keys in the process environment or .env at --cwd; "
        "never store secrets in glassbox.profile.json.",
        "Put reviewable defaults in glassbox.profile.json, for example "
        f"runtime.model_name={selected_model_name} "
        f"(current source: {selected_model_source}).",
        "Start the first chat with glassbox session chat --cwd .; the terminal "
        "header and command palette show the paired dashboard URL.",
        "Validate the local checkout with glassbox eval run --profile commit-smoke "
        "--cwd . or the repository's documented pre-commit checks.",
    ]


def _selected_model_name(
    workspace_root: Path,
    *,
    explicit_model_name: str | None,
) -> tuple[str, str]:
    if explicit_model_name is not None:
        return explicit_model_name, "cli"
    profile = load_workspace_profile(workspace_root)
    if profile is not None and profile.runtime.model_name is not None:
        return profile.runtime.model_name, "workspace-profile"
    return DEFAULT_MODEL_NAME, "built-in"


def _provider_diagnostic(
    provider: str,
    api_key: str | None,
    base_url: str | None,
    *,
    api_key_source: ProviderConfigSource,
    base_url_source: ProviderConfigSource,
) -> ProviderSecretDiagnostic:
    missing_credentials: list[str] = []
    if api_key is None and base_url is not None:
        missing_credentials.append(f"{provider.upper()}_API_KEY")
    return ProviderSecretDiagnostic(
        provider=provider,
        api_key_present=api_key is not None,
        api_key_source=api_key_source,
        base_url_present=base_url is not None,
        base_url_source=base_url_source,
        missing_credentials=missing_credentials,
    )


def _provider_source_map(
    workspace_root: Path,
    *,
    environ: Mapping[str, str] | None,
) -> dict[str, ProviderConfigSource]:
    dotenv_keys = _dotenv_keys(workspace_root / ".env")
    env_keys = set((environ or os.environ).keys())
    sources: dict[str, ProviderConfigSource] = {}
    for key in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_BASE_URL",
    ):
        if key in env_keys:
            sources[key] = "process-env"
        elif key in dotenv_keys:
            sources[key] = "dotenv"
        else:
            sources[key] = "unset"
    return sources


def _dotenv_keys(dotenv_path: Path) -> set[str]:
    if not dotenv_path.exists():
        return set()
    keys: set[str] = set()
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, _value = line.split("=", 1)
        normalized_key = key.strip()
        if normalized_key:
            keys.add(normalized_key)
    return keys


def _capability_preflight(
    *,
    state: ProviderDiagnosticState,
    selected_model_name: str,
    selected_provider: str,
    runtime_mode: str,
    selected_diagnostic: ProviderSecretDiagnostic | None,
) -> ProviderCapabilityPreflight:
    provider_ready = state == "ready" and runtime_mode in _SUPPORTED_PROVIDER_PREFIXES
    local_mode = state == "ready" and runtime_mode == "local"
    known_unsupported = (
        list(_ADVISORY_CANARY_SCENARIOS)
        if local_mode or state == "unsupported_model"
        else []
    )
    return ProviderCapabilityPreflight(
        provider_family=selected_provider,
        configured_model=selected_model_name,
        credential_source=_credential_source(
            selected_diagnostic, local_mode=local_mode
        ),
        base_url_posture=_base_url_posture(selected_diagnostic, local_mode=local_mode),
        streaming_assumption=(
            "supported"
            if provider_ready
            else "unsupported"
            if local_mode
            else "unknown"
        ),
        tool_call_assumption=(
            "assumed" if provider_ready else "unsupported" if local_mode else "unknown"
        ),
        known_unsupported_scenarios=known_unsupported,
        scenario_preflight=[
            _scenario_preflight(
                scenario_id,
                state=state,
                provider_ready=provider_ready,
                local_mode=local_mode,
            )
            for scenario_id in _ADVISORY_CANARY_SCENARIOS
        ],
    )


def _credential_source(
    selected_diagnostic: ProviderSecretDiagnostic | None,
    *,
    local_mode: bool,
) -> ProviderCredentialSource:
    if local_mode:
        return "not_applicable"
    if selected_diagnostic is None:
        return "unset"
    return selected_diagnostic.api_key_source


def _base_url_posture(
    selected_diagnostic: ProviderSecretDiagnostic | None,
    *,
    local_mode: bool,
) -> ProviderBaseUrlPosture:
    if local_mode:
        return "not_applicable"
    if selected_diagnostic is None or not selected_diagnostic.base_url_present:
        return "default"
    return "custom"


def _scenario_preflight(
    scenario_id: str,
    *,
    state: ProviderDiagnosticState,
    provider_ready: bool,
    local_mode: bool,
) -> ProviderScenarioPreflight:
    if local_mode:
        return ProviderScenarioPreflight(
            scenario_id=scenario_id,
            status="unsupported",
            reason="selected model uses the deterministic local runtime",
        )
    if state == "unsupported_model":
        return ProviderScenarioPreflight(
            scenario_id=scenario_id,
            status="unsupported",
            reason="selected model provider is not supported for live canaries",
        )
    if not provider_ready:
        return ProviderScenarioPreflight(
            scenario_id=scenario_id,
            status="skip",
            reason=f"provider diagnostics state is {state}",
        )
    if scenario_id not in _AUTOMATED_CANARY_SCENARIOS:
        return ProviderScenarioPreflight(
            scenario_id=scenario_id,
            status="not_automated",
            reason="scenario is policy-defined but not automated yet",
        )
    return ProviderScenarioPreflight(
        scenario_id=scenario_id,
        status="ready",
        reason="credentials and provider family are ready for advisory execution",
    )


def _invalid_report(
    *,
    state: ProviderDiagnosticState,
    selected_model_name: str,
    selected_model_source: str,
    problem: str,
    next_action: str,
) -> ProviderDiagnosticsReport:
    return ProviderDiagnosticsReport(
        state=state,
        selected_model_name=selected_model_name,
        selected_model_source=selected_model_source,
        selected_provider="unknown",
        runtime_mode="unavailable",
        diagnostics=[],
        capability_preflight=_capability_preflight(
            state=state,
            selected_model_name=selected_model_name,
            selected_provider="unknown",
            runtime_mode="unavailable",
            selected_diagnostic=None,
        ),
        problems=[problem],
        next_actions=[next_action],
        onboarding_steps=_onboarding_steps(
            selected_model_name=selected_model_name,
            selected_model_source=selected_model_source,
        ),
    )
