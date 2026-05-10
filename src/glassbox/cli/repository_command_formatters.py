"""Human output helpers for repository intelligence CLI commands."""

from pathlib import Path

from glassbox.core.models import BackgroundJobRecord
from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.runtime.repository_index_status import RepositoryIndexSourceDiff
from glassbox.runtime.repository_index_status import RepositoryIndexStatusSummary
from glassbox.runtime.repository_intelligence_freshness import (
    workspace_topology_freshness_cues,
)
from glassbox.runtime.workspace_topology import WorkspaceTopologySnapshot


def _print_status_summary(summary: RepositoryIndexStatusSummary) -> None:
    print(f"Repository index: {summary.status}")
    print(f"Path: {summary.path}")
    print(f"Entries: {summary.entry_count}")
    if summary.built_at is not None:
        print(f"Built: {summary.built_at}")
    print(f"Detail: {summary.detail}")
    if summary.stale_reason is not None:
        print(f"Reason: {summary.stale_reason}")
    if summary.failure_reason is not None:
        print(f"Failure: {summary.failure_reason}")
    if summary.current_source_digest is not None:
        print(f"Current source digest: {summary.current_source_digest}")
    if summary.source_digest is not None:
        print(f"Indexed source digest: {summary.source_digest}")
    if summary.source_file_count or summary.current_source_file_count:
        print(
            "Source files: "
            f"{summary.source_file_count} indexed, "
            f"{summary.current_source_file_count} current"
        )
    _print_repository_intelligence_counts(
        source_manifest_count=summary.source_manifest_count,
        source_root_count=summary.source_root_count,
        test_root_count=summary.test_root_count,
        doc_root_count=summary.doc_root_count,
        generated_path_count=summary.generated_path_count,
        policy_sensitive_path_count=summary.policy_sensitive_path_count,
        package_boundary_count=summary.package_boundary_count,
        command_recipe_count=summary.command_recipe_count,
        ownership_hint_count=summary.ownership_hint_count,
        subsystem_count=summary.subsystem_count,
        release_surface_count=summary.release_surface_count,
        memory_reference_count=summary.memory_reference_count,
    )
    for limitation in summary.limitations:
        print(f"Limitation: {limitation}")
    if summary.source_diff is not None:
        _print_source_diff(summary.source_diff)
    if summary.freshness_cues:
        print("Freshness cues:")
        for cue in summary.freshness_cues:
            print(f"- {cue.source}: {cue.state} ({cue.reason}) - {cue.detail}")
    if summary.next_actions:
        print("Next actions:")
        for action in summary.next_actions:
            print(f"- {action}")


def _print_source_diff(source_diff: RepositoryIndexSourceDiff) -> None:
    if not source_diff.available:
        if source_diff.detail is not None:
            print(f"Source diff: {source_diff.detail}")
        return
    print(
        "Source diff: "
        f"{source_diff.added_count} added, "
        f"{source_diff.removed_count} removed, "
        f"{source_diff.changed_count} changed"
    )
    for label, paths in (
        ("Added", source_diff.added_paths),
        ("Removed", source_diff.removed_paths),
        ("Changed", source_diff.changed_paths),
    ):
        if paths:
            print(f"{label} sample: {', '.join(paths)}")


def _print_index_snapshot(snapshot: RepositoryIndexSnapshot, path: Path) -> None:
    print(f"Repository index: {snapshot.status.value}")
    print(f"Path: {path}")
    print(f"Entries: {len(snapshot.entries)}")
    if snapshot.built_at is not None:
        print(f"Built: {snapshot.built_at.isoformat()}")
    _print_repository_intelligence_counts(
        source_manifest_count=len(snapshot.source_manifests),
        source_root_count=len(snapshot.source_roots),
        test_root_count=len(snapshot.test_roots),
        doc_root_count=len(snapshot.doc_roots),
        generated_path_count=len(snapshot.generated_paths),
        policy_sensitive_path_count=len(snapshot.policy_sensitive_paths),
        package_boundary_count=len(snapshot.package_boundaries),
        command_recipe_count=len(snapshot.command_recipes),
        ownership_hint_count=len(snapshot.ownership_hints),
        subsystem_count=len(snapshot.subsystems),
        release_surface_count=len(snapshot.release_sensitive_surfaces),
        memory_reference_count=len(snapshot.memory_references),
    )
    for limitation in snapshot.limitations:
        print(f"Limitation: {limitation}")


