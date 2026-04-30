"""Repository-index observability collector."""

import shlex
from pathlib import Path

from glassbox.runtime.observability_models import RepositoryIndexObservability
from glassbox.runtime.repository_index_status import (
    build_repository_index_status_summary,
)


def build_repository_index_observability(
    workspace_root: Path,
) -> RepositoryIndexObservability:
    quoted_workspace_root = shlex.quote(str(workspace_root.resolve()))
    summary = build_repository_index_status_summary(workspace_root)
    next_actions = [
        action.replace(str(workspace_root.resolve()), quoted_workspace_root)
        for action in summary.next_actions
    ]

    return RepositoryIndexObservability(
        status=summary.status,
        path=summary.path,
        entry_count=summary.entry_count,
        built_at=summary.built_at,
        failure_reason=summary.failure_reason,
        detail=summary.detail,
        stale_reason=summary.stale_reason,
        next_actions=next_actions,
    )


__all__ = ["build_repository_index_observability"]
