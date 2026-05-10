"""Repository index persistence and freshness helpers."""

from pathlib import Path

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.runtime.repository_index_discovery import repository_index_path
from glassbox.runtime.repository_index_discovery import scan_indexable_files
from glassbox.runtime.repository_index_discovery import source_digest


class RepositoryIndexNotFoundError(ValueError):
    """Raised when repository index reads require a missing snapshot."""


def write_repository_index(
    workspace_root: Path,
    snapshot: RepositoryIndexSnapshot,
) -> Path:
    """Write a repository index snapshot to the local artifact path."""

    path = repository_index_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_repository_index(workspace_root: Path) -> RepositoryIndexSnapshot:
    """Load the local index snapshot and mark it stale if sources changed."""

    path = repository_index_path(workspace_root)
    if not path.exists():
        raise RepositoryIndexNotFoundError("repository index has not been built")
    snapshot = RepositoryIndexSnapshot.model_validate_json(path.read_text())
    current_digest = source_digest(
        workspace_root.resolve(),
        scan_indexable_files(workspace_root.resolve()).files,
    )
    if snapshot.source_digest is not None and snapshot.source_digest != current_digest:
        return snapshot.model_copy(update={"status": RepositoryIndexFreshness.STALE})
    return snapshot


__all__ = [
    "RepositoryIndexNotFoundError",
    "load_repository_index",
    "write_repository_index",
]
