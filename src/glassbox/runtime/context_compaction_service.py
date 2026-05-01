"""Deterministic context compaction service."""

import json
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Any

from glassbox.core.events import ApprovalResolved
from glassbox.core.events import ContextCompactionCreated
from glassbox.core.events import ContextCompactionFreshnessChanged
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import SessionFailed
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.events import TaskStepCompleted
from glassbox.core.events import TaskStepFailed
from glassbox.core.events import TaskVerificationCompleted
from glassbox.core.events import TaskVerificationFailed
from glassbox.core.events import TaskVerificationResidualRiskAccepted
from glassbox.core.events import TurnFailed
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import ContextCompactionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.ids import new_context_compaction_id
from glassbox.core.models import ContextCompactionRecord
from glassbox.core.types import ContextCompactionFreshness
from glassbox.core.types import ContextCompactionScope
from glassbox.runtime.context_compaction import CONTEXT_COMPACTION_ARTIFACT_KIND
from glassbox.runtime.context_compaction import CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP
from glassbox.runtime.context_compaction import ContextCompactionArtifact
from glassbox.runtime.context_compaction import ContextCompactionEvidenceItem
from glassbox.runtime.context_compaction import ContextCompactionFailureItem
from glassbox.runtime.context_compaction import ContextCompactionSourceReference
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository

_NON_MATERIAL_COMPACTION_EVENTS = {
    "ContextCompactionCreated",
    "ContextCompactionFreshnessChanged",
}


@dataclass(frozen=True)
class ContextCompactionSuggestedRange:
    """A bounded source range that can fit the compaction artifact contract."""

    label: str
    source_start_sequence: int
    source_end_sequence: int
    selected_event_count: int

    def to_json_payload(self) -> dict[str, int | str]:
        return {
            "label": self.label,
            "source_start_sequence": self.source_start_sequence,
            "source_end_sequence": self.source_end_sequence,
            "selected_event_count": self.selected_event_count,
        }


class ContextCompactionRangeError(ValueError):
    """Raised when a requested range cannot fit source-reference limits."""

    def __init__(
        self,
        *,
        selected_event_count: int,
        source_reference_cap: int,
        source_start_sequence: int,
        source_end_sequence: int,
        suggested_ranges: list[ContextCompactionSuggestedRange],
    ) -> None:
        self.selected_event_count = selected_event_count
        self.source_reference_cap = source_reference_cap
        self.source_start_sequence = source_start_sequence
        self.source_end_sequence = source_end_sequence
        self.suggested_ranges = suggested_ranges
        super().__init__(self._message())

    def _message(self) -> str:
        suggestions = "; ".join(
            (
                f"{item.label} {item.source_start_sequence}-"
                f"{item.source_end_sequence} ({item.selected_event_count} event(s))"
            )
            for item in self.suggested_ranges
        )
        return (
            "Selected source range contains "
            f"{self.selected_event_count} event(s), but context compaction "
            f"artifacts support at most {self.source_reference_cap} source "
            "reference(s). Retry with a bounded range"
            f"{': ' + suggestions if suggestions else '.'}"
        )

    def to_json_payload(self) -> dict[str, object]:
        return {
            "error": "source_range_exceeds_cap",
            "message": str(self),
            "selected_event_count": self.selected_event_count,
            "source_reference_cap": self.source_reference_cap,
            "source_start_sequence": self.source_start_sequence,
            "source_end_sequence": self.source_end_sequence,
            "suggested_ranges": [
                item.to_json_payload() for item in self.suggested_ranges
            ],
        }


