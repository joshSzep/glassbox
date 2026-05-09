"""HTTP integration tests for repository index APIs."""

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_session_id
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.workspace_topology import build_and_write_workspace_topology
from glassbox.store import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.web import create_app


def test_repository_index_routes_return_status_search_and_detail(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        _seed_repository(tmp_path)
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            snapshot = build_and_write_repository_index(tmp_path)
            symbol_id = next(
                entry.entry_id
                for entry in snapshot.entries
                if entry.symbol == "UsefulThing"
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                status_response = await client.get("/repo/index/status")
                inspect_response = await client.get("/repo/index")
                search_response = await client.get(
                    "/repo/index/search",
                    params={"query": "useful", "limit": 5},
                )
                detail_response = await client.get(f"/repo/index/entries/{symbol_id}")

            assert status_response.status_code == 200
            assert status_response.json()["status"] == "fresh"
            assert status_response.json()["entry_count"] == len(snapshot.entries)
            assert status_response.json()["schema_version"] == 2
            assert status_response.json()["package_boundary_count"] >= 1
            assert status_response.json()["source_root_count"] >= 1
            assert inspect_response.status_code == 200
            assert inspect_response.json()["index"]["status"] == "fresh"
            assert "package:fixture" in inspect_response.json()["package_boundaries"]
            assert search_response.status_code == 200
            assert search_response.json()["page"]["returned_count"] >= 1
            assert search_response.json()["items"][0]["symbol"] == "UsefulThing"
            assert detail_response.status_code == 200
            assert detail_response.json()["entry"]["entry_id"] == symbol_id
        finally:
            connection.close()

    asyncio.run(scenario())


def test_repository_index_routes_report_missing_snapshot(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                status_response = await client.get("/repo/index/status")
                inspect_response = await client.get("/repo/index")
                search_response = await client.get(
                    "/repo/index/search",
                    params={"query": "anything"},
                )

            assert status_response.status_code == 200
            assert status_response.json()["status"] == "missing"
            assert inspect_response.status_code == 404
            assert search_response.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())


def test_repository_index_route_rebuilds_snapshot(tmp_path: Path) -> None:
    async def scenario() -> None:
        _seed_repository(tmp_path)
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                rebuild_response = await client.post(
                    "/repo/index/rebuild",
                    json={"background": False, "requested_by": "qa"},
                )
                status_response = await client.get("/repo/index/status")

            assert rebuild_response.status_code == 200
            assert rebuild_response.json()["mode"] == "synchronous"
            assert rebuild_response.json()["index"]["entry_count"] >= 1
            assert status_response.status_code == 200
            assert status_response.json()["status"] == "fresh"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_repository_intelligence_routes_return_typed_dashboard_data(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        _seed_repository(tmp_path)
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            build_and_write_repository_index(tmp_path)
            build_and_write_workspace_topology(tmp_path)
            session_id = new_session_id()
            SQLiteSessionRepository(connection).append_event(
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd=str(tmp_path),
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                overview_response = await client.get("/repo/intelligence")
                freshness_response = await client.get("/repo/intelligence/freshness")
                path_response = await client.get(
                    "/repo/intelligence/paths/src/sample.py"
                )
                recipes_response = await client.get(
                    "/repo/intelligence/command-recipes",
                    params={"query": "frontend", "limit": 1},
                )
                subsystem_response = await client.get(
                    "/repo/intelligence/subsystems/subsystem:frontend"
                )
                verification_response = await client.get(
                    "/repo/intelligence/verification",
                    params={"paths": "src/sample.py"},
                )
                candidates_response = await client.get(
                    "/repo/intelligence/memory-candidates",
                    params={"session_id": str(session_id), "limit": 5},
                )
                search_response = await client.get(
                    "/repo/intelligence/search",
                    params={"query": "UsefulThing", "limit": 1},
                )

            assert overview_response.status_code == 200
            overview = overview_response.json()
            assert overview["index"]["status"] in {"fresh", "stale"}
            assert overview["topology"]["freshness"] in {"fresh", "stale"}
            assert any(
                recipe["command"] == "npm --prefix frontend run test"
                for recipe in recipes_response.json()["items"]
            )
            assert freshness_response.status_code == 200
            assert freshness_response.json()["cues"][0]["source"] == "repository-index"
            assert path_response.status_code == 200
            assert path_response.json()["path"] == "src/sample.py"
            assert (
                path_response.json()["packages"][0]["package_id"] == "package:fixture"
            )
            assert subsystem_response.status_code == 200
            assert (
                subsystem_response.json()["subsystem"]["subsystem_id"]
                == "subsystem:frontend"
            )
            assert verification_response.status_code == 200
            assert verification_response.json()["status"] in {"ok", "unavailable"}
            assert verification_response.json()["paths"] == ["src/sample.py"]
            assert candidates_response.status_code == 200
            assert candidates_response.json()["session_id"] == str(session_id)
            assert search_response.status_code == 200
            assert search_response.json()["items"][0]["symbol"] == "UsefulThing"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_workspace_topology_routes_rebuild_status_and_detail(tmp_path: Path) -> None:
    async def scenario() -> None:
        _seed_repository(tmp_path)
        (tmp_path / "frontend" / "package.json").write_text(
            '{"name":"fixture-dashboard","dependencies":{"react":"latest"}}',
            encoding="utf-8",
        )
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                missing_response = await client.get("/repo/topology/status")
                rebuild_response = await client.post(
                    "/repo/topology/rebuild",
                    json={"requested_by": "qa"},
                )
                status_response = await client.get("/repo/topology/status")
                detail_response = await client.get("/repo/topology")

            assert missing_response.status_code == 200
            assert missing_response.json()["freshness"] == "missing"
            assert rebuild_response.status_code == 200
            assert rebuild_response.json()["topology"]["freshness"] == "fresh"
            assert status_response.status_code == 200
            assert status_response.json()["component_count"] >= 2
            assert detail_response.status_code == 200
            component_ids = {
                component["component_id"]
                for component in detail_response.json()["components"]
            }
            assert "package:fixture" in component_ids
            assert "app:fixture-dashboard" in component_ids
        finally:
            connection.close()

    asyncio.run(scenario())


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _make_app(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context)


def _seed_repository(root: Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n",
        encoding="utf-8",
    )
    (root / "frontend").mkdir()
    (root / "frontend" / "package.json").write_text(
        '{"name":"fixture-dashboard","scripts":{"test":"vitest run"}}',
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\n',
        encoding="utf-8",
    )
