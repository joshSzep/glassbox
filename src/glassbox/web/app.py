"""FastAPI application factory for the Glassbox web server."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from glassbox.runtime.context import RuntimeContext

_STATIC_DIR = Path(__file__).parent / "static"


def _get_runtime_context(request: Request) -> RuntimeContext:
    """Dependency: retrieve the RuntimeContext stored in app state."""
    return request.app.state.runtime_context


RuntimeContextDep = Annotated[RuntimeContext, Depends(_get_runtime_context)]


def create_app(runtime_context: RuntimeContext) -> FastAPI:
    """Build and return a configured FastAPI application.

    The *runtime_context* is stored on ``app.state`` so that route handlers
    can access services and repositories via the ``RuntimeContextDep``
    dependency without importing global state.
    """

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield

    app = FastAPI(title="Glassbox", lifespan=lifespan)
    # Attach immediately so the context is available both inside and outside
    # the ASGI lifespan (e.g. during testing with ASGITransport).
    app.state.runtime_context = runtime_context

    from glassbox.web.routes.approvals import router as approvals_router
    from glassbox.web.routes.events import router as events_router
    from glassbox.web.routes.health import router as health_router
    from glassbox.web.routes.sessions import router as sessions_router

    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(events_router)
    app.include_router(approvals_router)

    # Dashboard shell — served at the root path.
    @app.get("/", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(_STATIC_DIR / "dashboard.html", media_type="text/html")

    # Static assets (CSS, JS).
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    return app
