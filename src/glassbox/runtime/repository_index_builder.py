"""Repository intelligence index builder implementation."""

from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.runtime.repository_index_discovery import BUILDER_VERSION
from glassbox.runtime.repository_index_discovery import EXCLUDED_NAMES
from glassbox.runtime.repository_index_discovery import scan_indexable_files
from glassbox.runtime.repository_index_discovery import source_digest
from glassbox.runtime.repository_index_discovery import source_digest_inputs
from glassbox.runtime.repository_index_extraction import command_entries
from glassbox.runtime.repository_index_extraction import dedupe_entry_id
from glassbox.runtime.repository_index_extraction import dependency_entries
from glassbox.runtime.repository_index_extraction import file_entries
from glassbox.runtime.repository_index_extraction import memory_reference_entries
from glassbox.runtime.repository_index_extraction import (
    repository_intelligence_layout_fields,
)
from glassbox.runtime.repository_index_persistence import write_repository_index


def build_repository_index(
    workspace_root: Path,
    *,
    workspace_memory_entries: Sequence[WorkspaceMemoryEntry] = (),
) -> RepositoryIndexSnapshot:
    """Build a deterministic local repository intelligence snapshot."""

    root = workspace_root.resolve()
    scan = scan_indexable_files(root)
    files = scan.files
    source_inputs = source_digest_inputs(root, files)
    digest = source_digest(root, files)
    built_at = datetime.now(UTC)
    entries: list[RepositoryIndexEntry] = []
    seen_ids: set[str] = set()

    def add(entry: RepositoryIndexEntry) -> None:
        resolved = dedupe_entry_id(entry, seen_ids)
        seen_ids.add(resolved.entry_id)
        entries.append(resolved)

    for path in files:
        for entry in file_entries(root=root, path=path, updated_at=built_at):
            add(entry)
    for command_entry in command_entries(root, built_at):
        add(command_entry)
    for dependency_entry in dependency_entries(root, built_at):
        add(dependency_entry)

    layout_fields = repository_intelligence_layout_fields(root, built_at=built_at)
    layout_fields["memory_references"] = memory_reference_entries(
        workspace_memory_entries
    )
    layout_fields["limitations"] = [
        *layout_fields["limitations"],
        *scan.limitations,
    ]

    return RepositoryIndexSnapshot(
        schema_version=2,
        workspace_root=root,
        status=RepositoryIndexFreshness.FRESH,
        built_at=built_at,
        builder_version=BUILDER_VERSION,
        source_digest=digest,
        source_inputs=source_inputs,
        exclude_patterns=sorted(EXCLUDED_NAMES),
        entries=entries,
        **layout_fields,
    )


def build_and_write_repository_index(
    workspace_root: Path,
    *,
    workspace_memory_entries: Sequence[WorkspaceMemoryEntry] = (),
) -> RepositoryIndexSnapshot:
    """Build and persist the repository intelligence index."""

    snapshot = build_repository_index(
        workspace_root,
        workspace_memory_entries=workspace_memory_entries,
    )
    write_repository_index(workspace_root, snapshot)
    return snapshot


__all__ = ["build_and_write_repository_index", "build_repository_index"]
