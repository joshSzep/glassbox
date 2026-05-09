"""Deterministic local repository intelligence index builder facade."""

from glassbox.runtime.repository_index_builder import build_and_write_repository_index
from glassbox.runtime.repository_index_builder import build_repository_index
from glassbox.runtime.repository_index_discovery import repository_index_path
from glassbox.runtime.repository_index_persistence import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index_persistence import load_repository_index
from glassbox.runtime.repository_index_persistence import write_repository_index
from glassbox.runtime.repository_index_search import get_repository_index_entry
from glassbox.runtime.repository_index_search import search_repository_index

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
