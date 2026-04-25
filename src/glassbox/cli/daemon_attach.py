"""Live terminal attach helpers for daemon-owned workspace sessions."""

import argparse
import asyncio
import json
import sys
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass
from uuid import UUID

import httpx

from glassbox.cli.interactive_session import _interactive_blocked_input_message
from glassbox.cli.interactive_session import _interactive_help_text
from glassbox.cli.interactive_session import _interactive_mode
from glassbox.cli.interactive_session import _interactive_prompt_label
from glassbox.cli.interactive_session import _parse_interactive_input
from glassbox.cli.interactive_session import _read_interactive_input_async
from glassbox.cli.interactive_session import _render_interactive_prompt_context
from glassbox.cli.renderer import CliEventRenderer
from glassbox.cli.renderer import InteractivePromptState
from glassbox.cli.status_formatters import _format_current_turn_line
from glassbox.cli.status_formatters import _format_next_action_line
from glassbox.cli.status_formatters import _format_pending_question_line
from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionFailed
from glassbox.core.models import SessionState
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import SessionStatus
from glassbox.web.session_api import SessionSnapshotResponse


@dataclass(frozen=True, slots=True)
class _DaemonSessionClient:
    client: httpx.AsyncClient
    session_id: UUID
    dashboard_url: str

    async def fetch_snapshot(self) -> SessionSnapshotResponse:
        response = await _request_runtime(
            self.client,
            "GET",
            f"/sessions/{self.session_id}",
            dashboard_url=self.dashboard_url,
        )
        if response.status_code == 404:
            raise ValueError(f"unknown session_id: {self.session_id}")
        response.raise_for_status()
        return SessionSnapshotResponse.model_validate(response.json())

    async def resolve_approval(self, approval_id: UUID, decision: str) -> None:
        response = await _request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/approvals/{approval_id}",
            dashboard_url=self.dashboard_url,
            json={"decision": decision},
        )
        _raise_for_conflict_or_missing(response)

    async def submit_message(self, text: str) -> None:
        response = await _request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/messages",
            dashboard_url=self.dashboard_url,
            json={"text": text},
        )
        _raise_for_conflict_or_missing(response)

    async def submit_answer(self, question_id: UUID, answer: str) -> None:
        response = await _request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/questions/{question_id}",
            dashboard_url=self.dashboard_url,
            json={"answer": answer},
        )
        _raise_for_conflict_or_missing(response)


async def attach_via_daemon(
    args: argparse.Namespace,
    *,
    dashboard_url: str,
) -> int:
    """Attach the terminal UI to a daemon-owned live session over HTTP."""

    session_id = args.session_id
    async with httpx.AsyncClient(
        base_url=dashboard_url.rstrip("/"),
        timeout=httpx.Timeout(5.0, connect=1.0, read=None, write=5.0),
    ) as client:
        daemon_session = _DaemonSessionClient(client, session_id, dashboard_url)
        snapshot = await daemon_session.fetch_snapshot()
        _ensure_snapshot_can_live_attach(snapshot)

        prompt_state = InteractivePromptState()
        renderer = CliEventRenderer(sys.stdout, prompt_state=prompt_state)
        stop_stream = asyncio.Event()
        stream_task = asyncio.create_task(
            _render_live_events(
                client,
                session_id,
                dashboard_url=dashboard_url,
                after_sequence=snapshot.last_sequence,
                renderer=renderer,
                prompt_state=prompt_state,
                stop_stream=stop_stream,
            )
        )
        try:
            _write_prompt_safe_line(
                prompt_state,
                f"Attached to live session {session_id} via {dashboard_url}",
            )
            return await _interactive_remote_session_loop(
                daemon_session,
                prompt_state=prompt_state,
            )
        finally:
            stop_stream.set()
            stream_task.cancel()
            with suppress(asyncio.CancelledError):
                await stream_task


