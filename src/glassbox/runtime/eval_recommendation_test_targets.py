"""Likely test-target discovery for eval recommendations."""

from pathlib import Path

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.core.types import RepositoryIntelligencePackageKind
from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_models import EvalTestTargetConfidence
from glassbox.runtime.eval_recommendation_models import EvalTestTargetRecommendation
from glassbox.runtime.eval_recommendation_models import EvalTestTargetSource
from glassbox.runtime.eval_recommendation_models import PathVerificationFreshness
from glassbox.runtime.repository_index_persistence import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index_persistence import load_repository_index
from glassbox.runtime.workspace_topology import WorkspaceTopologyComponent
from glassbox.runtime.workspace_topology import WorkspaceTopologyNotFoundError
from glassbox.runtime.workspace_topology import load_workspace_topology


def build_test_target_recommendations(
    *,
    workspace_root: Path,
    normalized_paths: list[str],
) -> tuple[list[EvalTestTargetRecommendation], list[str]]:
    """Build likely test targets from repository intelligence and topology."""

    recommendations: list[EvalTestTargetRecommendation] = []
    warnings: list[str] = []

    repository_targets, repository_warnings = _repository_index_test_targets(
        workspace_root=workspace_root,
        normalized_paths=normalized_paths,
    )
    recommendations.extend(repository_targets)
    warnings.extend(repository_warnings)

    topology_targets, topology_warnings = _topology_test_targets(
        workspace_root=workspace_root,
        normalized_paths=normalized_paths,
    )
    recommendations.extend(topology_targets)
    warnings.extend(topology_warnings)

    return _dedupe_recommendations(recommendations), dedupe_strings(warnings)


def _repository_index_test_targets(
    *,
    workspace_root: Path,
    normalized_paths: list[str],
) -> tuple[list[EvalTestTargetRecommendation], list[str]]:
    try:
        snapshot = load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError:
        return [], []
    except ValueError as exc:
        return [], [f"Repository intelligence snapshot could not be read: {exc}"]

    if snapshot.status == RepositoryIndexFreshness.FAILED:
        reason = snapshot.failure_reason or "unknown failure"
        return [], [f"Repository intelligence snapshot is failed; reason: {reason}."]

    warnings: list[str] = []
    freshness: PathVerificationFreshness = "fresh"
    if snapshot.status == RepositoryIndexFreshness.STALE:
        freshness = "stale"
        warnings.append(
            "Repository intelligence snapshot is stale; test target guidance is "
            "degraded until `glassbox repo index build --cwd .` is rerun."
        )

    recommendations: list[EvalTestTargetRecommendation] = []
    for path in normalized_paths:
        matched_packages = _packages_for_path(snapshot, path)
        if _snapshot_generated_path(snapshot, path):
            warnings.append(
                f"Changed path `{path}` is generated; inspect the source generator "
                "before trusting generated-file test target guidance."
            )
            continue
        if _is_docs_path(path):
            recommendations.append(_docs_guardrail(path, freshness=freshness))
        for package in matched_packages:
            package_recommendations, package_warnings = (
                _package_test_targets_from_index(
                    workspace_root=workspace_root,
                    package=package,
                    path=path,
                    freshness=freshness,
                )
            )
            recommendations.extend(package_recommendations)
            warnings.extend(package_warnings)
    return recommendations, warnings


