"""Performance budget coverage for larger local session histories."""

import json
import sqlite3
from collections.abc import Callable
from collections.abc import Mapping
from pathlib import Path
from time import perf_counter

from glassbox.core import EventEnvelope
from glassbox.core import SessionId
from glassbox.core import SessionStarted
from glassbox.core import UserMessageReceived
from glassbox.core import new_message_id
from glassbox.core import new_session_id
from glassbox.runtime.performance_budgets import PAYLOAD_SIZE_BUDGETS
from glassbox.runtime.performance_budgets import PERFORMANCE_BUDGETS
from glassbox.runtime.repository_index import build_repository_index
from glassbox.runtime.repository_index_discovery import INDEX_SCAN_LIMITATION
from glassbox.runtime.repository_index_discovery import MAX_INDEXED_FILES
from glassbox.runtime.repository_intelligence_queries import (
    inspect_repository_intelligence_path,
)
from glassbox.runtime.repository_intelligence_queries import (
    search_repository_intelligence_entries,
)
from glassbox.runtime.session_queries import OPERATOR_SORT_PRIORITY
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import WorkspaceRuntimeSummaryView
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import list_sessions
from glassbox.store.sqlite import rebuild_session_projections
from glassbox.web.repository_index_api import build_repository_index_status_response
from glassbox.web.repository_intelligence_api import (
    build_repository_intelligence_overview_response,
)
from glassbox.web.session_api import SessionAggregateResponse
from glassbox.web.session_api import build_session_aggregate_response
from tests.integration.fault_test_support import open_initialized_database

_LARGE_SESSION_EVENT_COUNT = 600
_SESSION_INDEX_COUNT = 120
_AGGREGATE_SESSION_COUNT = 60
_LARGE_REPOSITORY_SOURCE_COUNT = MAX_INDEXED_FILES + 50


def test_large_event_stream_append_stays_within_budget(tmp_path: Path) -> None:
    connection = open_initialized_database(tmp_path)
    try:
        events = _large_message_session_events(
            tmp_path,
            event_count=_LARGE_SESSION_EVENT_COUNT,
        )

        elapsed_ms = _measure_ms(lambda: append_events(connection, events))

        _assert_within_budget("event-stream append", elapsed_ms)
        assert len(list_sessions(connection)) == 1
    finally:
        connection.close()


def test_projection_rebuild_stays_within_budget(tmp_path: Path) -> None:
    connection = open_initialized_database(tmp_path)
    try:
        session_id = _append_large_message_session(
            connection,
            tmp_path,
            event_count=_LARGE_SESSION_EVENT_COUNT,
        )

        elapsed_ms = _measure_ms(
            lambda: rebuild_session_projections(connection, session_id)
        )

        _assert_within_budget("projection rebuild", elapsed_ms)
        transcript_count = connection.execute(
            "select count(*) from transcript_messages where session_id = ?",
            (str(session_id),),
        ).fetchone()[0]
        assert transcript_count == _LARGE_SESSION_EVENT_COUNT - 1
    finally:
        connection.close()


def test_session_index_read_stays_within_budget(tmp_path: Path) -> None:
    connection = open_initialized_database(tmp_path)
    try:
        _append_small_sessions(connection, tmp_path, count=_SESSION_INDEX_COUNT)

        elapsed_ms = _measure_ms(lambda: list_sessions(connection, limit=50))

        _assert_within_budget("session index", elapsed_ms)
        assert len(list_sessions(connection, limit=50)) == 50
    finally:
        connection.close()


def test_operator_console_aggregate_stays_within_budget(tmp_path: Path) -> None:
    connection = open_initialized_database(tmp_path)
    try:
        _append_small_sessions(connection, tmp_path, count=_AGGREGATE_SESSION_COUNT)
        query_service = SessionQueryService(
            SQLiteSessionRepository(connection),
            FilesystemArtifactRepository(connection, tmp_path),
        )
        runtime = WorkspaceRuntimeSummaryView(
            workspace_root=str(tmp_path),
            state="stopped",
            health=None,
        )

        def build_console_payload() -> SessionAggregateResponse:
            aggregate = query_service.get_session_aggregate(
                runtime=runtime,
                sort=OPERATOR_SORT_PRIORITY,
                limit=25,
            )
            return build_session_aggregate_response(aggregate)

        elapsed_ms = _measure_ms(build_console_payload)

        _assert_within_budget("operator console aggregate", elapsed_ms)
        assert len(build_console_payload().sessions) == 25
    finally:
        connection.close()


