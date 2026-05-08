"""Deterministic local repository intelligence index builder facade."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.runtime.repository_index_discovery import BUILDER_VERSION
from glassbox.runtime.repository_index_discovery import EXCLUDED_NAMES
from glassbox.runtime.repository_index_discovery import MAX_INDEXED_FILES
from glassbox.runtime.repository_index_discovery import iter_indexable_files
from glassbox.runtime.repository_index_discovery import repository_index_path
from glassbox.runtime.repository_index_discovery import source_digest
from glassbox.runtime.repository_index_discovery import source_digest_inputs
from glassbox.runtime.repository_index_extraction import command_entries
from glassbox.runtime.repository_index_extraction import dedupe_entry_id
from glassbox.runtime.repository_index_extraction import dependency_entries
from glassbox.runtime.repository_index_extraction import file_entries
from glassbox.runtime.repository_index_extraction import (
    repository_intelligence_layout_fields,
)
from glassbox.runtime.repository_index_persistence import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index_persistence import load_repository_index
from glassbox.runtime.repository_index_persistence import write_repository_index
from glassbox.runtime.repository_index_search import get_repository_index_entry
from glassbox.runtime.repository_index_search import search_repository_index


def build_repository_index(workspace_root: Path) -> RepositoryIndexSnapshot:
    """Build a deterministic local repository intelligence snapshot."""

    root = workspace_root.resolve()
    files = list(iter_indexable_files(root))[:MAX_INDEXED_FILES]
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
        **repository_intelligence_layout_fields(root, built_at=built_at),
    )


def build_and_write_repository_index(workspace_root: Path) -> RepositoryIndexSnapshot:
    """Build and persist the repository intelligence index."""

    snapshot = build_repository_index(workspace_root)
    write_repository_index(workspace_root, snapshot)
    return snapshot


__all__ = [
    "RepositoryIndexNotFoundError",
    "build_and_write_repository_index",
    "build_repository_index",
    "get_repository_index_entry",
    "load_repository_index",
    "repository_index_path",
    "search_repository_index",
    "write_repository_index",
]