def _topology_test_targets(
    *,
    workspace_root: Path,
    normalized_paths: list[str],
) -> tuple[list[EvalTestTargetRecommendation], list[str]]:
    try:
        topology = load_workspace_topology(workspace_root)
    except WorkspaceTopologyNotFoundError:
        return [], []
    except ValueError as exc:
        return [], [f"Workspace topology could not be read: {exc}"]

    if topology.recommendation_posture == "unavailable":
        return [], []

    freshness: PathVerificationFreshness = "fresh"
    warnings: list[str] = []
    if topology.recommendation_posture == "degraded":
        freshness = "stale"
        warnings.append(
            "Workspace topology is stale; topology-derived test target guidance "
            "is degraded until `glassbox repo topology build --cwd .` is rerun."
        )

    recommendations: list[EvalTestTargetRecommendation] = []
    for component in topology.components:
        matched_paths = [
            path
            for path in normalized_paths
            if _component_contains_path(component, Path(path))
        ]
        if not matched_paths:
            continue
        for path in matched_paths:
            recommendations.extend(
                _component_test_targets(
                    workspace_root=workspace_root,
                    component=component,
                    path=path,
                    freshness=freshness,
                )
            )
    return recommendations, warnings


def _package_test_targets_from_index(
    *,
    workspace_root: Path,
    package: RepositoryIntelligencePackageBoundary,
    path: str,
    freshness: PathVerificationFreshness,
) -> tuple[list[EvalTestTargetRecommendation], list[str]]:
    if _path_in_roots(Path(path), package.generated_paths):
        return [], [
            f"Changed path `{path}` is generated by package `{package.package_id}`; "
            "test target guidance is degraded until the source path is inspected."
        ]

    if not package.test_roots:
        return [], [
            f"Repository intelligence found no test roots for package "
            f"`{package.package_id}`; no package-derived test target was emitted."
        ]

    if _path_in_roots(Path(path), package.test_roots):
        return [
            _test_target(
                target_id=f"test-direct:{path}",
                title=f"Changed test {path}",
                confidence="direct",
                source="repository-intelligence",
                freshness=freshness,
                matched_paths=[path],
                target_paths=[path],
                package_ids=[package.package_id],
                command=_test_command(package.kind, package.root, [path]),
                reasons=["Changed path is already inside a discovered test root."],
            )
        ], []

    related_tests = _related_tests(
        workspace_root=workspace_root,
        test_roots=package.test_roots,
        path=path,
    )
    if related_tests:
        return [
            _test_target(
                target_id=f"test-naming:{','.join(related_tests)}",
                title=f"Likely tests for {path}",
                confidence="naming-derived",
                source="repository-intelligence",
                freshness=freshness,
                matched_paths=[path],
                target_paths=related_tests,
                package_ids=[package.package_id],
                command=_test_command(package.kind, package.root, related_tests),
                reasons=[
                    "Repository intelligence matched source and test roots, "
                    "then found test files by naming convention."
                ],
            )
        ], []

    roots = [root.as_posix() for root in package.test_roots]
    return [
        _test_target(
            target_id=f"test-package:{package.package_id}",
            title=f"Package tests for {package.name}",
            confidence="package-derived",
            source="repository-intelligence",
            freshness=freshness,
            matched_paths=[path],
            target_paths=roots,
            package_ids=[package.package_id],
            command=_test_command(package.kind, package.root, roots),
            reasons=[
                "Repository intelligence matched the changed path to a package "
                "with discovered test roots."
            ],
            limitations=[
                "No naming-derived test file was found; package test roots are "
                "fallback guidance."
            ],
        )
    ], []


