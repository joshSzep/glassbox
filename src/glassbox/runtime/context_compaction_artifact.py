"""Artifact payload assembly for deterministic context compactions."""

import json
from datetime import UTC
from datetime import datetime
from typing import Any

from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import SessionFailed
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
from glassbox.core.types import ContextCompactionScope
from glassbox.runtime.context_compaction import ContextCompactionArtifact
from glassbox.runtime.context_compaction import ContextCompactionEvidenceItem
from glassbox.runtime.context_compaction import ContextCompactionFailureItem
from glassbox.runtime.context_compaction import ContextCompactionSourceReference


def build_context_compaction_artifact(
    session_id: SessionId,
    *,
    compaction_id: ContextCompactionId,
    scope: ContextCompactionScope,
    task_id: TaskId | None,
    source_events: list[EventEnvelope],
    source_start_sequence: int,
    source_end_sequence: int,
) -> ContextCompactionArtifact:
    """Build the deterministic artifact body from selected source events."""

    references = [
        ContextCompactionSourceReference(
            source_type="event",
            label=event_label(event),
            sequence=event.sequence,
        )
        for event in source_events
    ]
    decisions = decision_items(source_events)
    unresolved_questions = question_items(source_events)
    verification_state = verification_items(source_events)
    failures = failure_items(source_events)
    accepted_risks = accepted_risk_items(source_events)
    touched_files = touched_files_from_tool_calls(source_events)
    summary = summarize_compaction_events(
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


def decision_items(events: list[EventEnvelope]) -> list[ContextCompactionEvidenceItem]:
    """Collect decision evidence for the artifact."""

    items: list[ContextCompactionEvidenceItem] = []
    for event in events:
        payload = event.payload
        if isinstance(payload, ApprovalResolved):
            items.append(
                ContextCompactionEvidenceItem(
                    summary=f"Approval {payload.approval_id} was {payload.decision}.",
                    source_refs=[event_label(event)],
                )
            )
        elif isinstance(payload, TaskStepCompleted):
            items.append(
                ContextCompactionEvidenceItem(
                    summary=payload.summary
                    or f"Task step {payload.step_id} was completed.",
                    source_refs=[event_label(event)],
                )
            )
    return items[:25]


def question_items(events: list[EventEnvelope]) -> list[ContextCompactionEvidenceItem]:
    """Collect unresolved operator questions for the artifact."""

    return [
        ContextCompactionEvidenceItem(
            summary=f"Unresolved question: {event.payload.question}",
            source_refs=[event_label(event)],
        )
        for event in events
        if isinstance(event.payload, UserQuestionAsked)
    ][:25]


def verification_items(
    events: list[EventEnvelope],
) -> list[ContextCompactionEvidenceItem]:
    """Collect verification evidence for the artifact."""

    items: list[ContextCompactionEvidenceItem] = []
    for event in events:
        payload = event.payload
        if isinstance(payload, TaskVerificationCompleted):
            items.append(
                ContextCompactionEvidenceItem(
                    summary=payload.summary
                    or f"Verification {payload.verification_id} completed.",
                    source_refs=[event_label(event)],
                )
            )
        elif isinstance(payload, TaskVerificationFailed):
            items.append(
                ContextCompactionEvidenceItem(
                    summary=payload.failure.summary
                    or f"Verification {payload.verification_id} failed.",
                    source_refs=[event_label(event)],
                )
            )
    return items[:25]


def failure_items(events: list[EventEnvelope]) -> list[ContextCompactionFailureItem]:
    """Collect turn, session, and task-step failure evidence for the artifact."""

    items: list[ContextCompactionFailureItem] = []
    for event in events:
        payload = event.payload
        if isinstance(payload, TurnFailed):
            items.append(
                ContextCompactionFailureItem(
                    summary=payload.error_message,
                    status="turn_failed",
                    source_refs=[event_label(event)],
                )
            )
        elif isinstance(payload, SessionFailed):
            items.append(
                ContextCompactionFailureItem(
                    summary=payload.error_message,
                    status="session_failed",
                    source_refs=[event_label(event)],
                )
            )
        elif isinstance(payload, TaskStepFailed):
            items.append(
                ContextCompactionFailureItem(
                    summary=payload.reason or f"Task step {payload.step_id} failed.",
                    status="task_step_failed",
                    source_refs=[event_label(event)],
                )
            )
    return items[:25]


def accepted_risk_items(
    events: list[EventEnvelope],
) -> list[ContextCompactionEvidenceItem]:
    """Collect accepted residual risk evidence for the artifact."""

    return [
        ContextCompactionEvidenceItem(
            summary=event.payload.reason,
            source_refs=[event_label(event)],
        )
        for event in events
        if isinstance(event.payload, TaskVerificationResidualRiskAccepted)
    ][:25]


def touched_files_from_tool_calls(events: list[EventEnvelope]) -> list[str]:
    """Derive touched file hints from retained model tool-call arguments."""

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


def summarize_compaction_events(
    events: list[EventEnvelope],
    *,
    decisions: list[ContextCompactionEvidenceItem],
    unresolved_questions: list[ContextCompactionEvidenceItem],
    verification_state: list[ContextCompactionEvidenceItem],
    failures: list[ContextCompactionFailureItem],
    accepted_risks: list[ContextCompactionEvidenceItem],
) -> str:
    """Summarize the artifact contents without reading transcript bodies."""

    return (
        f"Compacted {len(events)} event(s): {len(decisions)} decision(s), "
        f"{len(unresolved_questions)} unresolved question(s), "
        f"{len(verification_state)} verification item(s), {len(failures)} "
        f"failure(s), {len(accepted_risks)} accepted risk(s)."
    )


def event_label(event: EventEnvelope) -> str:
    """Return the stable source-reference label for one event."""

    return f"event:{event.sequence}:{event.event_type}"


__all__ = [
    "accepted_risk_items",
    "build_context_compaction_artifact",
    "decision_items",
    "event_label",
    "failure_items",
    "question_items",
    "summarize_compaction_events",
    "touched_files_from_tool_calls",
    "verification_items",
]