def test_repository_intelligence_large_repo_paths_stay_within_budget(
    tmp_path: Path,
) -> None:
    _seed_large_repository(tmp_path, source_count=_LARGE_REPOSITORY_SOURCE_COUNT)

    snapshot = _measure_value_with_budget(
        "repository intelligence index build",
        lambda: build_repository_index(tmp_path),
    )
    inspection = _measure_value_with_budget(
        "repository intelligence path inspection",
        lambda: inspect_repository_intelligence_path(
            snapshot,
            Path("src/pkg/module_0001.py"),
        ),
    )
    matches = _measure_value_with_budget(
        "repository intelligence search",
        lambda: search_repository_intelligence_entries(snapshot, "module_0001"),
    )
    overview = build_repository_intelligence_overview_response(
        index=build_repository_index_status_response(
            snapshot,
            path=str(tmp_path / ".glassbox" / "repository-index.json"),
        ),
        topology=None,
        source_manifests=snapshot.source_manifests,
        source_roots=snapshot.source_roots,
        test_roots=snapshot.test_roots,
        doc_roots=snapshot.doc_roots,
        generated_paths=snapshot.generated_paths,
        policy_sensitive_paths=snapshot.policy_sensitive_paths,
        package_boundaries=snapshot.package_boundaries,
        subsystems=snapshot.subsystems,
        release_surfaces=snapshot.release_sensitive_surfaces,
        memory_references=snapshot.memory_references,
        limitations=snapshot.limitations,
    )

    assert len(snapshot.source_inputs) == MAX_INDEXED_FILES
    assert snapshot.limitations == [INDEX_SCAN_LIMITATION]
    assert inspection.next_actions == [
        "glassbox repo recommend src/pkg/module_0001.py",
        "glassbox eval recommend src/pkg/module_0001.py",
    ]
    assert matches
    _assert_payloads_within_budget(
        {
            "repository intelligence overview payload": _json_size_bytes(
                overview.model_dump(mode="json")
            )
        }
    )


def _large_message_session_events(
    workspace_root: Path,
    *,
    event_count: int,
) -> list[EventEnvelope]:
    session_id = new_session_id()
    events = [
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=SessionStarted(
                cwd=str(workspace_root),
                model_name="openai:gpt-5.4",
                approval_mode="confirm",
            ),
        )
    ]
    events.extend(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=UserMessageReceived(
                message_id=new_message_id(),
                text=f"message {index}",
            ),
        )
        for index in range(1, event_count)
    )
    return events


def _append_large_message_session(
    connection: sqlite3.Connection,
    workspace_root: Path,
    *,
    event_count: int,
) -> SessionId:
    events = _large_message_session_events(workspace_root, event_count=event_count)
    append_events(connection, events)
    return events[0].session_id


def _append_small_sessions(
    connection: sqlite3.Connection,
    workspace_root: Path,
    *,
    count: int,
) -> None:
    for index in range(count):
        session_id = new_session_id()
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd=str(workspace_root / f"workspace-{index}"),
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=UserMessageReceived(
                        message_id=new_message_id(),
                        text=f"session {index}",
                    ),
                ),
            ],
        )


def _measure_ms(operation: Callable[[], object]) -> float:
    started_at = perf_counter()
    operation()
    return (perf_counter() - started_at) * 1000


def _measure_value_with_budget[T](surface: str, operation: Callable[[], T]) -> T:
    value: T | None = None

    def measured_operation() -> None:
        nonlocal value
        value = operation()

    elapsed_ms = _measure_ms(measured_operation)
    _assert_within_budget(surface, elapsed_ms)
    assert value is not None
    return value


def _assert_within_budget(surface: str, elapsed_ms: float) -> None:
    budget = next(budget for budget in PERFORMANCE_BUDGETS if budget.surface == surface)
    assert elapsed_ms <= budget.budget_ms, (
        f"{surface} took {elapsed_ms:.1f} ms; budget is {budget.budget_ms} ms. "
        f"{budget.guidance}"
    )


def _json_size_bytes(payload: object) -> int:
    return len(
        json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


def _assert_payloads_within_budget(payload_sizes: Mapping[str, int]) -> None:
    budgets = {budget.surface: budget for budget in PAYLOAD_SIZE_BUDGETS}
    for surface, size_bytes in payload_sizes.items():
        budget = budgets[surface]
        assert size_bytes <= budget.budget_bytes, (
            f"{surface} serialized to {size_bytes} bytes; "
            f"budget is {budget.budget_bytes} bytes. {budget.guidance}"
        )


def _seed_large_repository(root: Path, *, source_count: int) -> None:
    src = root / "src" / "pkg"
    docs = root / "docs"
    tests = root / "tests"
    generated = root / "frontend" / "generated"
    node_modules = root / "frontend" / "node_modules"
    src.mkdir(parents=True)
    docs.mkdir()
    tests.mkdir()
    generated.mkdir(parents=True)
    node_modules.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "large-fixture"\ndependencies = ["pydantic>=2"]\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text("# Large Fixture\n", encoding="utf-8")
    (docs / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (tests / "test_pkg.py").write_text(
        "def test_pkg() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (root / "frontend" / "package.json").write_text(
        '{"name":"large-dashboard","scripts":{"test":"vitest run"}}',
        encoding="utf-8",
    )
    (generated / "api-types.ts").write_text("export type Api = {};\n", encoding="utf-8")
    (node_modules / "ignored.js").write_text("module.exports = {}\n", encoding="utf-8")
    for index in range(source_count):
        (src / f"module_{index:04d}.py").write_text(
            f"class Module{index:04d}:\n    value = {index}\n",
            encoding="utf-8",
        )