async def _interactive_remote_session_loop(
    daemon_session: _DaemonSessionClient,
    *,
    prompt_state: InteractivePromptState,
) -> int:
    while True:
        snapshot = await daemon_session.fetch_snapshot()
        state = _session_state_from_snapshot(snapshot)

        if _is_terminal_status(state.status):
            _write_prompt_safe_line(
                prompt_state,
                _historical_only_message(daemon_session.session_id, state.status),
            )
            return 0

        mode = _interactive_mode(state)
        prompt_context_lines = _interactive_remote_prompt_context_lines(
            daemon_session.session_id,
            snapshot,
            state,
            mode,
        )
        _render_interactive_prompt_context(prompt_context_lines)

        prompt_label = _interactive_prompt_label(mode)
        prompt_state.activate(prompt_label, prompt_context_lines)
        try:
            user_input = await _read_interactive_input_async(prompt_label)
        except EOFError, KeyboardInterrupt:
            prompt_state.clear()
            print()
            print(f"Leaving interactive session {daemon_session.session_id}")
            return 0
        finally:
            prompt_state.clear()

        snapshot = await daemon_session.fetch_snapshot()
        state = _session_state_from_snapshot(snapshot)
        mode = _interactive_mode(state)

        action_kind, action_value = _parse_interactive_input(user_input)
        if action_kind == "continue":
            continue
        if action_kind == "exit":
            print(f"Leaving interactive session {daemon_session.session_id}")
            return 0
        if action_kind == "help":
            print(_interactive_help_text(mode))
            continue
        if action_kind == "status":
            _print_remote_session_status(snapshot)
            continue
        if action_kind == "approve":
            await _handle_remote_approval_action(
                daemon_session,
                state=state,
                decision=ApprovalDecision.APPROVED,
            )
            continue
        if action_kind == "deny":
            await _handle_remote_approval_action(
                daemon_session,
                state=state,
                decision=ApprovalDecision.DENIED,
            )
            continue
        if action_kind == "submit":
            await _handle_remote_submit_action(
                daemon_session,
                state=state,
                mode=mode,
                action_value=action_value,
            )


async def _handle_remote_approval_action(
    daemon_session: _DaemonSessionClient,
    *,
    state: SessionState,
    decision: ApprovalDecision,
) -> None:
    if state.status != SessionStatus.AWAITING_APPROVAL:
        print(_interactive_blocked_input_message(state, daemon_session.session_id))
        return
    approval_id = state.pending_approval_id
    if approval_id is None:
        print(_interactive_blocked_input_message(state, daemon_session.session_id))
        return

    await daemon_session.resolve_approval(approval_id, decision.value)


async def _handle_remote_submit_action(
    daemon_session: _DaemonSessionClient,
    *,
    state: SessionState,
    mode: str,
    action_value: str,
) -> None:
    if mode == "prompt":
        await daemon_session.submit_message(action_value)
        return
    if mode == "answer":
        question_id = state.pending_question_id
        if question_id is None:
            print(_interactive_blocked_input_message(state, daemon_session.session_id))
            return
        await daemon_session.submit_answer(question_id, action_value)
        return
    print(_interactive_blocked_input_message(state, daemon_session.session_id))


async def _render_live_events(
    client: httpx.AsyncClient,
    session_id: UUID,
    *,
    dashboard_url: str,
    after_sequence: int,
    renderer: CliEventRenderer,
    prompt_state: InteractivePromptState,
    stop_stream: asyncio.Event,
) -> None:
    last_sequence = after_sequence
    reconnect_attempts = 0

    while not stop_stream.is_set():
        if reconnect_attempts > 0:
            _write_prompt_safe_line(prompt_state, "Live runtime stream reconnecting...")
        try:
            async with client.stream(
                "GET",
                f"/sessions/{session_id}/events",
                params={"after": last_sequence},
            ) as response:
                if response.status_code == 404:
                    raise ValueError(f"unknown session_id: {session_id}")
                response.raise_for_status()
                if reconnect_attempts > 0:
                    _write_prompt_safe_line(
                        prompt_state,
                        "Live runtime stream reconnected.",
                    )
                reconnect_attempts = 0
                async for event in _iter_sse_events(response):
                    if stop_stream.is_set():
                        return
                    last_sequence = max(last_sequence, event.sequence)
                    renderer.render_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            reconnect_attempts += 1
            if stop_stream.is_set():
                return
            if reconnect_attempts >= 3:
                raise ValueError(
                    "live runtime became unavailable at "
                    f"{dashboard_url} while attached to session {session_id}: {exc}"
                ) from exc
            await asyncio.sleep(0.1 * reconnect_attempts)


