"""Artifact integrity inspection and retention policy helpers."""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import ToolArtifactRecorded
from glassbox.services import SessionRepository

_EVENT_REFERENCED_ARTIFACT_CATEGORY = "event_referenced_artifact"
_ORPHAN_SESSION_ARTIFACT_CATEGORY = "orphan_session_artifact"
_STALE_EVAL_ARTIFACT_CATEGORY = "stale_eval_artifact"
_KEEP_ACTION = "keep"
_WOULD_DELETE_ACTION = "would_delete"
_DELETED_ACTION = "deleted"


@dataclass(frozen=True, slots=True)
class ArtifactRetentionPolicy:
    """Local artifact retention settings for managed derived outputs."""

    eval_max_age_days: int = 30
    storage_warning_threshold_bytes: int | None = 512 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ArtifactGcEntry:
    """One artifact file included in a retention report."""

    relative_path: Path
    category: str
    action: str
    reason: str
    size_bytes: int
    content_sha256: str
    modified_at: datetime
    age_days: int

    def with_action(self, action: str) -> ArtifactGcEntry:
        return ArtifactGcEntry(
            relative_path=self.relative_path,
            category=self.category,
            action=action,
            reason=self.reason,
            size_bytes=self.size_bytes,
            content_sha256=self.content_sha256,
            modified_at=self.modified_at,
            age_days=self.age_days,
        )

    def to_json_payload(self) -> dict[str, object]:
        return {
            "path": self.relative_path.as_posix(),
            "category": self.category,
            "action": self.action,
            "reason": self.reason,
            "size_bytes": self.size_bytes,
            "content_sha256": self.content_sha256,
            "modified_at": self.modified_at.isoformat(),
            "age_days": self.age_days,
        }


@dataclass(frozen=True, slots=True)
class ArtifactGcReport:
    """Artifact retention report for dry-run and mutation paths."""

    protected: list[ArtifactGcEntry]
    candidates: list[ArtifactGcEntry]
    deleted: list[ArtifactGcEntry]
    missing_references: list[Path]
    glassbox_size_bytes: int = 0
    storage_warning_threshold_bytes: int | None = None
    storage_warning: str | None = None

    @property
    def candidate_size_bytes(self) -> int:
        return sum(entry.size_bytes for entry in self.candidates)

    @property
    def deleted_size_bytes(self) -> int:
        return sum(entry.size_bytes for entry in self.deleted)

    @property
    def protected_size_bytes(self) -> int:
        return sum(entry.size_bytes for entry in self.protected)

    @property
    def reported_size_bytes(self) -> int:
        return self.protected_size_bytes + self.candidate_size_bytes

    @property
    def reported_count(self) -> int:
        return len(self.protected) + len(self.candidates)

    @property
    def category_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in [*self.protected, *self.candidates]:
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts

    @property
    def oldest_age_days(self) -> int | None:
        ages = [entry.age_days for entry in [*self.protected, *self.candidates]]
        return max(ages) if ages else None

    def to_json_payload(self) -> dict[str, object]:
        return {
            "protected_count": len(self.protected),
            "candidate_count": len(self.candidates),
            "deleted_count": len(self.deleted),
            "missing_reference_count": len(self.missing_references),
            "reported_count": self.reported_count,
            "protected_size_bytes": self.protected_size_bytes,
            "candidate_size_bytes": self.candidate_size_bytes,
            "deleted_size_bytes": self.deleted_size_bytes,
            "reported_size_bytes": self.reported_size_bytes,
            "glassbox_size_bytes": self.glassbox_size_bytes,
            "storage_warning_threshold_bytes": self.storage_warning_threshold_bytes,
            "storage_warning": self.storage_warning,
            "oldest_age_days": self.oldest_age_days,
            "category_counts": self.category_counts,
            "protected": [entry.to_json_payload() for entry in self.protected],
            "candidates": [entry.to_json_payload() for entry in self.candidates],
            "deleted": [entry.to_json_payload() for entry in self.deleted],
            "missing_references": [path.as_posix() for path in self.missing_references],
        }


def run_artifact_gc(
    root_dir: Path,
    repository: SessionRepository,
    *,
    policy: ArtifactRetentionPolicy | None = None,
    dry_run: bool = True,
    now: datetime | None = None,
) -> ArtifactGcReport:
    """Inspect managed artifacts and optionally delete stale derived files."""

    effective_policy = policy or ArtifactRetentionPolicy()
    report = inspect_artifact_state(
        root_dir,
        repository,
        policy=effective_policy,
        now=now,
    )
    if dry_run:
        return report

    deleted: list[ArtifactGcEntry] = []
    for entry in report.candidates:
        absolute_path = root_dir / entry.relative_path
        if not absolute_path.is_file():
            continue
        absolute_path.unlink()
        deleted.append(entry.with_action(_DELETED_ACTION))
    _remove_empty_managed_directories(root_dir)
    return ArtifactGcReport(
        protected=report.protected,
        candidates=report.candidates,
        deleted=deleted,
        missing_references=report.missing_references,
        glassbox_size_bytes=report.glassbox_size_bytes,
        storage_warning_threshold_bytes=report.storage_warning_threshold_bytes,
        storage_warning=report.storage_warning,
    )


