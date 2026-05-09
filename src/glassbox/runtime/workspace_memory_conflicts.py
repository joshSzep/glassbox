"""Advisory conflict detection for confirmed workspace memory."""

import re
from collections.abc import Iterable
from collections.abc import Sequence
from datetime import UTC
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.ids import WorkspaceMemoryId
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemoryState
from glassbox.runtime.repository_index_persistence import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index_persistence import load_repository_index

_PATH_TOKEN_RE = re.compile(
    r"(?<![\w@-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.@-]+)+|"
    r"[A-Za-z0-9_.-]+\.(?:toml|json|lock|md|py|ts|tsx|js|jsx|yaml|yml))(?![\w@-])"
)
_MANIFEST_NAMES = {
    "package.json",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "uv.lock",
}


class WorkspaceMemoryConflictRecord(BaseModel):
    """A review cue showing why a memory entry may no longer match the repo."""

    model_config = ConfigDict(extra="forbid")

    memory_id: WorkspaceMemoryId
    reason: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=500)
    evidence: list[str] = Field(default_factory=list, max_length=8)
    safe_next_actions: list[str] = Field(default_factory=list, max_length=8)


def workspace_memory_conflicts(
    workspace_root: Path,
    entries: Sequence[WorkspaceMemoryEntry],
) -> list[WorkspaceMemoryConflictRecord]:
    """Detect stale or conflicting active memory without mutating memory state."""

    root = workspace_root.resolve()
    snapshot = _load_optional_snapshot(root)
    conflicts: list[WorkspaceMemoryConflictRecord] = []
    for entry in entries:
        if not _is_conflict_eligible(entry):
            continue
        conflicts.extend(_entry_conflicts(root, entry, snapshot))
    return _dedupe_conflicts(conflicts)


def conflicted_memory_ids(
    workspace_root: Path,
    entries: Sequence[WorkspaceMemoryEntry],
) -> set[WorkspaceMemoryId]:
    """Return memory IDs that should be withheld from default prompt context."""

    return {
        record.memory_id
        for record in workspace_memory_conflicts(workspace_root, entries)
    }


def _is_conflict_eligible(entry: WorkspaceMemoryEntry) -> bool:
    return (
        entry.state == WorkspaceMemoryState.ACTIVE
        and entry.confirmed_at is not None
        and entry.kind
        in {
            WorkspaceMemoryKind.FACT,
            WorkspaceMemoryKind.CONVENTION,
            WorkspaceMemoryKind.COMMAND,
            WorkspaceMemoryKind.ARCHITECTURE_NOTE,
        }
    )


def _entry_conflicts(
    root: Path,
    entry: WorkspaceMemoryEntry,
    snapshot: RepositoryIndexSnapshot | None,
) -> list[WorkspaceMemoryConflictRecord]:
    text = " ".join(
        value for value in (entry.summary, entry.content, " ".join(entry.tags)) if value
    )
    paths = _path_tokens(text)
    conflicts: list[WorkspaceMemoryConflictRecord] = []
    for path in paths:
        absolute = root / path
        if not absolute.exists() and not _snapshot_mentions_path(snapshot, path):
            conflicts.append(
                _record(
                    entry,
                    reason="missing_path",
                    summary=f"Remembered path no longer exists: {path.as_posix()}",
                    evidence=[path.as_posix()],
                )
            )
            continue
        if _manifest_changed_after_confirmation(root, entry, path):
            conflicts.append(
                _record(
                    entry,
                    reason="changed_manifest",
                    summary=(
                        "Remembered repository fact cites a manifest that changed "
                        f"after confirmation: {path.as_posix()}"
                    ),
                    evidence=[path.as_posix()],
                )
            )
        if _looks_generated_memory(entry, text, path) and not _snapshot_generated_path(
            snapshot, path
        ):
            conflicts.append(
                _record(
                    entry,
                    reason="superseded_generated_path",
                    summary=(
                        "Remembered generated-output path is not present in the "
                        f"current repository intelligence snapshot: {path.as_posix()}"
                    ),
                    evidence=[path.as_posix()],
                )
            )
    if entry.kind == WorkspaceMemoryKind.COMMAND and not _command_still_known(
        snapshot,
        entry.content,
    ):
        conflicts.append(
            _record(
                entry,
                reason="unmatched_command_recipe",
                summary=(
                    "Remembered command is not present in current repository "
                    "command recipes."
                ),
                evidence=[entry.summary or entry.content[:160]],
            )
        )
    if _looks_release_memory(entry, text) and snapshot is not None:
        known_surface_paths = {
            scope_path.as_posix()
            for surface in snapshot.release_sensitive_surfaces
            for scope_path in surface.scope_paths
        }
        remembered_paths = {path.as_posix() for path in paths}
        if remembered_paths and remembered_paths.isdisjoint(known_surface_paths):
            conflicts.append(
                _record(
                    entry,
                    reason="changed_release_surface",
                    summary=(
                        "Remembered release-surface note does not match current "
                        "release-sensitive paths."
                    ),
                    evidence=sorted(remembered_paths)[:4],
                )
            )
    return conflicts


