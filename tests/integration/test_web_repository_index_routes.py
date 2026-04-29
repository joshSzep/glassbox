"""HTTP integration tests for repository index APIs."""

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.repository_index import build_and_write_repository_index
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
                search_response = await client.get(
                    "/repo/index/search",
                    params={"query": "useful", "limit": 5},
                )
                detail_response = await client.get(f"/repo/index/entries/{symbol_id}")

            assert status_response.status_code == 200
            assert status_response.json()["status"] == "fresh"
            assert status_response.json()["entry_count"] == len(snapshot.entries)
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
                search_response = await client.get(
                    "/repo/index/search",
                    params={"query": "anything"},
                )

            assert status_response.status_code == 200
            assert status_response.json()["status"] == "missing"
            assert search_response.status_code == 404
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
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\n',
        encoding="utf-8",
    )
