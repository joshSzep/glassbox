"""Error translation helpers for handoff routes."""

from typing import Any
from typing import cast
from uuid import UUID

from fastapi import HTTPException

from glassbox.core import HandoffProjectionRecord
from glassbox.runtime.context import RuntimeContext


def handoff_bad_request(detail: str) -> HTTPException:
    """Build a stable bad-request response for handoff route helpers."""

    return HTTPException(status_code=400, detail=detail)


def handoff_not_found(detail: str = "handoff record not found") -> HTTPException:
    """Build a stable not-found response for handoff route helpers."""

    return HTTPException(status_code=404, detail=detail)


def require_handoff_record(
    context: RuntimeContext,
    session_id: UUID,
    package_id: str,
) -> HandoffProjectionRecord:
    """Load a projected handoff record or raise the route-local 404."""

    repository = cast(Any, context.repositories.sessions)
    record = repository.get_handoff(session_id, package_id)
    if record is None:
        raise handoff_not_found()
    return record


__all__ = [
    "handoff_bad_request",
    "handoff_not_found",
    "require_handoff_record",
]
