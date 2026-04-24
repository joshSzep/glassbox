"""Typed context assembly for model turns."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from glassbox.core.ids import ApprovalId, SessionId, TurnId
from glassbox.core.models import TranscriptMessage
from glassbox.core.types import SessionStatus
from glassbox.services import SessionRepository
from glassbox.tools import ToolRegistry, ToolSchema

_DEFAULT_REPOSITORY_CONTEXT_DIRECTORY_LIMIT = 8
_DEFAULT_REPOSITORY_CONTEXT_FILE_LIMIT = 8
_HIGH_SIGNAL_REPOSITORY_ENTRIES = (
    "README.md",
    "pyproject.toml",
    "package.json",
    "src",
    "tests",
    "docs",
    "evals",
    "frontend",
)


class RepositoryContextSnapshot(BaseModel):
    """Deterministic top-level repository summary for prompt context."""

    model_config = ConfigDict(extra="forbid")

    workspace_name: str
    high_signal_paths: list[str] = Field(default_factory=list)
    top_level_directories: list[str] = Field(default_factory=list)
    additional_directory_count: int = Field(default=0, ge=0)
    top_level_files: list[str] = Field(default_factory=list)
    additional_file_count: int = Field(default=0, ge=0)
    project_markers: list[str] = Field(default_factory=list)


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
        tool_registry: ToolRegistry | None = None,
        repo_context: str | None = None,
        memory_notes: Sequence[str] = (),
    ) -> TurnContext:
        session = self._session_repository.get_session(session_id)
        session_state = self._session_repository.get_session_state(session_id)
        if session is None or session_state is None:
            raise ValueError(f"unknown session_id: {session_id}")
        if tool_registry is not None and tool_schemas:
            raise ValueError("pass either tool_registry or tool_schemas, not both")

        transcript = sorted(
            self._session_repository.list_transcript_messages(session_id),
            key=lambda message: message.created_at,
        )
        normalized_tools = (
            tool_registry.list_schemas()
            if tool_registry is not None
            else normalize_tool_schemas(tool_schemas)
        )
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


def build_repository_context_snapshot(
    workspace_root: Path,
    *,
    directory_limit: int = _DEFAULT_REPOSITORY_CONTEXT_DIRECTORY_LIMIT,
    file_limit: int = _DEFAULT_REPOSITORY_CONTEXT_FILE_LIMIT,
) -> RepositoryContextSnapshot:
    """Return a bounded deterministic summary of the workspace root."""

    resolved_root = workspace_root.resolve()
    entries = sorted(
        (entry for entry in resolved_root.iterdir() if not entry.name.startswith(".")),
        key=lambda entry: entry.name,
    )
    directory_names = [entry.name for entry in entries if entry.is_dir()]
    file_names = [entry.name for entry in entries if entry.is_file()]

    limited_directories = directory_names[:directory_limit]
    limited_files = file_names[:file_limit]

    return RepositoryContextSnapshot(
        workspace_name=resolved_root.name or str(resolved_root),
        high_signal_paths=[
            _repository_entry_display_name(entry_name)
            for entry_name in _HIGH_SIGNAL_REPOSITORY_ENTRIES
            if entry_name in directory_names or entry_name in file_names
        ],
        top_level_directories=[
            _repository_entry_display_name(directory_name)
            for directory_name in limited_directories
        ],
        additional_directory_count=max(
            len(directory_names) - len(limited_directories),
            0,
        ),
        top_level_files=limited_files,
        additional_file_count=max(len(file_names) - len(limited_files), 0),
        project_markers=_repository_project_markers(directory_names, file_names),
    )


def format_repository_context_for_prompt(
    snapshot: RepositoryContextSnapshot,
) -> str:
    """Render a repository-context snapshot into a stable prompt fragment."""

    lines = [f"Workspace: {snapshot.workspace_name}"]
    if snapshot.high_signal_paths:
        lines.append("High-signal paths: " + ", ".join(snapshot.high_signal_paths))
    if snapshot.top_level_directories:
        directory_line = ", ".join(snapshot.top_level_directories)
        if snapshot.additional_directory_count:
            directory_line += f" (+{snapshot.additional_directory_count} more)"
        lines.append("Top-level directories: " + directory_line)
    if snapshot.top_level_files:
        file_line = ", ".join(snapshot.top_level_files)
        if snapshot.additional_file_count:
            file_line += f" (+{snapshot.additional_file_count} more)"
        lines.append("Top-level files: " + file_line)
    if snapshot.project_markers:
        lines.append("Project markers: " + ", ".join(snapshot.project_markers))
    return "\n".join(lines)


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


def _repository_entry_display_name(entry_name: str) -> str:
    if "." not in entry_name:
        return f"{entry_name}/"
    return entry_name


def _repository_project_markers(
    directory_names: Sequence[str],
    file_names: Sequence[str],
) -> list[str]:
    markers: list[str] = []
    if "pyproject.toml" in file_names:
        markers.append("python_pyproject")
    if "package.json" in file_names:
        markers.append("javascript_package")
    if "src" in directory_names:
        markers.append("src_layout")
    if "tests" in directory_names:
        markers.append("tests_present")
    if "docs" in directory_names:
        markers.append("docs_present")
    if "evals" in directory_names:
        markers.append("evals_present")
    if "frontend" in directory_names:
        markers.append("frontend_present")
    return markers