def inspect_artifact_state(
    root_dir: Path,
    repository: SessionRepository,
    *,
    policy: ArtifactRetentionPolicy | None = None,
    now: datetime | None = None,
) -> ArtifactGcReport:
    """Build a non-mutating artifact retention report."""

    effective_policy = policy or ArtifactRetentionPolicy()
    effective_now = now or datetime.now(UTC)
    referenced_paths = _referenced_artifact_paths(root_dir, repository)
    protected, missing_references = _protected_entries(
        root_dir,
        referenced_paths,
        now=effective_now,
    )
    candidates = _candidate_entries(
        root_dir,
        referenced_paths,
        policy=effective_policy,
        now=effective_now,
    )
    glassbox_size_bytes = _tree_size_bytes(root_dir / ".glassbox")
    storage_warning = _storage_warning(
        glassbox_size_bytes,
        effective_policy.storage_warning_threshold_bytes,
    )
    return ArtifactGcReport(
        protected=protected,
        candidates=candidates,
        deleted=[],
        missing_references=missing_references,
        glassbox_size_bytes=glassbox_size_bytes,
        storage_warning_threshold_bytes=effective_policy.storage_warning_threshold_bytes,
        storage_warning=storage_warning,
    )


def _referenced_artifact_paths(
    root_dir: Path,
    repository: SessionRepository,
) -> set[Path]:
    referenced_paths: set[Path] = set()
    for session in repository.list_sessions():
        for event in repository.read_session_events(session.session_id):
            payload = event.payload
            if not isinstance(payload, ToolArtifactRecorded | ReplayArtifactRecorded):
                continue
            if payload.path is None:
                continue
            relative_path = _normalize_artifact_path(root_dir, payload.path)
            if relative_path is not None:
                referenced_paths.add(relative_path)
    return referenced_paths


def _protected_entries(
    root_dir: Path,
    referenced_paths: Iterable[Path],
    *,
    now: datetime,
) -> tuple[list[ArtifactGcEntry], list[Path]]:
    protected: list[ArtifactGcEntry] = []
    missing_references: list[Path] = []
    for relative_path in sorted(referenced_paths):
        absolute_path = root_dir / relative_path
        if not absolute_path.is_file():
            missing_references.append(relative_path)
            continue
        protected.append(
            _build_entry(
                root_dir,
                absolute_path,
                category=_EVENT_REFERENCED_ARTIFACT_CATEGORY,
                action=_KEEP_ACTION,
                reason="referenced by canonical event log",
                now=now,
            )
        )
    return protected, missing_references


def _candidate_entries(
    root_dir: Path,
    referenced_paths: set[Path],
    *,
    policy: ArtifactRetentionPolicy,
    now: datetime,
) -> list[ArtifactGcEntry]:
    candidates: list[ArtifactGcEntry] = []
    for artifact_path in _iter_files(root_dir / ".glassbox" / "sessions"):
        relative_path = artifact_path.relative_to(root_dir)
        if "artifacts" not in relative_path.parts:
            continue
        if relative_path in referenced_paths:
            continue
        candidates.append(
            _build_entry(
                root_dir,
                artifact_path,
                category=_ORPHAN_SESSION_ARTIFACT_CATEGORY,
                action=_WOULD_DELETE_ACTION,
                reason="session artifact is not referenced by canonical events",
                now=now,
            )
        )

    eval_cutoff = now - timedelta(days=policy.eval_max_age_days)
    for eval_path in _iter_files(root_dir / ".glassbox" / "evals"):
        modified_at = datetime.fromtimestamp(eval_path.stat().st_mtime, UTC)
        if modified_at >= eval_cutoff:
            continue
        candidates.append(
            _build_entry(
                root_dir,
                eval_path,
                category=_STALE_EVAL_ARTIFACT_CATEGORY,
                action=_WOULD_DELETE_ACTION,
                reason=(
                    f"managed eval artifact is older than "
                    f"{policy.eval_max_age_days} day(s)"
                ),
                now=now,
            )
        )
    return sorted(candidates, key=lambda entry: entry.relative_path.as_posix())


def _normalize_artifact_path(root_dir: Path, path: str) -> Path | None:
    artifact_path = Path(path)
    if artifact_path.is_absolute():
        try:
            return artifact_path.resolve().relative_to(root_dir)
        except ValueError:
            return None
    if artifact_path.parts[:1] != (".glassbox",):
        return None
    if ".." in artifact_path.parts:
        return None
    return artifact_path


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return ()
    return (
        path for path in root.rglob("*") if path.is_file() and not path.is_symlink()
    )


def _build_entry(
    root_dir: Path,
    absolute_path: Path,
    *,
    category: str,
    action: str,
    reason: str,
    now: datetime,
) -> ArtifactGcEntry:
    content = absolute_path.read_bytes()
    modified_at = datetime.fromtimestamp(absolute_path.stat().st_mtime, UTC)
    return ArtifactGcEntry(
        relative_path=absolute_path.relative_to(root_dir),
        category=category,
        action=action,
        reason=reason,
        size_bytes=len(content),
        content_sha256=hashlib.sha256(content).hexdigest(),
        modified_at=modified_at,
        age_days=max((now - modified_at).days, 0),
    )


def _tree_size_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in _iter_files(root))


def _storage_warning(
    glassbox_size_bytes: int,
    threshold_bytes: int | None,
) -> str | None:
    if threshold_bytes is None or threshold_bytes <= 0:
        return None
    if glassbox_size_bytes < threshold_bytes:
        return None
    return (
        f".glassbox contains {glassbox_size_bytes} bytes, meeting or exceeding "
        f"the configured warning threshold of {threshold_bytes} bytes"
    )


def _remove_empty_managed_directories(root_dir: Path) -> None:
    for managed_root in (
        root_dir / ".glassbox" / "sessions",
        root_dir / ".glassbox" / "evals",
    ):
        if not managed_root.exists():
            continue
        for directory in sorted(
            (path for path in managed_root.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                continue