def _record(
    entry: WorkspaceMemoryEntry,
    *,
    reason: str,
    summary: str,
    evidence: list[str],
) -> WorkspaceMemoryConflictRecord:
    memory_id = str(entry.memory_id)
    return WorkspaceMemoryConflictRecord(
        memory_id=entry.memory_id,
        reason=reason,
        summary=summary,
        evidence=evidence,
        safe_next_actions=[
            f"glassbox memory show {memory_id} --cwd .",
            "glassbox repo index status --cwd . --json",
            (
                f"glassbox memory invalidate {memory_id} --reason "
                "'repository conflict reviewed'"
            ),
        ],
    )


def _path_tokens(text: str) -> list[Path]:
    paths: list[Path] = []
    for match in _PATH_TOKEN_RE.finditer(text):
        token = match.group(1).strip("`'\".,)")
        path = Path(token)
        if path.is_absolute() or ".." in path.parts:
            continue
        if path.parts and path.parts[0] in {"http:", "https:"}:
            continue
        paths.append(path)
    return sorted(set(paths), key=lambda item: item.as_posix())


def _load_optional_snapshot(root: Path) -> RepositoryIndexSnapshot | None:
    try:
        snapshot = load_repository_index(root)
    except RepositoryIndexNotFoundError:
        return None
    if snapshot.status == RepositoryIndexFreshness.FAILED:
        return None
    return snapshot


def _snapshot_mentions_path(
    snapshot: RepositoryIndexSnapshot | None,
    path: Path,
) -> bool:
    if snapshot is None:
        return False
    value = path.as_posix()
    known_paths = [
        *(hint.path.as_posix() for hint in snapshot.source_roots),
        *(hint.path.as_posix() for hint in snapshot.test_roots),
        *(hint.path.as_posix() for hint in snapshot.doc_roots),
        *(hint.path.as_posix() for hint in snapshot.generated_paths),
        *(
            entry.path.as_posix()
            for entry in snapshot.entries
            if entry.path is not None
        ),
    ]
    return value in known_paths


def _snapshot_generated_path(
    snapshot: RepositoryIndexSnapshot | None,
    path: Path,
) -> bool:
    if snapshot is None:
        return False
    value = path.as_posix()
    return any(
        value == generated.path.as_posix()
        or value.startswith(f"{generated.path.as_posix().rstrip('/')}/")
        for generated in snapshot.generated_paths
    )


def _manifest_changed_after_confirmation(
    root: Path,
    entry: WorkspaceMemoryEntry,
    path: Path,
) -> bool:
    if path.name not in _MANIFEST_NAMES or entry.confirmed_at is None:
        return False
    absolute = root / path
    if not absolute.exists():
        return False
    try:
        changed_at = absolute.stat().st_mtime
    except OSError:
        return False
    return changed_at > entry.confirmed_at.astimezone(UTC).timestamp()


def _looks_generated_memory(
    entry: WorkspaceMemoryEntry,
    text: str,
    path: Path,
) -> bool:
    haystack = " ".join([text, " ".join(entry.tags)]).casefold()
    return (
        "generated" in haystack
        or "build output" in haystack
        or "static_next" in path.parts
        or "generated" in path.parts
    )


def _looks_release_memory(entry: WorkspaceMemoryEntry, text: str) -> bool:
    haystack = " ".join([text, " ".join(entry.tags)]).casefold()
    return "release" in haystack or "release-surface" in haystack


def _command_still_known(
    snapshot: RepositoryIndexSnapshot | None,
    command_text: str,
) -> bool:
    if snapshot is None or not snapshot.command_recipes:
        return True
    remembered = " ".join(command_text.split())
    return any(
        " ".join(recipe.command.split()) in remembered
        or remembered in " ".join(recipe.command.split())
        for recipe in snapshot.command_recipes
    )


def _dedupe_conflicts(
    conflicts: Iterable[WorkspaceMemoryConflictRecord],
) -> list[WorkspaceMemoryConflictRecord]:
    seen: set[tuple[WorkspaceMemoryId, str, str]] = set()
    deduped: list[WorkspaceMemoryConflictRecord] = []
    for conflict in conflicts:
        key = (conflict.memory_id, conflict.reason, conflict.summary)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(conflict)
    return deduped


__all__ = [
    "WorkspaceMemoryConflictRecord",
    "conflicted_memory_ids",
    "workspace_memory_conflicts",
]
