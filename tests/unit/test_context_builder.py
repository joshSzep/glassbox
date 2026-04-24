"""Unit tests for the runtime turn context builder."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel

from glassbox.core import (
    MessagePart,
    ResolvedForkPoint,
    SessionRecord,
    SessionState,
    SessionStatus,
    TranscriptMessage,
    new_approval_id,
    new_message_id,
    new_session_id,
    new_turn_id,
)
from glassbox.runtime import (
    ToolSchema,
    TurnContextBuilder,
    format_tool_schemas_for_prompt,
    format_transcript_for_prompt,
)
from glassbox.tools import ToolRegistry, ToolRiskLevel, ToolSpec


class FakeSessionRepository:
    def __init__(self, session, session_state, transcript):
        self._session = session
        self._session_state = session_state
        self._transcript = transcript

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

    def list_transcript_messages(self, session_id):
        if self._session.session_id != session_id:
            return []
        return list(self._transcript)

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

    def read_session_events(self, session_id):
        return []

    def read_session_events_after(self, session_id, after_sequence):
        return []

    def read_events_by_correlation_id(
        self,
        session_id,
        *,
        turn_id=None,
        message_id=None,
        tool_call_id=None,
        approval_id=None,
    ):
        return []

    def rebuild_session_projections(self, session_id) -> None:
        return None

    def list_tool_calls(self, session_id, *, status=None):
        return []

    def list_approvals(self, session_id, *, status=None):
        return []

    def list_turn_metrics(self, session_id, *, limit=None):
        return []

    def resolve_fork_point(self, session_id, *, turn_id=None):
        return ResolvedForkPoint(
            parent_session_id=session_id,
            turn_id=new_turn_id(),
            sequence=0,
            inherited_messages=[],
        )

    def build_imported_transcript_events(self, session_id, fork_point):
        return []


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
