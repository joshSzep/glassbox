"""Deterministic local repository intelligence index builder."""

import hashlib
import json
import re
import tomllib
from collections.abc import Iterable
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.types import RepositoryIndexEntityKind
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.core.types import RepositoryIndexSourceType

_INDEX_FILE = "repository-index.json"
_BUILDER_VERSION = "v1"
_MAX_INDEXED_FILES = 2000
_EXCLUDED_NAMES = {
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
_PROJECT_MARKERS = {
    "pyproject.toml",
    "package.json",
    "pnpm-lock.yaml",
    "package-lock.json",
    "uv.lock",
    "README.md",
    "Makefile",
    "next.config.ts",
    "next.config.js",
    "eslint.config.mjs",
}
_SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
_DOC_SUFFIXES = {".md", ".mdx", ".rst"}
_TEST_NAME_RE = re.compile(r"(^test_|_test\.|\.test\.|\.spec\.)")
_PY_SYMBOL_RE = re.compile(r"^(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")
_TS_SYMBOL_RE = re.compile(
    r"^(?:export\s+)?(?:async\s+)?(?:function|class|const|let)\s+([A-Za-z_$][A-Za-z0-9_$]*)"
)


class RepositoryIndexNotFoundError(ValueError):
    """Raised when repository index reads require a missing snapshot."""


def repository_index_path(workspace_root: Path) -> Path:
    """Return the local index artifact path for a workspace."""

    return workspace_root / ".glassbox" / _INDEX_FILE


def build_repository_index(workspace_root: Path) -> RepositoryIndexSnapshot:
    """Build a deterministic local repository intelligence snapshot."""

    root = workspace_root.resolve()
    files = list(_iter_indexable_files(root))[:_MAX_INDEXED_FILES]
    digest = _source_digest(root, files)
    built_at = datetime.now(UTC)
    entries: list[RepositoryIndexEntry] = []
    seen_ids: set[str] = set()

    def add(entry: RepositoryIndexEntry) -> None:
        resolved = _dedupe_entry_id(entry, seen_ids)
        seen_ids.add(resolved.entry_id)
        entries.append(resolved)

    for path in files:
        relative = path.relative_to(root)
        if path.name in _PROJECT_MARKERS:
            add(_project_marker_entry(relative, built_at))
        if (
            relative.parts
            and relative.parts[0] == "docs"
            and path.suffix in _DOC_SUFFIXES
        ):
            add(_doc_entry(relative, built_at))
        if relative.parts and relative.parts[0] == "evals":
            add(_eval_entry(relative, built_at))
        if path.suffix in _SOURCE_SUFFIXES:
            add(_file_entry(relative, built_at))
            module_entry = _module_entry(relative, built_at)
            if module_entry is not None:
                add(module_entry)
            for symbol_entry in _symbol_entries(path, relative, built_at):
                add(symbol_entry)
        if _is_test_file(relative):
            add(_test_entry(relative, built_at))

    for command_entry in _command_entries(root, built_at):
        add(command_entry)
    for dependency_entry in _dependency_entries(root, built_at):
        add(dependency_entry)

    return RepositoryIndexSnapshot(
        workspace_root=root,
        status=RepositoryIndexFreshness.FRESH,
        built_at=built_at,
        builder_version=_BUILDER_VERSION,
        source_digest=digest,
        exclude_patterns=sorted(_EXCLUDED_NAMES),
        entries=entries,
    )


def write_repository_index(
    workspace_root: Path,
    snapshot: RepositoryIndexSnapshot,
) -> Path:
    """Write a repository index snapshot to the local artifact path."""

    path = repository_index_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    return path


def build_and_write_repository_index(workspace_root: Path) -> RepositoryIndexSnapshot:
    """Build and persist the repository intelligence index."""

    snapshot = build_repository_index(workspace_root)
    write_repository_index(workspace_root, snapshot)
    return snapshot


def load_repository_index(workspace_root: Path) -> RepositoryIndexSnapshot:
    """Load the local index snapshot and mark it stale if sources changed."""

    path = repository_index_path(workspace_root)
    if not path.exists():
        raise RepositoryIndexNotFoundError("repository index has not been built")
    snapshot = RepositoryIndexSnapshot.model_validate_json(path.read_text())
    current_digest = _source_digest(
        workspace_root.resolve(),
        list(_iter_indexable_files(workspace_root.resolve()))[:_MAX_INDEXED_FILES],
    )
    if snapshot.source_digest is not None and snapshot.source_digest != current_digest:
        return snapshot.model_copy(update={"status": RepositoryIndexFreshness.STALE})
    return snapshot


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
        if normalized_query in _entry_search_text(entry)
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


def _iter_indexable_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if _is_excluded(relative):
            continue
        yield path


def _is_excluded(relative: Path) -> bool:
    return any(part in _EXCLUDED_NAMES for part in relative.parts)


def _source_digest(root: Path, files: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        relative = path.relative_to(root).as_posix()
        hasher.update(f"{relative}:{stat.st_size}:{stat.st_mtime_ns}\n".encode())
    return hasher.hexdigest()


def _project_marker_entry(relative: Path, updated_at: datetime) -> RepositoryIndexEntry:
    return _entry(
        kind=RepositoryIndexEntityKind.PROJECT_MARKER,
        name=relative.name,
        path=relative,
        summary=f"Project marker discovered at {relative.as_posix()}.",
        source_type=RepositoryIndexSourceType.MANIFEST,
        updated_at=updated_at,
        tags=["marker"],
    )


def _doc_entry(relative: Path, updated_at: datetime) -> RepositoryIndexEntry:
    return _entry(
        kind=RepositoryIndexEntityKind.DOC,
        name=relative.as_posix(),
        path=relative,
        summary=f"Documentation file {relative.as_posix()}.",
        source_type=RepositoryIndexSourceType.DOCUMENTATION,
        updated_at=updated_at,
        tags=["docs"],
    )


def _eval_entry(relative: Path, updated_at: datetime) -> RepositoryIndexEntry:
    return _entry(
        kind=RepositoryIndexEntityKind.EVAL_CASE,
        name=relative.as_posix(),
        path=relative,
        summary=f"Eval asset {relative.as_posix()}.",
        source_type=RepositoryIndexSourceType.EVAL,
        updated_at=updated_at,
        tags=["eval"],
    )


def _file_entry(relative: Path, updated_at: datetime) -> RepositoryIndexEntry:
    return _entry(
        kind=RepositoryIndexEntityKind.FILE,
        name=relative.name,
        path=relative,
        summary=f"Source file {relative.as_posix()}.",
        source_type=RepositoryIndexSourceType.FILE_SYSTEM,
        updated_at=updated_at,
        tags=["source", relative.suffix.removeprefix(".")],
    )


def _module_entry(relative: Path, updated_at: datetime) -> RepositoryIndexEntry | None:
    if len(relative.parts) < 2 or relative.suffix not in _SOURCE_SUFFIXES:
        return None
    module_path = Path(*relative.parts[:-1])
    return _entry(
        kind=RepositoryIndexEntityKind.MODULE,
        name=module_path.as_posix(),
        path=relative,
        summary=f"Module path {module_path.as_posix()} includes {relative.name}.",
        source_type=RepositoryIndexSourceType.FILE_SYSTEM,
        updated_at=updated_at,
        tags=["module"],
    )


def _symbol_entries(
    path: Path,
    relative: Path,
    updated_at: datetime,
) -> list[RepositoryIndexEntry]:
    regex = _PY_SYMBOL_RE if path.suffix == ".py" else _TS_SYMBOL_RE
    entries: list[RepositoryIndexEntry] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return entries
    for index, line in enumerate(lines, start=1):
        match = regex.match(line.strip())
        if match is None:
            continue
        symbol = match.group(1)
        entries.append(
            RepositoryIndexEntry(
                entry_id=_entry_id(RepositoryIndexEntityKind.SYMBOL, relative, symbol),
                kind=RepositoryIndexEntityKind.SYMBOL,
                name=symbol,
                summary=f"Symbol {symbol} in {relative.as_posix()}.",
                path=relative,
                symbol=symbol,
                language=_language_for_suffix(path.suffix),
                provenance=[
                    RepositoryIndexProvenance(
                        source_type=RepositoryIndexSourceType.STATIC_ANALYSIS,
                        path=relative,
                        line_start=index,
                        line_end=index,
                        tool_name="glassbox-static-symbol-scan",
                    )
                ],
                tags=["symbol"],
                updated_at=updated_at,
            )
        )
    return entries


def _test_entry(relative: Path, updated_at: datetime) -> RepositoryIndexEntry:
    return _entry(
        kind=RepositoryIndexEntityKind.TEST,
        name=relative.as_posix(),
        path=relative,
        summary=f"Test file or target {relative.as_posix()}.",
        source_type=RepositoryIndexSourceType.TEST,
        updated_at=updated_at,
        tags=["test"],
    )


def _command_entries(root: Path, updated_at: datetime) -> list[RepositoryIndexEntry]:
    entries: list[RepositoryIndexEntry] = []
    package_json = root / "frontend" / "package.json"
    if package_json.exists():
        for name, command in _package_scripts(package_json).items():
            entries.append(
                _entry(
                    kind=RepositoryIndexEntityKind.COMMAND,
                    name=f"frontend:{name}",
                    path=package_json.relative_to(root),
                    summary=str(command),
                    source_type=RepositoryIndexSourceType.MANIFEST,
                    updated_at=updated_at,
                    tags=["command", "frontend"],
                )
            )
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        for command in _pyproject_commands(pyproject):
            entries.append(
                _entry(
                    kind=RepositoryIndexEntityKind.COMMAND,
                    name=command,
                    path=pyproject.relative_to(root),
                    summary=f"Python tool command {command}.",
                    source_type=RepositoryIndexSourceType.MANIFEST,
                    updated_at=updated_at,
                    tags=["command", "python"],
                )
            )
    return entries


def _dependency_entries(root: Path, updated_at: datetime) -> list[RepositoryIndexEntry]:
    entries: list[RepositoryIndexEntry] = []
    package_json = root / "frontend" / "package.json"
    if package_json.exists():
        dependencies = _package_dependencies(package_json)
        if dependencies:
            entries.append(
                _entry(
                    kind=RepositoryIndexEntityKind.DEPENDENCY_HINT,
                    name="frontend dependencies",
                    path=package_json.relative_to(root),
                    summary=", ".join(sorted(dependencies)[:20]),
                    source_type=RepositoryIndexSourceType.MANIFEST,
                    updated_at=updated_at,
                    tags=["dependency", "frontend"],
                )
            )
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        dependencies = _pyproject_dependencies(pyproject)
        if dependencies:
            entries.append(
                _entry(
                    kind=RepositoryIndexEntityKind.DEPENDENCY_HINT,
                    name="python dependencies",
                    path=pyproject.relative_to(root),
                    summary=", ".join(sorted(dependencies)[:20]),
                    source_type=RepositoryIndexSourceType.MANIFEST,
                    updated_at=updated_at,
                    tags=["dependency", "python"],
                )
            )
    return entries


def _entry(
    *,
    kind: RepositoryIndexEntityKind,
    name: str,
    path: Path,
    summary: str,
    source_type: RepositoryIndexSourceType,
    updated_at: datetime,
    tags: list[str],
) -> RepositoryIndexEntry:
    return RepositoryIndexEntry(
        entry_id=_entry_id(kind, path, name),
        kind=kind,
        name=name,
        summary=summary,
        path=path,
        language=_language_for_suffix(path.suffix),
        provenance=[RepositoryIndexProvenance(source_type=source_type, path=path)],
        tags=tags,
        updated_at=updated_at,
    )


def _dedupe_entry_id(
    entry: RepositoryIndexEntry,
    seen_ids: set[str],
) -> RepositoryIndexEntry:
    if entry.entry_id not in seen_ids:
        return entry
    suffix = hashlib.sha1(entry.model_dump_json().encode()).hexdigest()[:8]
    return entry.model_copy(update={"entry_id": f"{entry.entry_id}:{suffix}"})


def _entry_id(kind: RepositoryIndexEntityKind, path: Path, name: str) -> str:
    stable = f"{kind.value}:{path.as_posix()}:{name}"
    digest = hashlib.sha1(stable.encode()).hexdigest()[:10]
    return f"{kind.value}:{digest}"


def _is_test_file(relative: Path) -> bool:
    value = relative.as_posix()
    return "tests/" in value or _TEST_NAME_RE.search(relative.name) is not None


def _language_for_suffix(suffix: str) -> str | None:
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescriptreact",
        ".js": "javascript",
        ".jsx": "javascriptreact",
        ".md": "markdown",
        ".mdx": "markdown",
    }.get(suffix)


def _package_scripts(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except OSError, json.JSONDecodeError:
        return {}
    scripts = data.get("scripts")
    return scripts if isinstance(scripts, dict) else {}


def _package_dependencies(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text())
    except OSError, json.JSONDecodeError:
        return set()
    dependencies: set[str] = set()
    for key in ("dependencies", "devDependencies"):
        value = data.get(key)
        if isinstance(value, dict):
            dependencies.update(str(name) for name in value)
    return dependencies


def _pyproject_commands(path: Path) -> list[str]:
    try:
        data = tomllib.loads(path.read_text())
    except OSError, tomllib.TOMLDecodeError:
        return []
    commands: list[str] = []
    project_scripts = data.get("project", {}).get("scripts", {})
    if isinstance(project_scripts, dict):
        commands.extend(str(name) for name in project_scripts)
    tool_scripts = data.get("tool", {}).get("uv", {}).get("scripts", {})
    if isinstance(tool_scripts, dict):
        commands.extend(str(name) for name in tool_scripts)
    return sorted(dict.fromkeys(commands))


def _pyproject_dependencies(path: Path) -> set[str]:
    try:
        data = tomllib.loads(path.read_text())
    except OSError, tomllib.TOMLDecodeError:
        return set()
    dependencies: set[str] = set()
    project = data.get("project", {})
    value = project.get("dependencies")
    if isinstance(value, list):
        dependencies.update(str(item).split()[0] for item in value)
    optional = project.get("optional-dependencies", {})
    if isinstance(optional, dict):
        for group in optional.values():
            if isinstance(group, list):
                dependencies.update(str(item).split()[0] for item in group)
    return dependencies


def _entry_search_text(entry: RepositoryIndexEntry) -> str:
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
    "RepositoryIndexNotFoundError",
    "build_and_write_repository_index",
    "build_repository_index",
    "get_repository_index_entry",
    "load_repository_index",
    "repository_index_path",
    "search_repository_index",
    "write_repository_index",
]
