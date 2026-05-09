"""Shared freshness and drift cues for repository intelligence consumers."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.runtime.workspace_topology import WorkspaceTopologySnapshot

RepositoryIntelligenceFreshnessState = Literal[
    "fresh",
    "stale",
    "missing",
    "degraded",
    "conflicting",
    "partial",
]
RepositoryIntelligenceDriftReason = Literal[
    "source_digest_changed",
    "artifact_missing",
    "build_failed",
    "refresh_in_progress",
    "topology_missing",
    "command_recipes_missing",
    "dependency_manifests_missing",
    "memory_conflict",
    "memory_references_missing",
    "eval_metadata_missing",
    "release_surfaces_missing",
    "current",
]
RepositoryIntelligenceFreshnessSeverity = Literal[
    "advisory",
    "warning",
    "blocking",
]

_EVAL_METADATA_FILES = (
    Path("evals/coverage.json"),
    Path("evals/impact.json"),
    Path("evals/profiles.json"),
    Path("evals/recipes.json"),
)


class RepositoryIntelligenceFreshnessCue(BaseModel):
    """Operator-facing state, reason, and remediation for one intelligence input."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=120)
    state: RepositoryIntelligenceFreshnessState
    reason: RepositoryIntelligenceDriftReason
    severity: RepositoryIntelligenceFreshnessSeverity = "advisory"
    detail: str = Field(min_length=1, max_length=500)
    safe_next_actions: list[str] = Field(default_factory=list, max_length=8)
    limitations: list[str] = Field(default_factory=list, max_length=8)


def repository_index_freshness_cues(
    workspace_root: Path,
    snapshot: RepositoryIndexSnapshot | None,
) -> list[RepositoryIntelligenceFreshnessCue]:
    """Return shared freshness cues for a repository-intelligence snapshot."""

    root = workspace_root.resolve()
    if snapshot is None:
        return [
            _cue(
                source="repository-index",
                state="missing",
                reason="artifact_missing",
                severity="advisory",
                detail=(
                    "No repository intelligence snapshot exists for this workspace."
                ),
                actions=[f"glassbox repo index build --cwd {root}"],
            )
        ]
    cues = [_snapshot_status_cue(root, snapshot)]
    cues.extend(
        [
            _presence_cue(
                source="command-recipes",
                count=len(snapshot.command_recipes),
                reason="command_recipes_missing",
                detail_present=(
                    f"{len(snapshot.command_recipes)} command recipe(s) are "
                    "available for advisory verification guidance."
                ),
                detail_missing=(
                    "No command recipes are present; recommendations will fall "
                    "back to broader checks."
                ),
                action=f"glassbox repo index build --cwd {root}",
            ),
            _presence_cue(
                source="dependency-manifests",
                count=len(snapshot.source_manifests),
                reason="dependency_manifests_missing",
                detail_present=(
                    f"{len(snapshot.source_manifests)} manifest source(s) are "
                    "available for package and dependency posture."
                ),
                detail_missing=(
                    "No manifest sources are recorded in repository intelligence."
                ),
                action=f"glassbox repo index inspect --cwd {root}",
            ),
            _presence_cue(
                source="memory-derived-entries",
                count=len(snapshot.memory_references),
                reason="memory_references_missing",
                detail_present=(
                    f"{len(snapshot.memory_references)} confirmed memory "
                    "reference(s) enrich repository intelligence."
                ),
                detail_missing=(
                    "No confirmed active workspace memory is attached to the snapshot."
                ),
                action="glassbox memory candidates SESSION_ID --cwd .",
            ),
            _eval_metadata_cue(root),
            _presence_cue(
                source="release-surfaces",
                count=len(snapshot.release_sensitive_surfaces),
                reason="release_surfaces_missing",
                detail_present=(
                    f"{len(snapshot.release_sensitive_surfaces)} release "
                    "surface(s) are available for verification explanations."
                ),
                detail_missing=(
                    "No release-sensitive surfaces are recorded; release guidance "
                    "will stay broad."
                ),
                action=f"glassbox repo index inspect --cwd {root}",
            ),
        ]
    )
    return cues


