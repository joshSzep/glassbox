"""Runtime wiring bootstrap for local Glassbox entrypoints."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from glassbox.core.models import SessionRecord
from glassbox.llm.adapters import ModelProviderConfig, PydanticAIModelAdapter
from glassbox.llm.executor import (
    build_anthropic_model_executor,
    build_local_text_model_executor,
    build_openai_model_executor,
)
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context import (
    RuntimeContext,
    RuntimeInfrastructure,
    RuntimeRepositories,
    RuntimeServices,
)
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.errors import SessionRuntimeFailure
from glassbox.runtime.logging import configure_runtime_logging
from glassbox.runtime.provider_config import (
    RuntimeProviderConfig,
    load_runtime_provider_config,
)
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.store import (
    FilesystemArtifactRepository,
    SQLiteSessionRepository,
    initialize_database,
    open_database,
)
from glassbox.tools import (
    ApprovalMode,
    ToolPolicyContext,
    ToolPolicyEngine,
    ToolRuntime,
    build_ask_user_tool_registry,
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
    configure_runtime_logging()
    event_bus = EventBus()
    provider_config = load_runtime_provider_config(cwd)
    session_repository = SQLiteSessionRepository(connection)
    artifact_repository = FilesystemArtifactRepository(connection, cwd)
    turn_engine = TurnEngine(
        session_repository,
        event_bus,
        TurnContextBuilder(session_repository),
        _build_model_adapter,
        _build_model_executor_factory(provider_config),
        _build_tool_runtime,
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


def _build_model_adapter(session: SessionRecord) -> PydanticAIModelAdapter:
    provider, model_name = _split_model_name(session.model_name)
    return PydanticAIModelAdapter(
        ModelProviderConfig(model_name=model_name, provider=provider)
    )


def _build_model_executor(session: SessionRecord):
    return build_local_text_model_executor(session.model_name)


def _build_model_executor_factory(provider_config: RuntimeProviderConfig):
    def build_model_executor(session: SessionRecord):
        provider, model_name = _split_model_name(session.model_name)
        if provider == "openai" and provider_config.openai.is_configured:
            return build_openai_model_executor(
                model_name,
                api_key=provider_config.openai.api_key,
                base_url=provider_config.openai.base_url,
            )
        if provider == "anthropic" and provider_config.anthropic.is_configured:
            return build_anthropic_model_executor(
                model_name,
                api_key=provider_config.anthropic.api_key,
                base_url=provider_config.anthropic.base_url,
            )
        return _build_model_executor(session)

    return build_model_executor


def _build_tool_runtime(session: SessionRecord) -> ToolRuntime:
    try:
        approval_mode = ApprovalMode(session.approval_mode)
    except ValueError as exc:
        raise SessionRuntimeFailure(
            f"invalid approval mode persisted for session: {session.approval_mode}",
            retryable=False,
        ) from exc

    return ToolRuntime(
        build_ask_user_tool_registry(session.cwd),
        ToolPolicyEngine(),
        ToolPolicyContext(
            workspace_root=session.cwd,
            approval_mode=approval_mode,
        ),
    )


def _split_model_name(model_name: str) -> tuple[str | None, str]:
    provider, separator, resolved_model_name = model_name.partition(":")
    if separator == "":
        return None, model_name
    return provider, resolved_model_name
