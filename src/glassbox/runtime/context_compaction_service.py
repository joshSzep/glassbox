"""Deterministic context compaction service."""

import json
from datetime import UTC
from datetime import datetime
from typing import Any

from glassbox.core.events import ApprovalResolved
from glassbox.core.events import ContextCompactionCreated
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
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.ids import new_context_compaction_id
from glassbox.core.types import ContextCompactionFreshness
from glassbox.core.types import ContextCompactionScope
from glassbox.runtime.context_compaction import CONTEXT_COMPACTION_ARTIFACT_KIND
from glassbox.runtime.context_compaction import ContextCompactionArtifact
from glassbox.runtime.context_compaction import ContextCompactionEvidenceItem
from glassbox.runtime.context_compaction import ContextCompactionFailureItem
from glassbox.runtime.context_compaction import ContextCompactionSourceReference
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository


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
    "create_deterministic_context_compaction",
]
