"""HTTP integration tests for the Glassbox web application bootstrap (GBX-080)."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import httpx
import pytest

from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import initialize_database, open_database
from glassbox.web import create_app


def _make_runtime_context(tmp_path: Path, connection: sqlite3.Connection):
    return _build_runtime_context(connection, tmp_path)


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)
    return connection


def test_healthz_returns_ok(tmp_path: Path) -> None:
    """GET /healthz responds with 200 and {status: ok}."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _make_runtime_context(tmp_path, connection)
            app = create_app(runtime_context)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/healthz")

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        finally:
            connection.close()

    asyncio.run(scenario())


def test_healthz_content_type_is_json(tmp_path: Path) -> None:
    """GET /healthz returns application/json content type."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _make_runtime_context(tmp_path, connection)
            app = create_app(runtime_context)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/healthz")

            assert "application/json" in response.headers["content-type"]
        finally:
            connection.close()

    asyncio.run(scenario())


def test_unknown_route_returns_404(tmp_path: Path) -> None:
    """Requests to undefined routes return 404."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _make_runtime_context(tmp_path, connection)
            app = create_app(runtime_context)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/not-a-route")

            assert response.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())


def test_cli_help_lists_serve_command(capsys: pytest.CaptureFixture[str]) -> None:
    """The `serve` subcommand appears in CLI help output."""
    import pytest

    from glassbox.cli import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "serve" in captured.out
