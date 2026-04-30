"""Prompt-facing formatting helpers for runtime context."""

from collections.abc import Iterable
from collections.abc import Sequence

from glassbox.core.models import TranscriptMessage
from glassbox.runtime.context_models import CheckpointResumeSnapshot
from glassbox.runtime.context_models import ContextCompactionContextSnapshot
from glassbox.runtime.context_models import RepositoryContextSnapshot
from glassbox.runtime.context_models import RepositoryIndexContextSnapshot
from glassbox.runtime.context_models import RuntimeContextNoteSnapshot
from glassbox.runtime.context_models import RuntimeContextSnapshot
from glassbox.runtime.context_models import WorkspaceMemoryContextItemSnapshot
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


def format_repository_index_for_prompt(
    snapshot: RepositoryIndexContextSnapshot | None,
) -> str:
    """Render repository-index selections into a separate prompt fragment."""

    if snapshot is None:
        return ""
    lines = [f"Repository index: {snapshot.status}; entries {snapshot.entry_count}"]
    if snapshot.detail is not None:
        lines.append(f"Repository index detail: {snapshot.detail}")
    for item in snapshot.items:
        location = item.path or "workspace"
        symbol_suffix = f"::{item.symbol}" if item.symbol else ""
        summary = item.summary or item.name
        source = item.source_type or "unknown"
        lines.append(
            f"- [{item.kind}] {location}{symbol_suffix}: {summary} (source: {source})"
        )
    return "\n".join(lines)


def format_runtime_notes_for_prompt(
    notes: Sequence[RuntimeContextNoteSnapshot],
) -> list[str]:
    """Render runtime-note snapshots into stable prompt memory notes."""

    formatted_notes: list[str] = []
    for note in notes:
        category_prefix = (
            f"inherited {note.category}" if note.inherited else note.category
        )
        formatted_notes.append(f"[{category_prefix}] {note.message}")
    return formatted_notes


def format_workspace_memory_for_prompt(
    entries: Sequence[WorkspaceMemoryContextItemSnapshot],
) -> list[str]:
    """Render confirmed workspace-memory entries into stable prompt notes."""

    formatted: list[str] = []
    for entry in entries:
        provenance = entry.provenance
        source = provenance.source_type
        if provenance.source_sequence is not None:
            source += f":{provenance.source_sequence}"
        if provenance.session_id is not None:
            source += f"@{str(provenance.session_id)[:8]}"
        text = entry.content if entry.content else entry.summary
        formatted.append(
            f"[workspace-memory {entry.kind} {source}] {entry.summary}: {text}"
        )
    return formatted


def format_checkpoint_resume_for_prompt(
    checkpoint: CheckpointResumeSnapshot,
) -> list[str]:
    """Render checkpoint resume posture into stable prompt notes."""

    source_range = (
        f"events {checkpoint.source_start_sequence}-{checkpoint.source_end_sequence}"
    )
    freshness = (
        f"checkpoint event {checkpoint.checkpoint_sequence}; "
        f"latest session event {checkpoint.latest_session_sequence}"
    )
    notes = [
        (
            f"[checkpoint-resume {checkpoint.status} {source_range}] "
            f"context source: {checkpoint.context_source}; {checkpoint.reason}"
        ),
        f"[checkpoint objective] {checkpoint.objective}",
    ]
    if checkpoint.current_phase is not None:
        notes.append(f"[checkpoint phase] {checkpoint.current_phase.value}")
    if checkpoint.completed_step:
        notes.append(f"[checkpoint completed] {checkpoint.completed_step}")
    notes.append(f"[checkpoint next action] {checkpoint.next_action}")
    notes.append(f"[checkpoint recovery] {checkpoint.recovery_guidance}")
    notes.append(f"[checkpoint provenance] {freshness}")
    if checkpoint.blockers:
        notes.append("[checkpoint blockers] " + "; ".join(checkpoint.blockers[:5]))
    if checkpoint.touched_files:
        notes.append(
            "[checkpoint touched files] " + ", ".join(checkpoint.touched_files[:8])
        )
    if checkpoint.workspace_drift_paths:
        notes.append(
            "[checkpoint workspace drift] "
            + ", ".join(checkpoint.workspace_drift_paths[:8])
        )
    if checkpoint.verification_status:
        notes.append(f"[checkpoint verification] {checkpoint.verification_status}")
    if checkpoint.budget_status:
        notes.append(f"[checkpoint budget] {checkpoint.budget_status}")
    for limitation in checkpoint.limitations[:3]:
        notes.append(f"[checkpoint limitation] {limitation}")
    if not checkpoint.safe_to_use:
        notes.append(
            "[checkpoint caveat] Treat transcript, events, and current workspace "
            "state as authoritative until the checkpoint is refreshed or resolved."
        )
    return notes


def format_context_compactions_for_prompt(
    compactions: ContextCompactionContextSnapshot,
) -> list[str]:
    """Render fresh compaction summaries into stable prompt notes."""

    notes: list[str] = []
    for item in compactions.items:
        notes.append(
            "[context-compaction "
            f"{item.scope.value} events {item.source_start_sequence}-"
            f"{item.source_end_sequence}] {item.summary}"
        )
        notes.append(
            "[context-compaction provenance] "
            f"compaction {item.compaction_id}; artifact {item.artifact_id}; "
            f"freshness {item.freshness.value}; decisions {item.decision_count}; "
            f"questions {item.unresolved_question_count}; risks "
            f"{item.accepted_risk_count}"
        )
        for limitation in item.limitations[:2]:
            notes.append(f"[context-compaction limitation] {limitation}")
    if compactions.additional_item_count:
        notes.append(
            "[context-compaction omitted] "
            f"{compactions.additional_item_count} additional fresh compaction(s)"
        )
    if compactions.stale_item_count:
        notes.append(
            "[context-compaction stale] "
            f"{compactions.stale_item_count} stale compaction(s) excluded from "
            "active prompt context"
        )
    return notes


def format_runtime_context_budget_summary(
    snapshot: RuntimeContextSnapshot,
) -> str:
    """Render visible and truncated runtime-context counts for operators."""

    return "; ".join(
        [
            _budget_segment(
                "repo dirs",
                len(snapshot.repository_context.top_level_directories),
                snapshot.repository_context.additional_directory_count,
            ),
            _budget_segment(
                "repo files",
                len(snapshot.repository_context.top_level_files),
                snapshot.repository_context.additional_file_count,
            ),
            _budget_segment(
                "notes",
                len(snapshot.runtime_notes),
                snapshot.additional_runtime_note_count,
            ),
            _budget_segment(
                "working set",
                len(snapshot.working_set.items),
                snapshot.working_set.additional_item_count,
            ),
            _budget_segment(
                "artifact summaries",
                len(snapshot.artifact_context.summaries),
                snapshot.artifact_context.additional_summary_count,
            ),
            _budget_segment(
                "workspace memory",
                len(snapshot.workspace_memory),
                snapshot.additional_workspace_memory_count,
            ),
            _budget_segment(
                "repo index",
                len(snapshot.repository_index.items)
                if snapshot.repository_index is not None
                else 0,
                snapshot.repository_index.additional_item_count
                if snapshot.repository_index is not None
                else 0,
            ),
        ]
    )


def _budget_segment(label: str, visible_count: int, additional_count: int) -> str:
    suffix = f" (+{additional_count} more)" if additional_count else ""
    return f"{label} {visible_count} visible{suffix}"
