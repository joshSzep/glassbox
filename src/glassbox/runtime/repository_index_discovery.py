"""Deterministic file discovery and freshness helpers for repository indexes."""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

INDEX_FILE = "repository-index.json"
BUILDER_VERSION = "v2-schema"
MAX_INDEXED_FILES = 2000
INDEX_SCAN_LIMITATION = (
    "Repository intelligence file crawling reached the configured "
    f"{MAX_INDEXED_FILES} file budget; snapshot entries and source digest are "
    "partial. Rebuild in a narrower checkout or inspect generated/excluded paths "
    "before relying on exhaustive path coverage."
)
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
GENERATED_PATH_PREFIXES = (
    "frontend/generated/",
    "src/glassbox/web/static_next/",
)
GENERATED_PATH_MARKERS = (
    "/__pycache__/",
    "/generated/",
    "/static_next/",
    "/node_modules/",
)
CACHE_PATH_NAMES = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
BUILD_OUTPUT_NAMES = {
    ".next",
    "build",
    "coverage",
    "dist",
    "out",
    "static_next",
}
POLICY_SENSITIVE_PATH_PREFIXES = (
    ".github/",
    "docs/tool-policy",
    "docs/tasks-v",
    "scripts/validate_",
    "src/glassbox/tools/policy",
    "src/glassbox/tools/policy_config",
)
POLICY_SENSITIVE_PATH_NAMES = {
    ".env",
    ".env.local",
    ".envrc",
    "glassbox-policy.json",
    "glassbox.tool-policy.json",
}


@dataclass(frozen=True)
class RepositoryPathClassification:
    """Shared local path classifier for repository intelligence consumers."""

    relative_path: Path
    excluded: bool
    generated: bool
    cache: bool
    build_output: bool
    policy_sensitive: bool


@dataclass(frozen=True)
class RepositoryIndexFileScan:
    """Bounded deterministic file scan used by repository intelligence."""

    files: list[Path]
    max_files: int
    truncated: bool

    @property
    def limitations(self) -> list[str]:
        return [INDEX_SCAN_LIMITATION] if self.truncated else []


def repository_index_path(workspace_root: Path) -> Path:
    """Return the local index artifact path for a workspace."""

    return workspace_root / ".glassbox" / INDEX_FILE


def iter_indexable_files(root: Path) -> Iterable[Path]:
    resolved_root = root.resolve()
    stack = [resolved_root]
    while stack:
        directory = stack.pop()
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError:
            continue
        child_directories: list[Path] = []
        for path in children:
            relative = path.relative_to(resolved_root)
            if is_excluded(relative):
                continue
            if path.is_dir():
                child_directories.append(path)
                continue
            if path.is_file():
                yield path
        stack.extend(reversed(child_directories))


def scan_indexable_files(
    root: Path,
    *,
    max_files: int = MAX_INDEXED_FILES,
) -> RepositoryIndexFileScan:
    """Return a bounded deterministic scan and whether results were truncated."""

    files: list[Path] = []
    truncated = False
    for path in iter_indexable_files(root):
        if len(files) >= max_files:
            truncated = True
            break
        files.append(path)
    return RepositoryIndexFileScan(
        files=files,
        max_files=max_files,
        truncated=truncated,
    )


def is_excluded(relative: Path) -> bool:
    return classify_repository_path(relative).excluded


def is_generated_repository_path(path: str | Path) -> bool:
    return classify_repository_path(path).generated


def is_policy_sensitive_repository_path(path: str | Path) -> bool:
    return classify_repository_path(path).policy_sensitive


def classify_repository_path(path: str | Path) -> RepositoryPathClassification:
    relative = _normalize_relative_path(path)
    parts = set(relative.parts)
    value = relative.as_posix()
    normalized = f"/{value}"
    cache = any(part in CACHE_PATH_NAMES for part in parts)
    build_output = any(part in BUILD_OUTPUT_NAMES for part in parts)
    generated = value.startswith(GENERATED_PATH_PREFIXES) or any(
        marker in normalized for marker in GENERATED_PATH_MARKERS
    )
    policy_sensitive = value in POLICY_SENSITIVE_PATH_NAMES or any(
        value.startswith(prefix) for prefix in POLICY_SENSITIVE_PATH_PREFIXES
    )
    return RepositoryPathClassification(
        relative_path=relative,
        excluded=any(part in EXCLUDED_NAMES for part in parts),
        generated=generated,
        cache=cache,
        build_output=build_output,
        policy_sensitive=policy_sensitive,
    )


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


def _normalize_relative_path(path: str | Path) -> Path:
    relative = Path(path)
    if relative.is_absolute():
        raise ValueError("repository paths must be relative to the workspace root")
    if ".." in relative.parts:
        raise ValueError("repository paths must not escape the workspace root")
    return relative


__all__ = [
    "BUILDER_VERSION",
    "BUILD_OUTPUT_NAMES",
    "CACHE_PATH_NAMES",
    "EXCLUDED_NAMES",
    "GENERATED_PATH_MARKERS",
    "GENERATED_PATH_PREFIXES",
    "INDEX_SCAN_LIMITATION",
    "MAX_INDEXED_FILES",
    "POLICY_SENSITIVE_PATH_NAMES",
    "POLICY_SENSITIVE_PATH_PREFIXES",
    "RepositoryIndexFileScan",
    "RepositoryPathClassification",
    "classify_repository_path",
    "iter_indexable_files",
    "is_generated_repository_path",
    "is_policy_sensitive_repository_path",
    "repository_index_path",
    "scan_indexable_files",
    "source_digest",
    "source_digest_inputs",
]
