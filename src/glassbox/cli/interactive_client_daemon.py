"""Daemon-backed implementation for interactive terminal sessions."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from glassbox.cli.interactive_client_models import InteractiveClientError
from glassbox.cli.interactive_client_models import InteractiveClientErrorKind
from glassbox.cli.interactive_client_models import InteractiveSessionSnapshot
from glassbox.cli.interactive_client_models import ReviewLoopAction
from glassbox.cli.interactive_client_models import ReviewLoopActionResult
from glassbox.cli.interactive_client_sse import interactive_snapshot_from_response
from glassbox.cli.interactive_client_sse import iter_sse_events
from glassbox.cli.interactive_client_sse import raise_for_action_error
from glassbox.cli.interactive_client_sse import request_runtime
from glassbox.cli.interactive_review_actions import create_changeset_result
from glassbox.cli.interactive_review_actions import generate_brief_result
from glassbox.cli.interactive_review_actions import payload_feedback_status_result
from glassbox.cli.interactive_review_actions import payload_handoff_readiness_result
from glassbox.cli.interactive_review_actions import payload_refresh_inventory_result
from glassbox.cli.interactive_review_actions import payload_review_status_result
from glassbox.cli.interactive_review_actions import preview_verification_result
from glassbox.cli.interactive_review_actions import string_tuple
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.types import ApprovalDecision
from glassbox.web.session_api import SessionSnapshotResponse


@dataclass(slots=True)
class DaemonInteractiveSessionClient:
    """Interactive client backed by daemon HTTP actions and SSE events."""

    client: httpx.AsyncClient
    session_id: SessionId
    dashboard_url: str

    async def fetch_snapshot(self) -> InteractiveSessionSnapshot:
        response = await request_runtime(
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

        response = await request_runtime(
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
        response = await request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/messages",
            dashboard_url=self.dashboard_url,
            json={"text": text},
        )
        raise_for_action_error(response)

    async def submit_answer(self, question_id: QuestionId, answer: str) -> None:
        response = await request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/questions/{question_id}",
            dashboard_url=self.dashboard_url,
            json={"answer": answer},
        )
        raise_for_action_error(response)

    async def resolve_approval(
        self,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None:
        response = await request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/approvals/{approval_id}",
            dashboard_url=self.dashboard_url,
            json={"decision": decision.value},
        )
        raise_for_action_error(response)

    async def cancel_turn(
        self,
        turn_id: TurnId | None = None,
        *,
        reason: str | None = None,
    ) -> None:
        response = await request_runtime(
            self.client,
            "POST",
            f"/sessions/{self.session_id}/cancel",
            dashboard_url=self.dashboard_url,
            json={"reason": reason, "turn_id": str(turn_id) if turn_id else None},
        )
        raise_for_action_error(response)

    async def create_review_changeset(
        self,
        *,
        objective: str | None = None,
    ) -> ReviewLoopActionResult:
        response = await request_runtime(
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
        raise_for_action_error(response)
        payload = response.json()
        changeset_id = str(payload["changeset_id"])
        return create_changeset_result(
            changeset_id,
            limitations=string_tuple(payload.get("limitations", [])),
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
            response = await request_runtime(
                self.client,
                "GET",
                f"/changesets/{resolved_changeset_id}",
                dashboard_url=self.dashboard_url,
            )
            raise_for_action_error(response)
            return payload_review_status_result(
                resolved_changeset_id,
                response.json(),
            )
        if action == ReviewLoopAction.REFRESH_INVENTORY:
            response = await request_runtime(
                self.client,
                "POST",
                f"/changesets/{resolved_changeset_id}/refresh",
                dashboard_url=self.dashboard_url,
                json={"actor": "terminal"},
            )
            raise_for_action_error(response)
            return payload_refresh_inventory_result(
                resolved_changeset_id,
                response.json(),
            )
        if action == ReviewLoopAction.GENERATE_BRIEF:
            response = await request_runtime(
                self.client,
                "POST",
                f"/changesets/{resolved_changeset_id}/brief",
                dashboard_url=self.dashboard_url,
                json={"actor": "terminal", "include_markdown": False},
            )
            raise_for_action_error(response)
            payload = response.json()
            return generate_brief_result(
                resolved_changeset_id,
                artifact_id=str(payload["artifact_id"]),
                limitations=string_tuple(payload.get("limitations", [])),
            )
        if action == ReviewLoopAction.PREVIEW_VERIFICATION:
            response = await request_runtime(
                self.client,
                "GET",
                f"/changesets/{resolved_changeset_id}/verification-plan",
                dashboard_url=self.dashboard_url,
            )
            raise_for_action_error(response)
            payload = response.json()
            commands = payload.get("recommended_commands", [])
            readiness = payload.get("readiness", {})
            return preview_verification_result(
                resolved_changeset_id,
                readiness_state=str(readiness.get("state", "unknown")),
                command_count=len(commands),
                limitations=string_tuple(payload.get("limitations", [])),
                safe_next_actions=string_tuple(payload.get("safe_next_actions", [])),
            )
        if action == ReviewLoopAction.INSPECT_HANDOFF:
            response = await request_runtime(
                self.client,
                "GET",
                f"/changesets/{resolved_changeset_id}/handoff-readiness",
                dashboard_url=self.dashboard_url,
            )
            raise_for_action_error(response)
            return payload_handoff_readiness_result(
                resolved_changeset_id,
                response.json(),
            )
        if action == ReviewLoopAction.SHOW_FEEDBACK_STATUS:
            response = await request_runtime(
                self.client,
                "GET",
                "/changesets/feedback",
                dashboard_url=self.dashboard_url,
                params={"changeset_id": resolved_changeset_id},
            )
            raise_for_action_error(response)
            payload = response.json()
            summary = payload.get("response_summary") or {}
            return payload_feedback_status_result(
                resolved_changeset_id,
                summary,
            )
        if action == ReviewLoopAction.RECORD_FEEDBACK_FIXUP:
            raise InteractiveClientError(
                InteractiveClientErrorKind.VALIDATION_ERROR,
                "Remote /review fixup is not available yet; use "
                "glassbox changeset feedback fixup FEEDBACK_ID --cwd .",
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
        response = await request_runtime(
            self.client,
            "GET",
            "/changesets",
            dashboard_url=self.dashboard_url,
            params={"session_id": str(self.session_id), "limit": 1},
        )
        raise_for_action_error(response)
        items = response.json().get("items", [])
        if not items:
            return None
        return str(items[0]["changeset_id"])