def _print_repository_intelligence_counts(
    *,
    source_manifest_count: int,
    source_root_count: int,
    test_root_count: int,
    doc_root_count: int,
    generated_path_count: int,
    policy_sensitive_path_count: int,
    package_boundary_count: int,
    command_recipe_count: int,
    ownership_hint_count: int,
    subsystem_count: int,
    release_surface_count: int,
    memory_reference_count: int = 0,
) -> None:
    if not any(
        (
            source_manifest_count,
            source_root_count,
            test_root_count,
            doc_root_count,
            generated_path_count,
            policy_sensitive_path_count,
            package_boundary_count,
            command_recipe_count,
            ownership_hint_count,
            subsystem_count,
            release_surface_count,
            memory_reference_count,
        )
    ):
        return
    print(
        "Intelligence: "
        f"{source_manifest_count} manifests, "
        f"{package_boundary_count} packages, "
        f"{source_root_count} source roots, "
        f"{test_root_count} test roots, "
        f"{doc_root_count} doc roots"
    )
    print(
        "Hints: "
        f"{generated_path_count} generated paths, "
        f"{policy_sensitive_path_count} policy-sensitive paths, "
        f"{command_recipe_count} command recipes, "
        f"{ownership_hint_count} owners, "
        f"{subsystem_count} subsystems, "
        f"{release_surface_count} release surfaces, "
        f"{memory_reference_count} memory references"
    )


def _print_index_entries(entries: list[RepositoryIndexEntry]) -> None:
    if not entries:
        print("No repository index entries found.")
        return
    print(f"Repository index entries: {len(entries)}")
    for entry in entries:
        path = entry.path.as_posix() if entry.path else ""
        print(f"{entry.entry_id}  {entry.kind.value:<16}  {entry.name}  {path}")


def _print_index_entry(entry: RepositoryIndexEntry) -> None:
    print(f"Entry: {entry.entry_id}")
    print(f"Kind: {entry.kind.value}")
    print(f"Name: {entry.name}")
    if entry.path is not None:
        print(f"Path: {entry.path.as_posix()}")
    if entry.symbol is not None:
        print(f"Symbol: {entry.symbol}")
    if entry.summary is not None:
        print(f"Summary: {entry.summary}")
    for provenance in entry.provenance:
        source_path = provenance.path.as_posix() if provenance.path else "operator hint"
        print(f"Source: {provenance.source_type.value} {source_path}")


def _print_topology_status(snapshot: WorkspaceTopologySnapshot, path: Path) -> None:
    print(f"Workspace topology: {snapshot.freshness}")
    print(f"Path: {path}")
    print(f"Components: {len(snapshot.components)}")
    print(f"Dependencies: {len(snapshot.dependencies)}")
    print(f"Recommendation posture: {snapshot.recommendation_posture}")
    if snapshot.built_at is not None:
        print(f"Built: {snapshot.built_at.isoformat()}")
    for limitation in snapshot.limitations:
        print(f"Limitation: {limitation}")
    for cue in workspace_topology_freshness_cues(snapshot.workspace_root, snapshot):
        print(f"Freshness: {cue.source} {cue.state} ({cue.reason}) - {cue.detail}")


def _print_topology_snapshot(snapshot: WorkspaceTopologySnapshot, path: Path) -> None:
    _print_topology_status(snapshot, path)
    for component in snapshot.components:
        print(
            f"{component.component_id}  {component.kind:<9}  "
            f"{component.name}  {component.root_path.as_posix()}"
        )
    if snapshot.dependencies:
        print("Dependencies:")
        for dependency in snapshot.dependencies[:20]:
            target = dependency.target_component_id or dependency.external_name
            print(f"- {dependency.source_component_id} -> {target} ({dependency.kind})")


