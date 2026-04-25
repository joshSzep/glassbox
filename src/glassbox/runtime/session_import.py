"""Portable session import for inspection-focused handoff workflows."""

import re
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.core.events import EventEnvelope
from glassbox.core.events import RuntimeNoteRecorded
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionStarted
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.ids import SessionId
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_session_id
from glassbox.core.models import MessagePart
from glassbox.runtime.session_export import SESSION_EXPORT_VERSION
from glassbox.runtime.session_export import SessionExportPayload
from glassbox.runtime.session_export import SessionExportTranscriptMessage
from glassbox.services import SessionRepository

type SessionImportMode = Literal["inspect", "resumable"]

_UNREDACTED_SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(?:openai|anthropic|api|access|secret|token|password)"
        r"[_-]?(?:api[_-]?)?(?:key|token|secret|password)?\s*=\s*"
        r"(?!<redacted>)[^\s,;\"]+"
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)


class SessionImportResult(BaseModel):
    """Summary of a local session import operation."""

    model_config = ConfigDict(extra="forbid")

    source_session_id: SessionId
    imported_session_id: SessionId
    import_mode: Literal["inspect"] = "inspect"
    original_status: str
    imported_status: Literal["completed"] = "completed"
    resumable: bool = False
    imported_event_count: int
    transcript_message_count: int


def import_session_package(
    package_path: Path,
    *,
    session_repository: SessionRepository,
    workspace_root: Path,
    mode: SessionImportMode = "inspect",
) -> SessionImportResult:
    """Import a portable session package into local inspectable state."""

    package = load_session_export_package(package_path)
    if mode == "resumable":
        raise ValueError(
            "resumable session import is not supported for session export "
            "packages; use --mode inspect"
        )

    imported_session_id = new_session_id()
    imported_events = _build_inspection_import_events(
        package,
        imported_session_id=imported_session_id,
        workspace_root=workspace_root,
    )
    stored_events = session_repository.append_events(imported_events)
    return SessionImportResult(
        source_session_id=package.metadata.session_id,
        imported_session_id=imported_session_id,
        original_status=package.metadata.status,
        imported_event_count=len(stored_events),
        transcript_message_count=len(package.transcript),
    )


def load_session_export_package(package_path: Path) -> SessionExportPayload:
    """Load and validate a supported portable session export package."""

    resolved_path = package_path.resolve()
    try:
        raw_package = resolved_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"missing session export package: {resolved_path}") from exc

    if _contains_unredacted_secret(raw_package):
        raise ValueError(
            "session export package appears to contain unredacted secret material"
        )

    try:
        package = SessionExportPayload.model_validate_json(raw_package)
    except ValueError as exc:
        raise ValueError(
            f"invalid session export package {resolved_path}: {exc}"
        ) from exc

    if package.export_version != SESSION_EXPORT_VERSION:
        raise ValueError(
            f"unsupported session export version: {package.export_version}"
        )
    return package


def _build_inspection_import_events(
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
                forked_from_turn_id=_parse_optional_uuid(
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
                message=_import_note(package),
            ),
        ),
    ]
    events.extend(
        _build_imported_transcript_events(
            package.transcript,
            imported_session_id=imported_session_id,
            source_session_id=package.metadata.session_id,
            imported_at=imported_at,
        )
    )
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


def _build_imported_transcript_events(
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
                source_message_id=_parse_uuid(message.message_id, kind="message_id"),
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


def _import_note(package: SessionExportPayload) -> str:
    fragments = [
        f"Imported for inspection from session {package.metadata.session_id}",
        f"original status {package.metadata.status}",
        f"next action: {package.handoff.next_action_summary}",
    ]
    if package.handoff.expected_custodian is not None:
        fragments.append(f"expected custodian: {package.handoff.expected_custodian}")
    if package.handoff.note is not None:
        fragments.append(f"handoff note: {package.handoff.note}")
    return "; ".join(fragments)


def _contains_unredacted_secret(raw_package: str) -> bool:
    return any(pattern.search(raw_package) for pattern in _UNREDACTED_SECRET_PATTERNS)


def _parse_optional_uuid(value: str | None, *, kind: str) -> UUID | None:
    if value is None:
        return None
    return _parse_uuid(value, kind=kind)


def _parse_uuid(value: str, *, kind: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError(f"invalid {kind} in session export package: {value}") from exc
