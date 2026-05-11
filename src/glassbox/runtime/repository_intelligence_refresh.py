"""Shared repository intelligence refresh orchestration."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.workspace_topology import WorkspaceTopologySnapshot
from glassbox.runtime.workspace_topology import build_workspace_topology
from glassbox.runtime.workspace_topology import workspace_topology_path
from glassbox.runtime.workspace_topology import write_workspace_topology


@dataclass(frozen=True)
class RepositoryIndexRefreshResult:
    """Result metadata for a persisted repository index refresh."""

    snapshot: RepositoryIndexSnapshot
    index_path: Path

    @property
    def entry_count(self) -> int:
        return len(self.snapshot.entries)


@dataclass(frozen=True)
class RepositoryIntelligenceRefreshResult:
    """Result metadata for a persisted repository intelligence refresh."""

    index_snapshot: RepositoryIndexSnapshot
    topology_snapshot: WorkspaceTopologySnapshot
    index_path: Path
    topology_path: Path

    @property
    def index_entry_count(self) -> int:
        return len(self.index_snapshot.entries)

    @property
    def command_recipe_count(self) -> int:
        return len(self.index_snapshot.command_recipes)

    @property
    def memory_reference_count(self) -> int:
        return len(self.index_snapshot.memory_references)

    @property
    def topology_component_count(self) -> int:
        return len(self.topology_snapshot.components)

    @property
    def topology_dependency_count(self) -> int:
        return len(self.topology_snapshot.dependencies)


def refresh_repository_index(
    workspace_root: Path,
    *,
    workspace_memory_entries: Sequence[WorkspaceMemoryEntry] = (),
) -> RepositoryIndexRefreshResult:
    """Build and persist the local repository intelligence index."""

    snapshot = build_and_write_repository_index(
        workspace_root,
        workspace_memory_entries=workspace_memory_entries,
    )
    return RepositoryIndexRefreshResult(
        snapshot=snapshot,
        index_path=repository_index_path(workspace_root),
    )


def refresh_repository_intelligence(
    workspace_root: Path,
    *,
    workspace_memory_entries: Sequence[WorkspaceMemoryEntry] = (),
) -> RepositoryIntelligenceRefreshResult:
    """Build and persist the repository index plus derived workspace topology."""

    index_result = refresh_repository_index(
        workspace_root,
        workspace_memory_entries=workspace_memory_entries,
    )
    topology_snapshot = build_workspace_topology(
        workspace_root,
        repository_index=index_result.snapshot,
    )
    write_workspace_topology(workspace_root, topology_snapshot)
    return RepositoryIntelligenceRefreshResult(
        index_snapshot=index_result.snapshot,
        topology_snapshot=topology_snapshot,
        index_path=index_result.index_path,
        topology_path=workspace_topology_path(workspace_root),
    )


def repository_intelligence_refresh_summary_text(
    refresh_result: RepositoryIntelligenceRefreshResult,
) -> str:
    """Return retained summary text for a repository intelligence refresh."""

    return "\n".join(
        [
            "Repository intelligence refresh",
            f"index_entries: {refresh_result.index_entry_count}",
            f"command_recipes: {refresh_result.command_recipe_count}",
            f"memory_references: {refresh_result.memory_reference_count}",
            f"topology_components: {refresh_result.topology_component_count}",
            f"topology_dependencies: {refresh_result.topology_dependency_count}",
            f"index_path: {refresh_result.index_path}",
            f"topology_path: {refresh_result.topology_path}",
            "source_mutation: none",
            "policy_mutation: none",
            "command_recipes_authority: advisory",
            "release_authority: deterministic",
        ]
    )


__all__ = [
    "RepositoryIndexRefreshResult",
    "RepositoryIntelligenceRefreshResult",
    "repository_intelligence_refresh_summary_text",
    "refresh_repository_index",
    "refresh_repository_intelligence",
]
