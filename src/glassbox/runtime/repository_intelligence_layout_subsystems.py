"""Subsystem discovery for repository intelligence layouts."""

from pathlib import Path

from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.runtime.repository_intelligence_layout_common import _existing_paths
from glassbox.runtime.repository_intelligence_layout_common import _provenance


def discover_repository_intelligence_subsystems(
    root: Path,
    packages: list[RepositoryIntelligencePackageBoundary],
) -> list[RepositoryIntelligenceSubsystem]:
    """Discover inferred subsystem groups from repository path conventions."""

    package_ids_by_root = {package.root: package.package_id for package in packages}
    subsystems: list[RepositoryIntelligenceSubsystem] = []
    for subsystem_id, name, paths, tags in _subsystem_definitions():
        existing = _existing_paths(root, paths)
        if not existing:
            continue
        subsystems.append(
            RepositoryIntelligenceSubsystem(
                subsystem_id=f"subsystem:{subsystem_id}",
                name=name,
                scope_paths=existing,
                package_ids=[
                    package_id
                    for path, package_id in package_ids_by_root.items()
                    if path in existing
                ],
                tags=tags,
                confidence=RepositoryIntelligenceConfidence.MEDIUM,
                provenance=[
                    _provenance(RepositoryIndexSourceType.FILE_SYSTEM, existing[0])
                ],
                limitations=["Subsystem hint is inferred from local path conventions."],
            )
        )
    return subsystems


def _subsystem_definitions() -> list[tuple[str, str, list[str], list[str]]]:
    return [
        ("runtime", "Runtime", ["src/glassbox/runtime"], ["backend"]),
        ("store", "Store", ["src/glassbox/store"], ["backend", "persistence"]),
        ("web", "Web API", ["src/glassbox/web"], ["api", "dashboard"]),
        ("cli", "CLI", ["src/glassbox/cli"], ["terminal"]),
        ("frontend", "Frontend", ["frontend"], ["dashboard"]),
        ("evals", "Evals", ["evals"], ["verification"]),
        ("docs", "Docs", ["docs", "README.md"], ["documentation"]),
        ("release", "Release scripts", ["scripts"], ["release"]),
        ("packaging", "Packaging", ["pyproject.toml", "uv.lock"], ["packaging"]),
        ("policy", "Policy", ["src/glassbox/tools/policy.py"], ["policy"]),
        ("provider", "Provider", ["src/glassbox/runtime/provider_config.py"], ["llm"]),
        (
            "memory",
            "Workspace memory",
            ["src/glassbox/runtime/workspace_memory_capture.py"],
            ["memory"],
        ),
        (
            "topology",
            "Workspace topology",
            ["src/glassbox/runtime/workspace_topology.py"],
            ["topology"],
        ),
        (
            "review-loop",
            "Review loop",
            ["src/glassbox/runtime/review_briefs.py"],
            ["review"],
        ),
    ]


__all__ = ["discover_repository_intelligence_subsystems"]
