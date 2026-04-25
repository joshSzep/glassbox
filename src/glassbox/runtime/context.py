"""Typed runtime dependency containers for Glassbox."""

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

from glassbox.core.events import EventEnvelope
from glassbox.runtime.provider_config import RuntimeProviderConfig
from glassbox.runtime.transport import RuntimeEventTransport
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository
from glassbox.services import SessionService


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

    event_bus: RuntimeEventTransport[EventEnvelope]
    artifacts_root: Path
    provider_config: RuntimeProviderConfig = field(
        default_factory=RuntimeProviderConfig
    )

    @property
    def event_transport(self) -> RuntimeEventTransport[EventEnvelope]:
        """Transport-oriented alias over the compatibility event_bus field."""

        return self.event_bus


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    """Fully wired runtime dependency container for Glassbox entrypoints."""

    repositories: RuntimeRepositories
    services: RuntimeServices
    infrastructure: RuntimeInfrastructure
