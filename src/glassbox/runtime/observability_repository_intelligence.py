"""Repository-intelligence health collector."""

from pathlib import Path

from glassbox.runtime.observability_models import RepositoryIntelligenceObservability
from glassbox.runtime.observability_models import WorkspaceMemoryObservability
from glassbox.runtime.repository_index_status import (
    build_repository_index_status_summary,
)
from glassbox.runtime.repository_intelligence_freshness import (
    RepositoryIntelligenceFreshnessCue,
)
from glassbox.runtime.repository_intelligence_freshness import (
    workspace_topology_freshness_cues,
)
from glassbox.runtime.workspace_topology import WorkspaceTopologyNotFoundError
from glassbox.runtime.workspace_topology import load_workspace_topology


def build_repository_intelligence_observability(
    workspace_root: Path,
    *,
    memory: WorkspaceMemoryObservability,
) -> RepositoryIntelligenceObservability:
    """Summarize repository intelligence health without mutating artifacts."""

    index_summary = build_repository_index_status_summary(workspace_root)
    try:
        topology = load_workspace_topology(workspace_root)
    except WorkspaceTopologyNotFoundError:
        topology = None
    cues = [
        *index_summary.freshness_cues,
        *workspace_topology_freshness_cues(workspace_root, topology),
    ]
    if memory.conflict_count:
        cues.append(
            RepositoryIntelligenceFreshnessCue(
                source="memory-conflicts",
                state="conflicting",
                reason="memory_conflict",
                severity="warning",
                detail=(
                    f"{memory.conflict_count} active workspace memory entrie(s) "
                    "conflict with current repository intelligence."
                ),
                safe_next_actions=memory.next_actions[:4],
            )
        )
    status_by_source = {cue.source: cue.state for cue in cues}
    next_actions = list(
        dict.fromkeys(
            action for cue in cues for action in cue.safe_next_actions if action.strip()
        )
    )
    warning_count = sum(
        1 for cue in cues if cue.severity == "warning" or cue.state == "degraded"
    )
    missing_count = sum(1 for cue in cues if cue.state == "missing")
    return RepositoryIntelligenceObservability(
        status=_overall_status(cues),
        index_status=status_by_source.get("repository-index", "missing"),
        topology_status=status_by_source.get("workspace-topology", "missing"),
        command_recipe_status=status_by_source.get("command-recipes", "missing"),
        memory_conflict_status=status_by_source.get("memory-conflicts", "fresh"),
        eval_metadata_status=status_by_source.get("eval-metadata", "missing"),
        release_surface_status=status_by_source.get("release-surfaces", "missing"),
        cue_count=len(cues),
        warning_count=warning_count,
        missing_count=missing_count,
        freshness_cues=cues,
        next_actions=next_actions,
    )


def _overall_status(cues: list[RepositoryIntelligenceFreshnessCue]) -> str:
    if any(cue.state == "degraded" for cue in cues):
        return "degraded"
    if any(cue.state == "conflicting" for cue in cues):
        return "conflicting"
    if any(cue.state in {"stale", "partial"} for cue in cues):
        return "stale"
    if cues and all(cue.state == "missing" for cue in cues):
        return "missing"
    if any(cue.state == "missing" for cue in cues):
        return "advisory"
    return "fresh"


__all__ = ["build_repository_intelligence_observability"]
