"""Portable session import for inspection-focused handoff workflows."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.core.ids import SessionId
from glassbox.core.ids import new_session_id
from glassbox.runtime.session_export import SessionExportPayload
from glassbox.runtime.session_export import SessionExportTranscriptMessage
from glassbox.runtime.session_import_events import build_inspection_import_events
from glassbox.runtime.session_import_validation import load_session_export_package
from glassbox.services import SessionRepository

type SessionImportMode = Literal["inspect", "resumable"]


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
    task_event_count: int = 0
    task_count: int = 0
    checkpoint_event_count: int = 0


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
    imported_events = build_inspection_import_events(
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
        task_event_count=len(package.task_event_references),
        task_count=len(package.task_summaries),
        checkpoint_event_count=len(package.checkpoint_event_references),
    )


__all__ = [
    "SessionExportPayload",
    "SessionExportTranscriptMessage",
    "SessionImportMode",
    "SessionImportResult",
    "import_session_package",
    "load_session_export_package",
]
