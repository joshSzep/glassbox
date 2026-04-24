"""Uvicorn-based server entry point and lifecycle helpers for Glassbox."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import uvicorn

from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.context import RuntimeContext
from glassbox.web.app import create_app


class UvicornServerProtocol(Protocol):
    """Minimal server contract shared by real and test Uvicorn wrappers."""

    started: bool
    should_exit: bool

    async def serve(self) -> None: ...

    def run(self) -> None: ...


@dataclass(slots=True, frozen=True)
class WebServerConfig:
    """Configuration for a Glassbox web server instance."""

    host: str = "127.0.0.1"
    port: int = 8765

    @property
    def dashboard_url(self) -> str:
        display_host = "127.0.0.1" if self.host in {"0.0.0.0", "::"} else self.host
        return f"http://{display_host}:{self.port}/"


class GlassboxWebServer:
    """Lifecycle wrapper for a FastAPI app served by Uvicorn."""

    def __init__(
        self,
        runtime_context: RuntimeContext,
        config: WebServerConfig,
        *,
        server_factory: Callable[[uvicorn.Config], UvicornServerProtocol] | None = None,
    ) -> None:
        self._runtime_context = runtime_context
        self._config = config
        self._app = create_app(runtime_context)
        self._server_factory = server_factory or uvicorn.Server
        self._server = self._server_factory(self._build_uvicorn_config())
        self._serve_task: asyncio.Task[None] | None = None

    @property
    def app(self):
        return self._app

    @property
    def config(self) -> WebServerConfig:
        return self._config

    def serve_blocking(self) -> None:
        self._server.run()

    async def start(self) -> None:
        if self._serve_task is not None:
            raise RuntimeError("web server already started")

        self._serve_task = asyncio.create_task(self._server.serve())
        await self._wait_until_started()

    async def stop(self) -> None:
        if self._serve_task is None:
            return

        self._server.should_exit = True
        try:
            await self._serve_task
        finally:
            self._serve_task = None

    async def _wait_until_started(self) -> None:
        assert self._serve_task is not None

        while not self._server.started:
            if self._serve_task.done():
                try:
                    self._serve_task.result()
                except Exception as exc:
                    self._serve_task = None
                    raise RuntimeError("web server failed to start") from exc

                self._serve_task = None
                raise RuntimeError("web server exited before startup completed")
            await asyncio.sleep(0.01)

    def _build_uvicorn_config(self) -> uvicorn.Config:
        return uvicorn.Config(
            self._app,
            host=self._config.host,
            port=self._config.port,
        )


def build_web_server(
    runtime_context: RuntimeContext,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    server_factory: Callable[[uvicorn.Config], UvicornServerProtocol] | None = None,
) -> GlassboxWebServer:
    """Construct a reusable web server bound to an existing runtime context."""

    return GlassboxWebServer(
        runtime_context,
        WebServerConfig(host=host, port=port),
        server_factory=server_factory,
    )


def run_server(
    cwd: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: Path | None = None,
) -> None:
    """Start the Glassbox web server, blocking until it shuts down.

    The runtime context is opened for the duration of the server's lifetime
    so that all services and the event bus are live for the duration of the
    process.
    """

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        server = build_web_server(runtime_context, host=host, port=port)
        server.serve_blocking()