def create_deterministic_context_compaction(
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    session_id: SessionId,
    *,
    scope: ContextCompactionScope = ContextCompactionScope.TRANSCRIPT,
    task_id: TaskId | None = None,
    source_start_sequence: int | None = None,
    source_end_sequence: int | None = None,
) -> ContextCompactionCreated:
    """Create a local deterministic compaction artifact and canonical event."""

    session = session_repository.get_session(session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    events = session_repository.read_session_events(session_id)
    if not events:
        raise ValueError(f"session {session_id} has no events to compact")

    start = (
        source_start_sequence
        if source_start_sequence is not None
        else events[0].sequence
    )
    end = (
        source_end_sequence if source_end_sequence is not None else events[-1].sequence
    )
    if end < start:
        raise ValueError("source end sequence must be greater than or equal to start")
    source_events = [event for event in events if start <= event.sequence <= end]
    if not source_events:
        raise ValueError("selected source range contains no events")
    _validate_source_range_within_reference_cap(
        source_events,
        source_start_sequence=start,
        source_end_sequence=end,
    )

    compaction_id = new_context_compaction_id()
    artifact = _build_artifact(
        session_id,
        compaction_id=compaction_id,
        scope=scope,
        task_id=task_id,
        source_events=source_events,
        source_start_sequence=start,
        source_end_sequence=end,
    )
    stored_artifact = artifact_repository.write_text_artifact(
        session_id,
        artifact.model_dump_json(indent=2),
        suffix=".context-compaction.json",
    )
    payload = ContextCompactionCreated(
        compaction_id=compaction_id,
        scope=scope,
        source_start_sequence=start,
        source_end_sequence=end,
        summary=artifact.summary,
        artifact_id=stored_artifact.artifact_id,
        freshness=ContextCompactionFreshness.FRESH,
        task_id=task_id,
        source_artifact_ids=artifact.source_artifact_ids,
        decision_count=len(artifact.decisions),
        unresolved_question_count=len(artifact.unresolved_questions),
        accepted_risk_count=len(artifact.accepted_risks),
        limitations=artifact.limitations,
    )
    session_repository.append_event(
        EventEnvelope(session_id=session_id, sequence=0, payload=payload)
    )
    return payload


def refresh_context_compaction(
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    session_id: SessionId,
    compaction_id: ContextCompactionId,
    *,
    changed_by: str = "operator",
    reason: str | None = None,
) -> tuple[ContextCompactionCreated, ContextCompactionFreshnessChanged]:
    """Create a replacement compaction and mark the previous one superseded."""

    record = session_repository.get_context_compaction(session_id, compaction_id)
    if record is None:
        raise ValueError(f"unknown compaction_id: {compaction_id}")

    source_end_sequence = latest_material_source_sequence(
        session_repository.read_session_events(session_id),
        default=record.source_end_sequence,
    )
    refreshed = create_deterministic_context_compaction(
        session_repository,
        artifact_repository,
        session_id,
        scope=record.scope,
        task_id=record.task_id,
        source_start_sequence=record.source_start_sequence,
        source_end_sequence=source_end_sequence,
    )
    change = ContextCompactionFreshnessChanged(
        compaction_id=record.compaction_id,
        freshness=ContextCompactionFreshness.STALE,
        reason=reason
        or (
            "Compaction was refreshed; the replacement covers source events "
            f"{refreshed.source_start_sequence}-{refreshed.source_end_sequence}."
        ),
        changed_by=changed_by,
        superseded_by_compaction_id=refreshed.compaction_id,
    )
    session_repository.append_event(
        EventEnvelope(session_id=session_id, sequence=0, payload=change)
    )
    return refreshed, change


def invalidate_context_compaction(
    session_repository: SessionRepository,
    session_id: SessionId,
    compaction_id: ContextCompactionId,
    *,
    reason: str,
    changed_by: str = "operator",
) -> ContextCompactionFreshnessChanged:
    """Record that a compaction must not be used for active context."""

    record = session_repository.get_context_compaction(session_id, compaction_id)
    if record is None:
        raise ValueError(f"unknown compaction_id: {compaction_id}")
    change = ContextCompactionFreshnessChanged(
        compaction_id=record.compaction_id,
        freshness=ContextCompactionFreshness.INVALIDATED,
        reason=reason,
        changed_by=changed_by,
    )
    session_repository.append_event(
        EventEnvelope(session_id=session_id, sequence=0, payload=change)
    )
    return change


def assessed_context_compaction_record(
    record: ContextCompactionRecord,
    events: list[EventEnvelope],
) -> ContextCompactionRecord:
    """Return a record with conservative freshness inferred from later events."""

    if record.freshness != ContextCompactionFreshness.FRESH:
        return record

    reason = _fresh_compaction_staleness_reason(record, events)
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
            if event.event_type not in _NON_MATERIAL_COMPACTION_EVENTS
        ),
        default=default,
    )
    return max(default, latest_material)


