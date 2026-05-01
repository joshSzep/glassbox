"""Freshness assessment for deterministic context compactions."""

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.models import ContextCompactionRecord
from glassbox.core.types import ContextCompactionFreshness

NON_MATERIAL_COMPACTION_EVENTS = {
    "ContextCompactionCreated",
    "ContextCompactionFreshnessChanged",
}


def assessed_context_compaction_record(
    record: ContextCompactionRecord,
    events: list[EventEnvelope],
) -> ContextCompactionRecord:
    """Return a record with conservative freshness inferred from later events."""

    if record.freshness != ContextCompactionFreshness.FRESH:
        return record

    reason = fresh_compaction_staleness_reason(record, events)
    if reason is None:
        return record

    return record.model_copy(
        update={
            "freshness": ContextCompactionFreshness.STALE,
            "freshness_reason": reason,
        }
    )


def latest_material_source_sequence(
    events: list[EventEnvelope],
    *,
    default: int = 0,
) -> int:
    """Return the latest event sequence that should be included in compactions."""

    latest_material = max(
        (
            event.sequence
            for event in events
            if event.event_type not in NON_MATERIAL_COMPACTION_EVENTS
        ),
        default=default,
    )
    return max(default, latest_material)


def fresh_compaction_staleness_reason(
    record: ContextCompactionRecord,
    events: list[EventEnvelope],
) -> str | None:
    """Explain why an otherwise-fresh compaction is stale after later events."""

    later_material_events = [
        event
        for event in events
        if event.sequence > record.source_end_sequence
        and event.event_type not in NON_MATERIAL_COMPACTION_EVENTS
    ]
    if not later_material_events:
        return None

    latest_checkpoint = next(
        (
            event
            for event in reversed(later_material_events)
            if isinstance(event.payload, TaskCheckpointCreated)
        ),
        None,
    )
    if latest_checkpoint is not None:
        return (
            "A newer checkpoint exists after this compaction's source range "
            f"(event {latest_checkpoint.sequence})."
        )

    verification_event = next(
        (
            event
            for event in reversed(later_material_events)
            if event.event_type.startswith("TaskVerification")
        ),
        None,
    )
    if verification_event is not None:
        return (
            "Verification evidence changed after this compaction's source range "
            f"(event {verification_event.sequence})."
        )

    tool_or_artifact_event = next(
        (
            event
            for event in reversed(later_material_events)
            if event.event_type
            in {
                "ModelToolCallRequested",
                "ToolExecutionStarted",
                "ToolExecutionCompleted",
                "ToolExecutionCancelled",
                "ToolArtifactRecorded",
            }
        ),
        None,
    )
    if tool_or_artifact_event is not None:
        return (
            "Workspace or tool evidence changed after this compaction's source "
            f"range (event {tool_or_artifact_event.sequence})."
        )

    latest = later_material_events[-1]
    return (
        "Session events exist after this compaction's source range "
        f"(latest event {latest.sequence})."
    )


__all__ = [
    "NON_MATERIAL_COMPACTION_EVENTS",
    "assessed_context_compaction_record",
    "fresh_compaction_staleness_reason",
    "latest_material_source_sequence",
]
