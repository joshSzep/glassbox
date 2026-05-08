"""Local in-process implementation for interactive terminal sessions."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import cast
from uuid import UUID

from glassbox.cli.interactive_client_models import InteractiveClientError
from glassbox.cli.interactive_client_models import InteractiveClientErrorKind
from glassbox.cli.interactive_client_models import InteractiveSessionSnapshot
from glassbox.cli.interactive_client_models import ReviewLoopAction
from glassbox.cli.interactive_client_models import ReviewLoopActionResult
from glassbox.cli.interactive_review_guidance import handoff_evidence_guidance
from glassbox.cli.interactive_review_guidance import review_evidence_guidance
from glassbox.cli.status_formatters import _pending_question_text_from_events
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.types import ApprovalDecision
from glassbox.runtime.context import RuntimeContext


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
        if action == ReviewLoopAction.RECORD_FEEDBACK_FIXUP:
            if changeset_id is None:
                raise InteractiveClientError(
                    InteractiveClientErrorKind.VALIDATION_ERROR,
                    "Usage: /review fixup FEEDBACK_ID",
                )
            feedback_id = UUID(changeset_id)
            workspace_root = self._workspace_root()
            repository = self._changeset_repository()
            artifact_repository = self.runtime_context.repositories.artifacts
            from glassbox.runtime.changesets import ChangesetQueryService
            from glassbox.runtime.changesets import ReviewFeedbackFixupInventoryService

            result = await ReviewFeedbackFixupInventoryService(
                repository,
                artifact_repository,
            ).record_workspace_inventory(
                feedback_id,
                workspace_root,
                source_summary=(
                    "terminal /review fixup recorded response-linked workspace "
                    "inventory"
                ),
                recorded_by="terminal",
            )
            response_status = ChangesetQueryService(
                repository
            ).get_review_feedback_response_status(
                result.feedback_id,
                workspace_root=workspace_root,
            )
            return ReviewLoopActionResult(
                action=action,
                headline=f"Recorded fixup inventory for feedback {feedback_id}",
                changeset_id=str(result.changeset_id),
                details=(
                    f"Artifact: {result.artifact.artifact_id}",
                    (
                        f"Paths: {result.inventory.changed_path_count} changed, "
                        f"{result.inventory.matched_scope_path_count} scoped matches."
                    ),
                    f"Verification: {response_status.verification_state.value}.",
                    "No tests, staging, commit, push, PR, or merge was run.",
                ),
                limitations=tuple(result.inventory.limitations),
                safe_next_actions=tuple(response_status.safe_next_actions),
                dashboard_path=f"/app/changesets/{result.changeset_id}",
            )
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
            skipped_total, skipped_browser, skipped_accessibility = (
                _local_skipped_evidence_counts(detail.manual_evidence)
            )
            return ReviewLoopActionResult(
                action=action,
                headline=f"Review status for changeset {resolved_changeset_id}",
                changeset_id=str(resolved_changeset_id),
                details=(
                    f"{summary.total_feedback_count} feedback item(s), "
                    f"{summary.unresolved_count} unresolved, "
                    f"{summary.stale_response_count} stale response check(s).",
                    f"Inventory: {detail.inventory_status.freshness.value}.",
                    *review_evidence_guidance(
                        changeset_id=str(resolved_changeset_id),
                        missing_fixup_feedback_ids=_missing_fixup_feedback_ids(summary),
                        stale_response_count=summary.stale_response_count,
                        review_brief_count=len(detail.review_briefs),
                        skipped_live_evidence_count=skipped_total,
                        skipped_browser_evidence_count=skipped_browser,
                        skipped_accessibility_evidence_count=skipped_accessibility,
                    ),
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
                    *handoff_evidence_guidance(readiness),
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
                    *review_evidence_guidance(
                        changeset_id=str(resolved_changeset_id),
                        missing_fixup_feedback_ids=_missing_fixup_feedback_ids(summary),
                        stale_response_count=summary.stale_response_count,
                        review_brief_count=None,
                        skipped_live_evidence_count=None,
                        skipped_browser_evidence_count=None,
                        skipped_accessibility_evidence_count=None,
                    ),
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


def _missing_fixup_feedback_ids(summary: Any) -> tuple[str, ...]:
    ids: list[str] = []
    for item in getattr(summary, "items", ()):
        response_state = getattr(item, "response_state", "")
        if str(response_state) in {"accepted_with_risk", "not_applicable"}:
            continue
        if getattr(item, "fixup_inventory_count", 0) == 0:
            ids.append(str(item.feedback_id))
    return tuple(ids)


def _local_skipped_evidence_counts(manual_evidence: Any) -> tuple[int, int, int]:
    from glassbox.runtime.skipped_evidence import skipped_live_evidence_counts

    return skipped_live_evidence_counts(manual_evidence)