def _component_test_targets(
    *,
    workspace_root: Path,
    component: WorkspaceTopologyComponent,
    path: str,
    freshness: PathVerificationFreshness,
) -> list[EvalTestTargetRecommendation]:
    if not component.test_roots and component.kind != "docs":
        return []
    if component.kind == "docs":
        return [
            _docs_guardrail(
                path, freshness=freshness, component_ids=[component.component_id]
            )
        ]
    if _path_in_roots(Path(path), component.test_roots):
        return [
            _test_target(
                target_id=f"test-topology-direct:{path}",
                title=f"Changed test {path}",
                confidence="topology-derived",
                source="topology",
                freshness=freshness,
                matched_paths=[path],
                target_paths=[path],
                component_ids=[component.component_id],
                command=_component_test_command(component, [path]),
                reasons=["Workspace topology matched the changed path to a test root."],
            )
        ]
    related_tests = _related_tests(
        workspace_root=workspace_root,
        test_roots=component.test_roots,
        path=path,
    )
    if related_tests:
        return [
            _test_target(
                target_id=f"test-topology-naming:{','.join(related_tests)}",
                title=f"Topology tests for {path}",
                confidence="topology-derived",
                source="topology",
                freshness=freshness,
                matched_paths=[path],
                target_paths=related_tests,
                component_ids=[component.component_id],
                command=_component_test_command(component, related_tests),
                reasons=[
                    "Workspace topology matched source and test roots, then "
                    "naming convention found likely tests."
                ],
            )
        ]
    roots = [root.as_posix() for root in component.test_roots]
    return [
        _test_target(
            target_id=f"test-topology-component:{component.component_id}",
            title=f"Topology tests for {component.name}",
            confidence="topology-derived",
            source="topology",
            freshness=freshness,
            matched_paths=[path],
            target_paths=roots,
            component_ids=[component.component_id],
            command=_component_test_command(component, roots),
            reasons=["Workspace topology matched the changed path to a component."],
            limitations=[
                "No naming-derived test file was found; component test roots are "
                "fallback guidance."
            ],
        )
    ]


def _test_target(
    *,
    target_id: str,
    title: str,
    confidence: EvalTestTargetConfidence,
    source: EvalTestTargetSource,
    freshness: PathVerificationFreshness,
    matched_paths: list[str],
    target_paths: list[str],
    command: str | None,
    reasons: list[str],
    component_ids: list[str] | None = None,
    package_ids: list[str] | None = None,
    limitations: list[str] | None = None,
) -> EvalTestTargetRecommendation:
    return EvalTestTargetRecommendation(
        target_id=target_id,
        title=title,
        confidence=confidence,
        source=source,
        freshness=freshness,
        matched_paths=dedupe_strings(matched_paths),
        target_paths=dedupe_strings(target_paths),
        component_ids=dedupe_strings(component_ids or []),
        package_ids=dedupe_strings(package_ids or []),
        command=command,
        reasons=dedupe_strings(reasons),
        limitations=dedupe_strings(limitations or []),
    )


def _docs_guardrail(
    path: str,
    *,
    freshness: PathVerificationFreshness,
    component_ids: list[str] | None = None,
) -> EvalTestTargetRecommendation:
    return _test_target(
        target_id="test-docs:release-candidate-docs",
        title="Documentation guardrail tests",
        confidence="fallback",
        source="fallback",
        freshness=freshness,
        matched_paths=[path],
        target_paths=["tests/unit/test_release_candidate_docs.py"],
        component_ids=component_ids,
        command="uv run pytest tests/unit/test_release_candidate_docs.py -q",
        reasons=[
            "Changed path is documentation, so the docs guardrail is the cheapest "
            "repository-owned test target."
        ],
    )


def _packages_for_path(
    snapshot: RepositoryIndexSnapshot,
    path: str,
) -> list[RepositoryIntelligencePackageBoundary]:
    relative = Path(path)
    packages = [
        package
        for package in snapshot.package_boundaries
        if _package_contains_path(package, relative)
    ]
    if any(package.root != Path(".") for package in packages):
        packages = [package for package in packages if package.root != Path(".")]
    packages.sort(key=lambda package: (len(package.root.parts), package.package_id))
    return packages


def _package_contains_path(
    package: RepositoryIntelligencePackageBoundary,
    path: Path,
) -> bool:
    roots = [
        package.root,
        *package.source_roots,
        *package.test_roots,
        *package.doc_roots,
        *package.generated_paths,
        *package.manifest_paths,
    ]
    return any(_path_contains(root, path) for root in roots)


def _snapshot_generated_path(snapshot: RepositoryIndexSnapshot, path: str) -> bool:
    relative = Path(path)
    return any(_path_contains(hint.path, relative) for hint in snapshot.generated_paths)