def workspace_topology_freshness_cues(
    workspace_root: Path,
    snapshot: WorkspaceTopologySnapshot | None,
) -> list[RepositoryIntelligenceFreshnessCue]:
    """Return shared freshness cues for workspace topology state."""

    root = workspace_root.resolve()
    if snapshot is None:
        return [
            _cue(
                source="workspace-topology",
                state="missing",
                reason="topology_missing",
                detail="Workspace topology has not been built.",
                actions=[f"glassbox repo topology build --cwd {root}"],
            )
        ]
    state: RepositoryIntelligenceFreshnessState
    reason: RepositoryIntelligenceDriftReason
    severity: RepositoryIntelligenceFreshnessSeverity = "advisory"
    if snapshot.freshness == "fresh":
        state = "fresh"
        reason = "current"
        detail = "Workspace topology is fresh for the retained source digest."
    elif snapshot.freshness == "stale":
        state = "stale"
        reason = "source_digest_changed"
        severity = "warning"
        detail = (
            "Workspace topology source inputs changed; rebuild before relying on "
            "topology-derived guidance."
        )
    elif snapshot.freshness == "failed":
        state = "degraded"
        reason = "build_failed"
        severity = "warning"
        detail = snapshot.failure_reason or "Workspace topology refresh failed."
    else:
        state = "missing"
        reason = "topology_missing"
        detail = "Workspace topology has no supported components yet."
    actions = (
        [f"glassbox repo topology build --cwd {root}"]
        if snapshot.freshness != "fresh"
        else [f"glassbox repo topology show --cwd {root}"]
    )
    return [
        _cue(
            source="workspace-topology",
            state=state,
            reason=reason,
            severity=severity,
            detail=detail,
            actions=actions,
            limitations=snapshot.limitations,
        )
    ]


def _snapshot_status_cue(
    root: Path,
    snapshot: RepositoryIndexSnapshot,
) -> RepositoryIntelligenceFreshnessCue:
    if snapshot.status == RepositoryIndexFreshness.FRESH:
        return _cue(
            source="repository-index",
            state="fresh",
            reason="current",
            detail="Repository intelligence is fresh for the current source digest.",
            actions=[f"glassbox repo index inspect --cwd {root}"],
            limitations=snapshot.limitations,
        )
    if snapshot.status == RepositoryIndexFreshness.STALE:
        return _cue(
            source="repository-index",
            state="stale",
            reason="source_digest_changed",
            severity="warning",
            detail=(
                "Repository intelligence source inputs changed; rebuild before "
                "treating recommendations as current."
            ),
            actions=[f"glassbox repo index build --cwd {root}"],
            limitations=snapshot.limitations,
        )
    if snapshot.status == RepositoryIndexFreshness.BUILDING:
        return _cue(
            source="repository-index",
            state="partial",
            reason="refresh_in_progress",
            detail="Repository intelligence refresh is in progress.",
            actions=[f"glassbox repo index status --cwd {root}"],
            limitations=snapshot.limitations,
        )
    return _cue(
        source="repository-index",
        state="degraded",
        reason="build_failed",
        severity="warning",
        detail=snapshot.failure_reason or "Repository intelligence refresh failed.",
        actions=[
            f"glassbox repo index status --cwd {root} --json",
            f"glassbox repo index build --cwd {root}",
        ],
        limitations=snapshot.limitations,
    )


def _presence_cue(
    *,
    source: str,
    count: int,
    reason: RepositoryIntelligenceDriftReason,
    detail_present: str,
    detail_missing: str,
    action: str,
) -> RepositoryIntelligenceFreshnessCue:
    if count:
        return _cue(
            source=source,
            state="fresh",
            reason="current",
            detail=detail_present,
        )
    return _cue(
        source=source,
        state="missing",
        reason=reason,
        detail=detail_missing,
        actions=[action],
        limitations=["Missing optional intelligence degrades confidence only."],
    )


def _eval_metadata_cue(root: Path) -> RepositoryIntelligenceFreshnessCue:
    missing = [
        path.as_posix() for path in _EVAL_METADATA_FILES if not (root / path).exists()
    ]
    if not missing:
        return _cue(
            source="eval-metadata",
            state="fresh",
            reason="current",
            detail="Eval profiles, coverage, impact, and recipes metadata are present.",
        )
    return _cue(
        source="eval-metadata",
        state="partial",
        reason="eval_metadata_missing",
        detail=f"Eval metadata is incomplete; missing: {', '.join(missing)}.",
        actions=["glassbox eval audit --cwd ."],
        limitations=["Eval recommendations may fall back to broader profiles."],
    )


def _cue(
    *,
    source: str,
    state: RepositoryIntelligenceFreshnessState,
    reason: RepositoryIntelligenceDriftReason,
    detail: str,
    severity: RepositoryIntelligenceFreshnessSeverity = "advisory",
    actions: list[str] | None = None,
    limitations: list[str] | None = None,
) -> RepositoryIntelligenceFreshnessCue:
    return RepositoryIntelligenceFreshnessCue(
        source=source,
        state=state,
        reason=reason,
        severity=severity,
        detail=detail,
        safe_next_actions=actions or [],
        limitations=limitations or [],
    )


__all__ = [
    "RepositoryIntelligenceDriftReason",
    "RepositoryIntelligenceFreshnessCue",
    "RepositoryIntelligenceFreshnessSeverity",
    "RepositoryIntelligenceFreshnessState",
    "repository_index_freshness_cues",
    "workspace_topology_freshness_cues",
]
