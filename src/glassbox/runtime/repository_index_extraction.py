"""Repository index entry extraction helpers."""

import hashlib
import json
import re
import tomllib
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import TypedDict

from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceMemoryReference
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligencePathHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSourceManifest
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.types import RepositoryIndexEntityKind
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types import WorkspaceMemoryState
from glassbox.runtime.repository_intelligence_layout import (
    discover_repository_intelligence_layout,
)


class RepositoryIntelligenceLayoutFields(TypedDict):
    """Keyword fields from layout discovery accepted by RepositoryIndexSnapshot."""

    source_manifests: list[RepositoryIntelligenceSourceManifest]
    source_roots: list[RepositoryIntelligencePathHint]
    test_roots: list[RepositoryIntelligencePathHint]
    doc_roots: list[RepositoryIntelligencePathHint]
    generated_paths: list[RepositoryIntelligencePathHint]
    policy_sensitive_paths: list[RepositoryIntelligencePathHint]
    package_boundaries: list[RepositoryIntelligencePackageBoundary]
    command_recipes: list[RepositoryIntelligenceCommandRecipe]
    ownership_hints: list[RepositoryIntelligenceOwnershipHint]
    subsystems: list[RepositoryIntelligenceSubsystem]
    release_sensitive_surfaces: list[RepositoryIntelligenceReleaseSurface]
    memory_references: list[RepositoryIntelligenceMemoryReference]
    limitations: list[str]


PROJECT_MARKERS = {
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
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
DOC_SUFFIXES = {".md", ".mdx", ".rst"}

_TEST_NAME_RE = re.compile(r"(^test_|_test\.|\.test\.|\.spec\.)")
_PY_SYMBOL_RE = re.compile(r"^(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")
_TS_SYMBOL_RE = re.compile(
    r"^(?:export\s+)?(?:async\s+)?(?:function|class|const|let)\s+([A-Za-z_$][A-Za-z0-9_$]*)"
)


def file_entries(
    *,
    root: Path,
    path: Path,
    updated_at: datetime,
) -> list[RepositoryIndexEntry]:
    relative = path.relative_to(root)
    entries: list[RepositoryIndexEntry] = []
    if path.name in PROJECT_MARKERS:
        entries.append(_project_marker_entry(relative, updated_at))
    if relative.parts and relative.parts[0] == "docs" and path.suffix in DOC_SUFFIXES:
        entries.append(_doc_entry(relative, updated_at))
    if relative.parts and relative.parts[0] == "evals":
        entries.append(_eval_entry(relative, updated_at))
    if path.suffix in SOURCE_SUFFIXES:
        entries.append(_file_entry(relative, updated_at))
        module_entry = _module_entry(relative, updated_at)
        if module_entry is not None:
            entries.append(module_entry)
        entries.extend(_symbol_entries(path, relative, updated_at))
    if is_test_file(relative):
        entries.append(_test_entry(relative, updated_at))
    return entries


def command_entries(root: Path, updated_at: datetime) -> list[RepositoryIndexEntry]:
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


def dependency_entries(root: Path, updated_at: datetime) -> list[RepositoryIndexEntry]:
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


def repository_intelligence_layout_fields(
    root: Path,
    *,
    built_at: datetime,
) -> RepositoryIntelligenceLayoutFields:
    """Return v2 layout fields for the repository index snapshot facade."""

    layout = discover_repository_intelligence_layout(root, built_at=built_at)
    return {
        "source_manifests": layout.source_manifests,
        "source_roots": layout.source_roots,
        "test_roots": layout.test_roots,
        "doc_roots": layout.doc_roots,
        "generated_paths": layout.generated_paths,
        "policy_sensitive_paths": layout.policy_sensitive_paths,
        "package_boundaries": layout.package_boundaries,
        "command_recipes": layout.command_recipes,
        "ownership_hints": layout.ownership_hints,
        "subsystems": layout.subsystems,
        "release_sensitive_surfaces": layout.release_sensitive_surfaces,
        "memory_references": [],
        "limitations": layout.limitations,
    }


def memory_reference_entries(
    entries: Sequence[WorkspaceMemoryEntry],
) -> list[RepositoryIntelligenceMemoryReference]:
    """Convert confirmed active workspace memory into repository intelligence refs."""

    references: list[RepositoryIntelligenceMemoryReference] = []
    for entry in entries:
        if entry.state != WorkspaceMemoryState.ACTIVE or entry.confirmed_at is None:
            continue
        references.append(
            RepositoryIntelligenceMemoryReference(
                reference_id=f"memory:{entry.memory_id}",
                memory_id=entry.memory_id,
                kind=entry.kind,
                summary=entry.summary or entry.content[:160],
                source_label=entry.provenance.source_label,
                confirmed_by=entry.confirmed_by,
                confirmed_at=entry.confirmed_at,
                tags=list(entry.tags),
                redacted=entry.redacted,
                confidence=RepositoryIntelligenceConfidence.MEDIUM,
                provenance=entry.provenance,
                limitations=[
                    "Memory-derived intelligence is advisory and does not "
                    "override current repository source metadata."
                ],
            )
        )
    return references


def dedupe_entry_id(
    entry: RepositoryIndexEntry,
    seen_ids: set[str],
) -> RepositoryIndexEntry:
    if entry.entry_id not in seen_ids:
        return entry
    suffix = hashlib.sha1(entry.model_dump_json().encode()).hexdigest()[:8]
    return entry.model_copy(update={"entry_id": f"{entry.entry_id}:{suffix}"})


def is_test_file(relative: Path) -> bool:
    value = relative.as_posix()
    return "tests/" in value or _TEST_NAME_RE.search(relative.name) is not None


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
    if len(relative.parts) < 2 or relative.suffix not in SOURCE_SUFFIXES:
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


def _entry_id(kind: RepositoryIndexEntityKind, path: Path, name: str) -> str:
    stable = f"{kind.value}:{path.as_posix()}:{name}"
    digest = hashlib.sha1(stable.encode()).hexdigest()[:10]
    return f"{kind.value}:{digest}"


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


__all__ = [
    "DOC_SUFFIXES",
    "PROJECT_MARKERS",
    "SOURCE_SUFFIXES",
    "command_entries",
    "dedupe_entry_id",
    "dependency_entries",
    "file_entries",
    "repository_intelligence_layout_fields",
]
