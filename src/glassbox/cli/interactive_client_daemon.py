"""Daemon-backed implementation for interactive terminal sessions."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from typing import cast

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
from glassbox.cli.interactive_review_guidance import payload_handoff_evidence_guidance
from glassbox.cli.interactive_review_guidance import review_evidence_guidance
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
            response = await request_runtime(
                self.client,
                "GET",
                f"/changesets/{resolved_changeset_id}",
                dashboard_url=self.dashboard_url,
            )
            raise_for_action_error(response)
            payload = response.json()
            review_summary = payload["review_response_summary"]
            inventory_status = payload["inventory_status"]
            skipped_total, skipped_browser, skipped_accessibility = (
                _payload_skipped_evidence_counts(payload.get("manual_evidence", []))
            )
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
                    *review_evidence_guidance(
                        changeset_id=resolved_changeset_id,
                        missing_fixup_feedback_ids=(
                            _payload_missing_fixup_feedback_ids(review_summary)
                        ),
                        stale_response_count=int(
                            review_summary.get("stale_response_count", 0)
                        ),
                        review_brief_count=len(payload.get("review_briefs", [])),
                        skipped_live_evidence_count=skipped_total,
                        skipped_browser_evidence_count=skipped_browser,
                        skipped_accessibility_evidence_count=skipped_accessibility,
                    ),
                ),
                limitations=_string_tuple(payload.get("limitations", [])),
                safe_next_actions=_string_tuple(payload.get("safe_next_actions", [])),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
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
            response = await request_runtime(
                self.client,
                "POST",
                f"/changesets/{resolved_changeset_id}/brief",
                dashboard_url=self.dashboard_url,
                json={"actor": "terminal", "include_markdown": False},
            )
            raise_for_action_error(response)
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
            response = await request_runtime(
                self.client,
                "GET",
                f"/changesets/{resolved_changeset_id}/handoff-readiness",
                dashboard_url=self.dashboard_url,
            )
            raise_for_action_error(response)
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
                    *payload_handoff_evidence_guidance(payload),
                ),
                limitations=_string_tuple(payload.get("limitations", [])),
                safe_next_actions=_string_tuple(payload.get("safe_next_actions", [])),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
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
                    *review_evidence_guidance(
                        changeset_id=resolved_changeset_id,
                        missing_fixup_feedback_ids=(
                            _payload_missing_fixup_feedback_ids(summary)
                        ),
                        stale_response_count=int(
                            summary.get("stale_response_count", 0)
                        ),
                        review_brief_count=None,
                        skipped_live_evidence_count=None,
                        skipped_browser_evidence_count=None,
                        skipped_accessibility_evidence_count=None,
                    ),
                ),
                safe_next_actions=_string_tuple(summary.get("safe_next_actions", [])),
                dashboard_path=f"/app/changesets/{resolved_changeset_id}",
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


def _string_tuple(items: object) -> tuple[str, ...]:
    if not isinstance(items, list):
        return ()
    return tuple(str(item) for item in items)


def _payload_missing_fixup_feedback_ids(summary: Any) -> tuple[str, ...]:
    if not isinstance(summary, dict):
        return ()
    ids: list[str] = []
    for item in summary.get("items", []):
        if not isinstance(item, dict):
            continue
        if item.get("response_state") in {"accepted_with_risk", "not_applicable"}:
            continue
        if int(item.get("fixup_inventory_count", 0)) == 0:
            ids.append(str(item.get("feedback_id")))
    return tuple(ids)


def _payload_skipped_evidence_counts(items: Any) -> tuple[int, int, int]:
    if not isinstance(items, list):
        return (0, 0, 0)
    evidence_items = [
        cast(dict[str, Any], item) for item in items if isinstance(item, dict)
    ]
    skipped = [
        item
        for item in evidence_items
        if item.get("evidence_kind")
        in {"browser_observation", "screenshot", "accessibility_note"}
        and _payload_is_skipped_evidence(item)
    ]
    skipped_browser = [
        item
        for item in skipped
        if item.get("evidence_kind") in {"browser_observation", "screenshot"}
    ]
    skipped_accessibility = [
        item for item in skipped if item.get("evidence_kind") == "accessibility_note"
    ]
    return (len(skipped), len(skipped_browser), len(skipped_accessibility))


def _payload_is_skipped_evidence(item: dict[str, Any]) -> bool:
    text = [
        *[str(value) for value in item.get("limitations", []) if value is not None],
        *[str(value) for value in item.get("non_claims", []) if value is not None],
    ]
    normalized = {value.strip().lower() for value in text}
    return bool(
        {
            "capture state: not_run",
            "capture state: not_applicable",
        }
        & normalized
    )
