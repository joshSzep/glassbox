"""Session query service implementation for shared CLI and web read models."""

from glassbox.core.ids import SessionId
from glassbox.core.models import AutonomyBudgetPostureRecord
from glassbox.core.models import SessionRecord
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import SessionStatus
from glassbox.core.types import ToolExecutionStatus
from glassbox.runtime.context_builder import RuntimeContextSnapshot
from glassbox.runtime.context_builder import build_repository_context_snapshot
from glassbox.runtime.operator_session_queries import build_operator_session_summary
from glassbox.runtime.operator_session_queries import matches_operator_queue
from glassbox.runtime.operator_session_queries import matches_operator_status
from glassbox.runtime.operator_session_queries import projection_health_counts
from glassbox.runtime.operator_session_queries import session_queue_counts
from glassbox.runtime.operator_session_queries import sort_operator_rows
from glassbox.runtime.runtime_context_derivation import derive_runtime_context_snapshot
from glassbox.runtime.session_query_helpers import branchable_turns_from_events
from glassbox.runtime.session_query_helpers import child_counts_by_parent
from glassbox.runtime.session_query_helpers import dashboard_url_from_events
from glassbox.runtime.session_query_helpers import effective_current_turn_id
from glassbox.runtime.session_query_helpers import find_turn_metrics
from glassbox.runtime.session_query_helpers import fork_capability
from glassbox.runtime.session_query_helpers import last_sequence
from glassbox.runtime.session_query_helpers import latest_message_summary
from glassbox.runtime.session_query_helpers import latest_policy_turn_id
from glassbox.runtime.session_query_helpers import latest_session_failure
from glassbox.runtime.session_query_helpers import next_action_summary
from glassbox.runtime.session_query_helpers import pending_question_text_from_events
from glassbox.runtime.session_query_helpers import recent_tool_calls
from glassbox.runtime.session_query_helpers import session_status
from glassbox.runtime.session_query_helpers import summarize_policy_activity
from glassbox.runtime.session_query_models import OPERATOR_SORT_PRIORITY
from glassbox.runtime.session_query_models import ChildSessionSummaryView
from glassbox.runtime.session_query_models import OperatorQueueName
from glassbox.runtime.session_query_models import OperatorSortName
from glassbox.runtime.session_query_models import SessionAggregateView
from glassbox.runtime.session_query_models import SessionSnapshotView
from glassbox.runtime.session_query_models import SessionStatusView
from glassbox.runtime.session_query_models import SessionSummaryView
from glassbox.runtime.session_query_models import WorkspaceRuntimeSummaryView
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository
from glassbox.tools import describe_effective_approval_behavior


