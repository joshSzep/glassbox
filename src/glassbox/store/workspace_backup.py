"""Workspace-local backup and restore helpers."""

import hashlib
import json
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.models import SessionRecord
from glassbox.store.repositories import SQLiteSessionRepository

BACKUP_FORMAT_VERSION = 1
BACKUP_MANIFEST_NAME = "glassbox-backup.json"
BACKUP_DATABASE_ARCHIVE_PATH = Path(".glassbox/glassbox.sqlite3")
_BACKUP_FORMAT = "glassbox.workspace-backup"
_DATABASE_ROLE = "sqlite_database"
_ARTIFACT_ROLE = "event_referenced_artifact"


@dataclass(frozen=True, slots=True)
class WorkspaceBackupFile:
    """One file included in a workspace backup archive."""

    archive_path: Path
    source_path: Path
    role: str
    size_bytes: int
    content_sha256: str

    def to_json_payload(self) -> dict[str, object]:
        return {
            "path": self.archive_path.as_posix(),
            "role": self.role,
            "size_bytes": self.size_bytes,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceBackupReport:
    """Result of creating a workspace backup."""

    archive_path: Path
    workspace_root: Path
    database_path: Path
    session_count: int
    artifact_count: int
    files: list[WorkspaceBackupFile]

    @property
    def total_size_bytes(self) -> int:
        return sum(file.size_bytes for file in self.files)

    def to_json_payload(self) -> dict[str, object]:
        return {
            "archive_path": str(self.archive_path),
            "workspace_root": str(self.workspace_root),
            "database_path": str(self.database_path),
            "session_count": self.session_count,
            "artifact_count": self.artifact_count,
            "file_count": len(self.files),
            "total_size_bytes": self.total_size_bytes,
            "files": [file.to_json_payload() for file in self.files],
        }


@dataclass(frozen=True, slots=True)
class WorkspaceRestoreReport:
    """Result of restoring a workspace backup archive."""

    archive_path: Path
    workspace_root: Path
    database_path: Path
    session_count: int
    artifact_count: int
    restored_files: list[Path]

    def to_json_payload(self) -> dict[str, object]:
        return {
            "archive_path": str(self.archive_path),
            "workspace_root": str(self.workspace_root),
            "database_path": str(self.database_path),
            "session_count": self.session_count,
            "artifact_count": self.artifact_count,
            "restored_file_count": len(self.restored_files),
            "restored_files": [path.as_posix() for path in self.restored_files],
        }


@dataclass(frozen=True, slots=True)
class WorkspaceBackupInspectionReport:
    """Result of inspecting and validating a workspace backup archive."""

    archive_path: Path
    source_workspace_root: str
    source_database_path: str
    created_at: str
    session_count: int
    artifact_count: int
    files: list[WorkspaceBackupFile]

    @property
    def total_size_bytes(self) -> int:
        return sum(file.size_bytes for file in self.files)

    def to_json_payload(self) -> dict[str, object]:
        return {
            "archive_path": str(self.archive_path),
            "source_workspace_root": self.source_workspace_root,
            "source_database_path": self.source_database_path,
            "created_at": self.created_at,
            "session_count": self.session_count,
            "artifact_count": self.artifact_count,
            "file_count": len(self.files),
            "total_size_bytes": self.total_size_bytes,
            "files": [file.to_json_payload() for file in self.files],
        }


def default_backup_path(workspace_root: Path) -> Path:
    """Return the default backup archive path for a workspace."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return workspace_root / ".glassbox" / "backups" / f"workspace-{timestamp}.zip"


def create_workspace_backup(
    workspace_root: Path,
    *,
    database_path: Path,
    output_path: Path,
) -> WorkspaceBackupReport:
    """Create an inspectable archive for canonical DB state and required artifacts."""

    resolved_workspace = workspace_root.resolve()
    resolved_database = database_path.resolve()
    resolved_output = output_path.resolve()
    if not resolved_database.is_file():
        raise ValueError(f"database does not exist: {resolved_database}")
    if resolved_output.exists():
        raise ValueError(f"backup output already exists: {resolved_output}")

    with tempfile.TemporaryDirectory(prefix="glassbox-backup-") as temp_dir:
        snapshot_path = Path(temp_dir) / "glassbox.sqlite3"
        _snapshot_database(resolved_database, snapshot_path)
        sessions, artifact_paths = _referenced_artifact_paths(
            resolved_workspace,
            resolved_database,
        )
        files = _backup_files(
            snapshot_path,
            workspace_root=resolved_workspace,
            artifact_paths=artifact_paths,
        )
        manifest = _build_manifest(
            workspace_root=resolved_workspace,
            database_path=resolved_database,
            session_count=len(sessions),
            artifact_count=len(artifact_paths),
            files=files,
        )
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(
            resolved_output,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                BACKUP_MANIFEST_NAME,
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            )
            for file in files:
                archive.write(file.source_path, file.archive_path.as_posix())

    return WorkspaceBackupReport(
        archive_path=resolved_output,
        workspace_root=resolved_workspace,
        database_path=resolved_database,
        session_count=len(sessions),
        artifact_count=len(artifact_paths),
        files=files,
    )


def restore_workspace_backup(
    archive_path: Path,
    *,
    workspace_root: Path,
    database_path: Path,
    force: bool = False,
) -> WorkspaceRestoreReport:
    """Restore a workspace backup archive into a workspace root."""

    resolved_archive = archive_path.resolve()
    resolved_workspace = workspace_root.resolve()
    resolved_database = database_path.resolve()
    if not resolved_archive.is_file():
        raise ValueError(f"backup archive does not exist: {resolved_archive}")

    with zipfile.ZipFile(resolved_archive) as archive:
        manifest = _load_manifest(archive)
        files = _manifest_files(manifest)
        _validate_archive_files(archive, files)
        target_paths = _target_paths(
            files,
            workspace_root=resolved_workspace,
            database_path=resolved_database,
        )
        conflicts = [path for path in target_paths if path.exists()]
        if conflicts and not force:
            conflict_list = ", ".join(str(path) for path in conflicts[:3])
            if len(conflicts) > 3:
                conflict_list += f", ... ({len(conflicts)} total)"
            raise ValueError(f"restore target already exists: {conflict_list}")

        for file, target_path in zip(files, target_paths, strict=True):
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(file.archive_path.as_posix()) as source:
                target_path.write_bytes(source.read())

    return WorkspaceRestoreReport(
        archive_path=resolved_archive,
        workspace_root=resolved_workspace,
        database_path=resolved_database,
        session_count=_manifest_int(manifest, "session_count"),
        artifact_count=_manifest_int(manifest, "artifact_count"),
        restored_files=[
            _display_path(path, resolved_workspace) for path in target_paths
        ],
    )


def inspect_workspace_backup(archive_path: Path) -> WorkspaceBackupInspectionReport:
    """Inspect and validate a workspace backup archive without restoring it."""

    resolved_archive = archive_path.resolve()
    if not resolved_archive.is_file():
        raise ValueError(f"backup archive does not exist: {resolved_archive}")

    with zipfile.ZipFile(resolved_archive) as archive:
        manifest = _load_manifest(archive)
        files = _manifest_files(manifest)
        _validate_archive_files(archive, files)

    return WorkspaceBackupInspectionReport(
        archive_path=resolved_archive,
        source_workspace_root=_manifest_str(manifest, "source_workspace_root"),
        source_database_path=_manifest_str(manifest, "source_database_path"),
        created_at=_manifest_str(manifest, "created_at"),
        session_count=_manifest_int(manifest, "session_count"),
        artifact_count=_manifest_int(manifest, "artifact_count"),
        files=files,
    )


def _snapshot_database(source_path: Path, snapshot_path: Path) -> None:
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    target = sqlite3.connect(snapshot_path)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def _referenced_artifact_paths(
    workspace_root: Path,
    database_path: Path,
) -> tuple[list[SessionRecord], list[Path]]:
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        repository = SQLiteSessionRepository(connection)
        sessions = repository.list_sessions()
        artifact_paths: set[Path] = set()
        for session in sessions:
            for event in repository.read_session_events(session.session_id):
                payload = event.payload
                if not isinstance(
                    payload, ToolArtifactRecorded | ReplayArtifactRecorded
                ):
                    continue
                if payload.path is None:
                    continue
                relative_path = _normalize_artifact_path(payload.path)
                if relative_path is None:
                    raise ValueError(
                        f"unsupported artifact path in event log: {payload.path}"
                    )
                absolute_path = workspace_root / relative_path
                if not absolute_path.is_file():
                    raise ValueError(
                        f"referenced artifact is missing: {relative_path.as_posix()}"
                    )
                artifact_paths.add(relative_path)
    finally:
        connection.close()
    return sessions, sorted(artifact_paths, key=lambda path: path.as_posix())


def _normalize_artifact_path(path: str) -> Path | None:
    artifact_path = Path(path)
    if artifact_path.is_absolute():
        return None
    if artifact_path.parts[:1] != (".glassbox",):
        return None
    if ".." in artifact_path.parts:
        return None
    return artifact_path


def _backup_files(
    snapshot_path: Path,
    *,
    workspace_root: Path,
    artifact_paths: list[Path],
) -> list[WorkspaceBackupFile]:
    files = [
        _build_backup_file(snapshot_path, BACKUP_DATABASE_ARCHIVE_PATH, _DATABASE_ROLE)
    ]
    files.extend(
        _build_backup_file(workspace_root / path, path, _ARTIFACT_ROLE)
        for path in artifact_paths
    )
    return files


def _build_backup_file(
    source_path: Path,
    archive_path: Path,
    role: str,
) -> WorkspaceBackupFile:
    content = source_path.read_bytes()
    return WorkspaceBackupFile(
        archive_path=archive_path,
        source_path=source_path,
        role=role,
        size_bytes=len(content),
        content_sha256=hashlib.sha256(content).hexdigest(),
    )


def _build_manifest(
    *,
    workspace_root: Path,
    database_path: Path,
    session_count: int,
    artifact_count: int,
    files: list[WorkspaceBackupFile],
) -> dict[str, object]:
    return {
        "format": _BACKUP_FORMAT,
        "format_version": BACKUP_FORMAT_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "source_workspace_root": str(workspace_root),
        "source_database_path": str(database_path),
        "scope": (
            "workspace-local canonical SQLite database and event-referenced "
            ".glassbox artifacts"
        ),
        "session_count": session_count,
        "artifact_count": artifact_count,
        "file_count": len(files),
        "files": [file.to_json_payload() for file in files],
    }


def _load_manifest(archive: zipfile.ZipFile) -> dict[str, object]:
    try:
        raw_manifest = archive.read(BACKUP_MANIFEST_NAME)
    except KeyError as exc:
        raise ValueError("backup archive is missing glassbox-backup.json") from exc
    try:
        manifest = json.loads(raw_manifest.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("backup manifest is not valid JSON") from exc
    if not isinstance(manifest, dict):
        raise ValueError("backup manifest must be a JSON object")
    if manifest.get("format") != _BACKUP_FORMAT:
        raise ValueError("unsupported backup archive format")
    if manifest.get("format_version") != BACKUP_FORMAT_VERSION:
        raise ValueError(
            f"unsupported backup format version: {manifest.get('format_version')!r}"
        )
    return manifest


def _manifest_files(manifest: dict[str, object]) -> list[WorkspaceBackupFile]:
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list):
        raise ValueError("backup manifest files must be a list")
    files = [_manifest_file(raw_file) for raw_file in raw_files]
    if not any(file.role == _DATABASE_ROLE for file in files):
        raise ValueError("backup archive is missing its SQLite database entry")
    return files


def _manifest_file(raw_file: object) -> WorkspaceBackupFile:
    if not isinstance(raw_file, dict):
        raise ValueError("backup manifest file entries must be objects")
    file_payload = cast(dict[str, object], raw_file)
    archive_path = _safe_archive_path(str(file_payload.get("path", "")))
    role = _manifest_file_role(file_payload)
    content_sha256 = _manifest_str(file_payload, "content_sha256")
    return WorkspaceBackupFile(
        archive_path=archive_path,
        source_path=Path(),
        role=role,
        size_bytes=_manifest_int(file_payload, "size_bytes"),
        content_sha256=content_sha256,
    )


def _manifest_file_role(payload: dict[str, object]) -> str:
    role = payload.get("role")
    if not isinstance(role, str) or role not in {_DATABASE_ROLE, _ARTIFACT_ROLE}:
        raise ValueError(f"unsupported backup file role: {role!r}")
    return role


def _validate_archive_files(
    archive: zipfile.ZipFile,
    files: list[WorkspaceBackupFile],
) -> None:
    for file in files:
        archive_name = file.archive_path.as_posix()
        try:
            content = archive.read(archive_name)
        except KeyError as exc:
            raise ValueError(f"backup archive is missing file: {archive_name}") from exc
        if len(content) != file.size_bytes:
            raise ValueError(f"backup file size mismatch: {archive_name}")
        if hashlib.sha256(content).hexdigest() != file.content_sha256:
            raise ValueError(f"backup file checksum mismatch: {archive_name}")


def _target_paths(
    files: list[WorkspaceBackupFile],
    *,
    workspace_root: Path,
    database_path: Path,
) -> list[Path]:
    target_paths: list[Path] = []
    for file in files:
        if file.role == _DATABASE_ROLE:
            target_paths.append(database_path)
            continue
        if file.archive_path.parts[:1] != (".glassbox",):
            raise ValueError(
                f"artifact backup path must be workspace-local: {file.archive_path}"
            )
        target_paths.append(workspace_root / file.archive_path)
    return target_paths


def _safe_archive_path(path: str) -> Path:
    archive_path = Path(path)
    if (
        archive_path.is_absolute()
        or ".." in archive_path.parts
        or not archive_path.parts
    ):
        raise ValueError(f"unsafe backup archive path: {path!r}")
    return archive_path


def _display_path(path: Path, workspace_root: Path) -> Path:
    try:
        return path.relative_to(workspace_root)
    except ValueError:
        return path


def _manifest_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"backup manifest field {key!r} must be a non-empty string")
    return value


def _manifest_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value < 0:
        raise ValueError(
            f"backup manifest field {key!r} must be a non-negative integer"
        )
    return value
