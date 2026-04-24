"""Integration tests for the SSE event stream API (GBX-082).

Strategy: call the _event_stream async generator directly with a mock
request rather than going through ASGITransport, which cannot handle
infinite streaming responses.  HTTP-layer concerns (404 routing, response
headers) are tested by inspecting the StreamingResponse returned by the
route handler.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import SessionConfig
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.store.sqlite import initialize_database, open_database
from glassbox.web import create_app
from glassbox.web.routes.events import (
    _event_stream,  # noqa: PLC2701
    stream_session_events,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)
    return connection


def _make_app_and_context(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context), runtime_context


def _parse_sse_frames(text: str) -> list[dict]:
    """Parse raw SSE text into a list of frame dicts (event, data, id)."""
    frames: list[dict] = []
    current: dict = {}
    for line in text.splitlines():
        if line.startswith("data:"):
            current["data"] = line[len("data:") :].strip()
        elif line.startswith("event:"):
            current["event"] = line[len("event:") :].strip()
        elif line.startswith("id:"):
            current["id"] = line[len("id:") :].strip()
        elif line == "" and current:
            frames.append(current)
            current = {}
    if current:
        frames.append(current)
    return frames


class _MockRequest:
    """Minimal fake Request for testing _event_stream directly.

    ``disconnect_after`` controls how many live-loop iterations run before
    ``is_disconnected()`` returns True.  The default of 0 means the live
    loop never executes, so only historical (replay) events are yielded.
    """

    def __init__(self, *, disconnect_after: int = 0) -> None:
        self._calls = 0
        self._disconnect_after = disconnect_after

    async def is_disconnected(self) -> bool:
        result = self._calls >= self._disconnect_after
        self._calls += 1
        return result


async def _collect_all_frames(gen) -> list[str]:
    """Exhaust an async generator and return all yielded strings."""
    frames: list[str] = []
    async for frame in gen:
        frames.append(frame)
    return frames


# ---------------------------------------------------------------------------
# Tests: HTTP routing layer (non-streaming calls only with ASGITransport)
# ---------------------------------------------------------------------------


def test_sse_returns_404_for_unknown_session(tmp_path: Path) -> None:
    """GET /sessions/{id}/events returns 404 when session does not exist."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, _ = _make_app_and_context(tmp_path, connection)
            unknown_id = "00000000-0000-0000-0000-000000000099"

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{unknown_id}/events")

            assert response.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())


def test_sse_response_has_event_stream_content_type(tmp_path: Path) -> None:
    """StreamingResponse from the route handler carries text/event-stream."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _build_runtime_context(connection, tmp_path)
            bus = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(runtime_context.repositories.sessions, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)

            mock_request = _MockRequest(disconnect_after=0)
            response = await stream_session_events(
                state.session_id,
                runtime_context,
                mock_request,  # ty: ignore[invalid-argument-type]
                after=0,
            )

            assert "text/event-stream" in (response.media_type or "")
            assert response.headers.get("cache-control") == "no-cache"
            assert response.headers.get("x-accel-buffering") == "no"
        finally:
            connection.close()

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Tests: generator behaviour (call _event_stream directly)
# ---------------------------------------------------------------------------


def test_sse_replays_historical_events_on_connect(tmp_path: Path) -> None:
    """Connecting without 'after' replays all persisted events for the session."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _build_runtime_context(connection, tmp_path)
            bus = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(runtime_context.repositories.sessions, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)

            mock_request = _MockRequest(disconnect_after=0)
            frames = await _collect_all_frames(
                _event_stream(mock_request, runtime_context, state.session_id, 0)
            )

            raw = "".join(frames)
            parsed = _parse_sse_frames(raw)
            assert len(parsed) >= 1
            assert parsed[0]["event"] == "SessionStarted"
            data = json.loads(parsed[0]["data"])
            assert data["session_id"] == str(state.session_id)
            assert data["event_type"] == "SessionStarted"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_sse_after_parameter_skips_already_seen_events(tmp_path: Path) -> None:
    """Connecting with after=N replays only events with sequence > N."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _build_runtime_context(connection, tmp_path)
            bus = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(runtime_context.repositories.sessions, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)

            repo = runtime_context.repositories.sessions
            all_events = repo.read_session_events(state.session_id)
            last_seq = all_events[-1].sequence

            # after=last_seq means every persisted event is skipped
            mock_request = _MockRequest(disconnect_after=0)
            frames = await _collect_all_frames(
                _event_stream(mock_request, runtime_context, state.session_id, last_seq)
            )

            raw = "".join(frames)
            parsed = _parse_sse_frames(raw)
            for frame in parsed:
                assert frame.get("event") != "SessionStarted"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_sse_frame_contains_required_fields(tmp_path: Path) -> None:
    """Each SSE data payload contains event_id, session_id, sequence,
    event_type, created_at, and payload."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _build_runtime_context(connection, tmp_path)
            bus = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(runtime_context.repositories.sessions, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)

            mock_request = _MockRequest(disconnect_after=0)
            frames = await _collect_all_frames(
                _event_stream(mock_request, runtime_context, state.session_id, 0)
            )
            assert frames, "Expected at least one SSE frame"

            raw = "".join(frames)
            parsed = _parse_sse_frames(raw)
            assert parsed

            first = json.loads(parsed[0]["data"])
            for key in (
                "event_id",
                "session_id",
                "sequence",
                "event_type",
                "created_at",
                "payload",
            ):
                assert key in first, f"Missing key: {key}"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_sse_delivers_live_events(tmp_path: Path) -> None:
    """Events published to the bus after replay are yielded by the generator."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _build_runtime_context(connection, tmp_path)
            bus = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(runtime_context.repositories.sessions, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)

            repo = runtime_context.repositories.sessions
            all_events = repo.read_session_events(state.session_id)
            last_seq = all_events[-1].sequence

            # after=last_seq skips history; disconnect_after=1 lets one live
            # iteration run before the generator exits.
            mock_request = _MockRequest(disconnect_after=1)
            live_event = all_events[-1]

            async def publish_after_delay() -> None:
                await asyncio.sleep(0.05)
                bus.publish(live_event)

            frames: list[str] = []
            publisher = asyncio.create_task(publish_after_delay())
            async for frame in _event_stream(
                mock_request, runtime_context, state.session_id, last_seq
            ):
                frames.append(frame)
            await publisher

            raw = "".join(frames)
            parsed = _parse_sse_frames(raw)
            assert len(parsed) >= 1
            data = json.loads(parsed[0]["data"])
            assert data["session_id"] == str(state.session_id)
        finally:
            connection.close()

    asyncio.run(scenario())
