"""Runtime-agnostic client boundary for interactive terminal sessions."""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

import httpx

from glassbox.cli.status_formatters import _pending_question_text_from_events
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.models import SessionState
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import SessionStatus
from glassbox.runtime.context import RuntimeContext
from glassbox.web.session_api import SessionSnapshotResponse


class InteractiveClientErrorKind(StrEnum):
    UNKNOWN_SESSION = "unknown_session"
    HISTORICAL_ONLY = "historical_only"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    STREAM_UNAVAILABLE = "stream_unavailable"


class InteractiveClientError(ValueError):
    """Normalized error raised by interactive session clients."""

    def __init__(self, kind: InteractiveClientErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True, slots=True)
class InteractiveSessionSnapshot:
    """Client-neutral session state used by terminal UI entrypoints."""

    state: SessionState
    cwd: str | None = None
    model_name: str | None = None
    approval_mode: str | None = None
    dashboard_url: str | None = None
    pending_question_text: str | None = None

    @property
    def session_id(self) -> SessionId:
        return self.state.session_id

    @property
    def last_sequence(self) -> int:
        return self.state.last_sequence


class InteractiveSessionClient(Protocol):
    """Common mutation and event-stream boundary for terminal clients."""

    @property
    def session_id(self) -> SessionId: ...

    async def fetch_snapshot(self) -> InteractiveSessionSnapshot: ...

    async def submit_message(self, text: str) -> None: ...

    async def submit_answer(self, question_id: QuestionId, answer: str) -> None: ...

    async def resolve_approval(
        self,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None: ...

    def stream_events(
        self, *, after_sequence: int = 0
    ) -> AsyncIterator[EventEnvelope]: ...

    async def aclose(self) -> None: ...


@dataclass(slots=True)
class LocalInteractiveSessionClient:
    """Interactive client backed by the in-process runtime context."""

    runtime_context: RuntimeContext
    session_id: SessionId
    dashboard_url: str | None = None

    async def fetch_snapshot(self) -> InteractiveSessionSnapshot:
        repository = self.runtime_context.repositories.sessions
        state = repository.get_session_state(self.session_id)
        if state is None:
            raise InteractiveClientError(
                InteractiveClientErrorKind.UNKNOWN_SESSION,
                f"unknown session_id: {self.session_id}",
            )
        record = repository.get_session(self.session_id)
        events = repository.read_session_events(self.session_id)
        return InteractiveSessionSnapshot(
            state=state,
            cwd=str(record.cwd) if record is not None else None,
            model_name=record.model_name if record is not None else None,
            approval_mode=record.approval_mode if record is not None else None,
            dashboard_url=self.dashboard_url,
            pending_question_text=_pending_question_text_from_events(
                events,
                state.pending_question_id,
            ),
        )

    async def submit_message(self, text: str) -> None:
        await self.runtime_context.services.session_service.submit_user_message(
            self.session_id,
            text,
        )

    async def submit_answer(self, question_id: QuestionId, answer: str) -> None:
        await self.runtime_context.services.session_service.provide_user_answer(
            self.session_id,
            question_id,
            answer,
        )

    async def resolve_approval(
        self,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None:
        await self.runtime_context.services.session_service.resolve_approval(
            self.session_id,
            approval_id,
            decision,
        )

    async def stream_events(
        self,
        *,
        after_sequence: int = 0,
    ) -> AsyncIterator[EventEnvelope]:
        last_sequence = after_sequence
        repository = self.runtime_context.repositories.sessions
        for event in repository.read_session_events_after(
            self.session_id,
            after_sequence,
        ):
            last_sequence = max(last_sequence, event.sequence)
            yield event

        event_transport = self.runtime_context.infrastructure.event_transport
        async with event_transport.subscribe() as subscription:
            async for event in subscription:
                if event.session_id != self.session_id:
                    continue
                if event.sequence <= last_sequence:
                    continue
                last_sequence = event.sequence
                yield event

    async def aclose(self) -> None:
        return None


@dataclass(slots=True)
class DaemonInteractiveSessionClient:
    """Interactive client backed by daemon HTTP actions and SSE events."""

    client: httpx.AsyncClient
    session_id: SessionId
    dashboard_url: str

    async def fetch_snapshot(self) -> InteractiveSessionSnapshot:
        response = await _request_runtime(
            self.client,
            "GET",
            f"/sessions/{self.session_id}",
            dashboard_url=self.dashboard_url,
        )
        if response.status_code == 404:
            raise InteractiveClientError(
                InteractiveClientErrorKind.UNKNOWN_SESSION,
                f"unknown session_id: {self.session_id}",
            )
        response.raise_for_status()
        snapshot = SessionSnapshotResponse.model_validate(response.json())
        return interactive_snapshot_from_response(snapshot)

    async def fetch_response_snapshot(self) -> SessionSnapshotResponse:
        """Return the full web snapshot for legacy line-mode status rendering."""

        response = await _request_runtime(
            self.client,
            "GET",
            f"/sessions/{self.session_id}",
            dashboard_url=self.dashboard_url,
        )
        if response.status_code == 404:
            raise InteractiveClientError(
                InteractiveClientErrorKind.UNKNOWN_SESSION,
                f"unknown session_id: {self.session_id}",
            )
        response.raise_for_status()
        return SessionSnapshotResponse.model_validate(response.json())

    async def submit_message(self, text: str) -> None:
        response = await _request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/messages",
            dashboard_url=self.dashboard_url,
            json={"text": text},
        )
        _raise_for_action_error(response)

    async def submit_answer(self, question_id: QuestionId, answer: str) -> None:
        response = await _request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/questions/{question_id}",
            dashboard_url=self.dashboard_url,
            json={"answer": answer},
        )
        _raise_for_action_error(response)

    async def resolve_approval(
        self,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None:
        response = await _request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/approvals/{approval_id}",
            dashboard_url=self.dashboard_url,
            json={"decision": decision.value},
        )
        _raise_for_action_error(response)

    async def stream_events(
        self,
        *,
        after_sequence: int = 0,
    ) -> AsyncIterator[EventEnvelope]:
        try:
            async with self.client.stream(
                "GET",
                f"/sessions/{self.session_id}/events",
                params={"after": after_sequence},
            ) as response:
                if response.status_code == 404:
                    raise InteractiveClientError(
                        InteractiveClientErrorKind.UNKNOWN_SESSION,
                        f"unknown session_id: {self.session_id}",
                    )
                response.raise_for_status()
                async for event in iter_sse_events(response):
                    yield event
        except httpx.HTTPError as exc:
            raise InteractiveClientError(
                InteractiveClientErrorKind.STREAM_UNAVAILABLE,
                f"live runtime stream unavailable at {self.dashboard_url}: {exc}",
            ) from exc

    async def aclose(self) -> None:
        await self.client.aclose()


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

    async for line in response.aiter_lines():
        if line.startswith(":"):
            continue
        if line == "":
            if data_lines:
                payload = json.loads("\n".join(data_lines))
                yield EventEnvelope.model_validate(payload)
            data_lines = []
            continue
        if line.startswith("event:"):
            continue
        if line.startswith("id:"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())

    if data_lines:
        payload = json.loads("\n".join(data_lines))
        yield EventEnvelope.model_validate(payload)


async def _request_runtime(
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


def _raise_for_action_error(response: httpx.Response) -> None:
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
