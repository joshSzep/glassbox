"""Repository intelligence layout discovery for v2 index snapshots."""

import hashlib
import json
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligencePathHint
from glassbox.core.models import RepositoryIntelligenceSourceManifest
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types import RepositoryIntelligencePackageKind
from glassbox.core.types import RepositoryIntelligencePathKind
from glassbox.runtime.repository_index_discovery import BUILD_OUTPUT_NAMES
from glassbox.runtime.repository_index_discovery import CACHE_PATH_NAMES
from glassbox.runtime.repository_index_discovery import classify_repository_path
from glassbox.runtime.repository_index_discovery import (
    is_policy_sensitive_repository_path,
)

EXCLUDED_PATH_LIMITATION = (
    "Excluded from file crawling; retained as path-level posture only."
)


@dataclass(frozen=True)
class RepositoryIntelligenceLayout:
    """Derived layout sections ready for a repository index snapshot."""

    source_manifests: list[RepositoryIntelligenceSourceManifest]
    source_roots: list[RepositoryIntelligencePathHint]
    test_roots: list[RepositoryIntelligencePathHint]
    doc_roots: list[RepositoryIntelligencePathHint]
    generated_paths: list[RepositoryIntelligencePathHint]
    policy_sensitive_paths: list[RepositoryIntelligencePathHint]
    package_boundaries: list[RepositoryIntelligencePackageBoundary]
    limitations: list[str]


def discover_repository_intelligence_layout(
    root: Path,
    *,
    built_at: datetime,
) -> RepositoryIntelligenceLayout:
    """Derive roots, package boundaries, manifests, and generated path hints."""

    del built_at
    source_manifests: list[RepositoryIntelligenceSourceManifest] = []
    source_roots: list[RepositoryIntelligencePathHint] = []
    test_roots: list[RepositoryIntelligencePathHint] = []
    doc_roots: list[RepositoryIntelligencePathHint] = []
    generated_paths: list[RepositoryIntelligencePathHint] = []
    policy_sensitive_paths: list[RepositoryIntelligencePathHint] = []
    package_boundaries: list[RepositoryIntelligencePackageBoundary] = []

    def add_manifest(path: Path, role: str) -> None:
        if not (root / path).exists():
            return
        source_manifests.append(
            RepositoryIntelligenceSourceManifest(
                manifest_id=f"manifest:{_slug(path)}",
                path=path,
                source_type=RepositoryIndexSourceType.MANIFEST,
                role=role,
                digest=_file_digest(root / path),
                provenance=[_provenance(RepositoryIndexSourceType.MANIFEST, path)],
            )
        )

    pyproject = Path("pyproject.toml")
    if (root / pyproject).exists():
        add_manifest(pyproject, "python project manifest")
        package = _python_package(root, pyproject)
        package_boundaries.append(package)
        source_roots.extend(
            _path_hints(
                package.source_roots, RepositoryIntelligencePathKind.SOURCE_ROOT
            )
        )
        test_roots.extend(
            _path_hints(package.test_roots, RepositoryIntelligencePathKind.TEST_ROOT)
        )
        doc_roots.extend(
            _path_hints(package.doc_roots, RepositoryIntelligencePathKind.DOC_ROOT)
        )
        generated_paths.extend(_generated_hints(package.generated_paths))
        for lockfile in ("uv.lock", "poetry.lock"):
            add_manifest(Path(lockfile), "python lockfile")

    for package_json in sorted(root.rglob("package.json")):
        relative = package_json.relative_to(root)
        if classify_repository_path(relative).excluded:
            continue
        add_manifest(relative, "node package manifest")
        package = _node_package(root, relative)
        package_boundaries.append(package)
        source_roots.extend(
            _path_hints(
                package.source_roots, RepositoryIntelligencePathKind.SOURCE_ROOT
            )
        )
        test_roots.extend(
            _path_hints(package.test_roots, RepositoryIntelligencePathKind.TEST_ROOT)
        )
        generated_paths.extend(_generated_hints(package.generated_paths))
        for lockfile in ("pnpm-lock.yaml", "package-lock.json"):
            add_manifest(relative.parent / lockfile, "node lockfile")

    if (root / "docs").is_dir():
        docs_path = Path("docs")
        doc_roots.append(_path_hint(docs_path, RepositoryIntelligencePathKind.DOC_ROOT))
        package_boundaries.append(
            RepositoryIntelligencePackageBoundary(
                package_id="docs:docs",
                name="docs",
                kind=RepositoryIntelligencePackageKind.DOCS,
                root=docs_path,
                doc_roots=[docs_path],
                confidence=RepositoryIntelligenceConfidence.HIGH,
                provenance=[
                    _provenance(RepositoryIndexSourceType.DOCUMENTATION, docs_path)
                ],
            )
        )

    if (root / "evals").is_dir():
        eval_root = Path("evals")
        package_boundaries.append(
            RepositoryIntelligencePackageBoundary(
                package_id="evals:evals",
                name="evals",
                kind=RepositoryIntelligencePackageKind.EVAL,
                root=eval_root,
                manifest_paths=_existing_paths(
                    root,
                    [
                        "evals/coverage.json",
                        "evals/impact.json",
                        "evals/profiles.json",
                        "evals/recipes.json",
                    ],
                ),
                confidence=RepositoryIntelligenceConfidence.MEDIUM,
                provenance=[_provenance(RepositoryIndexSourceType.EVAL, eval_root)],
            )
        )
        for manifest in (
            "coverage.json",
            "impact.json",
            "profiles.json",
            "recipes.json",
        ):
            add_manifest(eval_root / manifest, "eval metadata")

    generated_paths.extend(_known_generated_and_ignored_hints(root))
    policy_sensitive_paths.extend(_policy_sensitive_hints(root))

    return RepositoryIntelligenceLayout(
        source_manifests=_dedupe_by_id(source_manifests, "manifest_id"),
        source_roots=_dedupe_by_id(source_roots, "hint_id"),
        test_roots=_dedupe_by_id(test_roots, "hint_id"),
        doc_roots=_dedupe_by_id(doc_roots, "hint_id"),
        generated_paths=_dedupe_by_id(generated_paths, "hint_id"),
        policy_sensitive_paths=_dedupe_by_id(policy_sensitive_paths, "hint_id"),
        package_boundaries=_dedupe_by_id(package_boundaries, "package_id"),
        limitations=[],
    )


