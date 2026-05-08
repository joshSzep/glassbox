"""SSE parsing and daemon error normalization for interactive clients."""

import json
from collections.abc import AsyncIterator
from uuid import UUID

import httpx

from glassbox.cli.interactive_client_models import InteractiveClientError
from glassbox.cli.interactive_client_models import InteractiveClientErrorKind
from glassbox.cli.interactive_client_models import InteractiveSessionSnapshot
from glassbox.core.events import EventEnvelope
from glassbox.core.models import SessionState
from glassbox.core.types import SessionStatus
from glassbox.web.session_api import SessionSnapshotResponse


def interactive_snapshot_from_response(
    snapshot: SessionSnapshotResponse,
) -> InteractiveSessionSnapshot:
    state = SessionState(
        session_id=UUID(snapshot.session_id),
        status=SessionStatus(snapshot.status),
        current_turn_id=(
            UUID(snapshot.current_turn_id)
            if snapshot.current_turn_id is not None
            else None
        ),
        last_sequence=snapshot.last_sequence,
        pending_approval_id=(
            UUID(snapshot.pending_approval_id)
            if snapshot.pending_approval_id is not None
            else None
        ),
        pending_question_id=(
            UUID(snapshot.pending_question_id)
            if snapshot.pending_question_id is not None
            else None
        ),
    )
    return InteractiveSessionSnapshot(
        state=state,
        cwd=snapshot.cwd,
        model_name=snapshot.model_name,
        approval_mode=snapshot.approval_mode,
        dashboard_url=snapshot.dashboard_url,
        pending_question_text=snapshot.pending_question_text,
    )


async def iter_sse_events(response: httpx.Response) -> AsyncIterator[EventEnvelope]:
    data_lines: list[str] = []
    event_type: str | None = None

    async for line in response.aiter_lines():
        if line.startswith(":"):
            continue
        if line == "":
            if data_lines:
                if event_type != "glassbox.stream.status":
                    payload = json.loads("\n".join(data_lines))
                    yield EventEnvelope.model_validate(payload)
            data_lines = []
            event_type = None
            continue
        if line.startswith("event:"):
            event_type = line[len("event:") :].strip()
            continue
        if line.startswith("id:"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())

    if data_lines:
        if event_type != "glassbox.stream.status":
            payload = json.loads("\n".join(data_lines))
            yield EventEnvelope.model_validate(payload)


async def request_runtime(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    dashboard_url: str,
    **kwargs,
) -> httpx.Response:
    try:
        return await client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise InteractiveClientError(
            InteractiveClientErrorKind.RUNTIME_UNAVAILABLE,
            f"live runtime unavailable at {dashboard_url}: {exc}",
        ) from exc


def raise_for_action_error(response: httpx.Response) -> None:
    if response.status_code == 404:
        raise InteractiveClientError(
            InteractiveClientErrorKind.UNKNOWN_SESSION,
            _response_detail(response),
        )
    if response.status_code == 409:
        raise InteractiveClientError(
            InteractiveClientErrorKind.CONFLICT,
            _response_detail(response),
        )
    if response.status_code == 422:
        raise InteractiveClientError(
            InteractiveClientErrorKind.VALIDATION_ERROR,
            _response_detail(response),
        )
    response.raise_for_status()


def _response_detail(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail", response.text)
    except json.JSONDecodeError:
        detail = response.text
    return str(detail)
