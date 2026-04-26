"""HTTP integration tests for the Glassbox web application bootstrap (GBX-080)."""

import asyncio
import logging
import sqlite3
from pathlib import Path

import httpx
import pytest

from glassbox.core import EventEnvelope
from glassbox.core import SessionConfig
from glassbox.core import SessionStarted
from glassbox.core import new_session_id
from glassbox.llm import PydanticAIModelExecutor
from glassbox.llm import build_local_text_model_executor
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.logging import configure_runtime_logging
from glassbox.store import initialize_database
from glassbox.store import open_database
from glassbox.web import build_web_server
from glassbox.web import create_app
from glassbox.web import run_server


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
            payload = response.json()
            assert payload["status"] == "ok"
            assert payload["event_transport"]["subscriber_count"] == 0
            assert payload["event_transport"]["dropped_events"] == 0
            assert payload["event_transport"]["reconnect_mode"].startswith(
                "resume with"
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_healthz_reports_event_transport_backpressure(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _make_runtime_context(tmp_path, connection)
            app = create_app(runtime_context)
            event = EventEnvelope(
                session_id=new_session_id(),
                sequence=0,
                payload=SessionStarted(
                    cwd=str(tmp_path),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            )

            async with runtime_context.infrastructure.event_transport.subscribe():
                for _ in range(80):
                    runtime_context.infrastructure.event_transport.publish(event)

                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://testserver",
                ) as client:
                    response = await client.get("/healthz")

            payload = response.json()
            assert response.status_code == 200
            assert payload["event_transport"]["subscriber_count"] == 1
            assert payload["event_transport"]["dropped_events"] > 0
            assert payload["event_transport"]["degraded"] is True
            assert payload["event_transport"]["next_actions"]
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


def test_cli_help_lists_dashboard_command(capsys: pytest.CaptureFixture[str]) -> None:
    """The `dashboard` command appears in CLI help output."""
    import pytest

    from glassbox.cli import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "dashboard" in captured.out


def test_cli_dashboard_help_lists_serve_subcommand(
    capsys: pytest.CaptureFixture[str],
) -> None:
    import pytest

    from glassbox.cli import main

    with pytest.raises(SystemExit) as exc_info:
        main(["dashboard", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "serve" in captured.out
    assert "Start the browser dashboard" in captured.out
    assert "inspect browser dashboard" not in captured.out


def test_cli_help_lists_chat_dashboard_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    import pytest

    from glassbox.cli import main

    with pytest.raises(SystemExit) as exc_info:
        main(["session", "chat", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "--dashboard-host" in captured.out
    assert "--dashboard-port" in captured.out
    assert "--no-dashboard" in captured.out


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

    monkeypatch.setattr("glassbox.cli.server_commands.run_server", fake_run_server)

    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    exit_code = main(
        [
            "dashboard",
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


def test_build_web_server_embedded_lifecycle_starts_and_stops(tmp_path: Path) -> None:
    class FakeServer:
        def __init__(self, config) -> None:
            self.config = config
            self.started = False
            self.should_exit = False
            self.run_called = False

        async def serve(self) -> None:
            self.started = True
            while not self.should_exit:
                await asyncio.sleep(0)

        def run(self) -> None:
            self.run_called = True

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _make_runtime_context(tmp_path, connection)
            server = build_web_server(
                runtime_context,
                host="0.0.0.0",
                port=9876,
                server_factory=FakeServer,
            )

            assert server.config.host == "0.0.0.0"
            assert server.config.port == 9876
            assert server.app.state.runtime_context is runtime_context

            await server.start()

            assert isinstance(server._server, FakeServer)  # noqa: SLF001
            assert server._server.started is True  # noqa: SLF001

            await server.stop()

            assert server._server.should_exit is True  # noqa: SLF001
        finally:
            connection.close()

    asyncio.run(scenario())


def test_run_server_opens_runtime_context_and_uses_shared_server_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recorded: dict[str, object] = {}

    class FakeRuntimeContext:
        pass

    runtime_context = FakeRuntimeContext()

    class FakeContextManager:
        def __enter__(self):
            recorded["entered"] = True
            return runtime_context

        def __exit__(self, exc_type, exc, tb):
            recorded["exited"] = True
            return False

    class FakeServer:
        def __init__(self) -> None:
            self.serve_blocking_called = False

        def serve_blocking(self) -> None:
            self.serve_blocking_called = True
            recorded["serve_blocking_called"] = True

    def fake_open_runtime_context(cwd: Path, *, db_path: Path | None = None):
        recorded["cwd"] = cwd
        recorded["db_path"] = db_path
        return FakeContextManager()

    def fake_build_web_server(runtime_context_arg, *, host: str, port: int):
        recorded["runtime_context"] = runtime_context_arg
        recorded["host"] = host
        recorded["port"] = port
        return FakeServer()

    monkeypatch.setattr(
        "glassbox.web.server.open_runtime_context",
        fake_open_runtime_context,
    )
    monkeypatch.setattr("glassbox.web.server.build_web_server", fake_build_web_server)

    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    run_server(tmp_path, host="0.0.0.0", port=9876, db_path=db_path)

    assert recorded == {
        "cwd": tmp_path,
        "db_path": db_path,
        "entered": True,
        "runtime_context": runtime_context,
        "host": "0.0.0.0",
        "port": 9876,
        "serve_blocking_called": True,
        "exited": True,
    }


def test_runtime_context_loads_provider_config_and_keeps_secrets_out_of_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _open_initialized_db(tmp_path)
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "OPENAI_API_KEY=dotenv-openai\nANTHROPIC_API_KEY=dotenv-anthropic\n"
    )
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai")
    try:
        runtime_context = _make_runtime_context(tmp_path, connection)
        repository = runtime_context.repositories.sessions
        session_state = asyncio.run(
            runtime_context.services.session_service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
        )
        session_record = repository.get_session(session_state.session_id)
        events = repository.read_session_events(session_state.session_id)

        assert (
            runtime_context.infrastructure.provider_config.openai.api_key
            == "env-openai"
        )
        assert (
            runtime_context.infrastructure.provider_config.anthropic.api_key
            == "dotenv-anthropic"
        )
        assert session_record is not None
        assert "env-openai" not in session_record.model_dump_json()
        assert "dotenv-anthropic" not in session_record.model_dump_json()
        assert all(
            "env-openai" not in event.model_dump_json()
            and "dotenv-anthropic" not in event.model_dump_json()
            for event in events
        )
    finally:
        connection.close()


def test_runtime_context_uses_provider_executor_when_runtime_config_is_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _open_initialized_db(tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=dotenv-openai\n")

    captured: dict[str, str | None] = {}

    def fake_build_openai_model_executor(
        model_name: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> PydanticAIModelExecutor:
        captured["model_name"] = model_name
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return build_local_text_model_executor(f"openai:{model_name}")

    monkeypatch.setattr(
        "glassbox.runtime.bootstrap.build_openai_model_executor",
        fake_build_openai_model_executor,
    )

    try:
        runtime_context = _make_runtime_context(tmp_path, connection)
        session_record = runtime_context.repositories.sessions.create_session(
            session_id=new_session_id(),
            config=SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            ),
        )
        turn_engine = runtime_context.services.session_service._turn_engine
        build_executor = turn_engine._model_executor_factory
        executor = build_executor(session_record)

        assert isinstance(executor, PydanticAIModelExecutor)
        assert captured == {
            "model_name": "gpt-5.4",
            "api_key": "dotenv-openai",
            "base_url": None,
        }
    finally:
        connection.close()
