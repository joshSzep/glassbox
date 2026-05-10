"""Path hint discovery for repository intelligence layouts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligencePathHint
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types import RepositoryIntelligencePathKind
from glassbox.runtime.repository_index_discovery import BUILD_OUTPUT_NAMES
from glassbox.runtime.repository_index_discovery import CACHE_PATH_NAMES
from glassbox.runtime.repository_index_discovery import classify_repository_path
from glassbox.runtime.repository_index_discovery import (
    is_policy_sensitive_repository_path,
)
from glassbox.runtime.repository_intelligence_layout_common import (
    EXCLUDED_PATH_LIMITATION,
)
from glassbox.runtime.repository_intelligence_layout_common import _provenance
from glassbox.runtime.repository_intelligence_layout_common import _slug


@dataclass(frozen=True)
class RepositoryIntelligencePathDiscovery:
    """Path hint sections derived from packages and repository layout."""

    source_roots: list[RepositoryIntelligencePathHint]
    test_roots: list[RepositoryIntelligencePathHint]
    doc_roots: list[RepositoryIntelligencePathHint]
    generated_paths: list[RepositoryIntelligencePathHint]
    policy_sensitive_paths: list[RepositoryIntelligencePathHint]


def discover_repository_intelligence_paths(
    root: Path,
    packages: list[RepositoryIntelligencePackageBoundary],
) -> RepositoryIntelligencePathDiscovery:
    """Discover source, test, docs, generated, and policy-sensitive path hints."""

    source_roots: list[RepositoryIntelligencePathHint] = []
    test_roots: list[RepositoryIntelligencePathHint] = []
    doc_roots: list[RepositoryIntelligencePathHint] = []
    generated_paths: list[RepositoryIntelligencePathHint] = []

    for package in packages:
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

    generated_paths.extend(_known_generated_and_ignored_hints(root))

    return RepositoryIntelligencePathDiscovery(
        source_roots=source_roots,
        test_roots=test_roots,
        doc_roots=doc_roots,
        generated_paths=generated_paths,
        policy_sensitive_paths=_policy_sensitive_hints(root),
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


__all__ = [
    "RepositoryIntelligencePathDiscovery",
    "discover_repository_intelligence_paths",
]
