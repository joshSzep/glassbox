"""Operator-facing repository-index freshness summaries."""

from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.runtime.repository_index_discovery import MAX_INDEXED_FILES
from glassbox.runtime.repository_index_discovery import iter_indexable_files
from glassbox.runtime.repository_index_discovery import repository_index_path
from glassbox.runtime.repository_index_discovery import source_digest
from glassbox.runtime.repository_index_discovery import source_digest_inputs
from glassbox.runtime.repository_index_persistence import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index_persistence import load_repository_index
from glassbox.runtime.repository_intelligence_freshness import (
    RepositoryIntelligenceFreshnessCue,
)
from glassbox.runtime.repository_intelligence_freshness import (
    repository_index_freshness_cues,
)


class RepositoryIndexSourceDiff(BaseModel):
    """Bounded read-only diff between retained and current index inputs."""

    model_config = ConfigDict(extra="forbid")

    added_count: int = 0
    removed_count: int = 0
    changed_count: int = 0
    added_paths: list[str] = Field(default_factory=list)
    removed_paths: list[str] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    available: bool = True
    detail: str | None = None


class RepositoryIndexStatusSummary(BaseModel):
    """Status payload shared by CLI, observability, and dashboard guidance."""

    model_config = ConfigDict(extra="forbid")

    status: str
    path: str
    entry_count: int
    built_at: str | None = None
    schema_version: int | None = None
    builder_version: str | None = None
    source_digest: str | None = None
    current_source_digest: str | None = None
    source_file_count: int = 0
    current_source_file_count: int = 0
    source_manifest_count: int = 0
    source_root_count: int = 0
    test_root_count: int = 0
    doc_root_count: int = 0
    generated_path_count: int = 0
    policy_sensitive_path_count: int = 0
    package_boundary_count: int = 0
    command_recipe_count: int = 0
    ownership_hint_count: int = 0
    subsystem_count: int = 0
    release_surface_count: int = 0
    memory_reference_count: int = 0
    failure_reason: str | None = None
    detail: str
    stale_reason: str | None = None
    source_diff: RepositoryIndexSourceDiff | None = None
    freshness_cues: list[RepositoryIntelligenceFreshnessCue] = Field(
        default_factory=list
    )
    limitations: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


def build_repository_index_status_summary(
    workspace_root: Path,
) -> RepositoryIndexStatusSummary:
    """Build a clear status summary without mutating repository-index state."""

    root = workspace_root.resolve()
    path = repository_index_path(root)
    files = list(iter_indexable_files(root))[:MAX_INDEXED_FILES]
    current_inputs = source_digest_inputs(root, files)
    current_digest = source_digest(root, files)

    try:
        snapshot = load_repository_index(root)
    except RepositoryIndexNotFoundError:
        return RepositoryIndexStatusSummary(
            status="missing",
            path=str(path),
            entry_count=0,
            current_source_digest=current_digest,
            current_source_file_count=len(current_inputs),
            detail=(
                "No repository index exists for this workspace. Build it when you "
                "want local repository intelligence for search and context."
            ),
            freshness_cues=repository_index_freshness_cues(root, None),
            next_actions=[f"glassbox repo index build --cwd {root}"],
        )

    stale_reason: str | None = None
    source_diff: RepositoryIndexSourceDiff | None = None
    if snapshot.status == RepositoryIndexFreshness.STALE:
        stale_reason = (
            "Current source digest differs from the digest retained when the "
            "index was built."
        )
        source_diff = _source_diff(snapshot.source_inputs, current_inputs)
    elif snapshot.status == RepositoryIndexFreshness.FAILED:
        stale_reason = snapshot.failure_reason

    return RepositoryIndexStatusSummary(
        status=snapshot.status.value,
        path=str(path),
        entry_count=len(snapshot.entries),
        built_at=snapshot.built_at.isoformat() if snapshot.built_at else None,
        schema_version=snapshot.schema_version,
        builder_version=snapshot.builder_version,
        source_digest=snapshot.source_digest,
        current_source_digest=current_digest,
        source_file_count=len(snapshot.source_inputs),
        current_source_file_count=len(current_inputs),
        source_manifest_count=len(snapshot.source_manifests),
        source_root_count=len(snapshot.source_roots),
        test_root_count=len(snapshot.test_roots),
        doc_root_count=len(snapshot.doc_roots),
        generated_path_count=len(snapshot.generated_paths),
        policy_sensitive_path_count=len(snapshot.policy_sensitive_paths),
        package_boundary_count=len(snapshot.package_boundaries),
        command_recipe_count=len(snapshot.command_recipes),
        ownership_hint_count=len(snapshot.ownership_hints),
        subsystem_count=len(snapshot.subsystems),
        release_surface_count=len(snapshot.release_sensitive_surfaces),
        memory_reference_count=len(snapshot.memory_references),
        failure_reason=snapshot.failure_reason,
        detail=_status_detail(snapshot),
        stale_reason=stale_reason,
        source_diff=source_diff,
        freshness_cues=repository_index_freshness_cues(root, snapshot),
        limitations=snapshot.limitations,
        next_actions=_next_actions(root, snapshot.status),
    )


