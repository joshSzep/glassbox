"""Unit tests for the runtime turn context builder."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Never

import pytest
from pydantic import BaseModel

from glassbox.core import ApprovalStatus
from glassbox.core import ContextCompactionFreshness
from glassbox.core import ContextCompactionRecord
from glassbox.core import ContextCompactionScope
from glassbox.core import EventEnvelope
from glassbox.core import LongRunPhase
from glassbox.core import MessagePart
from glassbox.core import ModelToolCallRequested
from glassbox.core import ProjectionHealth
from glassbox.core import ReplayArtifactRecorded
from glassbox.core import ResolvedForkPoint
from glassbox.core import RuntimeNoteRecord
from glassbox.core import RuntimeNoteRecorded
from glassbox.core import SessionRecord
from glassbox.core import SessionState
from glassbox.core import SessionStatus
from glassbox.core import TaskCheckpointCreated
from glassbox.core import TaskCheckpointRecord
from glassbox.core import ToolArtifactRecorded
from glassbox.core import ToolCallRecord
from glassbox.core import ToolExecutionStatus
from glassbox.core import TranscriptMessage
from glassbox.core import WorkspaceMemoryEntry
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import WorkspaceMemoryProvenance
from glassbox.core import WorkspaceMemorySourceType
from glassbox.core import WorkspaceMemoryState
from glassbox.core import new_approval_id
from glassbox.core import new_artifact_id
from glassbox.core import new_context_compaction_id
from glassbox.core import new_message_id
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.core import new_workspace_memory_id
from glassbox.core.models import ApprovalRecord
from glassbox.runtime.checkpoints import build_checkpoint_resume_snapshot
from glassbox.runtime.context_builder import PYTEST_FAILURE_DIGEST_ARTIFACT_KIND
from glassbox.runtime.context_builder import ArtifactBackedContextSnapshot
from glassbox.runtime.context_builder import ArtifactBackedContextSummarySnapshot
from glassbox.runtime.context_builder import ContextCompactionContextItemSnapshot
from glassbox.runtime.context_builder import ContextCompactionContextSnapshot
from glassbox.runtime.context_builder import PytestFailureDigestArtifact
from glassbox.runtime.context_builder import RepositoryContextSnapshot
from glassbox.runtime.context_builder import RepositoryIndexContextSnapshot
from glassbox.runtime.context_builder import RuntimeContextNoteSnapshot
from glassbox.runtime.context_builder import RuntimeContextSnapshot
from glassbox.runtime.context_builder import ToolSchema
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.context_builder import WorkingSetItemSnapshot
from glassbox.runtime.context_builder import WorkingSetSnapshot
from glassbox.runtime.context_builder import WorkspaceMemoryContextItemSnapshot
from glassbox.runtime.context_builder import WorkspaceMemoryContextProvenanceSnapshot
from glassbox.runtime.context_formatting import format_repository_context_for_prompt
from glassbox.runtime.context_formatting import format_repository_index_for_prompt
from glassbox.runtime.context_formatting import format_runtime_context_budget_summary
from glassbox.runtime.context_formatting import format_runtime_notes_for_prompt
from glassbox.runtime.context_formatting import format_tool_schemas_for_prompt
from glassbox.runtime.context_formatting import format_transcript_for_prompt
from glassbox.runtime.context_formatting import format_workspace_memory_for_prompt
from glassbox.runtime.context_snapshots import build_artifact_backed_context_snapshot
from glassbox.runtime.context_snapshots import build_pytest_failure_digest_artifact
from glassbox.runtime.context_snapshots import build_repository_context_snapshot
from glassbox.runtime.context_snapshots import build_repository_index_context_snapshot
from glassbox.runtime.context_snapshots import build_runtime_context_snapshot
from glassbox.runtime.context_snapshots import build_workspace_memory_context_snapshot
from glassbox.runtime.context_working_set import build_working_set_snapshot
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.runtime_context_derivation import derive_runtime_context_snapshot
from glassbox.tools import ToolRegistry
from glassbox.tools import ToolRiskLevel
from glassbox.tools import ToolSpec


class FakeSessionRepository:
    def __init__(
        self,
        session,
        session_state,
        transcript,
        *,
        runtime_notes=None,
        events=None,
        tool_calls=None,
        approvals=None,
        workspace_memory=None,
        latest_checkpoint=None,
        context_compactions=None,
    ):
        self._session = session
        self._session_state = session_state
        self._transcript = transcript
        self._runtime_notes = list(runtime_notes or [])
        self._events = list(events or [])
        self._tool_calls = list(tool_calls or [])
        self._approvals = list(approvals or [])
        self._workspace_memory = list(workspace_memory or [])
        self._latest_checkpoint = latest_checkpoint
        self._context_compactions = list(context_compactions or [])

    def create_session(
        self,
        session_id,
        config,
        *,
        status=SessionStatus.IDLE,
        created_at=None,
        updated_at=None,
        last_sequence=0,
    ):
        return self._session

    def get_session(self, session_id):
        return self._session if self._session.session_id == session_id else None

    def get_session_state(self, session_id):
        return (
            self._session_state
            if self._session_state.session_id == session_id
            else None
        )

    def list_transcript_messages(self, session_id, *, limit=None, offset=0):
        if self._session.session_id != session_id:
            return []
        messages = list(self._transcript)[offset:]
        return messages if limit is None else messages[:limit]

    def list_runtime_notes(self, session_id, *, include_inherited=True):
        if self._session.session_id != session_id:
            return []
        if include_inherited:
            return list(self._runtime_notes)
        return [note for note in self._runtime_notes if not note.inherited]

    def list_sessions(self, *, status=None, limit=None):
        return [self._session]

    def update_session(
        self,
        session_id,
        *,
        status=None,
        updated_at=None,
        cwd=None,
        model_name=None,
        approval_mode=None,
        last_sequence=None,
        parent_session_id=None,
        forked_from_turn_id=None,
        forked_from_sequence=None,
        branch_label=None,
    ):
        return self._session

    def append_event(self, event):
        return event

    def append_events(self, events):
        return list(events)

    def record_runtime_note(self, session_id, *, category, message):
        return EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=RuntimeNoteRecorded(category=category, message=message),
        )

    def read_session_events(self, session_id):
        if self._session.session_id != session_id:
            return []
        return list(self._events)

    def read_session_events_after(self, session_id, after_sequence, *, limit=None):
        events = [event for event in self._events if event.sequence > after_sequence]
        return events if limit is None else events[:limit]

    def read_events_by_correlation_id(
        self,
        session_id,
        *,
        turn_id=None,
        message_id=None,
        tool_call_id=None,
        approval_id=None,
        task_id=None,
        checkpoint_id=None,
        compaction_id=None,
        tool_attempt_id=None,
        recovery_decision_id=None,
    ):
        return []

    def rebuild_session_projections(self, session_id) -> None:
        return None

    def inspect_session_projection_health(self, session_id) -> ProjectionHealth:
        return ProjectionHealth(
            state="ok",
            canonical_last_sequence=0,
            projected_last_sequence=0,
        )

    def list_tool_calls(self, session_id, *, status=None, limit=None, offset=0):
        if self._session.session_id != session_id:
            return []
        if status is None:
            tool_calls = list(self._tool_calls)
        else:
            tool_calls = [
                tool_call
                for tool_call in self._tool_calls
                if tool_call.status == status
            ]
        tool_calls = tool_calls[offset:]
        return tool_calls if limit is None else tool_calls[:limit]

    def list_approvals(self, session_id, *, status=None):
        if self._session.session_id != session_id:
            return []
        if status is None:
            return list(self._approvals)
        return [approval for approval in self._approvals if approval.status == status]

    def list_turn_metrics(self, session_id, *, limit=None, offset=0):
        del offset
        return []

    def get_budget_posture(self, session_id, *, task_id=None):
        return None

    def get_latest_task_checkpoint(self, session_id, *, task_id=None):
        del task_id
        if self._session.session_id != session_id:
            return None
        return self._latest_checkpoint

    def list_task_checkpoints(
        self,
        session_id,
        *,
        task_id=None,
        limit=None,
        offset=0,
    ):
        del task_id, limit, offset
        return []

    def get_context_compaction(self, session_id, compaction_id):
        if self._session.session_id != session_id:
            return None
        return next(
            (
                compaction
                for compaction in self._context_compactions
                if compaction.compaction_id == compaction_id
            ),
            None,
        )

    def list_context_compactions(
        self,
        session_id,
        *,
        task_id=None,
        limit=None,
        offset=0,
    ):
        del task_id
        if self._session.session_id != session_id:
            return []
        compactions = self._context_compactions[offset:]
        return compactions if limit is None else compactions[:limit]

    def get_tool_attempt(self, session_id, tool_attempt_id):
        return None

    def list_tool_attempts(self, session_id, *, status=None, limit=None, offset=0):
        del status, limit, offset
        return []

    def get_latest_provider_recovery(self, session_id):
        return None

    def list_provider_recovery(self, session_id, *, limit=None, offset=0):
        del limit, offset
        return []

    def enqueue_background_job(self, session_id, **kwargs):
        raise NotImplementedError

    def claim_background_job(self, job_id, **kwargs):
        raise NotImplementedError

    def heartbeat_background_job(self, job_id, **kwargs):
        raise NotImplementedError

    def complete_background_job(self, job_id, **kwargs):
        raise NotImplementedError

    def fail_background_job(self, job_id, **kwargs):
        raise NotImplementedError

    def cancel_background_job(self, job_id, **kwargs):
        raise NotImplementedError

    def retry_background_job(self, job_id, **kwargs):
        raise NotImplementedError

    def abandon_background_job(self, job_id, **kwargs):
        raise NotImplementedError

    def list_background_jobs(self, **kwargs):
        return []

    def get_background_job(self, job_id):
        return None

    def count_background_jobs_by_state(self):
        return {}

    def latest_failed_background_job(self):
        return None

    def list_workspace_memory(self, **kwargs):
        return list(self._workspace_memory)

    def get_workspace_memory(self, memory_id):
        return None

    def confirm_workspace_memory(self, memory_id, **kwargs):
        raise NotImplementedError

    def invalidate_workspace_memory(self, memory_id, **kwargs):
        raise NotImplementedError

    def prune_workspace_memory(self, memory_id, **kwargs):
        raise NotImplementedError

    def resolve_fork_point(self, session_id, *, turn_id=None):
        return ResolvedForkPoint(
            parent_session_id=session_id,
            turn_id=new_turn_id(),
            sequence=0,
            inherited_messages=[],
        )

    def build_imported_transcript_events(self, session_id, fork_point):
        return []


class FakeArtifactRepository:
    def __init__(self, text_artifacts: dict[str, str]) -> None:
        self._text_artifacts = dict(text_artifacts)

    def write_text_artifact(self, session_id, content: str, *, suffix: str):
        raise NotImplementedError

    def write_binary_artifact(self, session_id, content: bytes, *, suffix: str):
        raise NotImplementedError

    def read_text_artifact(
        self,
        relative_path: Path,
        *,
        encoding: str = "utf-8",
    ) -> str:
        del encoding
        return self._text_artifacts[relative_path.as_posix()]

    def read_binary_artifact(self, relative_path: Path) -> bytes:
        raise NotImplementedError

    def record_text_artifact(
        self,
        session_id,
        turn_id,
        tool_call_id,
        artifact_kind: str,
        content: str,
        *,
        suffix: str,
    ) -> Never:
        raise NotImplementedError

    def record_binary_artifact(
        self,
        session_id,
        turn_id,
        tool_call_id,
        artifact_kind: str,
        content: bytes,
        *,
        suffix: str,
    ) -> Never:
        raise NotImplementedError


def test_turn_context_builder_orders_transcript_and_includes_policy_and_tools() -> None:
    session_id = new_session_id()
    approval_id = new_approval_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.AWAITING_APPROVAL,
            created_at=datetime(2026, 4, 16, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 16, 12, 2, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=5,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.AWAITING_APPROVAL,
            current_turn_id=new_turn_id(),
            last_sequence=5,
            pending_approval_id=approval_id,
        ),
        [
            TranscriptMessage(
                message_id=new_message_id(),
                role="assistant",
                parts=[MessagePart(kind="text", text="second")],
                created_at=datetime(2026, 4, 16, 12, 2, tzinfo=UTC),
            ),
            TranscriptMessage(
                message_id=new_message_id(),
                role="user",
                parts=[MessagePart(kind="text", text="first")],
                created_at=datetime(2026, 4, 16, 12, 1, tzinfo=UTC),
            ),
        ],
    )
    builder = TurnContextBuilder(repository)

    context = builder.build(
        session_id,
        tool_schemas=[
            ToolSchema(name="write_file", description="Write a file"),
            ToolSchema(name="read_file", description="Read a file"),
        ],
        repo_context="git branch: main",
        memory_notes=["user prefers concise output"],
    )

    assert [message.parts[0].text for message in context.transcript] == [
        "first",
        "second",
    ]
    assert [tool.name for tool in context.available_tools] == [
        "read_file",
        "write_file",
    ]
    assert context.policy.approval_mode == "confirm"
    assert context.policy.pending_approval_id == approval_id
    assert context.repo_context == "git branch: main"
    assert context.memory_notes == ["user prefers concise output"]


def test_turn_context_builder_rejects_unknown_sessions() -> None:
    session_id = new_session_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 16, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 16, 12, 0, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=1,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=1,
        ),
        [],
    )
    builder = TurnContextBuilder(repository)

    with pytest.raises(ValueError):
        builder.build(new_session_id())


def test_turn_context_builder_builds_prompt_fields_from_runtime_context() -> None:
    session_id = new_session_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=1,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=1,
        ),
        [],
    )
    builder = TurnContextBuilder(repository)
    runtime_context = RuntimeContextSnapshot(
        repository_context=RepositoryContextSnapshot(
            workspace_name="glassbox",
            high_signal_paths=["README.md", "src/"],
        ),
        runtime_notes=[
            RuntimeContextNoteSnapshot(
                category="repo",
                message="Keep runtime-context derivation shared",
                inherited=True,
                source_session_id=session_id,
            )
        ],
        working_set=WorkingSetSnapshot(
            items=[
                WorkingSetItemSnapshot(
                    subject_kind="file",
                    subject="src/glassbox/runtime/session_queries.py",
                    summary="recently targeted workspace path",
                    reasons=[
                        "read_file targeted src/glassbox/runtime/session_queries.py"
                    ],
                    signal_types=["tool_request_path"],
                )
            ]
        ),
        artifact_context=ArtifactBackedContextSnapshot(
            summaries=[
                ArtifactBackedContextSummarySnapshot(
                    summary_kind="pytest_failure_digest",
                    source_tool_name="run_tests",
                    artifact_kind=PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
                    artifact_path=".glassbox/sessions/test/artifacts/failure.json",
                    summary="1 failing test(s) for tests/unit/test_context_builder.py",
                    freshness="fresh",
                    target_paths=["tests/unit/test_context_builder.py"],
                )
            ]
        ),
    )

    context = builder.build_from_runtime_context(session_id, runtime_context)

    assert context.repo_context == format_repository_context_for_prompt(
        runtime_context.repository_context
    )
    assert context.memory_notes == format_runtime_notes_for_prompt(
        runtime_context.runtime_notes
    )
    assert context.working_set == runtime_context.working_set
    assert context.artifact_context == runtime_context.artifact_context


def test_turn_context_builder_includes_checkpoint_resume_context() -> None:
    session_id = new_session_id()
    checkpoint = TaskCheckpointRecord(
        checkpoint_id=new_task_checkpoint_id(),
        session_id=session_id,
        objective="Finish checkpoint-guided resume",
        current_phase=LongRunPhase.CHECKPOINTING,
        completed_step="Stored checkpoint projection",
        next_action="Prepare the next turn from checkpoint context",
        recovery_guidance="Resume with checkpoint provenance in the prompt",
        source_start_sequence=1,
        source_end_sequence=4,
        created_at=datetime(2026, 4, 24, 12, 1, tzinfo=UTC),
        last_sequence=5,
    )
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 24, 12, 1, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=5,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=5,
        ),
        [],
        latest_checkpoint=checkpoint,
    )
    runtime_context = RuntimeContextSnapshot(
        repository_context=RepositoryContextSnapshot(workspace_name="glassbox"),
        checkpoint_resume=build_checkpoint_resume_snapshot(
            checkpoint,
            latest_session_sequence=5,
            workspace_root=Path("/tmp/glassbox"),
        ),
    )

    context = TurnContextBuilder(repository).build_from_runtime_context(
        session_id,
        runtime_context,
    )

    assert context.checkpoint_context is not None
    assert context.checkpoint_context.status == "usable"
    assert context.checkpoint_context.context_source == "checkpoint"
    assert any(
        "[checkpoint-resume usable events 1-4]" in note for note in context.memory_notes
    )
    assert any(
        "Finish checkpoint-guided resume" in note for note in context.memory_notes
    )


def test_turn_context_builder_includes_fresh_context_compactions() -> None:
    session_id = new_session_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 24, 12, 1, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=8,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=8,
        ),
        [],
    )
    compactions = ContextCompactionContextSnapshot(
        items=[
            ContextCompactionContextItemSnapshot(
                compaction_id=new_context_compaction_id(),
                scope=ContextCompactionScope.TRANSCRIPT,
                artifact_id=new_artifact_id(),
                source_start_sequence=1,
                source_end_sequence=8,
                summary="Compacted decisions and verification posture.",
                freshness=ContextCompactionFreshness.FRESH,
                limitations=["Raw transcript omitted."],
                decision_count=2,
            )
        ],
        stale_item_count=1,
    )
    runtime_context = RuntimeContextSnapshot(
        repository_context=RepositoryContextSnapshot(workspace_name="glassbox"),
        context_compactions=compactions,
    )

    context = TurnContextBuilder(repository).build_from_runtime_context(
        session_id,
        runtime_context,
    )

    assert context.context_compactions == compactions
    assert any(
        "[context-compaction transcript events 1-8]" in note
        for note in context.memory_notes
    )
    assert any("stale compaction(s) excluded" in note for note in context.memory_notes)


def test_runtime_context_derivation_marks_old_compactions_stale(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    compaction_id = new_context_compaction_id()
    artifact_id = new_artifact_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 24, 12, 1, tzinfo=UTC),
            cwd=tmp_path,
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=3,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=3,
        ),
        [],
        context_compactions=[
            ContextCompactionRecord(
                compaction_id=compaction_id,
                session_id=session_id,
                scope=ContextCompactionScope.TRANSCRIPT,
                source_start_sequence=1,
                source_end_sequence=2,
                summary="Compacted old context.",
                artifact_id=artifact_id,
                artifact_schema_version=1,
                freshness=ContextCompactionFreshness.FRESH,
                created_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
                last_sequence=2,
            )
        ],
        events=[
            EventEnvelope(
                session_id=session_id,
                sequence=3,
                payload=TaskCheckpointCreated(
                    checkpoint_id=new_task_checkpoint_id(),
                    objective="continue safely",
                    next_action="refresh stale compaction",
                    recovery_guidance="inspect the latest checkpoint first",
                    source_start_sequence=1,
                    source_end_sequence=3,
                ),
            )
        ],
    )

    runtime_context = derive_runtime_context_snapshot(
        repository,
        session_id,
        tmp_path,
    )

    assert runtime_context.context_compactions.items == []
    assert runtime_context.context_compactions.stale_item_count == 1
    stale = runtime_context.context_compactions.stale_items[0]
    assert stale.compaction_id == compaction_id
    assert stale.freshness == ContextCompactionFreshness.STALE
    assert "newer checkpoint" in stale.reason


def test_turn_context_builder_includes_memory_and_repository_index_context() -> None:
    session_id = new_session_id()
    memory_id = new_workspace_memory_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=1,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=1,
        ),
        [],
    )
    builder = TurnContextBuilder(repository)
    memory = WorkspaceMemoryContextItemSnapshot(
        memory_id=memory_id,
        kind="command",
        summary="Use uv run pytest for backend tests",
        content="Use uv run pytest for backend tests.",
        provenance=WorkspaceMemoryContextProvenanceSnapshot(
            source_type="session_event",
            session_id=session_id,
            source_sequence=3,
        ),
        confirmed_by="operator",
    )
    repository_index = RepositoryIndexContextSnapshot(
        status="fresh",
        path=".glassbox/repository-index.json",
        entry_count=1,
        items=[],
    )
    runtime_context = RuntimeContextSnapshot(
        repository_context=RepositoryContextSnapshot(workspace_name="glassbox"),
        workspace_memory=[memory],
        repository_index=repository_index,
    )

    context = builder.build_from_runtime_context(session_id, runtime_context)

    assert context.workspace_memory == [memory]
    assert context.repository_index == repository_index
    assert context.memory_notes == format_workspace_memory_for_prompt([memory])
    assert context.repo_context == (
        format_repository_context_for_prompt(runtime_context.repository_context)
        + "\n\n"
        + format_repository_index_for_prompt(repository_index)
    )


def test_turn_context_builder_can_derive_tools_from_registry() -> None:
    session_id = new_session_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 16, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 16, 12, 0, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=1,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=1,
        ),
        [],
    )
    builder = TurnContextBuilder(repository)
    registry = ToolRegistry([ReadFileTool()])

    context = builder.build(session_id, tool_registry=registry)

    assert [tool.name for tool in context.available_tools] == ["read_file"]
    assert context.available_tools[0].parameters_json_schema["properties"] == {
        "path": {"title": "Path", "type": "string"}
    }


def test_turn_context_builder_rejects_tool_registry_and_tool_schemas_together() -> None:
    session_id = new_session_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 16, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 16, 12, 0, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=1,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=1,
        ),
        [],
    )
    builder = TurnContextBuilder(repository)

    with pytest.raises(ValueError, match="either tool_registry or tool_schemas"):
        builder.build(
            session_id,
            tool_schemas=[ToolSchema(name="read_file", description="Read a file")],
            tool_registry=ToolRegistry([ReadFileTool()]),
        )


def test_prompt_formatters_include_expected_content() -> None:
    transcript = [
        TranscriptMessage(
            message_id=new_message_id(),
            role="user",
            parts=[MessagePart(kind="text", text="Inspect the repo")],
            created_at=datetime(2026, 4, 16, 12, 0, tzinfo=UTC),
        ),
        TranscriptMessage(
            message_id=new_message_id(),
            role="assistant",
            parts=[MessagePart(kind="text", text="Inspecting now")],
            created_at=datetime(2026, 4, 16, 12, 1, tzinfo=UTC),
        ),
    ]
    tools = [
        ToolSchema(name="read_file", description="Read a file"),
        ToolSchema(name="list_dir", description="List directory contents"),
    ]

    transcript_text = format_transcript_for_prompt(transcript)
    tool_text = format_tool_schemas_for_prompt(tools)

    assert "USER: Inspect the repo" in transcript_text
    assert "ASSISTANT: Inspecting now" in transcript_text
    assert "- list_dir: List directory contents" in tool_text
    assert "- read_file: Read a file" in tool_text


def test_tool_schema_formatter_rejects_duplicates() -> None:
    with pytest.raises(ValueError):
        format_tool_schemas_for_prompt(
            [
                ToolSchema(name="read_file", description="Read once"),
                ToolSchema(name="read_file", description="Read twice"),
            ]
        )


def test_repository_context_snapshot_is_bounded_and_deterministic(
    tmp_path: Path,
) -> None:
    for directory_name in (
        "src",
        "tests",
        "docs",
        "evals",
        "frontend",
        "examples",
        "scripts",
        "fixtures",
        "extra-dir",
    ):
        (tmp_path / directory_name).mkdir()
    for file_name in (
        "README.md",
        "pyproject.toml",
        "uv.lock",
        "LICENSE",
        "Makefile",
        "CONTRIBUTING.md",
        "notes.txt",
        "changelog.md",
        "extra.txt",
    ):
        (tmp_path / file_name).write_text(file_name, encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".env").write_text("secret=true\n", encoding="utf-8")

    first_snapshot = build_repository_context_snapshot(tmp_path)
    second_snapshot = build_repository_context_snapshot(tmp_path)

    assert first_snapshot == second_snapshot
    assert first_snapshot.workspace_name == tmp_path.name
    assert first_snapshot.top_level_directories == [
        "docs/",
        "evals/",
        "examples/",
        "extra-dir/",
        "fixtures/",
        "frontend/",
        "scripts/",
        "src/",
    ]
    assert first_snapshot.additional_directory_count == 1
    assert first_snapshot.top_level_files == [
        "CONTRIBUTING.md",
        "LICENSE",
        "Makefile",
        "README.md",
        "changelog.md",
        "extra.txt",
        "notes.txt",
        "pyproject.toml",
    ]
    assert first_snapshot.additional_file_count == 1
    assert first_snapshot.high_signal_paths == [
        "README.md",
        "pyproject.toml",
        "src/",
        "tests/",
        "docs/",
        "evals/",
        "frontend/",
    ]
    assert first_snapshot.project_markers == [
        "python_pyproject",
        "src_layout",
        "tests_present",
        "docs_present",
        "evals_present",
        "frontend_present",
    ]


def test_repository_context_formatter_renders_expected_summary() -> None:
    formatted = format_repository_context_for_prompt(
        RepositoryContextSnapshot(
            workspace_name="glassbox",
            high_signal_paths=["README.md", "src/", "tests/"],
            top_level_directories=["docs/", "src/", "tests/"],
            additional_directory_count=2,
            top_level_files=["LICENSE", "README.md", "pyproject.toml"],
            additional_file_count=1,
            project_markers=["python_pyproject", "src_layout", "tests_present"],
        )
    )

    assert formatted == "\n".join(
        [
            "Workspace: glassbox",
            "High-signal paths: README.md, src/, tests/",
            "Top-level directories: docs/, src/, tests/ (+2 more)",
            "Top-level files: LICENSE, README.md, pyproject.toml (+1 more)",
            "Project markers: python_pyproject, src_layout, tests_present",
        ]
    )


def test_repository_context_snapshot_handles_missing_workspace() -> None:
    snapshot = build_repository_context_snapshot(
        Path("/tmp/glassbox-missing-workspace")
    )

    assert snapshot == RepositoryContextSnapshot(
        workspace_name="glassbox-missing-workspace"
    )


def test_runtime_context_snapshot_is_bounded_and_preserves_note_provenance(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    parent_session_id = new_session_id()
    child_session_id = new_session_id()

    runtime_context = build_runtime_context_snapshot(
        tmp_path,
        [
            RuntimeNoteRecord(
                source_sequence=1,
                category="repo",
                message="README changed recently",
                source_session_id=parent_session_id,
                created_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
                inherited=True,
            ),
            RuntimeNoteRecord(
                source_sequence=2,
                category="plan",
                message="Need operator approval before write",
                source_session_id=child_session_id,
                created_at=datetime(2026, 4, 23, 12, 1, tzinfo=UTC),
                inherited=False,
            ),
        ],
        note_limit=1,
    )

    assert runtime_context == RuntimeContextSnapshot(
        repository_context=RepositoryContextSnapshot(
            workspace_name=tmp_path.name,
            high_signal_paths=["README.md", "src/"],
            top_level_directories=["src/"],
            additional_directory_count=0,
            top_level_files=["README.md"],
            additional_file_count=0,
            project_markers=["src_layout"],
        ),
        runtime_notes=[
            RuntimeContextNoteSnapshot(
                category="repo",
                message="README changed recently",
                inherited=True,
                source_session_id=parent_session_id,
            )
        ],
        additional_runtime_note_count=1,
        working_set=WorkingSetSnapshot(),
    )


def test_runtime_context_snapshot_includes_working_set_summary(tmp_path: Path) -> None:
    runtime_context = build_runtime_context_snapshot(
        tmp_path,
        [],
        working_set=WorkingSetSnapshot(
            items=[
                WorkingSetItemSnapshot(
                    subject_kind="file",
                    subject="src/glassbox/runtime/context_builder.py",
                    summary="recently targeted workspace path",
                    reasons=[
                        ("apply_patch targeted src/glassbox/runtime/context_builder.py")
                    ],
                    signal_types=["tool_request_path"],
                )
            ],
            additional_item_count=1,
        ),
    )

    assert runtime_context.working_set == WorkingSetSnapshot(
        items=[
            WorkingSetItemSnapshot(
                subject_kind="file",
                subject="src/glassbox/runtime/context_builder.py",
                summary="recently targeted workspace path",
                reasons=[
                    ("apply_patch targeted src/glassbox/runtime/context_builder.py")
                ],
                signal_types=["tool_request_path"],
                inherited=False,
            )
        ],
        additional_item_count=1,
    )


def test_memory_and_repository_index_context_snapshots_are_bounded(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    confirmed = _workspace_memory_entry(
        session_id,
        summary="Run backend tests with uv",
        content="Use uv run pytest tests/unit for backend unit tests.",
        source_sequence=2,
    )
    unconfirmed = _workspace_memory_entry(
        session_id,
        summary="Draft memory",
        content="Do not include unconfirmed memory.",
        source_sequence=3,
        confirmed=False,
    )
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            cwd=tmp_path,
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=4,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=4,
        ),
        [],
        workspace_memory=[confirmed, unconfirmed],
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\n',
        encoding="utf-8",
    )
    build_and_write_repository_index(tmp_path)

    memory_items, additional_memory, memory_bytes = (
        build_workspace_memory_context_snapshot(repository)
    )
    repository_index = build_repository_index_context_snapshot(tmp_path, item_limit=2)

    assert [item.memory_id for item in memory_items] == [confirmed.memory_id]
    assert additional_memory == 0
    assert memory_bytes > 0
    assert repository_index.status == "fresh"
    assert repository_index.entry_count >= 2
    assert len(repository_index.items) == 2
    assert repository_index.additional_item_count == repository_index.entry_count - 2


def test_runtime_context_snapshot_includes_artifact_backed_summary() -> None:
    runtime_context = build_runtime_context_snapshot(
        Path("/tmp/glassbox"),
        [],
        artifact_context=ArtifactBackedContextSnapshot(
            summaries=[
                ArtifactBackedContextSummarySnapshot(
                    summary_kind="pytest_failure_digest",
                    source_tool_name="run_tests",
                    artifact_kind=PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
                    artifact_path=".glassbox/sessions/session-123/artifacts/digest.json",
                    summary="1 failing test(s) for tests/unit/test_context_builder.py",
                    target_paths=["tests/unit/test_context_builder.py"],
                    failing_tests=[
                        "tests/unit/test_context_builder.py::test_example_failure"
                    ],
                    failure_count=1,
                )
            ]
        ),
    )

    assert runtime_context.artifact_context == ArtifactBackedContextSnapshot(
        summaries=[
            ArtifactBackedContextSummarySnapshot(
                summary_kind="pytest_failure_digest",
                source_tool_name="run_tests",
                artifact_kind=PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
                artifact_path=".glassbox/sessions/session-123/artifacts/digest.json",
                summary="1 failing test(s) for tests/unit/test_context_builder.py",
                target_paths=["tests/unit/test_context_builder.py"],
                failing_tests=[
                    "tests/unit/test_context_builder.py::test_example_failure"
                ],
                failure_count=1,
                error_count=0,
                timed_out=False,
                freshness="fresh",
                inherited=False,
            )
        ],
        additional_summary_count=0,
    )


def test_runtime_context_budget_summary_reports_visible_and_truncated_counts() -> None:
    runtime_context = RuntimeContextSnapshot(
        repository_context=RepositoryContextSnapshot(
            workspace_name="glassbox",
            top_level_directories=["docs/", "src/"],
            additional_directory_count=3,
            top_level_files=["README.md"],
        ),
        runtime_notes=[
            RuntimeContextNoteSnapshot(category="repo", message="Keep context small")
        ],
        additional_runtime_note_count=2,
        working_set=WorkingSetSnapshot(
            items=[
                WorkingSetItemSnapshot(
                    subject_kind="file",
                    subject="src/glassbox/runtime/context_builder.py",
                    summary="recently targeted workspace path",
                )
            ],
            additional_item_count=4,
        ),
        artifact_context=ArtifactBackedContextSnapshot(additional_summary_count=1),
    )

    assert format_runtime_context_budget_summary(runtime_context) == (
        "repo dirs 2 visible (+3 more); repo files 1 visible; "
        "notes 1 visible (+2 more); working set 1 visible (+4 more); "
        "artifact summaries 0 visible (+1 more); "
        "workspace memory 0 visible; repo index 0 visible"
    )


def test_build_pytest_failure_digest_artifact_ignores_successful_test_runs() -> None:
    artifact = build_pytest_failure_digest_artifact(
        {"paths": ["tests/unit/test_context_builder.py"]},
        {
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "stdout": ".\n1 passed in 0.01s\n",
            "stderr": "",
            "timed_out": False,
        },
    )

    assert artifact is None


def test_artifact_backed_context_snapshot_tracks_freshness_and_staleness() -> None:
    session_id = new_session_id()
    stale_tool_call_id = new_tool_call_id()
    current_tool_call_id = new_tool_call_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 23, 12, 1, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=4,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=4,
        ),
        [],
        events=[
            EventEnvelope(
                session_id=session_id,
                sequence=1,
                payload=ModelToolCallRequested(
                    turn_id=new_turn_id(),
                    tool_call_id=stale_tool_call_id,
                    tool_name="run_tests",
                    arguments_json='{"paths":["tests/unit/test_old.py"]}',
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=2,
                payload=ToolArtifactRecorded(
                    turn_id=new_turn_id(),
                    tool_call_id=stale_tool_call_id,
                    artifact_id=new_artifact_id(),
                    artifact_kind=PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
                    path=".glassbox/sessions/session/artifacts/old-digest.json",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=3,
                payload=ModelToolCallRequested(
                    turn_id=new_turn_id(),
                    tool_call_id=current_tool_call_id,
                    tool_name="run_tests",
                    arguments_json='{"paths":["tests/unit/test_new.py"]}',
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=4,
                payload=ToolArtifactRecorded(
                    turn_id=new_turn_id(),
                    tool_call_id=current_tool_call_id,
                    artifact_id=new_artifact_id(),
                    artifact_kind=PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
                    path=".glassbox/sessions/session/artifacts/new-digest.json",
                ),
            ),
        ],
    )
    artifact_repository = FakeArtifactRepository(
        {
            ".glassbox/sessions/session/artifacts/old-digest.json": json.dumps(
                PytestFailureDigestArtifact(
                    target_paths=["tests/unit/test_old.py"],
                    failure_count=1,
                    failing_tests=["tests/unit/test_old.py::test_old_failure"],
                ).model_dump(mode="json")
            ),
            ".glassbox/sessions/session/artifacts/new-digest.json": json.dumps(
                PytestFailureDigestArtifact(
                    target_paths=["tests/unit/test_new.py"],
                    failure_count=2,
                    failing_tests=[
                        "tests/unit/test_new.py::test_first_failure",
                        "tests/unit/test_new.py::test_second_failure",
                    ],
                ).model_dump(mode="json")
            ),
        }
    )

    artifact_context = build_artifact_backed_context_snapshot(
        repository,
        artifact_repository,
        session_id,
    )
    fresh_only_context = build_artifact_backed_context_snapshot(
        repository,
        artifact_repository,
        session_id,
        include_stale=False,
    )

    assert [summary.freshness for summary in artifact_context.summaries] == [
        "fresh",
        "stale",
    ]
    assert [summary.target_paths for summary in fresh_only_context.summaries] == [
        ["tests/unit/test_new.py"]
    ]


def test_working_set_snapshot_prefers_explicit_signals_and_deduplicates_paths() -> None:
    session_id = new_session_id()
    parent_session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.AWAITING_APPROVAL,
            created_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 23, 12, 5, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=12,
            parent_session_id=parent_session_id,
            branch_label="alt-path",
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.AWAITING_APPROVAL,
            last_sequence=12,
            pending_approval_id=new_approval_id(),
        ),
        [],
        runtime_notes=[
            RuntimeNoteRecord(
                source_sequence=2,
                category="repo",
                message="Keep src/glassbox/runtime/context_builder.py in focus",
                source_session_id=session_id,
                created_at=datetime(2026, 4, 23, 12, 4, tzinfo=UTC),
                inherited=False,
            ),
            RuntimeNoteRecord(
                source_sequence=1,
                category="plan",
                message="Child session inherited runtime-context investigation",
                source_session_id=parent_session_id,
                created_at=datetime(2026, 4, 23, 12, 3, tzinfo=UTC),
                inherited=True,
            ),
        ],
        events=[
            EventEnvelope(
                session_id=session_id,
                sequence=8,
                payload=ModelToolCallRequested(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="read_file",
                    arguments_json='{"path":"src/glassbox/runtime/context_builder.py"}',
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=9,
                payload=ModelToolCallRequested(
                    turn_id=turn_id,
                    tool_call_id=new_tool_call_id(),
                    tool_name="apply_patch",
                    arguments_json='{"path":"src/glassbox/runtime/context_builder.py","old_text":"x","new_text":"y"}',
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=10,
                payload=ModelToolCallRequested(
                    turn_id=turn_id,
                    tool_call_id=new_tool_call_id(),
                    tool_name="run_tests",
                    arguments_json='{"paths":["tests/unit/test_context_builder.py"]}',
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=11,
                payload=ToolArtifactRecorded(
                    turn_id=turn_id,
                    tool_call_id=new_tool_call_id(),
                    artifact_id=new_artifact_id(),
                    artifact_kind="pytest_failure",
                    path=(f".glassbox/sessions/{session_id}/artifacts/failure.txt"),
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=12,
                payload=ToolArtifactRecorded(
                    turn_id=turn_id,
                    tool_call_id=new_tool_call_id(),
                    artifact_id=new_artifact_id(),
                    artifact_kind="tool_output_partial_truncated_unredacted",
                    path=(f".glassbox/sessions/{session_id}/artifacts/output.json"),
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=13,
                payload=ReplayArtifactRecorded(
                    turn_id=turn_id,
                    artifact_id=new_artifact_id(),
                    artifact_kind="replay_model_call",
                    path=".glassbox/sessions/ignored/artifacts/replay.json",
                ),
            ),
        ],
        tool_calls=[
            ToolCallRecord(
                tool_call_id=tool_call_id,
                turn_id=turn_id,
                tool_name="run_command",
                status=ToolExecutionStatus.FAILED,
                started_at=datetime(2026, 4, 23, 12, 2, tzinfo=UTC),
                completed_at=datetime(2026, 4, 23, 12, 2, 30, tzinfo=UTC),
                summary="pytest exited with code 1",
            )
        ],
        approvals=[
            ApprovalRecord(
                approval_id=new_approval_id(),
                turn_id=turn_id,
                subject="apply_patch src/glassbox/runtime/context_builder.py",
                reason="workspace write requires approval",
                status=ApprovalStatus.PENDING,
                requested_at=datetime(2026, 4, 23, 12, 5, tzinfo=UTC),
            )
        ],
    )

    working_set = build_working_set_snapshot(repository, session_id)

    assert working_set.items[0] == WorkingSetItemSnapshot(
        subject_kind="approval",
        subject="apply_patch src/glassbox/runtime/context_builder.py",
        summary="pending approval focus",
        reasons=["pending approval: workspace write requires approval"],
        signal_types=["approval"],
        inherited=False,
    )
    file_item = next(
        item
        for item in working_set.items
        if item.subject == "src/glassbox/runtime/context_builder.py"
    )
    assert file_item.subject_kind == "file"
    assert file_item.summary == "recently targeted workspace path"
    assert file_item.signal_types == ["tool_request_path"]
    assert file_item.reasons == [
        "apply_patch targeted src/glassbox/runtime/context_builder.py",
        "read_file targeted src/glassbox/runtime/context_builder.py",
    ]

    assert next(
        item
        for item in working_set.items
        if item.subject == "tests/unit/test_context_builder.py"
    ) == WorkingSetItemSnapshot(
        subject_kind="test",
        subject="tests/unit/test_context_builder.py",
        summary="recent test target",
        reasons=["run_tests targeted tests/unit/test_context_builder.py"],
        signal_types=["tool_request_test_path"],
        inherited=False,
    )
    assert (
        next(
            item for item in working_set.items if item.subject_kind == "artifact"
        ).summary
        == "recent test artifact"
    )
    assert all("output.json" not in item.subject for item in working_set.items)
    assert (
        next(
            item for item in working_set.items if item.subject_kind == "branch"
        ).inherited
        is True
    )


def test_working_set_snapshot_is_bounded_and_reports_overflow() -> None:
    session_id = new_session_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 23, 12, 1, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=4,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=4,
        ),
        [],
        events=[
            EventEnvelope(
                session_id=session_id,
                sequence=1,
                payload=ModelToolCallRequested(
                    turn_id=new_turn_id(),
                    tool_call_id=new_tool_call_id(),
                    tool_name="read_file",
                    arguments_json='{"path":"src/a.py"}',
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=2,
                payload=ModelToolCallRequested(
                    turn_id=new_turn_id(),
                    tool_call_id=new_tool_call_id(),
                    tool_name="read_file",
                    arguments_json='{"path":"src/b.py"}',
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=3,
                payload=ModelToolCallRequested(
                    turn_id=new_turn_id(),
                    tool_call_id=new_tool_call_id(),
                    tool_name="run_tests",
                    arguments_json='{"paths":["tests/test_b.py"]}',
                ),
            ),
        ],
        runtime_notes=[
            RuntimeNoteRecord(
                source_sequence=1,
                category="repo",
                message="Keep src/a.py in focus",
                source_session_id=session_id,
                created_at=datetime(2026, 4, 23, 12, 1, tzinfo=UTC),
                inherited=False,
            )
        ],
    )

    working_set = build_working_set_snapshot(repository, session_id, item_limit=2)

    assert working_set.additional_item_count == 2
    assert [item.subject for item in working_set.items] == [
        "tests/test_b.py",
        "src/b.py",
    ]


def test_derive_runtime_context_snapshot_preserves_shared_structured_inputs() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    repository = FakeSessionRepository(
        SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 24, 12, 1, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=4,
        ),
        SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=4,
        ),
        [],
        runtime_notes=[
            RuntimeNoteRecord(
                source_sequence=1,
                category="repo",
                message="Carry branch notes into child sessions",
                source_session_id=new_session_id(),
                created_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
                inherited=True,
            )
        ],
        events=[
            EventEnvelope(
                session_id=session_id,
                sequence=1,
                payload=ModelToolCallRequested(
                    turn_id=turn_id,
                    tool_call_id=new_tool_call_id(),
                    tool_name="run_tests",
                    arguments_json='{"paths":["tests/unit/test_context_builder.py"]}',
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=2,
                payload=ToolArtifactRecorded(
                    turn_id=turn_id,
                    tool_call_id=new_tool_call_id(),
                    artifact_id=new_artifact_id(),
                    artifact_kind=PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
                    path=".glassbox/sessions/test/artifacts/failure.json",
                ),
            ),
        ],
    )
    artifacts = FakeArtifactRepository(
        {
            ".glassbox/sessions/test/artifacts/failure.json": json.dumps(
                {
                    "summary_kind": "pytest_failure_digest",
                    "source_tool_name": "run_tests",
                    "target_paths": ["tests/unit/test_context_builder.py"],
                    "failure_count": 1,
                    "error_count": 0,
                    "timed_out": False,
                    "failing_tests": [
                        "tests/unit/test_context_builder.py::test_example"
                    ],
                }
            )
        }
    )

    runtime_context = derive_runtime_context_snapshot(
        repository,
        session_id,
        Path("/tmp/glassbox"),
        artifact_repository=artifacts,
        include_stale_artifacts=False,
    )

    assert runtime_context.runtime_notes == [
        RuntimeContextNoteSnapshot(
            category="repo",
            message="Carry branch notes into child sessions",
            inherited=True,
            source_session_id=repository.list_runtime_notes(session_id)[
                0
            ].source_session_id,
        )
    ]
    assert runtime_context.artifact_context.summaries[0].freshness == "fresh"
    assert runtime_context.artifact_context.summaries[0].failing_tests == [
        "tests/unit/test_context_builder.py::test_example"
    ]


def _workspace_memory_entry(
    session_id,
    *,
    summary: str,
    content: str,
    source_sequence: int,
    confirmed: bool = True,
) -> WorkspaceMemoryEntry:
    now = datetime(2026, 4, 24, 12, source_sequence, tzinfo=UTC)
    return WorkspaceMemoryEntry(
        memory_id=new_workspace_memory_id(),
        session_id=session_id,
        kind=WorkspaceMemoryKind.COMMAND,
        state=WorkspaceMemoryState.ACTIVE,
        content=content,
        summary=summary,
        provenance=WorkspaceMemoryProvenance(
            source_type=WorkspaceMemorySourceType.SESSION_EVENT,
            session_id=session_id,
            source_sequence=source_sequence,
        ),
        created_at=now,
        updated_at=now,
        confirmed_by="operator" if confirmed else None,
        confirmed_at=now if confirmed else None,
        last_sequence=source_sequence,
    )


class ReadFileArgs(BaseModel):
    path: str


class ReadFileResult(BaseModel):
    content: str


class ReadFileTool:
    spec = ToolSpec(
        name="read_file",
        description="Read a file from the workspace.",
        input_model=ReadFileArgs,
        output_model=ReadFileResult,
        risk_level=ToolRiskLevel.READ_ONLY,
    )

    async def execute(self, arguments: ReadFileArgs) -> ReadFileResult:
        return ReadFileResult(content=arguments.path)
