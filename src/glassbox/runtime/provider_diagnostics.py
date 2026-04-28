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
type ProviderDiagnosticState = Literal[
    "ready",
    "local_fallback",
    "missing_credentials",
    "unsupported_model",
    "invalid_workspace_profile",
    "invalid_provider_config",
]

_SUPPORTED_PROVIDER_PREFIXES = {"openai", "anthropic"}


class ProviderSecretDiagnostic(BaseModel):
    """Secret-preserving diagnostic for one provider family."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    api_key_present: bool
    api_key_source: ProviderConfigSource
    base_url_present: bool
    base_url_source: ProviderConfigSource
    missing_credentials: list[str]


class ProviderDiagnosticsReport(BaseModel):
    """Operator-facing provider configuration diagnostic report."""

    model_config = ConfigDict(extra="forbid")

    state: ProviderDiagnosticState
    selected_model_name: str
    selected_model_source: str
    selected_provider: str
    runtime_mode: str
    diagnostics: list[ProviderSecretDiagnostic]
    problems: list[str]
    next_actions: list[str]


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
            "choose an unprefixed local model, openai:MODEL, or anthropic:MODEL"
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
                f"set {provider.upper()}_API_KEY or remove partial overrides"
            )
            state = "missing_credentials"
            runtime_mode = "unavailable"
        elif selected_diagnostic.api_key_present:
            state = "ready"
            runtime_mode = provider
        else:
            next_actions.append(
                f"set {provider.upper()}_API_KEY to use the real provider; "
                "otherwise local fallback will run"
            )
            state = "local_fallback"
            runtime_mode = "local_fallback"

    return ProviderDiagnosticsReport(
        state=state,
        selected_model_name=selected_model_name,
        selected_model_source=selected_model_source,
        selected_provider=selected_provider,
        runtime_mode=runtime_mode,
        diagnostics=diagnostics,
        problems=problems,
        next_actions=next_actions,
    )


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
        problems=[problem],
        next_actions=[next_action],
    )