def _status_detail(snapshot: RepositoryIndexSnapshot) -> str:
    if snapshot.status == RepositoryIndexFreshness.FRESH:
        return "Repository intelligence is fresh for the current source digest."
    if snapshot.status == RepositoryIndexFreshness.STALE:
        return (
            "Repository intelligence is stale. Search and context can still be "
            "inspected, but rebuild before relying on it for current work."
        )
    if snapshot.status == RepositoryIndexFreshness.FAILED:
        return (
            "The last repository index refresh failed; inspect the reason before "
            "rebuilding."
        )
    if snapshot.status == RepositoryIndexFreshness.BUILDING:
        return (
            "A repository index refresh is in progress; check status again before "
            "rebuilding."
        )
    return "Repository index state is available for inspection."


def _next_actions(root: Path, status: RepositoryIndexFreshness) -> list[str]:
    if status == RepositoryIndexFreshness.FRESH:
        return [f"glassbox repo index search QUERY --cwd {root}"]
    if status == RepositoryIndexFreshness.BUILDING:
        return [f"glassbox repo index status --cwd {root}"]
    return [
        f"glassbox repo index status --cwd {root} --json",
        f"glassbox repo index build --cwd {root}",
    ]


def _source_diff(
    retained_inputs: list[str],
    current_inputs: list[str],
    *,
    sample_limit: int = 5,
) -> RepositoryIndexSourceDiff:
    if not retained_inputs:
        return RepositoryIndexSourceDiff(
            available=False,
            detail=(
                "Retained snapshot does not include source input inventory; "
                "rebuild once to enable path-level stale explanations."
            ),
        )

    retained = _source_input_map(retained_inputs)
    current = _source_input_map(current_inputs)
    retained_paths = set(retained)
    current_paths = set(current)
    added = sorted(current_paths - retained_paths)
    removed = sorted(retained_paths - current_paths)
    changed = sorted(
        path
        for path in retained_paths & current_paths
        if retained[path] != current[path]
    )
    return RepositoryIndexSourceDiff(
        added_count=len(added),
        removed_count=len(removed),
        changed_count=len(changed),
        added_paths=added[:sample_limit],
        removed_paths=removed[:sample_limit],
        changed_paths=changed[:sample_limit],
    )


def _source_input_map(inputs: list[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for source_input in inputs:
        path_and_size, _, _mtime = source_input.rpartition(":")
        path, _, _size = path_and_size.rpartition(":")
        if path:
            mapped[path] = source_input
    return mapped


__all__ = [
    "RepositoryIndexSourceDiff",
    "RepositoryIndexStatusSummary",
    "build_repository_index_status_summary",
]
