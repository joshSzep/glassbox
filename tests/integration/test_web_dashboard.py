"""Integration tests for dashboard asset serving (GBX-090)."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import initialize_database, open_database
from glassbox.web import create_app


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)
    return connection


def _make_app(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context)


def test_dashboard_root_returns_html(tmp_path: Path) -> None:
    """GET / returns 200 with text/html content-type."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/")

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
        finally:
            connection.close()

    asyncio.run(scenario())


def test_dashboard_html_contains_expected_structure(tmp_path: Path) -> None:
    """Dashboard HTML contains the key structural landmarks."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/")

            html = response.text
            assert "<!DOCTYPE html>" in html
            assert "Glassbox" in html
            assert "/static/dashboard.css" in html
            assert "/static/dashboard.js" in html
            # Key pane landmarks
            assert "pane-transcript" in html
            assert "pane-turn" in html
            assert "pane-tools" in html
            assert "pane-output" in html
            assert "pane-approvals" in html
            assert "pane-events" in html
        finally:
            connection.close()

    asyncio.run(scenario())


def test_dashboard_css_is_served(tmp_path: Path) -> None:
    """GET /static/dashboard.css returns 200 with text/css content-type."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/static/dashboard.css")

            assert response.status_code == 200
            assert "text/css" in response.headers["content-type"]
        finally:
            connection.close()

    asyncio.run(scenario())


def test_dashboard_js_is_served(tmp_path: Path) -> None:
    """GET /static/dashboard.js returns 200 with JavaScript content-type."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/static/dashboard.js")

            assert response.status_code == 200
            ct = response.headers["content-type"]
            assert "javascript" in ct
        finally:
            connection.close()

    asyncio.run(scenario())


def test_static_unknown_file_returns_404(tmp_path: Path) -> None:
    """GET /static/nonexistent.txt returns 404."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/static/nonexistent.txt")

            assert response.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())
