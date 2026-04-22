"""Runtime-only provider configuration sourced from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProviderSecretConfig:
    """Resolved runtime config for one external model provider."""

    api_key: str | None = None
    base_url: str | None = None

    @property
    def is_configured(self) -> bool:
        """Return whether any runtime override is present for this provider."""

        return self.api_key is not None or self.base_url is not None


@dataclass(frozen=True, slots=True)
class RuntimeProviderConfig:
    """Resolved runtime-only provider configuration for supported providers."""

    openai: ProviderSecretConfig = ProviderSecretConfig()
    anthropic: ProviderSecretConfig = ProviderSecretConfig()


def load_runtime_provider_config(
    workspace_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> RuntimeProviderConfig:
    """Resolve provider config from process environment and optional .env file."""

    resolved_environ = dict(environ or os.environ)
    dotenv_values = _load_dotenv_file(workspace_root / ".env")
    merged_values = {**dotenv_values, **resolved_environ}
    return RuntimeProviderConfig(
        openai=ProviderSecretConfig(
            api_key=merged_values.get("OPENAI_API_KEY") or None,
            base_url=merged_values.get("OPENAI_BASE_URL") or None,
        ),
        anthropic=ProviderSecretConfig(
            api_key=merged_values.get("ANTHROPIC_API_KEY") or None,
            base_url=merged_values.get("ANTHROPIC_BASE_URL") or None,
        ),
    )


def _load_dotenv_file(dotenv_path: Path) -> dict[str, str]:
    if not dotenv_path.exists():
        return {}

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        dotenv_path.read_text().splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise ValueError(f"invalid .env line {line_number}: expected KEY=VALUE")

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError(f"invalid .env line {line_number}: empty key")
        values[normalized_key] = _strip_optional_quotes(value.strip())
    return values


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
