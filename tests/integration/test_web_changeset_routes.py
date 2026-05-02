"""HTTP integration tests for changeset dashboard APIs."""

import asyncio
import sqlite3
import subprocess
from pathlib import Path

import httpx

from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_session_id
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.web import create_app


def test_changeset_routes_create_list_show_refresh_and_archive(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            _init_git_repo(tmp_path)
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            repository = SQLiteSessionRepository(connection)
            repository.append_event(
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
                create_response = await client.post(
                    "/changesets",
                    json={
                        "source_kind": "session",
                        "session_id": str(session_id),
                        "objective": "Review session evidence",
                    },
                )
                changeset_id = create_response.json()["changeset_id"]
                list_response = await client.get("/changesets")
                detail_response = await client.get(f"/changesets/{changeset_id}")
                (tmp_path / "app.py").write_text(
                    "print('changed')\n",
                    encoding="utf-8",
                )
                refresh_response = await client.post(
                    f"/changesets/{changeset_id}/refresh",
                    json={"actor": "qa"},
                )
                (tmp_path / "app.py").write_text(
                    "print('changed again')\n",
                    encoding="utf-8",
                )
                stale_response = await client.get(f"/changesets/{changeset_id}")
                archive_response = await client.post(
                    f"/changesets/{changeset_id}/archive",
                    json={"actor": "qa", "reason": "superseded"},
                )

            assert create_response.status_code == 200
            assert create_response.json()["session_id"] == str(session_id)
            assert list_response.status_code == 200
            assert list_response.json()["items"][0]["changeset_id"] == changeset_id
            assert detail_response.status_code == 200
            assert detail_response.json()["sources"][0]["source_kind"] == "session"
            assert (
                "glassbox changeset show"
                in detail_response.json()["safe_next_actions"][0]
            )
            assert refresh_response.status_code == 200
            assert refresh_response.json()["status"] == "refreshed"
            assert (
                refresh_response.json()["detail"]["inventory"]["freshness"] == "fresh"
            )
            assert stale_response.status_code == 200
            assert stale_response.json()["inventory_status"]["stale"] is True
            assert stale_response.json()["inventory"]["freshness"] == "stale"
            assert archive_response.status_code == 200
            assert (
                archive_response.json()["detail"]["changeset"]["status"] == "archived"
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def _init_git_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "app.py").write_text("print('base')\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / ".glassbox" / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _make_app(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context)
