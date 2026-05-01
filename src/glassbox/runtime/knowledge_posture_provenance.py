"""Provenance shaping for workspace knowledge posture cues."""

from typing import Any

from glassbox.core.models import ContextCompactionRecord
from glassbox.core.models import SessionRecord
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.runtime.knowledge_posture_models import KnowledgeCueProvenance


def memory_provenance(entry: WorkspaceMemoryEntry) -> KnowledgeCueProvenance:
    source_sequence = entry.provenance.source_sequence
    return KnowledgeCueProvenance(
        label=f"Memory {entry.memory_id}",
        source_kind="workspace-memory",
        source_id=str(entry.memory_id),
        session_id=str(entry.session_id),
        task_id=optional_str(entry.provenance.task_id),
        artifact_id=optional_str(entry.provenance.artifact_id),
        source_start_sequence=source_sequence,
        source_end_sequence=source_sequence,
        last_sequence=entry.last_sequence,
        timestamp=entry.updated_at.isoformat(),
        freshness=enum_value(entry.state),
        detail=(
            f"{enum_value(entry.provenance.source_type)}"
            f"{detail_suffix(entry.provenance.source_label)}"
        ),
    )


def checkpoint_provenance(
    checkpoint: TaskCheckpointRecord,
) -> KnowledgeCueProvenance:
    return KnowledgeCueProvenance(
        label=f"Checkpoint {checkpoint.checkpoint_id}",
        source_kind="checkpoint",
        source_id=str(checkpoint.checkpoint_id),
        session_id=str(checkpoint.session_id),
        task_id=optional_str(checkpoint.task_id),
        artifact_id=optional_str(checkpoint.artifact_id),
        source_start_sequence=checkpoint.source_start_sequence,
        source_end_sequence=checkpoint.source_end_sequence,
        last_sequence=checkpoint.last_sequence,
        timestamp=checkpoint.created_at.isoformat(),
        freshness=checkpoint.verification_status or checkpoint.budget_status,
        detail=(
            checkpoint.current_phase.value
            if checkpoint.current_phase is not None
            else checkpoint.next_action
        ),
    )


def session_without_checkpoint_provenance(
    session: SessionRecord,
) -> KnowledgeCueProvenance:
    return KnowledgeCueProvenance(
        label="Active session without checkpoint",
        source_kind="session",
        source_id=str(session.session_id),
        session_id=str(session.session_id),
        source_start_sequence=0,
        source_end_sequence=session.last_sequence,
        last_sequence=session.last_sequence,
        timestamp=session.updated_at.isoformat(),
        freshness="missing-checkpoint",
        detail=f"{session.status.value} session has no checkpoint projection",
    )


def compaction_provenance(
    compaction: ContextCompactionRecord,
) -> KnowledgeCueProvenance:
    return KnowledgeCueProvenance(
        label=f"Compaction {compaction.compaction_id}",
        source_kind="context-compaction",
        source_id=str(compaction.compaction_id),
        session_id=str(compaction.session_id),
        task_id=optional_str(compaction.task_id),
        artifact_id=str(compaction.artifact_id),
        source_start_sequence=compaction.source_start_sequence,
        source_end_sequence=compaction.source_end_sequence,
        last_sequence=compaction.last_sequence,
        timestamp=compaction.created_at.isoformat(),
        freshness=enum_value(compaction.freshness),
        detail=compaction.freshness_reason or compaction.summary,
    )


def sort_latest(items: list[Any], attribute: str) -> list[Any]:
    return sorted(
        items,
        key=lambda item: _sort_key(getattr(item, attribute, None)),
        reverse=True,
    )


def enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def detail_suffix(value: str | None) -> str:
    return "" if value is None else f"; {value}"


def _sort_key(value: Any) -> tuple[int, str]:
    if value is None:
        return (0, "")
    if hasattr(value, "isoformat"):
        return (1, value.isoformat())
    if isinstance(value, int):
        return (1, f"{value:020d}")
    return (1, str(value))


__all__ = [
    "checkpoint_provenance",
    "compaction_provenance",
    "detail_suffix",
    "enum_value",
    "memory_provenance",
    "optional_str",
    "session_without_checkpoint_provenance",
    "sort_latest",
]