def _fresh_compaction_staleness_reason(
    record: ContextCompactionRecord,
    events: list[EventEnvelope],
) -> str | None:
    later_material_events = [
        event
        for event in events
        if event.sequence > record.source_end_sequence
        and event.event_type not in _NON_MATERIAL_COMPACTION_EVENTS
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


def _build_artifact(
    session_id: SessionId,
    *,
    compaction_id,
    scope: ContextCompactionScope,
    task_id: TaskId | None,
    source_events: list[EventEnvelope],
    source_start_sequence: int,
    source_end_sequence: int,
) -> ContextCompactionArtifact:
    references = [
        ContextCompactionSourceReference(
            source_type="event",
            label=_event_label(event),
            sequence=event.sequence,
        )
        for event in source_events
    ]
    decisions = _decision_items(source_events)
    unresolved_questions = _question_items(source_events)
    verification_state = _verification_items(source_events)
    failures = _failure_items(source_events)
    accepted_risks = _accepted_risk_items(source_events)
    touched_files = _touched_files(source_events)
    summary = _summary(
        source_events,
        decisions=decisions,
        unresolved_questions=unresolved_questions,
        verification_state=verification_state,
        failures=failures,
        accepted_risks=accepted_risks,
    )
    limitations = [
        "Deterministic compaction summarizes event payloads only; raw transcript "
        "and artifact bodies remain source evidence."
    ]
    return ContextCompactionArtifact(
        compaction_id=compaction_id,
        session_id=session_id,
        scope=scope,
        source_start_sequence=source_start_sequence,
        source_end_sequence=source_end_sequence,
        transcript_start_sequence=source_start_sequence,
        transcript_end_sequence=source_end_sequence,
        task_start_sequence=source_start_sequence if task_id is not None else None,
        task_end_sequence=source_end_sequence if task_id is not None else None,
        created_at=datetime.now(tz=UTC),
        summary=summary,
        task_id=task_id,
        source_references=references,
        decisions=decisions,
        unresolved_questions=unresolved_questions,
        touched_files=touched_files,
        verification_state=verification_state,
        failures=failures,
        accepted_risks=accepted_risks,
        limitations=limitations,
    )


def _validate_source_range_within_reference_cap(
    source_events: list[EventEnvelope],
    *,
    source_start_sequence: int,
    source_end_sequence: int,
) -> None:
    selected_event_count = len(source_events)
    if selected_event_count <= CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP:
        return

    raise ContextCompactionRangeError(
        selected_event_count=selected_event_count,
        source_reference_cap=CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP,
        source_start_sequence=source_start_sequence,
        source_end_sequence=source_end_sequence,
        suggested_ranges=_suggest_bounded_ranges(
            source_events,
            cap=CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP,
        ),
    )


def _suggest_bounded_ranges(
    source_events: list[EventEnvelope],
    *,
    cap: int,
) -> list[ContextCompactionSuggestedRange]:
    suggestions: list[ContextCompactionSuggestedRange] = []
    seen: set[tuple[int, int]] = set()
    for label, bounded_events in (
        ("first", source_events[:cap]),
        ("latest", source_events[-cap:]),
    ):
        if not bounded_events:
            continue
        start = bounded_events[0].sequence
        end = bounded_events[-1].sequence
        key = (start, end)
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(
            ContextCompactionSuggestedRange(
                label=label,
                source_start_sequence=start,
                source_end_sequence=end,
                selected_event_count=len(bounded_events),
            )
        )
    return suggestions


def _decision_items(events: list[EventEnvelope]) -> list[ContextCompactionEvidenceItem]:
    items: list[ContextCompactionEvidenceItem] = []
    for event in events:
        payload = event.payload
        if isinstance(payload, ApprovalResolved):
            items.append(
                ContextCompactionEvidenceItem(
                    summary=f"Approval {payload.approval_id} was {payload.decision}.",
                    source_refs=[_event_label(event)],
                )
            )
        elif isinstance(payload, TaskStepCompleted):
            items.append(
                ContextCompactionEvidenceItem(
                    summary=payload.summary
                    or f"Task step {payload.step_id} was completed.",
                    source_refs=[_event_label(event)],
                )
            )
    return items[:25]


def _question_items(events: list[EventEnvelope]) -> list[ContextCompactionEvidenceItem]:
    return [
        ContextCompactionEvidenceItem(
            summary=f"Unresolved question: {event.payload.question}",
            source_refs=[_event_label(event)],
        )
        for event in events
        if isinstance(event.payload, UserQuestionAsked)
    ][:25]


def _verification_items(
    events: list[EventEnvelope],
) -> list[ContextCompactionEvidenceItem]:
    items: list[ContextCompactionEvidenceItem] = []
    for event in events:
        payload = event.payload
        if isinstance(payload, TaskVerificationCompleted):
            items.append(
                ContextCompactionEvidenceItem(
                    summary=payload.summary
                    or f"Verification {payload.verification_id} completed.",
                    source_refs=[_event_label(event)],
                )
            )
        elif isinstance(payload, TaskVerificationFailed):
            items.append(
                ContextCompactionEvidenceItem(
                    summary=payload.failure.summary
                    or f"Verification {payload.verification_id} failed.",
                    source_refs=[_event_label(event)],
                )
            )
    return items[:25]


def _failure_items(events: list[EventEnvelope]) -> list[ContextCompactionFailureItem]:
    items: list[ContextCompactionFailureItem] = []
    for event in events:
        payload = event.payload
        if isinstance(payload, TurnFailed):
            items.append(
                ContextCompactionFailureItem(
                    summary=payload.error_message,
                    status="turn_failed",
                    source_refs=[_event_label(event)],
                )
            )
        elif isinstance(payload, SessionFailed):
            items.append(
                ContextCompactionFailureItem(
                    summary=payload.error_message,
                    status="session_failed",
                    source_refs=[_event_label(event)],
                )
            )
        elif isinstance(payload, TaskStepFailed):
            items.append(
                ContextCompactionFailureItem(
                    summary=payload.reason or f"Task step {payload.step_id} failed.",
                    status="task_step_failed",
                    source_refs=[_event_label(event)],
                )
            )
    return items[:25]


def _accepted_risk_items(
    events: list[EventEnvelope],
) -> list[ContextCompactionEvidenceItem]:
    return [
        ContextCompactionEvidenceItem(
            summary=event.payload.reason,
            source_refs=[_event_label(event)],
        )
        for event in events
        if isinstance(event.payload, TaskVerificationResidualRiskAccepted)
    ][:25]


def _touched_files(events: list[EventEnvelope]) -> list[str]:
    files: list[str] = []
    for event in events:
        payload = event.payload
        if not isinstance(payload, ModelToolCallRequested):
            continue
        try:
            arguments: Any = json.loads(payload.arguments_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(arguments, dict):
            continue
        raw_path = arguments.get("path")
        if isinstance(raw_path, str):
            files.append(raw_path)
        raw_paths = arguments.get("paths")
        if isinstance(raw_paths, list):
            files.extend(path for path in raw_paths if isinstance(path, str))
    return sorted(dict.fromkeys(files))[:100]


def _summary(
    events: list[EventEnvelope],
    *,
    decisions: list[ContextCompactionEvidenceItem],
    unresolved_questions: list[ContextCompactionEvidenceItem],
    verification_state: list[ContextCompactionEvidenceItem],
    failures: list[ContextCompactionFailureItem],
    accepted_risks: list[ContextCompactionEvidenceItem],
) -> str:
    return (
        f"Compacted {len(events)} event(s): {len(decisions)} decision(s), "
        f"{len(unresolved_questions)} unresolved question(s), "
        f"{len(verification_state)} verification item(s), {len(failures)} "
        f"failure(s), {len(accepted_risks)} accepted risk(s)."
    )


def _event_label(event: EventEnvelope) -> str:
    return f"event:{event.sequence}:{event.event_type}"


__all__ = [
    "CONTEXT_COMPACTION_ARTIFACT_KIND",
    "CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP",
    "ContextCompactionRangeError",
    "ContextCompactionSuggestedRange",
    "assessed_context_compaction_record",
    "create_deterministic_context_compaction",
    "invalidate_context_compaction",
    "latest_material_source_sequence",
    "refresh_context_compaction",
]
