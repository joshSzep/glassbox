"""Repository-index observability collector."""

import shlex
from pathlib import Path

from glassbox.core.types import RepositoryIndexFreshness
from glassbox.runtime.observability_models import RepositoryIndexObservability
from glassbox.runtime.repository_index import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path


def build_repository_index_observability(
    workspace_root: Path,
) -> RepositoryIndexObservability:
    path = repository_index_path(workspace_root)
    quoted_workspace_root = shlex.quote(str(workspace_root))
    try:
        snapshot = load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError:
        return RepositoryIndexObservability(
            status="missing",
            path=str(path),
            entry_count=0,
            next_actions=[f"glassbox repo index build --cwd {quoted_workspace_root}"],
        )

    next_actions: list[str] = []
    if snapshot.status in {
        RepositoryIndexFreshness.STALE,
        RepositoryIndexFreshness.FAILED,
    }:
        next_actions.append(f"glassbox repo index status --cwd {quoted_workspace_root}")
        next_actions.append(f"glassbox repo index build --cwd {quoted_workspace_root}")
    elif snapshot.status == RepositoryIndexFreshness.BUILDING:
        next_actions.append(f"glassbox repo index status --cwd {quoted_workspace_root}")

    return RepositoryIndexObservability(
        status=snapshot.status.value,
        path=str(path),
        entry_count=len(snapshot.entries),
        built_at=snapshot.built_at.isoformat() if snapshot.built_at else None,
        failure_reason=snapshot.failure_reason,
        next_actions=next_actions,
    )


__all__ = ["build_repository_index_observability"]
