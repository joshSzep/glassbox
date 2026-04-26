"""Health check route."""

from fastapi import APIRouter
from pydantic import BaseModel

from glassbox.runtime.observability import EventTransportObservability
from glassbox.runtime.observability import build_event_transport_observability
from glassbox.web.app import RuntimeContextDep

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    event_transport: EventTransportObservability


@router.get("/healthz", response_model=HealthResponse)
async def healthz(context: RuntimeContextDep) -> HealthResponse:
    """Return service health status."""
    return HealthResponse(
        status="ok",
        event_transport=build_event_transport_observability(
            context.infrastructure.event_transport.stats()
        ),
    )
