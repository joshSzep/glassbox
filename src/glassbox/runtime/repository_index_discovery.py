"""Deterministic file discovery and freshness helpers for repository indexes."""

import hashlib
from collections.abc import Iterable
from pathlib import Path

INDEX_FILE = "repository-index.json"
BUILDER_VERSION = "v1"
MAX_INDEXED_FILES = 2000
EXCLUDED_NAMES = {
    ".git",
    ".glassbox",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
    "static_next",
}


def repository_index_path(workspace_root: Path) -> Path:
    """Return the local index artifact path for a workspace."""

    return workspace_root / ".glassbox" / INDEX_FILE


def iter_indexable_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if is_excluded(relative):
            continue
        yield path


def is_excluded(relative: Path) -> bool:
    return any(part in EXCLUDED_NAMES for part in relative.parts)


def source_digest(root: Path, files: list[Path]) -> str:
    hasher = hashlib.sha256()
    for source_input in source_digest_inputs(root, files):
        hasher.update(f"{source_input}\n".encode())
    return hasher.hexdigest()


def source_digest_inputs(root: Path, files: list[Path]) -> list[str]:
    inputs: list[str] = []
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        relative = path.relative_to(root).as_posix()
        inputs.append(f"{relative}:{stat.st_size}:{stat.st_mtime_ns}")
    return inputs


__all__ = [
    "BUILDER_VERSION",
    "EXCLUDED_NAMES",
    "MAX_INDEXED_FILES",
    "iter_indexable_files",
    "repository_index_path",
    "source_digest",
    "source_digest_inputs",
]
