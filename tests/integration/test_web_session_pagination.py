"""HTTP integration tests for paginated session detail APIs."""

import asyncio
from pathlib import Path

import httpx

from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.web import create_app
from tests.integration.large_session_fixture import LargeSessionFixtureConfig
from tests.integration.large_session_fixture import append_large_session_fixture


def test_session_detail_pages_return_ordered_cursor_windows(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = open_database(tmp_path / "glassbox.sqlite3")
        initialize_database(connection)
        try:
            runtime_context = _build_runtime_context(connection, tmp_path)
            fixture = append_large_session_fixture(
                connection,
                tmp_path,
                config=LargeSessionFixtureConfig(),
            )
            app = create_app(runtime_context)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                transcript_page = await client.get(
                    f"/sessions/{fixture.session_id}/transcript",
                    params={"limit": 25},
                )
                transcript_next = await client.get(
                    f"/sessions/{fixture.session_id}/transcript",
                    params={"cursor": 25, "limit": 25},
                )
                event_page = await client.get(
                    f"/sessions/{fixture.session_id}/event-log",
                    params={"limit": 50},
                )
                event_next = await client.get(
                    f"/sessions/{fixture.session_id}/event-log",
                    params={"cursor": 50, "limit": 50},
                )
                tool_page = await client.get(
                    f"/sessions/{fixture.session_id}/tool-calls",
                    params={"limit": 15},
                )
                metrics_page = await client.get(
                    f"/sessions/{fixture.session_id}/turn-metrics",
                    params={"limit": 20},
                )
                artifact_page = await client.get(
                    f"/sessions/{fixture.session_id}/artifacts",
                    params={"limit": 12},
                )
                empty_page = await client.get(
                    f"/sessions/{fixture.session_id}/transcript",
                    params={"cursor": fixture.transcript_message_count + 10},
                )

            assert transcript_page.status_code == 200
            transcript_body = transcript_page.json()
            assert transcript_body["page"] == {
                "cursor": 0,
                "limit": 25,
                "next_cursor": 25,
                "has_more": True,
                "returned_count": 25,
            }
            assert transcript_body["items"][0]["role"] == "user"
            assert transcript_body["items"][1]["role"] == "assistant"

            assert transcript_next.status_code == 200
            assert (
                transcript_next.json()["items"][0]["message_id"]
                != (transcript_body["items"][0]["message_id"])
            )

            assert event_page.status_code == 200
            event_body = event_page.json()
            assert event_body["page"]["next_cursor"] == 50
            assert event_body["items"][0]["sequence"] == 1
            assert event_body["items"][-1]["sequence"] == 50

            assert event_next.status_code == 200
            assert event_next.json()["items"][0]["sequence"] == 51

            assert tool_page.status_code == 200
            assert tool_page.json()["page"]["returned_count"] == 15
            assert tool_page.json()["items"][0]["tool_name"] == "read_file"

            assert metrics_page.status_code == 200
            assert metrics_page.json()["page"]["returned_count"] == 20
            assert metrics_page.json()["items"][0]["model_call_count"] == 1

            assert artifact_page.status_code == 200
            artifact_body = artifact_page.json()
            assert artifact_body["page"]["next_cursor"] == 12
            assert artifact_body["items"][0]["artifact_kind"] == "fixture-output"
            assert artifact_body["items"][0]["path"].startswith(".glassbox/sessions/")

            assert empty_page.status_code == 200
            assert empty_page.json()["items"] == []
            assert empty_page.json()["page"]["has_more"] is False
        finally:
            connection.close()

    asyncio.run(scenario())


def test_session_detail_pages_reject_invalid_cursors(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = open_database(tmp_path / "glassbox.sqlite3")
        initialize_database(connection)
        try:
            runtime_context = _build_runtime_context(connection, tmp_path)
            fixture = append_large_session_fixture(connection, tmp_path)
            app = create_app(runtime_context)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                bad_cursor = await client.get(
                    f"/sessions/{fixture.session_id}/transcript",
                    params={"cursor": -1},
                )
                bad_limit = await client.get(
                    f"/sessions/{fixture.session_id}/event-log",
                    params={"limit": 0},
                )
                missing_session = await client.get(
                    "/sessions/00000000-0000-0000-0000-000000000099/transcript"
                )

            assert bad_cursor.status_code == 422
            assert bad_limit.status_code == 422
            assert missing_session.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())
