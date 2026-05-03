"""Runtime-agnostic client boundary for interactive terminal sessions."""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from typing import cast
from uuid import UUID

import httpx

from glassbox.cli.status_formatters import _pending_question_text_from_events
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
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


class ReviewLoopAction(StrEnum):
    STATUS = "status"
    REFRESH_INVENTORY = "refresh_inventory"
    GENERATE_BRIEF = "generate_brief"
    PREVIEW_VERIFICATION = "preview_verification"
    INSPECT_HANDOFF = "inspect_handoff"
    SHOW_FEEDBACK_STATUS = "show_feedback_status"


@dataclass(frozen=True, slots=True)
class ReviewLoopActionResult:
    """Terminal-friendly summary of one review-loop action."""

    action: ReviewLoopAction | str
    headline: str
    changeset_id: str | None = None
    details: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    safe_next_actions: tuple[str, ...] = ()
    dashboard_path: str | None = None


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

    async def cancel_turn(
        self,
        turn_id: TurnId | None = None,
        *,
        reason: str | None = None,
    ) -> None: ...

    async def create_review_changeset(
        self,
        *,
        objective: str | None = None,
    ) -> ReviewLoopActionResult: ...

    async def run_review_action(
        self,
        action: ReviewLoopAction,
        *,
        changeset_id: str | None = None,
    ) -> ReviewLoopActionResult: ...

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

    async def cancel_turn(
        self,
        turn_id: TurnId | None = None,
        *,
        reason: str | None = None,
    ) -> None:
        await self.runtime_context.services.session_service.cancel_turn(
            self.session_id,
            turn_id=turn_id,
            requested_by="terminal",
            reason=reason,
        )

    async def create_review_changeset(
        self,
        *,
        objective: str | None = None,
    ) -> ReviewLoopActionResult:
        from glassbox.runtime.changesets import ChangesetDerivationService

        workspace_root = self._workspace_root()
        result = ChangesetDerivationService(
            self._changeset_repository()
        ).create_from_workspace_diff(
            self.session_id,
            workspace_root,
            objective=objective,
        )
        changeset_id = str(result.changeset_id)
        return ReviewLoopActionResult(
            action="create",
            headline=f"Created review changeset {changeset_id}",
            changeset_id=changeset_id,
            details=(
                "Source: current workspace diff for this chat session.",
                "No tests, staging, commit, push, PR, or merge was run.",
            ),
            limitations=tuple(result.limitations),
            safe_next_actions=(
                f"glassbox changeset show {changeset_id} --cwd .",
                f"glassbox changeset verification-plan {changeset_id} --cwd .",
                f"glassbox changeset brief {changeset_id} --cwd .",
                f"glassbox changeset handoff-readiness {changeset_id} --cwd .",
            ),
            dashboard_path=f"/app/changesets/{changeset_id}",
        )

    async def run_review_action(
        self,
        action: ReviewLoopAction,
        *,
        changeset_id: str | None = None,
    ) -> ReviewLoopActionResult:
        resolved_changeset_id = UUID(changeset_id) if changeset_id else None
        if resolved_changeset_id is None:
            resolved_changeset_id = self._latest_changeset_id()
        if resolved_changeset_id is None:
            raise InteractiveClientError(
                InteractiveClientErrorKind.VALIDATION_ERROR,
                "No changeset exists for this session. Start with /review create.",
            )
        workspace_root = self._workspace_root()
        repository = self._changeset_repository()
        artifact_repository = self.runtime_context.repositories.artifacts
        if action == ReviewLoopAction.STATUS:
            from glassbox.runtime.changesets import ChangesetQueryService

            detail = ChangesetQueryService(repository).get_detail(
                resolved_changeset_id,
                workspace_root=workspace_root,
            )
            summary = detail.review_response_summary
            return ReviewLoopActionResult(
                action=action,
                headline=f"Review status for changeset {resolved_changeset_id}",
                changeset_id=str(resolved_changeset_id),
                details=(
                    f"{summary.total_feedback_count} feedback item(s), "
                    f"{summary.unresolved_count} unresolved, "
                    f"{summary.stale_response_count} stale response check(s).",
                    f"Inventory: {detail.inventory_status.freshness.value}.",
                ),
                limitations=tuple(detail.limitations),
                safe_next_actions=tuple(detail.safe_next_actions),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        if action == ReviewLoopAction.REFRESH_INVENTORY:
            from glassbox.runtime.changesets import ChangesetActionService

            result = await ChangesetActionService(
                repository,
                artifact_repository,
            ).refresh_inventory(
                resolved_changeset_id,
                workspace_root,
                refreshed_by="terminal",
            )
            return ReviewLoopActionResult(
                action=action,
                headline=f"Refreshed review inventory for {resolved_changeset_id}",
                changeset_id=str(resolved_changeset_id),
                details=(
                    f"Inventory artifact: {result.artifact.artifact_id}",
                    f"Freshness: {result.freshness.value}",
                ),
                safe_next_actions=(
                    f"glassbox changeset show {resolved_changeset_id} --cwd .",
                    "glassbox changeset verification-plan "
                    f"{resolved_changeset_id} --cwd .",
                ),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        if action == ReviewLoopAction.GENERATE_BRIEF:
            from glassbox.runtime.changesets import ChangesetReviewBriefService

            result = ChangesetReviewBriefService(
                repository,
                artifact_repository,
            ).generate(
                resolved_changeset_id,
                workspace_root,
                created_by="terminal",
            )
            return ReviewLoopActionResult(
                action=action,
                headline=f"Generated lifecycle brief for {resolved_changeset_id}",
                changeset_id=str(resolved_changeset_id),
                details=(f"Brief artifact: {result.artifact.artifact_id}",),
                limitations=tuple(result.limitations),
                safe_next_actions=(
                    f"glassbox changeset show {resolved_changeset_id} --cwd .",
                    "glassbox changeset handoff-readiness "
                    f"{resolved_changeset_id} --cwd .",
                ),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        if action == ReviewLoopAction.PREVIEW_VERIFICATION:
            from glassbox.runtime.changesets import ChangesetVerificationService

            preview = ChangesetVerificationService(
                repository,
                artifact_repository,
            ).preview_plan(resolved_changeset_id, workspace_root)
            command_count = len(preview.recommended_commands)
            return ReviewLoopActionResult(
                action=action,
                headline=f"Previewed verification for {resolved_changeset_id}",
                changeset_id=str(resolved_changeset_id),
                details=(
                    f"Readiness: {preview.readiness.state.value}",
                    f"{command_count} recommended command(s); none were run.",
                ),
                limitations=tuple(preview.limitations),
                safe_next_actions=tuple(preview.safe_next_actions),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        if action == ReviewLoopAction.INSPECT_HANDOFF:
            from glassbox.runtime.handoff_readiness import (
                ChangesetHandoffReadinessService,
            )

            readiness = await ChangesetHandoffReadinessService(
                repository,
                artifact_repository,
            ).preview(resolved_changeset_id, workspace_root)
            return ReviewLoopActionResult(
                action=action,
                headline=f"Handoff readiness for {resolved_changeset_id}",
                changeset_id=str(resolved_changeset_id),
                details=(
                    f"State: {readiness.state}",
                    readiness.reason,
                    f"{len(readiness.blockers)} blocker(s).",
                ),
                limitations=tuple(readiness.limitations),
                safe_next_actions=tuple(readiness.safe_next_actions),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        if action == ReviewLoopAction.SHOW_FEEDBACK_STATUS:
            from glassbox.runtime.changesets import ChangesetQueryService

            summary = ChangesetQueryService(repository).get_review_response_summary(
                resolved_changeset_id,
                workspace_root=workspace_root,
            )
            return ReviewLoopActionResult(
                action=action,
                headline=f"Feedback status for {resolved_changeset_id}",
                changeset_id=str(resolved_changeset_id),
                details=(
                    f"{summary.total_feedback_count} feedback item(s), "
                    f"{summary.unresolved_count} unresolved.",
                    f"{summary.stale_response_count} stale response check(s).",
                ),
                safe_next_actions=tuple(summary.safe_next_actions),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        raise InteractiveClientError(
            InteractiveClientErrorKind.VALIDATION_ERROR,
            f"unsupported review action: {action}",
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

    def _workspace_root(self) -> Path:
        session = self.runtime_context.repositories.sessions.get_session(
            self.session_id
        )
        if session is None:
            raise InteractiveClientError(
                InteractiveClientErrorKind.UNKNOWN_SESSION,
                f"unknown session_id: {self.session_id}",
            )
        return session.cwd

    def _latest_changeset_id(self) -> UUID | None:
        changesets = self.runtime_context.repositories.sessions.list_changesets(
            session_id=self.session_id,
            include_archived=False,
            limit=1,
        )
        return changesets[0].changeset_id if changesets else None

    def _changeset_repository(self):
        from glassbox.runtime.changesets import ChangesetRepository

        return cast(ChangesetRepository, self.runtime_context.repositories.sessions)


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

    async def cancel_turn(
        self,
        turn_id: TurnId | None = None,
        *,
        reason: str | None = None,
    ) -> None:
        response = await _request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/cancel",
            dashboard_url=self.dashboard_url,
            json={"reason": reason, "turn_id": str(turn_id) if turn_id else None},
        )
        _raise_for_action_error(response)

    async def create_review_changeset(
        self,
        *,
        objective: str | None = None,
    ) -> ReviewLoopActionResult:
        response = await _request_runtime(
            self.client,
            "POST",
            "/changesets",
            dashboard_url=self.dashboard_url,
            json={
                "source_kind": "workspace-diff",
                "session_id": str(self.session_id),
                "objective": objective,
            },
        )
        _raise_for_action_error(response)
        payload = response.json()
        changeset_id = str(payload["changeset_id"])
        limitations = tuple(str(item) for item in payload.get("limitations", []))
        return ReviewLoopActionResult(
            action="create",
            headline=f"Created review changeset {changeset_id}",
            changeset_id=changeset_id,
            details=(
                "Source: current workspace diff for this chat session.",
                "No tests, staging, commit, push, PR, or merge was run.",
            ),
            limitations=limitations,
            safe_next_actions=(
                f"glassbox changeset show {changeset_id} --cwd .",
                f"glassbox changeset verification-plan {changeset_id} --cwd .",
                f"glassbox changeset brief {changeset_id} --cwd .",
                f"glassbox changeset handoff-readiness {changeset_id} --cwd .",
            ),
            dashboard_path=f"/app/changesets/{changeset_id}",
        )

    async def run_review_action(
        self,
        action: ReviewLoopAction,
        *,
        changeset_id: str | None = None,
    ) -> ReviewLoopActionResult:
        resolved_changeset_id = changeset_id or await self._latest_changeset_id()
        if resolved_changeset_id is None:
            raise InteractiveClientError(
                InteractiveClientErrorKind.VALIDATION_ERROR,
                "No changeset exists for this session. Start with /review create.",
            )
        if action == ReviewLoopAction.STATUS:
            response = await _request_runtime(
                self.client,
                "GET",
                f"/changesets/{resolved_changeset_id}",
                dashboard_url=self.dashboard_url,
            )
            _raise_for_action_error(response)
            payload = response.json()
            review_summary = payload["review_response_summary"]
            inventory_status = payload["inventory_status"]
            return ReviewLoopActionResult(
                action=action,
                headline=f"Review status for changeset {resolved_changeset_id}",
                changeset_id=resolved_changeset_id,
                details=(
                    (
                        f"{review_summary['total_feedback_count']} feedback item(s), "
                        f"{review_summary['unresolved_count']} unresolved, "
                        f"{review_summary['stale_response_count']} stale response "
                        "check(s)."
                    ),
                    f"Inventory: {inventory_status['freshness']}.",
                ),
                limitations=_string_tuple(payload.get("limitations", [])),
                safe_next_actions=_string_tuple(payload.get("safe_next_actions", [])),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        if action == ReviewLoopAction.REFRESH_INVENTORY:
            response = await _request_runtime(
                self.client,
                "POST",
                f"/changesets/{resolved_changeset_id}/refresh",
                dashboard_url=self.dashboard_url,
                json={"actor": "terminal"},
            )
            _raise_for_action_error(response)
            payload = response.json()
            detail = payload.get("detail", {})
            inventory = detail.get("inventory") or {}
            return ReviewLoopActionResult(
                action=action,
                headline=f"Refreshed review inventory for {resolved_changeset_id}",
                changeset_id=resolved_changeset_id,
                details=(
                    f"Inventory artifact: {inventory.get('artifact_id', 'unknown')}",
                    f"Status: {payload.get('status', 'refreshed')}",
                ),
                safe_next_actions=(
                    f"glassbox changeset show {resolved_changeset_id} --cwd .",
                    "glassbox changeset verification-plan "
                    f"{resolved_changeset_id} --cwd .",
                ),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        if action == ReviewLoopAction.GENERATE_BRIEF:
            response = await _request_runtime(
                self.client,
                "POST",
                f"/changesets/{resolved_changeset_id}/brief",
                dashboard_url=self.dashboard_url,
                json={"actor": "terminal", "include_markdown": False},
            )
            _raise_for_action_error(response)
            payload = response.json()
            return ReviewLoopActionResult(
                action=action,
                headline=f"Generated lifecycle brief for {resolved_changeset_id}",
                changeset_id=resolved_changeset_id,
                details=(f"Brief artifact: {payload['artifact_id']}",),
                limitations=_string_tuple(payload.get("limitations", [])),
                safe_next_actions=(
                    f"glassbox changeset show {resolved_changeset_id} --cwd .",
                    "glassbox changeset handoff-readiness "
                    f"{resolved_changeset_id} --cwd .",
                ),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        if action == ReviewLoopAction.PREVIEW_VERIFICATION:
            response = await _request_runtime(
                self.client,
                "GET",
                f"/changesets/{resolved_changeset_id}/verification-plan",
                dashboard_url=self.dashboard_url,
            )
            _raise_for_action_error(response)
            payload = response.json()
            commands = payload.get("recommended_commands", [])
            readiness = payload.get("readiness", {})
            return ReviewLoopActionResult(
                action=action,
                headline=f"Previewed verification for {resolved_changeset_id}",
                changeset_id=resolved_changeset_id,
                details=(
                    f"Readiness: {readiness.get('state', 'unknown')}",
                    f"{len(commands)} recommended command(s); none were run.",
                ),
                limitations=_string_tuple(payload.get("limitations", [])),
                safe_next_actions=_string_tuple(payload.get("safe_next_actions", [])),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        if action == ReviewLoopAction.INSPECT_HANDOFF:
            response = await _request_runtime(
                self.client,
                "GET",
                f"/changesets/{resolved_changeset_id}/handoff-readiness",
                dashboard_url=self.dashboard_url,
            )
            _raise_for_action_error(response)
            payload = response.json()
            blockers = payload.get("blockers", [])
            return ReviewLoopActionResult(
                action=action,
                headline=f"Handoff readiness for {resolved_changeset_id}",
                changeset_id=resolved_changeset_id,
                details=(
                    f"State: {payload.get('state', 'unknown')}",
                    str(payload.get("reason", "No reason returned.")),
                    f"{len(blockers)} blocker(s).",
                ),
                limitations=_string_tuple(payload.get("limitations", [])),
                safe_next_actions=_string_tuple(payload.get("safe_next_actions", [])),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        if action == ReviewLoopAction.SHOW_FEEDBACK_STATUS:
            response = await _request_runtime(
                self.client,
                "GET",
                "/changesets/feedback",
                dashboard_url=self.dashboard_url,
                params={"changeset_id": resolved_changeset_id},
            )
            _raise_for_action_error(response)
            payload = response.json()
            summary = payload.get("response_summary") or {}
            return ReviewLoopActionResult(
                action=action,
                headline=f"Feedback status for {resolved_changeset_id}",
                changeset_id=resolved_changeset_id,
                details=(
                    (
                        f"{summary.get('total_feedback_count', 0)} feedback item(s), "
                        f"{summary.get('unresolved_count', 0)} unresolved."
                    ),
                    (
                        f"{summary.get('stale_response_count', 0)} stale response "
                        "check(s)."
                    ),
                ),
                safe_next_actions=_string_tuple(summary.get("safe_next_actions", [])),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
            )
        raise InteractiveClientError(
            InteractiveClientErrorKind.VALIDATION_ERROR,
            f"unsupported review action: {action}",
        )

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

    async def _latest_changeset_id(self) -> str | None:
        response = await _request_runtime(
            self.client,
            "GET",
            "/changesets",
            dashboard_url=self.dashboard_url,
            params={"session_id": str(self.session_id), "limit": 1},
        )
        _raise_for_action_error(response)
        items = response.json().get("items", [])
        if not items:
            return None
        return str(items[0]["changeset_id"])


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


def _string_tuple(items: object) -> tuple[str, ...]:
    if not isinstance(items, list):
        return ()
    return tuple(str(item) for item in items)
