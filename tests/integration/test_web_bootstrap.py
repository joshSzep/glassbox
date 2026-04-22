"""HTTP integration tests for the Glassbox web application bootstrap (GBX-080)."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path

import httpx
import pytest

from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.logging import configure_runtime_logging
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


def test_serve_command_prints_dashboard_url_and_passes_runtime_args(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from glassbox.cli import main

    recorded: dict[str, object] = {}

    def fake_run_server(
        cwd: Path, *, host: str, port: int, db_path: Path | None
    ) -> None:
        recorded["cwd"] = cwd
        recorded["host"] = host
        recorded["port"] = port
        recorded["db_path"] = db_path

    monkeypatch.setattr("glassbox.web.run_server", fake_run_server)

    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    exit_code = main(
        [
            "serve",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--host",
            "0.0.0.0",
            "--port",
            "9876",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Dashboard available at http://127.0.0.1:9876/" in captured.out
    assert "Use ?session=SESSION_ID" in captured.out
    assert recorded == {
        "cwd": tmp_path.resolve(),
        "host": "0.0.0.0",
        "port": 9876,
        "db_path": db_path.resolve(),
    }


def test_runtime_logging_configuration_does_not_break_startup(tmp_path: Path) -> None:
    connection = _open_initialized_db(tmp_path)
    try:
        runtime_logger = configure_runtime_logging()
        runtime_context = _make_runtime_context(tmp_path, connection)
        app = create_app(runtime_context)

        assert app.state.runtime_context is runtime_context
        assert runtime_logger.name == "glassbox.runtime"
        assert any(
            isinstance(handler, logging.NullHandler)
            for handler in runtime_logger.handlers
        )
    finally:
        connection.close()
