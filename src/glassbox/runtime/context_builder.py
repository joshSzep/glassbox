"""Typed context assembly for model turns."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field

from glassbox.core.ids import ApprovalId, SessionId, TurnId
from glassbox.core.models import TranscriptMessage
from glassbox.core.types import SessionStatus
from glassbox.services import SessionRepository


class ToolSchema(BaseModel):
    """Stable typed description of a tool exposed to the model."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    parameters_json_schema: dict[str, object] = Field(default_factory=dict)


class PolicyContext(BaseModel):
    """Policy-relevant session context used for prompt assembly."""

    model_config = ConfigDict(extra="forbid")

    approval_mode: str
    pending_approval_id: ApprovalId | None = None


class TurnContext(BaseModel):
    """Structured context derived for one model turn."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    session_status: SessionStatus
    current_turn_id: TurnId | None = None
    last_sequence: int = Field(ge=0)
    transcript: list[TranscriptMessage]
    available_tools: list[ToolSchema]
    policy: PolicyContext
    repo_context: str | None = None
    memory_notes: list[str] = Field(default_factory=list)


class TurnContextBuilder:
    """Build a stable typed turn context from persisted session data."""

    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    def build(
        self,
        session_id: SessionId,
        *,
        tool_schemas: Sequence[ToolSchema] = (),
        repo_context: str | None = None,
        memory_notes: Sequence[str] = (),
    ) -> TurnContext:
        session = self._session_repository.get_session(session_id)
        session_state = self._session_repository.get_session_state(session_id)
        if session is None or session_state is None:
            raise ValueError(f"unknown session_id: {session_id}")

        transcript = sorted(
            self._session_repository.list_transcript_messages(session_id),
            key=lambda message: message.created_at,
        )
        normalized_tools = normalize_tool_schemas(tool_schemas)
        return TurnContext(
            session_id=session_id,
            session_status=session_state.status,
            current_turn_id=session_state.current_turn_id,
            last_sequence=session_state.last_sequence,
            transcript=transcript,
            available_tools=normalized_tools,
            policy=PolicyContext(
                approval_mode=session.approval_mode,
                pending_approval_id=session_state.pending_approval_id,
            ),
            repo_context=repo_context,
            memory_notes=list(memory_notes),
        )


def normalize_tool_schemas(tool_schemas: Iterable[ToolSchema]) -> list[ToolSchema]:
    """Return tool schemas in stable name order with duplicate protection."""

    ordered_tools = sorted(tool_schemas, key=lambda tool: tool.name)
    seen_names: set[str] = set()
    for tool in ordered_tools:
        if tool.name in seen_names:
            raise ValueError(f"duplicate tool schema name: {tool.name}")
        seen_names.add(tool.name)
    return ordered_tools


def format_transcript_for_prompt(transcript: Sequence[TranscriptMessage]) -> str:
    """Render transcript summaries into a stable prompt-friendly text block."""

    lines: list[str] = []
    for message in transcript:
        content = "\n".join(part.text for part in message.parts)
        lines.append(f"{message.role.upper()}: {content}")
    return "\n\n".join(lines)


def format_tool_schemas_for_prompt(tool_schemas: Sequence[ToolSchema]) -> str:
    """Render tool schemas into a stable prompt-friendly text block."""

    lines: list[str] = []
    for tool in normalize_tool_schemas(tool_schemas):
        lines.append(f"- {tool.name}: {tool.description}")
    return "\n".join(lines)
