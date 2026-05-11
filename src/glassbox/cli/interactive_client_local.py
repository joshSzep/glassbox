"""Local in-process implementation for interactive terminal sessions."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from uuid import UUID

from glassbox.cli.interactive_client_models import InteractiveClientError
from glassbox.cli.interactive_client_models import InteractiveClientErrorKind
from glassbox.cli.interactive_client_models import InteractiveSessionSnapshot
from glassbox.cli.interactive_client_models import ReviewLoopAction
from glassbox.cli.interactive_client_models import ReviewLoopActionResult
from glassbox.cli.interactive_review_actions import create_changeset_result
from glassbox.cli.interactive_review_actions import feedback_status_result
from glassbox.cli.interactive_review_actions import fixup_inventory_result
from glassbox.cli.interactive_review_actions import generate_brief_result
from glassbox.cli.interactive_review_actions import handoff_readiness_result
from glassbox.cli.interactive_review_actions import preview_verification_result
from glassbox.cli.interactive_review_actions import refresh_inventory_result
from glassbox.cli.interactive_review_actions import review_status_result_from_detail
from glassbox.cli.interactive_review_actions import workup_guide_result
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
        return create_changeset_result(
            changeset_id,
            limitations=tuple(result.limitations),
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
            return fixup_inventory_result(feedback_id, result, response_status)
        resolved_changeset_id = UUID(changeset_id) if changeset_id else None
        if resolved_changeset_id is None:
            resolved_changeset_id = self._latest_changeset_id()
        if resolved_changeset_id is None:
            if action == ReviewLoopAction.WORKUP_GUIDE:
                from glassbox.runtime.changesets import ChangesetWorkupPreviewService

                workup_preview = await ChangesetWorkupPreviewService().preview(
                    self._workspace_root(),
                    session_id=str(self.session_id),
                )
                return workup_guide_result(
                    changeset_id=None,
                    changed_path_count=len(workup_preview.changed_paths),
                )
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
            return review_status_result_from_detail(resolved_changeset_id, detail)
        if action == ReviewLoopAction.WORKUP_GUIDE:
            from glassbox.runtime.changesets import ChangesetVerificationService
            from glassbox.runtime.changesets import ChangesetWorkupPreviewService
            from glassbox.runtime.handoff_readiness import (
                ChangesetHandoffReadinessService,
            )

            workup_preview = await ChangesetWorkupPreviewService().preview(
                workspace_root,
                session_id=str(self.session_id),
            )
            verification_plan = ChangesetVerificationService(
                repository,
                artifact_repository,
            ).preview_plan(resolved_changeset_id, workspace_root)
            handoff = await ChangesetHandoffReadinessService(
                repository,
                artifact_repository,
            ).preview(resolved_changeset_id, workspace_root)
            return workup_guide_result(
                changeset_id=str(resolved_changeset_id),
                changed_path_count=len(workup_preview.changed_paths),
                plan_entry_count=len(verification_plan.plan_entries),
                handoff_state=handoff.state,
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
            return refresh_inventory_result(resolved_changeset_id, result)
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
            return generate_brief_result(
                str(resolved_changeset_id),
                artifact_id=str(result.artifact.artifact_id),
                limitations=tuple(result.limitations),
            )
        if action == ReviewLoopAction.PREVIEW_VERIFICATION:
            from glassbox.runtime.changesets import ChangesetVerificationService

            preview = ChangesetVerificationService(
                repository,
                artifact_repository,
            ).preview_plan(resolved_changeset_id, workspace_root)
            command_count = len(preview.recommended_commands)
            return preview_verification_result(
                str(resolved_changeset_id),
                readiness_state=preview.readiness.state.value,
                command_count=command_count,
                limitations=tuple(preview.limitations),
                safe_next_actions=tuple(preview.safe_next_actions),
            )
        if action == ReviewLoopAction.INSPECT_HANDOFF:
            from glassbox.runtime.handoff_readiness import (
                ChangesetHandoffReadinessService,
            )

            readiness = await ChangesetHandoffReadinessService(
                repository,
                artifact_repository,
            ).preview(resolved_changeset_id, workspace_root)
            return handoff_readiness_result(resolved_changeset_id, readiness)
        if action == ReviewLoopAction.SHOW_FEEDBACK_STATUS:
            from glassbox.runtime.changesets import ChangesetQueryService

            summary = ChangesetQueryService(repository).get_review_response_summary(
                resolved_changeset_id,
                workspace_root=workspace_root,
            )
            return feedback_status_result(resolved_changeset_id, summary)
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