async def _iter_sse_events(
    response: httpx.Response,
) -> AsyncIterator[EventEnvelope]:
    data_lines: list[str] = []

    async for line in response.aiter_lines():
        if line.startswith(":"):
            continue
        if line == "":
            if data_lines:
                payload = json.loads("\n".join(data_lines))
                event = EventEnvelope.model_validate(payload)
                yield event
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
        event = EventEnvelope.model_validate(payload)
        yield event


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
        raise ValueError(f"live runtime unavailable at {dashboard_url}: {exc}") from exc


def _raise_for_conflict_or_missing(response: httpx.Response) -> None:
    if response.status_code in {404, 409}:
        detail = response.json().get("detail", response.text)
        raise ValueError(str(detail))
    response.raise_for_status()


def _ensure_snapshot_can_live_attach(snapshot: SessionSnapshotResponse) -> None:
    status = SessionStatus(snapshot.status)
    if _is_terminal_status(status):
        raise ValueError(_historical_only_message(UUID(snapshot.session_id), status))


def _session_state_from_snapshot(snapshot: SessionSnapshotResponse) -> SessionState:
    return SessionState(
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


def _interactive_remote_prompt_context_lines(
    session_id: UUID,
    snapshot: SessionSnapshotResponse,
    state: SessionState,
    mode: str,
) -> list[str]:
    if mode == "answer":
        return [
            _format_pending_question_line(
                state.pending_question_id,
                snapshot.pending_question_text,
            ),
            "Interactive mode: answer the pending question, or use /status, "
            "/help, or /exit.",
        ]
    if mode == "approval":
        return [
            _interactive_blocked_input_message(state, session_id),
            "Interactive mode: use /approve, /deny, /status, /help, or /exit.",
        ]
    if mode == "prompt":
        return [
            "Interactive mode: type the next prompt, or use /status, /help, or /exit."
        ]
    return [
        "Live runtime is still processing this session. "
        "Use /status, /help, or /exit while waiting for updates."
    ]


def _print_remote_session_status(snapshot: SessionSnapshotResponse) -> None:
    state = _session_state_from_snapshot(snapshot)
    print(f"Session {snapshot.session_id}")
    print(f"Status: {snapshot.status}")
    print(f"Last sequence: {snapshot.last_sequence}")
    print(_format_current_turn_line(state.current_turn_id, snapshot.status))
    print(f"Workspace: {snapshot.cwd}")
    print(f"Model: {snapshot.model_name}")
    print(f"Approval mode: {snapshot.approval_mode}")
    if snapshot.dashboard_url is not None:
        print(f"Dashboard URL: {snapshot.dashboard_url}")
    if snapshot.pending_question_id is not None:
        print(
            _format_pending_question_line(
                state.pending_question_id,
                snapshot.pending_question_text,
            )
        )
    failure = None
    if snapshot.session_failure_message is not None:
        failure = SessionFailed(
            error_message=snapshot.session_failure_message,
            retryable=bool(snapshot.session_failure_retryable),
        )
    print(
        _format_next_action_line(
            UUID(snapshot.session_id),
            snapshot.status,
            state.current_turn_id,
            state.pending_approval_id,
            state.pending_question_id,
            failure,
        )
    )


def _write_prompt_safe_line(
    prompt_state: InteractivePromptState,
    line: str,
) -> None:
    if prompt_state.prompt_label is not None:
        sys.stdout.write("\n")
        sys.stdout.write(f"{line}\n")
        for context_line in prompt_state.context_lines:
            sys.stdout.write(f"{context_line}\n")
        sys.stdout.write(prompt_state.prompt_label)
    else:
        sys.stdout.write(f"{line}\n")
    sys.stdout.flush()


def _historical_only_message(session_id: UUID, status: SessionStatus) -> str:
    return (
        f"session {session_id} is only historically inspectable in status {status}; "
        "live attach is unavailable"
    )


def _is_terminal_status(status: SessionStatus) -> bool:
    return status in {
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.CANCELLED,
    }
