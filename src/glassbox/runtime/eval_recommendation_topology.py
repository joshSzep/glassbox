"""Topology-derived verification guidance for changed paths."""

import re
from pathlib import Path

from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_models import (
    EvalVerificationRecipeRecommendation,
)
from glassbox.runtime.workspace_topology import WorkspaceTopologyComponent
from glassbox.runtime.workspace_topology import WorkspaceTopologyNotFoundError
from glassbox.runtime.workspace_topology import WorkspaceTopologySnapshot
from glassbox.runtime.workspace_topology import load_workspace_topology


def build_topology_recipe_recommendations(
    *,
    workspace_root: Path,
    normalized_paths: list[str],
) -> tuple[list[EvalVerificationRecipeRecommendation], list[str]]:
    """Build advisory verification recipes from a workspace topology snapshot."""

    try:
        topology = load_workspace_topology(workspace_root)
    except WorkspaceTopologyNotFoundError:
        return [], []
    except ValueError as exc:
        return [], [f"Workspace topology could not be read: {exc}"]

    if topology.recommendation_posture == "unavailable":
        reason = topology.failure_reason or topology.freshness
        return [], [f"Workspace topology is unavailable; reason: {reason}."]

    warnings: list[str] = []
    if topology.recommendation_posture == "degraded":
        warnings.append(
            "Workspace topology is stale; topology-derived verification guidance "
            "is degraded until `glassbox repo topology build --cwd .` is rerun."
        )

    recommendations: list[EvalVerificationRecipeRecommendation] = []
    for component, matched_paths in _matched_components(topology, normalized_paths):
        recommendation = _recommendation_for_component(
            workspace_root=workspace_root,
            topology=topology,
            component=component,
            matched_paths=matched_paths,
        )
        if recommendation is not None:
            recommendations.append(recommendation)

    recommendations.sort(key=lambda item: item.recipe_id)
    return recommendations, warnings


def _matched_components(
    topology: WorkspaceTopologySnapshot,
    normalized_paths: list[str],
) -> list[tuple[WorkspaceTopologyComponent, list[str]]]:
    matches: list[tuple[WorkspaceTopologyComponent, list[str]]] = []
    for component in topology.components:
        component_paths = [
            path
            for path in normalized_paths
            if _component_contains_path(component, Path(path))
        ]
        if component_paths:
            matches.append((component, component_paths))
    return matches


def _component_contains_path(
    component: WorkspaceTopologyComponent,
    path: Path,
) -> bool:
    roots = [
        *component.source_roots,
        *component.test_roots,
        *component.docs_roots,
        *component.generated_output_roots,
    ]
    if not roots:
        roots = [component.root_path]
    if path in {manifest.path for manifest in component.manifests}:
        return True
    if path in {lockfile.path for lockfile in component.lockfiles}:
        return True
    return any(_path_contains(root, path) for root in roots)


def _recommendation_for_component(
    *,
    workspace_root: Path,
    topology: WorkspaceTopologySnapshot,
    component: WorkspaceTopologyComponent,
    matched_paths: list[str],
) -> EvalVerificationRecipeRecommendation | None:
    commands: list[str] = []
    limitations: list[str] = []
    title = f"Topology checks for {component.name}"

    if component.kind == "docs":
        commands.append("uv run pytest tests/unit/test_release_candidate_docs.py -q")
    elif component.ecosystem == "node":
        commands.extend(_node_commands(component))
    elif component.ecosystem == "python":
        commands.extend(
            _python_commands(
                workspace_root=workspace_root,
                component=component,
                matched_paths=matched_paths,
                limitations=limitations,
            )
        )

    if not commands:
        return None

    if topology.recommendation_posture == "degraded":
        limitations.append("Topology inputs changed after this snapshot was built.")

    confidence = (
        "topology" if topology.recommendation_posture == "fresh" else "degraded"
    )
    notes = (
        f"Derived from {topology.freshness} workspace topology for "
        f"{component.kind} component `{component.name}`."
    )
    return EvalVerificationRecipeRecommendation(
        recipe_id=f"topology-{_slug(component.component_id)}",
        title=title,
        confidence=confidence,
        source="topology",
        matched_paths=matched_paths,
        component_ids=[component.component_id],
        commands=dedupe_strings(commands),
        notes=notes,
        limitations=dedupe_strings(limitations),
    )


def _node_commands(component: WorkspaceTopologyComponent) -> list[str]:
    package_root = component.root_path.as_posix()
    manager = component.package_manager or "npm"
    if manager == "pnpm":
        return [
            f"pnpm --dir {package_root} lint",
            f"pnpm --dir {package_root} typecheck",
            f"pnpm --dir {package_root} test",
            f"pnpm --dir {package_root} build",
        ]
    if package_root == ".":
        return [
            "npm run lint",
            "npm run typecheck",
            "npm test",
            "npm run build",
        ]
    return [
        f"npm --prefix {package_root} run lint",
        f"npm --prefix {package_root} run typecheck",
        f"npm --prefix {package_root} test",
        f"npm --prefix {package_root} run build",
    ]


def _python_commands(
    *,
    workspace_root: Path,
    component: WorkspaceTopologyComponent,
    matched_paths: list[str],
    limitations: list[str],
) -> list[str]:
    commands: list[str] = []
    lint_targets = [
        path
        for path in matched_paths
        if path.endswith(".py") and not _path_in_roots(Path(path), component.test_roots)
    ]
    if lint_targets:
        commands.append("uv run ruff check " + " ".join(lint_targets))
        commands.append("uv run ty check " + " ".join(lint_targets))

    matched_test_paths = [
        path
        for path in matched_paths
        if _path_in_roots(Path(path), component.test_roots)
    ]
    related_tests = _related_python_tests(workspace_root, component, matched_paths)
    if matched_test_paths:
        commands.append("uv run pytest " + " ".join(matched_test_paths) + " -q")
    elif related_tests:
        commands.append("uv run pytest " + " ".join(related_tests) + " -q")
    elif component.test_roots:
        roots = " ".join(root.as_posix() for root in component.test_roots)
        commands.append(f"uv run pytest {roots} -q")
        limitations.append(
            "No direct test target was found for the changed source path; "
            "recommended test roots are component-level fallback guidance."
        )
    return commands


def _related_python_tests(
    workspace_root: Path,
    component: WorkspaceTopologyComponent,
    matched_paths: list[str],
) -> list[str]:
    related: list[str] = []
    for matched_path in matched_paths:
        path = Path(matched_path)
        if not matched_path.endswith(".py"):
            continue
        if _path_in_roots(path, component.test_roots):
            continue
        test_name = f"test_{path.stem}.py"
        for root in component.test_roots:
            for candidate in sorted((workspace_root / root).rglob(test_name)):
                related.append(
                    candidate.relative_to(workspace_root).as_posix(),
                )
    return dedupe_strings(related)


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


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "component"


__all__ = ["build_topology_recipe_recommendations"]
