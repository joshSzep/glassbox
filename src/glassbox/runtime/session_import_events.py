"""Inspection-only event construction for imported session packages."""

from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from uuid import UUID

from glassbox.core.events import EventEnvelope
from glassbox.core.events import RuntimeNoteRecorded
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionStarted
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.events import event_payload_adapter
from glassbox.core.ids import SessionId
from glassbox.core.ids import new_message_id
from glassbox.core.models import MessagePart
from glassbox.runtime.session_export import SessionExportPayload
from glassbox.runtime.session_export import SessionExportTranscriptMessage
from glassbox.runtime.session_import_handoff import import_note


def build_inspection_import_events(
    package: SessionExportPayload,
    *,
    imported_session_id: SessionId,
    workspace_root: Path,
) -> list[EventEnvelope]:
    imported_at = datetime.now(UTC)
    events = [
        EventEnvelope(
            session_id=imported_session_id,
            sequence=0,
            created_at=imported_at,
            payload=SessionStarted(
                cwd=str(workspace_root.resolve()),
                model_name=package.metadata.model_name,
                approval_mode=package.metadata.approval_mode,
                parent_session_id=package.lineage.parent_session_id,
                forked_from_turn_id=parse_optional_uuid(
                    package.lineage.forked_from_turn_id,
                    kind="forked_from_turn_id",
                ),
                forked_from_sequence=package.lineage.forked_from_sequence,
                branch_label=package.lineage.branch_label,
            ),
        ),
        EventEnvelope(
            session_id=imported_session_id,
            sequence=0,
            created_at=imported_at,
            payload=RuntimeNoteRecorded(
                category="handoff",
                message=import_note(package),
            ),
        ),
    ]
    events.extend(
        build_imported_transcript_events(
            package.transcript,
            imported_session_id=imported_session_id,
            source_session_id=package.metadata.session_id,
            imported_at=imported_at,
        )
    )
    events.extend(build_imported_task_events(package, imported_session_id))
    events.extend(build_imported_checkpoint_events(package, imported_session_id))
    events.append(
        EventEnvelope(
            session_id=imported_session_id,
            sequence=0,
            created_at=imported_at,
            payload=SessionCompleted(
                reason=(
                    "imported for inspection from session export package; "
                    f"original status was {package.metadata.status}"
                ),
            ),
        )
    )
    return events


def build_imported_task_events(
    package: SessionExportPayload,
    imported_session_id: SessionId,
) -> list[EventEnvelope]:
    return [
        EventEnvelope(
            session_id=imported_session_id,
            sequence=0,
            created_at=reference.created_at,
            payload=event_payload_adapter.validate_python(reference.payload),
        )
        for reference in package.task_event_references
    ]


def build_imported_checkpoint_events(
    package: SessionExportPayload,
    imported_session_id: SessionId,
) -> list[EventEnvelope]:
    return [
        EventEnvelope(
            session_id=imported_session_id,
            sequence=0,
            created_at=reference.created_at,
            payload=event_payload_adapter.validate_python(reference.payload),
        )
        for reference in package.checkpoint_event_references
    ]


def build_imported_transcript_events(
    transcript: Sequence[SessionExportTranscriptMessage],
    *,
    imported_session_id: SessionId,
    source_session_id: SessionId,
    imported_at: datetime,
) -> list[EventEnvelope]:
    return [
        EventEnvelope(
            session_id=imported_session_id,
            sequence=0,
            created_at=imported_at,
            payload=TranscriptMessageImported(
                message_id=new_message_id(),
                source_session_id=source_session_id,
                source_message_id=parse_uuid(message.message_id, kind="message_id"),
                source_turn_id=None,
                role=message.role,
                parts=[
                    MessagePart(kind=part.kind, text=part.text)
                    for part in message.parts
                ],
                source_created_at=message.created_at,
            ),
        )
        for message in transcript
    ]


def parse_optional_uuid(value: str | None, *, kind: str) -> UUID | None:
    if value is None:
        return None
    return parse_uuid(value, kind=kind)


def parse_uuid(value: str, *, kind: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError(f"invalid {kind} in session export package: {value}") from exc