def _component_contains_path(
    component: WorkspaceTopologyComponent,
    path: Path,
) -> bool:
    roots = [
        component.root_path,
        *component.source_roots,
        *component.test_roots,
        *component.docs_roots,
        *component.generated_output_roots,
    ]
    return any(_path_contains(root, path) for root in roots)


def _related_tests(
    *,
    workspace_root: Path,
    test_roots: list[Path],
    path: str,
) -> list[str]:
    relative = Path(path)
    if _path_in_roots(relative, test_roots):
        return [path]
    candidate_names = _candidate_test_names(relative)
    related: list[str] = []
    for root in test_roots:
        absolute_root = workspace_root / root
        if not absolute_root.exists():
            continue
        for candidate_name in candidate_names:
            for candidate in sorted(absolute_root.rglob(candidate_name)):
                related.append(candidate.relative_to(workspace_root).as_posix())
    return dedupe_strings(related)


def _candidate_test_names(path: Path) -> list[str]:
    suffixes = "".join(path.suffixes)
    stem = path.name.removesuffix(suffixes) if suffixes else path.stem
    if suffixes == ".py":
        return [f"test_{stem}.py", f"{stem}_test.py"]
    if suffixes in {".ts", ".tsx", ".js", ".jsx"}:
        return [
            f"{stem}.test{suffixes}",
            f"{stem}.spec{suffixes}",
            f"{stem}.test.ts",
            f"{stem}.spec.ts",
        ]
    return [f"test_{path.stem}{path.suffix}"] if path.suffix else []


def _test_command(
    kind: RepositoryIntelligencePackageKind,
    root: Path,
    targets: list[str],
) -> str | None:
    if kind == RepositoryIntelligencePackageKind.PYTHON:
        return "uv run pytest " + " ".join(targets) + " -q"
    if kind in {
        RepositoryIntelligencePackageKind.FRONTEND,
        RepositoryIntelligencePackageKind.NODE_WORKSPACE,
    }:
        prefix = (
            "pnpm test" if root == Path(".") else f"pnpm --dir {root.as_posix()} test"
        )
        if targets:
            return prefix + " -- " + " ".join(targets)
        return prefix
    return None


def _component_test_command(
    component: WorkspaceTopologyComponent,
    targets: list[str],
) -> str | None:
    if component.ecosystem == "python":
        return "uv run pytest " + " ".join(targets) + " -q"
    if component.ecosystem == "node":
        root = component.root_path.as_posix()
        manager = component.package_manager or "pnpm"
        if manager == "pnpm":
            prefix = "pnpm test" if root == "." else f"pnpm --dir {root} test"
        else:
            prefix = "npm test" if root == "." else f"npm --prefix {root} test"
        return prefix + (" -- " + " ".join(targets) if targets else "")
    return None


def _path_in_roots(path: Path, roots: list[Path]) -> bool:
    return any(_path_contains(root, path) for root in roots)


def _path_contains(root: Path, path: Path) -> bool:
    if root == Path("."):
        return True
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_docs_path(path: str) -> bool:
    return path.startswith("docs/") and path.endswith(".md")


def _dedupe_recommendations(
    recommendations: list[EvalTestTargetRecommendation],
) -> list[EvalTestTargetRecommendation]:
    by_key: dict[
        tuple[str, tuple[str, ...], str | None], EvalTestTargetRecommendation
    ] = {}
    for recommendation in recommendations:
        key = (
            recommendation.target_id,
            tuple(recommendation.target_paths),
            recommendation.command,
        )
        if key not in by_key:
            by_key[key] = recommendation
    return sorted(
        by_key.values(),
        key=lambda recommendation: (
            recommendation.confidence,
            recommendation.target_id,
            recommendation.command or "",
        ),
    )


__all__ = ["build_test_target_recommendations"]
