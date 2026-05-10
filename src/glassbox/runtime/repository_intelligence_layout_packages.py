"""Package and manifest discovery for repository intelligence layouts."""

from dataclasses import dataclass
from pathlib import Path

from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligenceSourceManifest
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types import RepositoryIntelligencePackageKind
from glassbox.runtime.repository_index_discovery import classify_repository_path
from glassbox.runtime.repository_intelligence_layout_common import _existing_paths
from glassbox.runtime.repository_intelligence_layout_common import _file_digest
from glassbox.runtime.repository_intelligence_layout_common import _provenance
from glassbox.runtime.repository_intelligence_layout_common import _read_json
from glassbox.runtime.repository_intelligence_layout_common import _read_toml
from glassbox.runtime.repository_intelligence_layout_common import _slug


@dataclass(frozen=True)
class RepositoryIntelligencePackageDiscovery:
    """Manifest and package-boundary sections derived from repository layout."""

    source_manifests: list[RepositoryIntelligenceSourceManifest]
    package_boundaries: list[RepositoryIntelligencePackageBoundary]


def discover_repository_intelligence_packages(
    root: Path,
) -> RepositoryIntelligencePackageDiscovery:
    """Discover repository manifests and package boundaries."""

    source_manifests: list[RepositoryIntelligenceSourceManifest] = []
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
        package_boundaries.append(_python_package(root, pyproject))
        for lockfile in ("uv.lock", "poetry.lock"):
            add_manifest(Path(lockfile), "python lockfile")

    for package_json in sorted(root.rglob("package.json")):
        relative = package_json.relative_to(root)
        if classify_repository_path(relative).excluded:
            continue
        add_manifest(relative, "node package manifest")
        package_boundaries.append(_node_package(root, relative))
        for lockfile in ("pnpm-lock.yaml", "package-lock.json"):
            add_manifest(relative.parent / lockfile, "node lockfile")

    if (root / "docs").is_dir():
        docs_path = Path("docs")
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

    return RepositoryIntelligencePackageDiscovery(
        source_manifests=source_manifests,
        package_boundaries=package_boundaries,
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


__all__ = [
    "RepositoryIntelligencePackageDiscovery",
    "discover_repository_intelligence_packages",
]
