"""Search helpers for persisted repository indexes."""

from pathlib import Path

from glassbox.core.models import RepositoryIndexEntry
from glassbox.runtime.repository_index_persistence import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index_persistence import load_repository_index


def search_repository_index(
    workspace_root: Path,
    query: str,
    *,
    limit: int | None = None,
) -> list[RepositoryIndexEntry]:
    """Search index entries by name, path, summary, symbol, or tags."""

    normalized_query = query.strip().lower()
    if not normalized_query:
        return []
    matches = [
        entry
        for entry in load_repository_index(workspace_root).entries
        if normalized_query in entry_search_text(entry)
    ]
    return matches if limit is None else matches[:limit]


def get_repository_index_entry(
    workspace_root: Path,
    entry_id: str,
) -> RepositoryIndexEntry:
    """Read one index entry by stable ID."""

    for entry in load_repository_index(workspace_root).entries:
        if entry.entry_id == entry_id:
            return entry
    raise RepositoryIndexNotFoundError(f"unknown repository index entry: {entry_id}")


def entry_search_text(entry: RepositoryIndexEntry) -> str:
    return " ".join(
        part.lower()
        for part in [
            entry.entry_id,
            entry.kind.value,
            entry.name,
            entry.summary or "",
            entry.path.as_posix() if entry.path else "",
            entry.symbol or "",
            " ".join(entry.tags),
        ]
    )


__all__ = [
    "entry_search_text",
    "get_repository_index_entry",
    "search_repository_index",
]