def _python_package(
    root: Path, pyproject: Path
) -> RepositoryIntelligencePackageBoundary:
    data = _read_toml(root / pyproject)
    project = data.get("project", {})
    if not isinstance(project, dict):
        project = {}
    name = str(project.get("name") or root.name)
    source_candidates = ["src", name.replace("-", "_"), f"src/{name.replace('-', '_')}"]
    generated = _existing_paths(root, ["src/glassbox/web/static_next"])
    return RepositoryIntelligencePackageBoundary(
        package_id=f"package:{name}",
        name=name,
        kind=RepositoryIntelligencePackageKind.PYTHON,
        root=Path("."),
        manifest_paths=[pyproject],
        source_roots=_existing_paths(root, source_candidates) or [Path(".")],
        test_roots=_existing_paths(root, ["tests"]),
        doc_roots=_existing_paths(root, ["docs"]),
        generated_paths=generated,
        confidence=RepositoryIntelligenceConfidence.HIGH,
        provenance=[_provenance(RepositoryIndexSourceType.MANIFEST, pyproject)],
    )


def _node_package(
    root: Path,
    package_json: Path,
) -> RepositoryIntelligencePackageBoundary:
    data = _read_json(root / package_json)
    component_root = package_json.parent
    name = str(data.get("name") or component_root.name or root.name)
    source_roots = _existing_paths(
        root,
        [
            component_root / "app",
            component_root / "components",
            component_root / "src",
            component_root / "stores",
        ],
    )
    test_roots = _existing_paths(
        root,
        [component_root / "tests", component_root / "e2e"],
    )
    generated = _existing_paths(
        root,
        [
            component_root / "generated",
            component_root / "out",
            component_root / ".next",
            component_root / "dist",
            component_root / "build",
        ],
    )
    return RepositoryIntelligencePackageBoundary(
        package_id=f"app:{name}",
        name=name,
        kind=RepositoryIntelligencePackageKind.FRONTEND,
        root=component_root,
        manifest_paths=[package_json],
        source_roots=source_roots or [component_root],
        test_roots=test_roots,
        generated_paths=generated,
        confidence=RepositoryIntelligenceConfidence.HIGH,
        provenance=[_provenance(RepositoryIndexSourceType.MANIFEST, package_json)],
    )


