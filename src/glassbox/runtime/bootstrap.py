"""Runtime wiring bootstrap for local Glassbox entrypoints."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from glassbox.core.models import SessionRecord
from glassbox.llm.adapters import ModelProviderConfig, PydanticAIModelAdapter
from glassbox.llm.executor import build_local_text_model_executor
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context import (
    RuntimeContext,
    RuntimeInfrastructure,
    RuntimeRepositories,
    RuntimeServices,
)
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.store import (
    FilesystemArtifactRepository,
    SQLiteSessionRepository,
    initialize_database,
    open_database,
)


def default_database_path(cwd: Path) -> Path:
    """Return the default SQLite database path for a workspace root."""

    return cwd / ".glassbox" / "glassbox.sqlite3"


@contextmanager
def open_runtime_context(
    cwd: Path,
    *,
    db_path: Path | None = None,
) -> Iterator[RuntimeContext]:
    """Open the minimal runtime wiring needed by the CLI entrypoint."""

    resolved_cwd = cwd.resolve()
    resolved_db_path = (db_path or default_database_path(resolved_cwd)).resolve()
    connection = open_database(resolved_db_path)
    try:
        initialize_database(connection)
        yield _build_runtime_context(connection, resolved_cwd)
    finally:
        connection.close()


def _build_runtime_context(
    connection: sqlite3.Connection,
    cwd: Path,
) -> RuntimeContext:
    event_bus = EventBus()
    session_repository = SQLiteSessionRepository(connection)
    artifact_repository = FilesystemArtifactRepository(connection, cwd)
    turn_engine = TurnEngine(
        session_repository,
        event_bus,
        TurnContextBuilder(session_repository),
        _build_model_adapter,
        _build_model_executor,
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
        ),
    )


def _build_model_adapter(session: SessionRecord) -> PydanticAIModelAdapter:
    provider, model_name = _split_model_name(session.model_name)
    return PydanticAIModelAdapter(
        ModelProviderConfig(model_name=model_name, provider=provider)
    )


def _build_model_executor(session: SessionRecord):
    return build_local_text_model_executor(session.model_name)


def _split_model_name(model_name: str) -> tuple[str | None, str]:
    provider, separator, resolved_model_name = model_name.partition(":")
    if separator == "":
        return None, model_name
    return provider, resolved_model_name
