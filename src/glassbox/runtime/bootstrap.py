"""Runtime wiring bootstrap for local Glassbox entrypoints."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from glassbox.core.models import SessionRecord
from glassbox.llm.executor import build_anthropic_model_executor
from glassbox.llm.executor import build_local_text_model_executor
from glassbox.llm.executor import build_openai_model_executor
from glassbox.runtime.bootstrap_assembly import build_runtime_context
from glassbox.runtime.bootstrap_provider import build_model_adapter
from glassbox.runtime.bootstrap_provider import build_model_executor_factory
from glassbox.runtime.bootstrap_storage import (
    default_database_path as storage_default_database_path,
)
from glassbox.runtime.bootstrap_storage import open_initialized_runtime_database
from glassbox.runtime.bootstrap_storage import resolve_runtime_storage_paths
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.errors import SessionRuntimeFailure
from glassbox.runtime.logging import configure_runtime_logging
from glassbox.runtime.provider_config import RuntimeProviderConfig
from glassbox.runtime.provider_config import load_runtime_provider_config
from glassbox.tools import ApprovalMode
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import ToolRuntime
from glassbox.tools import build_ask_user_tool_registry


def default_database_path(cwd: Path) -> Path:
    """Return the default SQLite database path for a workspace root."""

    return storage_default_database_path(cwd)


@contextmanager
def open_runtime_context(
    cwd: Path,
    *,
    db_path: Path | None = None,
) -> Iterator[RuntimeContext]:
    """Open the minimal runtime wiring needed by the CLI entrypoint."""

    storage_paths = resolve_runtime_storage_paths(cwd, db_path=db_path)
    connection = open_initialized_runtime_database(storage_paths)
    try:
        yield _build_runtime_context(connection, storage_paths.workspace_root)
    finally:
        connection.close()


def _build_runtime_context(
    connection: sqlite3.Connection,
    cwd: Path,
) -> RuntimeContext:
    configure_runtime_logging()
    provider_config = load_runtime_provider_config(cwd)
    return build_runtime_context(
        connection,
        cwd,
        provider_config=provider_config,
        model_adapter_builder=_build_model_adapter,
        model_executor_factory_builder=_build_model_executor_factory,
        tool_runtime_builder=_build_tool_runtime,
    )


def _build_model_adapter(session: SessionRecord):
    return build_model_adapter(session)


def _build_model_executor(session: SessionRecord):
    return build_local_text_model_executor(session.model_name)


def _build_model_executor_factory(provider_config: RuntimeProviderConfig):
    return build_model_executor_factory(
        provider_config,
        local_executor_builder=_build_model_executor,
        openai_executor_builder=build_openai_model_executor,
        anthropic_executor_builder=build_anthropic_model_executor,
    )


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