def _known_generated_and_ignored_hints(
    root: Path,
) -> list[RepositoryIntelligencePathHint]:
    hints: list[RepositoryIntelligencePathHint] = []
    known_paths: set[Path] = set()
    candidates = [
        "frontend/generated",
        "frontend/out",
        "frontend/.next",
        "src/glassbox/web/static_next",
        "dist",
        "build",
        "coverage",
    ]
    for package_json in sorted(root.rglob("package.json")):
        relative = package_json.relative_to(root)
        if classify_repository_path(relative).excluded:
            continue
        for name in [*BUILD_OUTPUT_NAMES, *CACHE_PATH_NAMES, "generated"]:
            candidates.append((relative.parent / name).as_posix())
    for candidate in candidates:
        relative = Path(candidate)
        if relative in known_paths or not (root / relative).exists():
            continue
        classification = classify_repository_path(relative)
        if not (
            classification.generated
            or classification.cache
            or classification.build_output
        ):
            continue
        known_paths.add(relative)
        hints.append(
            _path_hint(
                relative,
                _generated_kind(classification),
                confidence=RepositoryIntelligenceConfidence.HIGH,
                limitations=(
                    [EXCLUDED_PATH_LIMITATION] if classification.excluded else []
                ),
            )
        )
    return hints


def _policy_sensitive_hints(root: Path) -> list[RepositoryIntelligencePathHint]:
    candidates = [
        ".github",
        "docs/tool-policy",
        "scripts",
        "src/glassbox/tools/policy.py",
        "src/glassbox/tools/policy_config.py",
    ]
    hints: list[RepositoryIntelligencePathHint] = []
    for candidate in candidates:
        relative = Path(candidate)
        if (root / relative).exists() and is_policy_sensitive_repository_path(relative):
            hints.append(
                _path_hint(
                    relative,
                    RepositoryIntelligencePathKind.POLICY_SENSITIVE_PATH,
                    confidence=RepositoryIntelligenceConfidence.MEDIUM,
                )
            )
    for docs_task in sorted((root / "docs").glob("tasks-v*.md"))[:20]:
        relative = docs_task.relative_to(root)
        hints.append(
            _path_hint(
                relative,
                RepositoryIntelligencePathKind.POLICY_SENSITIVE_PATH,
                confidence=RepositoryIntelligenceConfidence.MEDIUM,
            )
        )
    return hints


def _path_hints(
    paths: list[Path],
    kind: RepositoryIntelligencePathKind,
) -> list[RepositoryIntelligencePathHint]:
    return [_path_hint(path, kind) for path in paths]


def _generated_hints(paths: list[Path]) -> list[RepositoryIntelligencePathHint]:
    hints: list[RepositoryIntelligencePathHint] = []
    for path in paths:
        classification = classify_repository_path(path)
        hints.append(
            _path_hint(
                path,
                _generated_kind(classification),
                confidence=RepositoryIntelligenceConfidence.HIGH,
                limitations=(
                    [EXCLUDED_PATH_LIMITATION] if classification.excluded else []
                ),
            )
        )
    return hints


def _generated_kind(classification: Any) -> RepositoryIntelligencePathKind:
    if classification.cache:
        return RepositoryIntelligencePathKind.CACHE_PATH
    if classification.build_output:
        return RepositoryIntelligencePathKind.BUILD_OUTPUT
    return RepositoryIntelligencePathKind.GENERATED_PATH


def _path_hint(
    path: Path,
    kind: RepositoryIntelligencePathKind,
    *,
    confidence: RepositoryIntelligenceConfidence = (
        RepositoryIntelligenceConfidence.HIGH
    ),
    limitations: list[str] | None = None,
) -> RepositoryIntelligencePathHint:
    source_type = (
        RepositoryIndexSourceType.DOCUMENTATION
        if kind == RepositoryIntelligencePathKind.DOC_ROOT
        else RepositoryIndexSourceType.FILE_SYSTEM
    )
    return RepositoryIntelligencePathHint(
        hint_id=f"{kind.value}:{_slug(path)}",
        kind=kind,
        path=path,
        confidence=confidence,
        provenance=[_provenance(source_type, path)],
        limitations=limitations or [],
    )


def _existing_paths(root: Path, candidates: Sequence[str | Path]) -> list[Path]:
    paths: list[Path] = []
    for candidate in candidates:
        relative = Path(candidate)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        if (root / relative).exists():
            paths.append(relative)
    return paths


def _provenance(
    source_type: RepositoryIndexSourceType,
    path: Path,
) -> RepositoryIndexProvenance:
    return RepositoryIndexProvenance(source_type=source_type, path=path)


def _file_digest(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return hashlib.sha256(data).hexdigest()


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError:
        return {}
    except tomllib.TOMLDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _dedupe_by_id[T](items: list[T], field_name: str) -> list[T]:
    seen: set[str] = set()
    deduped: list[T] = []
    for item in items:
        value = str(getattr(item, field_name))
        if value in seen:
            continue
        seen.add(value)
        deduped.append(item)
    return deduped


def _slug(path: Path) -> str:
    value = path.as_posix()
    if value in {"", "."}:
        return "root"
    return value.replace("/", ":")


__all__ = [
    "RepositoryIntelligenceLayout",
    "discover_repository_intelligence_layout",
]
