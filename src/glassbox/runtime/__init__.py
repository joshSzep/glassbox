"""Curated public runtime package surface for Glassbox."""

from glassbox.runtime.bus import EventBus
from glassbox.runtime.bus import EventBusStats
from glassbox.runtime.bus import EventBusSubscription
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.context import RuntimeInfrastructure
from glassbox.runtime.context import RuntimeRepositories
from glassbox.runtime.context import RuntimeServices


def __getattr__(name: str):
    if name in {"default_database_path", "open_runtime_context"}:
        from glassbox.runtime import bootstrap as _bootstrap

        return getattr(_bootstrap, name)
    raise AttributeError(f"module 'glassbox.runtime' has no attribute {name!r}")


__all__ = [
    "default_database_path",
    "EventBus",
    "EventBusStats",
    "EventBusSubscription",
    "open_runtime_context",
    "RuntimeContext",
    "RuntimeInfrastructure",
    "RuntimeRepositories",
    "RuntimeServices",
]
