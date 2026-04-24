"""Runtime assembly helpers for local Glassbox entrypoints."""

import sqlite3
from pathlib import Path

from glassbox.runtime.bus import EventBus
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.context import RuntimeInfrastructure
from glassbox.runtime.context import RuntimeRepositories
from glassbox.runtime.context import RuntimeServices
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.provider_config import RuntimeProviderConfig
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository


def build_runtime_context(
    connection: sqlite3.Connection,
    cwd: Path,
    *,
    provider_config: RuntimeProviderConfig,
    model_adapter_builder,
    model_executor_factory_builder,
    tool_runtime_builder,
) -> RuntimeContext:
    """Assemble repositories, services, and infrastructure into RuntimeContext."""

    event_bus = EventBus()
    session_repository = SQLiteSessionRepository(connection)
    artifact_repository = FilesystemArtifactRepository(connection, cwd)
    turn_engine = TurnEngine(
        session_repository,
        event_bus,
        TurnContextBuilder(session_repository),
        model_adapter_builder,
        model_executor_factory_builder(provider_config),
        tool_runtime_builder,
        artifact_repository=artifact_repository,
    )
    session_service = SessionSupervisor(
        session_repository,
        event_bus,
        turn_engine=turn_engine,
    )
    return RuntimeContext(
        repositories=RuntimeRepositories(
            sessions=session_repository,
            artifacts=artifact_repository,
        ),
        services=RuntimeServices(session_service=session_service),
        infrastructure=RuntimeInfrastructure(
            event_bus=event_bus,
            artifacts_root=cwd,
            provider_config=provider_config,
        ),
    )