def _print_topology_status_payload(payload: dict[str, object]) -> None:
    print(f"Workspace topology: {payload['freshness']}")
    print(f"Path: {payload['path']}")
    print(f"Components: {payload['component_count']}")
    print(f"Dependencies: {payload['dependency_count']}")
    print(f"Recommendation posture: {payload['recommendation_posture']}")
    detail = payload.get("detail")
    if isinstance(detail, str):
        print(f"Detail: {detail}")


def _print_next_actions(actions: object) -> None:
    if not isinstance(actions, list) or not actions:
        return
    print("Next actions:")
    for action in actions:
        print(f"- {action}")


def _print_path_intelligence(payload: dict[str, object]) -> None:
    print(f"Repository path: {payload['path']}")
    print(f"Snapshot status: {payload['snapshot_status']}")
    for label, key in (
        ("Packages", "packages"),
        ("Path hints", "path_hints"),
        ("Subsystems", "subsystems"),
        ("Command recipes", "command_recipes"),
        ("Owners", "ownership_hints"),
        ("Release surfaces", "release_surfaces"),
    ):
        values = payload[key]
        if isinstance(values, list):
            print(f"{label}: {len(values)}")
            for value in values[:8]:
                if isinstance(value, dict):
                    identifier = (
                        value.get("package_id")
                        or value.get("hint_id")
                        or value.get("subsystem_id")
                        or value.get("recipe_id")
                        or value.get("surface_id")
                        or value.get("owner_label")
                    )
                    name = value.get("name")
                    print(f"  - {identifier}" + (f": {name}" if name else ""))
    _print_next_actions(payload.get("next_actions"))


def _print_command_recipes(recipes) -> None:
    if not recipes:
        print("No command recipes found.")
        return
    print(f"Command recipes: {len(recipes)}")
    for recipe in recipes:
        print(f"- {recipe.recipe_id}: {recipe.name}")
        print(f"  Command: {recipe.command}")
        print(f"  Purpose: {recipe.purpose.value}, risk {recipe.risk.value}")


def _print_command_recipe(recipe) -> None:
    print(f"Recipe: {recipe.recipe_id}")
    print(f"Name: {recipe.name}")
    print(f"Command: {recipe.command}")
    print(f"Purpose: {recipe.purpose.value}")
    print(f"Review relevance: {recipe.review_relevance.value}")
    print(f"Risk: {recipe.risk.value}")
    print(f"Confidence: {recipe.confidence.value}")
    if recipe.scope_paths:
        print("Scope: " + ", ".join(path.as_posix() for path in recipe.scope_paths))
    for limitation in recipe.limitations:
        print(f"Limitation: {limitation}")


def _print_subsystems(subsystems) -> None:
    if not subsystems:
        print("No subsystems found.")
        return
    print(f"Subsystems: {len(subsystems)}")
    for subsystem in subsystems:
        print(f"- {subsystem.subsystem_id}: {subsystem.name}")
        print(
            "  Scope: " + ", ".join(path.as_posix() for path in subsystem.scope_paths)
        )


def _print_subsystem(subsystem) -> None:
    print(f"Subsystem: {subsystem.subsystem_id}")
    print(f"Name: {subsystem.name}")
    print(f"Confidence: {subsystem.confidence.value}")
    print("Scope: " + ", ".join(path.as_posix() for path in subsystem.scope_paths))
    if subsystem.package_ids:
        print("Packages: " + ", ".join(subsystem.package_ids))
    if subsystem.owner_hint_ids:
        print("Owner hints: " + ", ".join(subsystem.owner_hint_ids))
    if subsystem.release_surface_ids:
        print("Release surfaces: " + ", ".join(subsystem.release_surface_ids))


def _print_background_job(job: BackgroundJobRecord) -> None:
    if job.job_type == "repository-index-refresh":
        label = "repository index refresh"
    else:
        label = "repository intelligence refresh"
    print(f"Queued {label} job {job.job_id}: {job.state.value}")


__all__ = [
    "_print_background_job",
    "_print_command_recipe",
    "_print_command_recipes",
    "_print_index_entries",
    "_print_index_entry",
    "_print_index_snapshot",
    "_print_next_actions",
    "_print_path_intelligence",
    "_print_status_summary",
    "_print_subsystem",
    "_print_subsystems",
    "_print_topology_snapshot",
    "_print_topology_status",
    "_print_topology_status_payload",
]
