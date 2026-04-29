"""Artifact repository adapters backed by local files and SQLite events."""

import sqlite3
from pathlib import Path

import glassbox.store.artifacts as artifact_store
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.services.contracts import StoredArtifact


class FilesystemArtifactRepository:
    """Artifact repository adapter backed by the local filesystem and SQLite."""

    def __init__(self, connection: sqlite3.Connection, root_dir: Path) -> None:
        self._connection = connection
        self._root_dir = root_dir

    def write_text_artifact(
        self,
        session_id: SessionId,
        content: str,
        *,
        suffix: str,
    ) -> StoredArtifact:
        return artifact_store.write_text_artifact(
            self._root_dir,
            session_id,
            content,
            suffix=suffix,
        )

    def write_binary_artifact(
        self,
        session_id: SessionId,
        content: bytes,
        *,
        suffix: str,
    ) -> StoredArtifact:
        return artifact_store.write_binary_artifact(
            self._root_dir,
            session_id,
            content,
            suffix=suffix,
        )

    def read_text_artifact(
        self,
        relative_path: Path,
        *,
        encoding: str = "utf-8",
    ) -> str:
        return artifact_store.read_text_artifact(
            self._root_dir,
            relative_path,
            encoding=encoding,
        )

    def read_binary_artifact(self, relative_path: Path) -> bytes:
        return artifact_store.read_binary_artifact(self._root_dir, relative_path)

    def record_text_artifact(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        tool_call_id: ToolCallId,
        artifact_kind: str,
        content: str,
        *,
        suffix: str,
    ) -> tuple[StoredArtifact, EventEnvelope]:
        return artifact_store.record_text_artifact(
            self._connection,
            self._root_dir,
            session_id,
            turn_id,
            tool_call_id,
            artifact_kind,
            content,
            suffix=suffix,
        )

    def record_binary_artifact(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        tool_call_id: ToolCallId,
        artifact_kind: str,
        content: bytes,
        *,
        suffix: str,
    ) -> tuple[StoredArtifact, EventEnvelope]:
        return artifact_store.record_binary_artifact(
            self._connection,
            self._root_dir,
            session_id,
            turn_id,
            tool_call_id,
            artifact_kind,
            content,
            suffix=suffix,
        )


__all__ = ["FilesystemArtifactRepository"]
