"""Workspace memory observability collector."""

from pathlib import Path

from glassbox.core.types import WorkspaceMemoryState
from glassbox.runtime.observability_models import WorkspaceMemoryObservability
from glassbox.runtime.workspace_memory_conflicts import workspace_memory_conflicts
from glassbox.services import SessionRepository


def build_workspace_memory_observability(
    session_repository: SessionRepository,
    *,
    workspace_root: Path | None = None,
) -> WorkspaceMemoryObservability:
    entries = session_repository.list_workspace_memory(include_pruned=True)
    counts = {state.value: 0 for state in WorkspaceMemoryState}
    redacted_count = 0
    invalidated_entries = []
    for entry in entries:
        counts[entry.state.value] = counts.get(entry.state.value, 0) + 1
        if entry.redacted:
            redacted_count += 1
        if entry.state == WorkspaceMemoryState.INVALIDATED:
            invalidated_entries.append(entry)

    latest_invalidated = max(
        invalidated_entries,
        key=lambda entry: entry.updated_at,
        default=None,
    )
    conflict_records = (
        workspace_memory_conflicts(workspace_root, entries)
        if workspace_root is not None
        else []
    )
    next_actions: list[str] = []
    if conflict_records:
        next_actions.append("glassbox memory list --state active --cwd .")
        next_actions.append("glassbox repo index status --cwd . --json")
        for record in conflict_records[:2]:
            next_actions.extend(record.safe_next_actions[:1])
    if counts.get("stale", 0):
        next_actions.append("glassbox memory list --state stale")
        next_actions.append(
            "glassbox memory invalidate MEMORY_ID --reason 'stale memory reviewed'"
        )
    if counts.get("imported", 0):
        next_actions.append("glassbox memory list --state imported")
        next_actions.append("glassbox memory confirm MEMORY_ID")
    if counts.get("invalidated", 0):
        next_actions.append("glassbox memory list --state invalidated")
        next_actions.append(
            "glassbox memory prune MEMORY_ID --dry-run --reason 'validated cleanup'"
        )

    return WorkspaceMemoryObservability(
        active_count=counts.get("active", 0),
        stale_count=counts.get("stale", 0),
        imported_count=counts.get("imported", 0),
        invalidated_count=counts.get("invalidated", 0),
        pruned_count=counts.get("pruned", 0),
        redacted_count=redacted_count,
        conflict_count=len(conflict_records),
        conflicted_memory_ids=[
            str(record.memory_id) for record in conflict_records[:10]
        ],
        last_invalidated_memory_id=(
            str(latest_invalidated.memory_id)
            if latest_invalidated is not None
            else None
        ),
        next_actions=next_actions,
    )


__all__ = ["build_workspace_memory_observability"]
