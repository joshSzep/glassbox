"""Uvicorn-based server entry point for the Glassbox web application."""

from __future__ import annotations

from pathlib import Path

import uvicorn

from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.web.app import create_app


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
        app = create_app(runtime_context)
        uvicorn.run(app, host=host, port=port)
