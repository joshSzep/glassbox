"""Integration tests for serving the v3 SPA static export."""

import asyncio
import re
import sqlite3
import tomllib
from pathlib import Path

import httpx
import pytest
from scripts.validate_frontend_release_assets import validate_frontend_release_assets

import glassbox.web.app as web_app
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import initialize_database
from glassbox.store import open_database
from glassbox.web import create_app


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)
    return connection


def _make_app(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context)


def _write_spa_build(root: Path) -> None:
    chunk_dir = root / "_next" / "static" / "chunks"
    chunk_dir.mkdir(parents=True)
    (root / "index.html").write_text(
        "<!doctype html><html><head>"
        '<script src="/app/_next/static/chunks/app.js"></script>'
        "</head><body><main>Glassbox Operator Console</main></body></html>",
        encoding="utf-8",
    )
    (chunk_dir / "app.js").write_text("console.log('glassbox spa');", encoding="utf-8")


def _write_generated_api(root: Path) -> None:
    generated_dir = root / "frontend" / "generated"
    generated_dir.mkdir(parents=True)
    (generated_dir / "openapi.json").write_text('{"openapi":"3.1.0"}\n')
    (generated_dir / "api-types.ts").write_text("export type paths = {};\n")


def test_default_dashboard_reports_clear_error_when_spa_build_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        monkeypatch.setattr(
            web_app, "_STATIC_NEXT_DIR", tmp_path / "missing-static-next"
        )
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/")

            assert response.status_code == 503
            assert "pnpm --dir frontend build" in response.json()["detail"]
            assert "static_next" in response.json()["detail"]
        finally:
            connection.close()

    asyncio.run(scenario())


def test_default_dashboard_reports_clear_error_for_stale_spa_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        static_next = tmp_path / "static_next"
        _write_spa_build(static_next)
        (static_next / "_next" / "static" / "chunks" / "app.js").unlink()
        monkeypatch.setattr(web_app, "_STATIC_NEXT_DIR", static_next)
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/")

            assert response.status_code == 503
            assert "missing SPA asset" in response.json()["detail"]
            assert "/app/_next/static/chunks/app.js" in response.json()["detail"]
        finally:
            connection.close()

    asyncio.run(scenario())


def test_frontend_release_asset_validator_reports_missing_next_assets(
    tmp_path: Path,
) -> None:
    _write_generated_api(tmp_path)
    static_next = tmp_path / "src" / "glassbox" / "web" / "static_next"
    static_next.mkdir(parents=True)
    (static_next / "index.html").write_text(
        '<!doctype html><script src="/app/_next/static/chunks/app.js"></script>',
        encoding="utf-8",
    )

    problems = validate_frontend_release_assets(tmp_path)

    assert problems == [
        "missing SPA asset referenced by index.html: /app/_next/static/chunks/app.js",
        "missing SPA _next static assets: src/glassbox/web/static_next/_next",
    ]


def test_frontend_release_asset_validator_accepts_generated_api_and_static_export(
    tmp_path: Path,
) -> None:
    _write_generated_api(tmp_path)
    _write_spa_build(tmp_path / "src" / "glassbox" / "web" / "static_next")

    assert validate_frontend_release_assets(tmp_path) == []


def test_package_build_config_includes_spa_static_artifacts() -> None:
    project = tomllib.loads((Path(__file__).parents[2] / "pyproject.toml").read_text())

    wheel = project["tool"]["hatch"]["build"]["targets"]["wheel"]
    sdist = project["tool"]["hatch"]["build"]["targets"]["sdist"]

    assert "src/glassbox/web/static_next/**" in wheel["artifacts"]
    assert "src/glassbox/web/static_next/**" in sdist["artifacts"]


def test_default_dashboard_serves_spa_shell_when_build_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        static_next = tmp_path / "static_next"
        _write_spa_build(static_next)
        monkeypatch.setattr(web_app, "_STATIC_NEXT_DIR", static_next)
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
            assert "Glassbox Operator Console" in response.text
        finally:
            connection.close()

    asyncio.run(scenario())


def test_default_dashboard_session_query_serves_spa_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        static_next = tmp_path / "static_next"
        _write_spa_build(static_next)
        monkeypatch.setattr(web_app, "_STATIC_NEXT_DIR", static_next)
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/?session=demo-session")

            assert response.status_code == 200
            assert "Glassbox Operator Console" in response.text
        finally:
            connection.close()

    asyncio.run(scenario())


def test_app_route_remains_spa_alias_when_build_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        static_next = tmp_path / "static_next"
        _write_spa_build(static_next)
        monkeypatch.setattr(web_app, "_STATIC_NEXT_DIR", static_next)
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/app")

            assert response.status_code == 200
            assert "Glassbox Operator Console" in response.text
        finally:
            connection.close()

    asyncio.run(scenario())


def test_app_nested_client_route_falls_back_to_spa_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        static_next = tmp_path / "static_next"
        _write_spa_build(static_next)
        monkeypatch.setattr(web_app, "_STATIC_NEXT_DIR", static_next)
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/app/sessions/demo-session")

            assert response.status_code == 200
            assert "Glassbox Operator Console" in response.text
        finally:
            connection.close()

    asyncio.run(scenario())


def test_app_next_static_asset_is_served(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        static_next = tmp_path / "static_next"
        _write_spa_build(static_next)
        monkeypatch.setattr(web_app, "_STATIC_NEXT_DIR", static_next)
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/app/_next/static/chunks/app.js")

            assert response.status_code == 200
            assert "javascript" in response.headers["content-type"]
            assert "glassbox spa" in response.text
        finally:
            connection.close()

    asyncio.run(scenario())


@pytest.mark.skipif(
    not web_app._spa_index_path().is_file(),  # noqa: SLF001
    reason="frontend static export has not been built",
)
def test_built_spa_export_serves_real_next_asset(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                app_response = await client.get("/app")
                match = re.search(
                    r'src="(/app/_next/static/[^"]+\.js)"', app_response.text
                )
                assert match is not None
                asset_response = await client.get(match.group(1))

            assert app_response.status_code == 200
            assert "text/html" in app_response.headers["content-type"]
            assert asset_response.status_code == 200
            assert "javascript" in asset_response.headers["content-type"]
        finally:
            connection.close()

    asyncio.run(scenario())
