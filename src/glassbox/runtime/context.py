"""Typed runtime dependency containers for Glassbox."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from glassbox.core.events import EventEnvelope
from glassbox.runtime.bus import EventBus
from glassbox.runtime.provider_config import RuntimeProviderConfig
from glassbox.services import ArtifactRepository, SessionRepository, SessionService


@dataclass(frozen=True, slots=True)
class RuntimeRepositories:
    """Repository dependencies required by runtime services."""

    sessions: SessionRepository
    artifacts: ArtifactRepository


@dataclass(frozen=True, slots=True)
class RuntimeServices:
    """Service dependencies exposed to application entrypoints."""

    session_service: SessionService


@dataclass(frozen=True, slots=True)
class RuntimeInfrastructure:
    """Shared runtime primitives that are not repositories or services."""

    event_bus: EventBus[EventEnvelope]
    artifacts_root: Path
    provider_config: RuntimeProviderConfig = field(
        default_factory=RuntimeProviderConfig
    )


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    """Fully wired runtime dependency container for Glassbox entrypoints."""

    repositories: RuntimeRepositories
    services: RuntimeServices
    infrastructure: RuntimeInfrastructure
