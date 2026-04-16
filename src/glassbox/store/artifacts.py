"""File-backed artifact storage helpers for Glassbox sessions."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from glassbox.core.events import EventEnvelope, ToolArtifactRecorded
from glassbox.core.ids import ArtifactId, SessionId, ToolCallId, TurnId, new_artifact_id
from glassbox.store.sqlite import append_event


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    """Resolved information for a file-backed session artifact."""

    artifact_id: ArtifactId
    session_id: SessionId
    relative_path: Path
    absolute_path: Path


def artifact_relative_path(
    session_id: SessionId,
    artifact_id: ArtifactId,
    suffix: str,
) -> Path:
    """Build the canonical relative path for a session artifact."""

    normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return (
        Path(".glassbox")
        / "sessions"
        / str(session_id)
        / "artifacts"
        / f"{artifact_id}{normalized_suffix}"
    )


def write_text_artifact(
    root_dir: Path,
    session_id: SessionId,
    content: str,
    *,
    suffix: str,
    artifact_id: ArtifactId | None = None,
    encoding: str = "utf-8",
) -> StoredArtifact:
    """Write a UTF-8 text artifact beneath a session-scoped artifact directory."""

    stored_artifact = _prepare_artifact_path(
        root_dir,
        session_id,
        suffix=suffix,
        artifact_id=artifact_id,
    )
    stored_artifact.absolute_path.write_text(content, encoding=encoding)
    return stored_artifact


def write_binary_artifact(
    root_dir: Path,
    session_id: SessionId,
    content: bytes,
    *,
    suffix: str,
    artifact_id: ArtifactId | None = None,
) -> StoredArtifact:
    """Write a binary artifact beneath a session-scoped artifact directory."""

    stored_artifact = _prepare_artifact_path(
        root_dir,
        session_id,
        suffix=suffix,
        artifact_id=artifact_id,
    )
    stored_artifact.absolute_path.write_bytes(content)
    return stored_artifact


def read_text_artifact(
    root_dir: Path,
    relative_path: Path,
    *,
    encoding: str = "utf-8",
) -> str:
    """Read a previously stored text artifact using its relative artifact path."""

    return (root_dir / relative_path).read_text(encoding=encoding)


def read_binary_artifact(root_dir: Path, relative_path: Path) -> bytes:
    """Read a previously stored binary artifact using its relative artifact path."""

    return (root_dir / relative_path).read_bytes()


def record_text_artifact(
    connection: sqlite3.Connection,
    root_dir: Path,
    session_id: SessionId,
    turn_id: TurnId,
    tool_call_id: ToolCallId,
    artifact_kind: str,
    content: str,
    *,
    suffix: str,
    artifact_id: ArtifactId | None = None,
    encoding: str = "utf-8",
) -> tuple[StoredArtifact, EventEnvelope]:
    """Write a text artifact and append a matching ToolArtifactRecorded event."""

    stored_artifact = write_text_artifact(
        root_dir,
        session_id,
        content,
        suffix=suffix,
        artifact_id=artifact_id,
        encoding=encoding,
    )
    event = append_event(
        connection,
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=ToolArtifactRecorded(
                turn_id=turn_id,
                tool_call_id=tool_call_id,
                artifact_id=stored_artifact.artifact_id,
                artifact_kind=artifact_kind,
                path=stored_artifact.relative_path.as_posix(),
            ),
        ),
    )
    return stored_artifact, event


def record_binary_artifact(
    connection: sqlite3.Connection,
    root_dir: Path,
    session_id: SessionId,
    turn_id: TurnId,
    tool_call_id: ToolCallId,
    artifact_kind: str,
    content: bytes,
    *,
    suffix: str,
    artifact_id: ArtifactId | None = None,
) -> tuple[StoredArtifact, EventEnvelope]:
    """Write a binary artifact and append a matching ToolArtifactRecorded event."""

    stored_artifact = write_binary_artifact(
        root_dir,
        session_id,
        content,
        suffix=suffix,
        artifact_id=artifact_id,
    )
    event = append_event(
        connection,
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=ToolArtifactRecorded(
                turn_id=turn_id,
                tool_call_id=tool_call_id,
                artifact_id=stored_artifact.artifact_id,
                artifact_kind=artifact_kind,
                path=stored_artifact.relative_path.as_posix(),
            ),
        ),
    )
    return stored_artifact, event


def _prepare_artifact_path(
    root_dir: Path,
    session_id: SessionId,
    *,
    suffix: str,
    artifact_id: ArtifactId | None,
) -> StoredArtifact:
    resolved_artifact_id = artifact_id or new_artifact_id()
    relative_path = artifact_relative_path(session_id, resolved_artifact_id, suffix)
    absolute_path = root_dir / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    return StoredArtifact(
        artifact_id=resolved_artifact_id,
        session_id=session_id,
        relative_path=relative_path,
        absolute_path=absolute_path,
    )
