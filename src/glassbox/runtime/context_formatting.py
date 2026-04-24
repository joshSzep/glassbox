"""Prompt-facing formatting helpers for runtime context."""

from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Sequence

from glassbox.core.models import TranscriptMessage
from glassbox.runtime.context_models import RepositoryContextSnapshot
from glassbox.tools import ToolSchema


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