class SessionQueryService:
    """Build shared session summaries and snapshots from repository projections."""

    def __init__(
        self,
        session_repository: SessionRepository,
        artifact_repository: ArtifactRepository,
    ) -> None:
        self._session_repository = session_repository
        self._artifact_repository = artifact_repository

    def list_session_summaries(
        self,
        *,
        status: SessionStatus | None = None,
        limit: int | None = None,
    ) -> list[SessionSummaryView]:
        records = self._session_repository.list_sessions()
        child_counts = child_counts_by_parent(records)
        summaries = [
            self._build_session_summary(
                record,
                child_count=child_counts.get(str(record.session_id), 0),
            )
            for record in records
        ]
        if status is not None:
            summaries = [summary for summary in summaries if summary.status == status]
        if limit is not None:
            summaries = summaries[:limit]
        return summaries

    def get_session_snapshot(
        self,
        session_id: SessionId,
        *,
        turn_metrics_limit: int = 10,
    ) -> SessionSnapshotView:
        record = self._session_repository.get_session(session_id)
        if record is None:
            raise ValueError(f"session {session_id} not found")

        projection_health = self._session_repository.inspect_session_projection_health(
            session_id
        )
        projections_available = projection_health.state != "unavailable"
        state = (
            self._session_repository.get_session_state(session_id)
            if projections_available
            else None
        )
        session_events = self._session_repository.read_session_events(session_id)
        transcript = (
            self._session_repository.list_transcript_messages(session_id)
            if projections_available
            else []
        )
        all_tool_calls = (
            self._session_repository.list_tool_calls(session_id)
            if projections_available
            else []
        )
        active_tool_calls = [
            tool_call
            for tool_call in all_tool_calls
            if tool_call.status == ToolExecutionStatus.RUNNING
        ]
        pending_approvals = (
            self._session_repository.list_approvals(
                session_id,
                status=ApprovalStatus.PENDING,
            )
            if projections_available
            else []
        )
        turn_metrics = (
            self._session_repository.list_turn_metrics(
                session_id,
                limit=turn_metrics_limit,
            )
            if projections_available
            else []
        )
        budget_posture = (
            self._get_budget_posture(session_id) if projections_available else None
        )
        dashboard_url = dashboard_url_from_events(session_events)
        latest_failure = latest_session_failure(session_events)
        pending_question_id = state.pending_question_id if state is not None else None
        pending_question_text = pending_question_text_from_events(
            session_events,
            pending_question_id,
        )
        if projections_available:
            (
                can_fork,
                latest_fork_point_turn_id,
                latest_fork_point_sequence,
                fork_blocked_reason,
            ) = fork_capability(self._session_repository, session_id)
            runtime_context = self._build_runtime_context(record, session_id)
            child_sessions = self._child_session_summaries(session_id)
        else:
            can_fork = False
            latest_fork_point_turn_id = None
            latest_fork_point_sequence = None
            fork_blocked_reason = projection_health.detail
            runtime_context = self._build_degraded_runtime_context(record)
            child_sessions = []

        snapshot_status = session_status(record, state)
        effective_turn_id = effective_current_turn_id(
            state.current_turn_id if state is not None else None,
            snapshot_status,
            pending_approvals,
        )

        return SessionSnapshotView(
            session_id=record.session_id,
            status=snapshot_status,
            current_turn_id=state.current_turn_id if state is not None else None,
            model_name=record.model_name,
            cwd=str(record.cwd),
            approval_mode=record.approval_mode,
            budget_posture=budget_posture,
            approval_behavior=self._approval_behavior(
                record.approval_mode,
                budget_posture,
            ),
            parent_session_id=record.parent_session_id,
            forked_from_turn_id=record.forked_from_turn_id,
            forked_from_sequence=record.forked_from_sequence,
            branch_label=record.branch_label,
            child_sessions=child_sessions,
            branchable_turns=(
                branchable_turns_from_events(session_events) if can_fork else []
            ),
            can_fork=can_fork,
            latest_fork_point_turn_id=latest_fork_point_turn_id,
            latest_fork_point_sequence=latest_fork_point_sequence,
            fork_blocked_reason=fork_blocked_reason,
            dashboard_url=dashboard_url,
            created_at=record.created_at,
            updated_at=record.updated_at,
            last_sequence=last_sequence(record, state),
            pending_approval_id=(
                str(state.pending_approval_id)
                if state is not None and state.pending_approval_id is not None
                else None
            ),
            pending_question_id=(
                str(state.pending_question_id)
                if state is not None and state.pending_question_id is not None
                else None
            ),
            pending_question_text=pending_question_text,
            session_failure_message=(
                latest_failure.error_message if latest_failure is not None else None
            ),
            session_failure_retryable=(
                latest_failure.retryable if latest_failure is not None else None
            ),
            transcript=transcript,
            active_tool_calls=active_tool_calls,
            pending_approvals=pending_approvals,
            session_policy_summary=summarize_policy_activity(all_tool_calls),
            current_turn_policy_summary=(
                summarize_policy_activity(
                    all_tool_calls,
                    turn_id=effective_turn_id,
                )
                if effective_turn_id is not None
                else None
            ),
            turn_metrics=turn_metrics,
            runtime_context=runtime_context,
            projection_health=projection_health,
        )

    def get_session_status_view(
        self,
        session_id: SessionId,
        *,
        turn_metrics_limit: int = 5,
        recent_tool_call_limit: int = 3,
    ) -> SessionStatusView:
        snapshot = self.get_session_snapshot(
            session_id,
            turn_metrics_limit=turn_metrics_limit,
        )
        all_tool_calls = (
            self._session_repository.list_tool_calls(session_id)
            if snapshot.projection_health.state != "unavailable"
            else []
        )
        effective_turn_id = effective_current_turn_id(
            snapshot.current_turn_id,
            snapshot.status,
            snapshot.pending_approvals,
        )
        current_turn_metrics = find_turn_metrics(
            snapshot.turn_metrics,
            effective_turn_id,
        )
        latest_turn_metrics = current_turn_metrics or (
            snapshot.turn_metrics[0] if snapshot.turn_metrics else None
        )
        latest_turn_policy_summary = snapshot.current_turn_policy_summary
        if latest_turn_policy_summary is None:
            latest_policy_turn = latest_policy_turn_id(all_tool_calls)
            if latest_policy_turn is not None:
                latest_turn_policy_summary = summarize_policy_activity(
                    all_tool_calls,
                    turn_id=latest_policy_turn,
                )

        return SessionStatusView(
            snapshot=snapshot,
            effective_current_turn_id=effective_turn_id,
            current_turn_metrics=current_turn_metrics,
            latest_turn_metrics=latest_turn_metrics,
            latest_turn_policy_summary=latest_turn_policy_summary,
            recent_tool_calls=recent_tool_calls(
                all_tool_calls,
                limit=recent_tool_call_limit,
            ),
            latest_message_summary=latest_message_summary(snapshot.transcript),
        )

    def get_session_aggregate(
        self,
        *,
        runtime: WorkspaceRuntimeSummaryView,
        queue: OperatorQueueName | None = None,
        status: str | None = None,
        sort: OperatorSortName = OPERATOR_SORT_PRIORITY,
        limit: int | None = None,
    ) -> SessionAggregateView:
        rows = [
            build_operator_session_summary(summary)
            for summary in self.list_session_summaries()
        ]
        filtered_rows = [
            row
            for row in rows
            if matches_operator_queue(row, queue)
            and matches_operator_status(row, status)
        ]
        sorted_rows = sort_operator_rows(filtered_rows, sort=sort)
        if limit is not None:
            sorted_rows = sorted_rows[:limit]

        return SessionAggregateView(
            queue=queue,
            status=status,
            sort=sort,
            limit=limit,
            queue_counts=session_queue_counts(rows),
            projection_health_counts=projection_health_counts(rows),
            runtime=runtime,
            sessions=sorted_rows,
        )

    def _build_session_summary(
        self,
        record: SessionRecord,
        *,
        child_count: int,
    ) -> SessionSummaryView:
        projection_health = self._session_repository.inspect_session_projection_health(
            record.session_id
        )
        projections_available = projection_health.state != "unavailable"
        state = (
            self._session_repository.get_session_state(record.session_id)
            if projections_available
            else None
        )
        session_events = self._session_repository.read_session_events(record.session_id)
        transcript = (
            self._session_repository.list_transcript_messages(record.session_id)
            if projections_available
            else []
        )
        dashboard_url = dashboard_url_from_events(session_events)
        latest_failure = latest_session_failure(session_events)
        pending_question_id = state.pending_question_id if state is not None else None
        pending_question_text = pending_question_text_from_events(
            session_events,
            pending_question_id,
        )
        if projections_available:
            (
                can_fork,
                latest_fork_point_turn_id,
                latest_fork_point_sequence,
                fork_blocked_reason,
            ) = fork_capability(self._session_repository, record.session_id)
        else:
            can_fork = False
            latest_fork_point_turn_id = None
            latest_fork_point_sequence = None
            fork_blocked_reason = projection_health.detail
        budget_posture = (
            self._get_budget_posture(record.session_id)
            if projections_available
            else None
        )
        status = session_status(record, state)

        return SessionSummaryView(
            session_id=record.session_id,
            status=status,
            model_name=record.model_name,
            cwd=str(record.cwd),
            approval_mode=record.approval_mode,
            budget_posture=budget_posture,
            approval_behavior=self._approval_behavior(
                record.approval_mode,
                budget_posture,
            ),
            parent_session_id=record.parent_session_id,
            forked_from_turn_id=record.forked_from_turn_id,
            forked_from_sequence=record.forked_from_sequence,
            branch_label=record.branch_label,
            child_session_count=child_count,
            can_fork=can_fork,
            latest_fork_point_turn_id=latest_fork_point_turn_id,
            latest_fork_point_sequence=latest_fork_point_sequence,
            fork_blocked_reason=fork_blocked_reason,
            dashboard_url=dashboard_url,
            created_at=record.created_at,
            updated_at=record.updated_at,
            last_sequence=last_sequence(record, state),
            pending_approval_id=(
                str(state.pending_approval_id)
                if state is not None and state.pending_approval_id is not None
                else None
            ),
            pending_question_id=(
                str(state.pending_question_id)
                if state is not None and state.pending_question_id is not None
                else None
            ),
            pending_question_text=pending_question_text,
            session_failure_message=(
                latest_failure.error_message if latest_failure is not None else None
            ),
            session_failure_retryable=(
                latest_failure.retryable if latest_failure is not None else None
            ),
            latest_message_summary=latest_message_summary(transcript),
            projection_health=projection_health,
            next_action_summary=next_action_summary(
                status,
                projection_health=projection_health,
                pending_question_text=pending_question_text,
                session_failure=latest_failure,
                current_turn_id=state.current_turn_id if state is not None else None,
                budget_posture=budget_posture,
            ),
        )

    def _build_runtime_context(
        self,
        record: SessionRecord,
        session_id: SessionId,
    ) -> RuntimeContextSnapshot:
        return derive_runtime_context_snapshot(
            self._session_repository,
            session_id,
            record.cwd,
            artifact_repository=self._artifact_repository,
        )

    def _get_budget_posture(
        self,
        session_id: SessionId,
    ) -> AutonomyBudgetPostureRecord | None:
        get_budget_posture = getattr(
            self._session_repository,
            "get_budget_posture",
            None,
        )
        if get_budget_posture is None:
            return None
        return get_budget_posture(session_id)

    def _approval_behavior(
        self,
        approval_mode: str,
        budget_posture: AutonomyBudgetPostureRecord | None,
    ) -> str:
        return describe_effective_approval_behavior(
            approval_mode,
            autonomy_mode=(budget_posture.mode if budget_posture is not None else None),
            budget=(budget_posture.budget if budget_posture is not None else None),
        )

    def _build_degraded_runtime_context(
        self,
        record: SessionRecord,
    ) -> RuntimeContextSnapshot:
        return RuntimeContextSnapshot(
            repository_context=build_repository_context_snapshot(record.cwd),
        )

    def _child_session_summaries(
        self,
        session_id: SessionId,
    ) -> list[ChildSessionSummaryView]:
        child_records = [
            record
            for record in self._session_repository.list_sessions()
            if record.parent_session_id == session_id
        ]
        child_records.sort(key=lambda record: record.updated_at, reverse=True)

        return [
            ChildSessionSummaryView(
                session_id=record.session_id,
                status=record.status,
                branch_label=record.branch_label,
                updated_at=record.updated_at,
                latest_message_summary=latest_message_summary(
                    self._session_repository.list_transcript_messages(record.session_id)
                ),
            )
            for record in child_records
        ]
