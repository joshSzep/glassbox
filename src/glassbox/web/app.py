"""FastAPI application factory for the Glassbox web server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import FileResponse

from glassbox.runtime.context import RuntimeContext
from glassbox.web.spa_static import validate_spa_static_assets

_STATIC_NEXT_DIR = Path(__file__).parent / "static_next"
_SPA_MISSING_DETAIL = (
    "Glassbox SPA assets have not been built. Run "
    "`pnpm --dir frontend build` from the repository root to generate "
    "src/glassbox/web/static_next/."
)


def _get_runtime_context(request: Request) -> RuntimeContext:
    """Dependency: retrieve the RuntimeContext stored in app state."""
    return request.app.state.runtime_context


RuntimeContextDep = Annotated[RuntimeContext, Depends(_get_runtime_context)]


def _spa_index_path() -> Path:
    return _STATIC_NEXT_DIR / "index.html"


def _ensure_spa_build_available() -> None:
    problems = validate_spa_static_assets(_STATIC_NEXT_DIR)
    if problems:
        detail = f"{_SPA_MISSING_DETAIL} Problem: {problems[0]}"
        raise HTTPException(status_code=503, detail=detail)


def _resolve_spa_file(relative_path: str) -> Path | None:
    static_root = _STATIC_NEXT_DIR.resolve()
    candidate = (static_root / relative_path).resolve()
    if candidate == static_root or static_root not in candidate.parents:
        return None
    if not candidate.is_file():
        return None
    return candidate


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

    from glassbox.web.repository_index_routes import router as repository_index_router
    from glassbox.web.repository_index_routes import topology_router
    from glassbox.web.routes.approvals import router as approvals_router
    from glassbox.web.routes.branch_searches import router as branch_searches_router
    from glassbox.web.routes.changesets import router as changesets_router
    from glassbox.web.routes.events import router as events_router
    from glassbox.web.routes.handoffs import router as handoffs_router
    from glassbox.web.routes.health import router as health_router
    from glassbox.web.routes.jobs import router as jobs_router
    from glassbox.web.routes.memory import router as memory_router
    from glassbox.web.routes.repository_intelligence import (
        router as repository_intelligence_router,
    )
    from glassbox.web.routes.sessions import router as sessions_router
    from glassbox.web.routes.tasks import router as tasks_router

    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(tasks_router)
    app.include_router(changesets_router)
    app.include_router(handoffs_router)
    app.include_router(branch_searches_router)
    app.include_router(jobs_router)
    app.include_router(memory_router)
    app.include_router(repository_intelligence_router)
    app.include_router(repository_index_router)
    app.include_router(topology_router)
    app.include_router(events_router)
    app.include_router(approvals_router)

    # Dashboard shell — the SPA is the default route after the v3 parity gate.
    @app.get("/", include_in_schema=False)
    async def dashboard() -> FileResponse:
        _ensure_spa_build_available()
        return FileResponse(_spa_index_path(), media_type="text/html")

    @app.get("/app", include_in_schema=False)
    async def spa_root() -> FileResponse:
        _ensure_spa_build_available()
        return FileResponse(_spa_index_path(), media_type="text/html")

    @app.get("/app/_next/{asset_path:path}", include_in_schema=False)
    async def spa_next_asset(asset_path: str) -> FileResponse:
        _ensure_spa_build_available()
        asset = _resolve_spa_file(f"_next/{asset_path}")
        if asset is None:
            raise HTTPException(status_code=404, detail="SPA asset not found")
        return FileResponse(asset)

    @app.get("/app/{client_path:path}", include_in_schema=False)
    async def spa_fallback(client_path: str) -> FileResponse:
        _ensure_spa_build_available()
        asset = _resolve_spa_file(client_path)
        if asset is not None:
            return FileResponse(asset)
        if Path(client_path).suffix:
            raise HTTPException(status_code=404, detail="SPA asset not found")
        return FileResponse(_spa_index_path(), media_type="text/html")

    return app
