"""Runtime orchestration package for Glassbox."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from glassbox.runtime.bus import EventBus, EventBusStats, EventBusSubscription
from glassbox.runtime.context import (
    RuntimeContext,
    RuntimeInfrastructure,
    RuntimeRepositories,
    RuntimeServices,
)
from glassbox.runtime.context_builder import (
    PolicyContext,
    ToolSchema,
    TurnContext,
    TurnContextBuilder,
    format_tool_schemas_for_prompt,
    format_transcript_for_prompt,
    normalize_tool_schemas,
)
from glassbox.runtime.provider_config import (
    ProviderSecretConfig,
    RuntimeProviderConfig,
    load_runtime_provider_config,
)

if TYPE_CHECKING:
    from glassbox.runtime.replay import ReplayBundle, ReplayResult, ReplayRunner
    from glassbox.runtime.supervisor import SessionSupervisor
    from glassbox.runtime.turn_engine import TurnEngine


def __getattr__(name: str) -> Any:
    if name in {"default_database_path", "open_runtime_context"}:
        from glassbox.runtime import bootstrap as _bootstrap

        return getattr(_bootstrap, name)
    if name == "SessionSupervisor":
        from glassbox.runtime.supervisor import SessionSupervisor as _SessionSupervisor

        return _SessionSupervisor
    if name in {"ReplayBundle", "ReplayResult", "ReplayRunner"}:
        from glassbox.runtime import replay as _replay

        return getattr(_replay, name)
    if name == "TurnEngine":
        from glassbox.runtime.turn_engine import TurnEngine as _TurnEngine

        return _TurnEngine
    raise AttributeError(f"module 'glassbox.runtime' has no attribute {name!r}")


__all__ = [
    "default_database_path",
    "EventBus",
    "EventBusStats",
    "EventBusSubscription",
    "open_runtime_context",
    "PolicyContext",
    "ProviderSecretConfig",
    "ReplayBundle",
    "ReplayResult",
    "ReplayRunner",
    "RuntimeContext",
    "RuntimeInfrastructure",
    "RuntimeProviderConfig",
    "RuntimeRepositories",
    "RuntimeServices",
    "SessionSupervisor",
    "ToolSchema",
    "TurnEngine",
    "TurnContext",
    "TurnContextBuilder",
    "format_tool_schemas_for_prompt",
    "format_transcript_for_prompt",
    "load_runtime_provider_config",
    "normalize_tool_schemas",
]
