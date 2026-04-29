"""Artifact retention observability collector."""

from pathlib import Path

from glassbox.runtime.observability_models import ArtifactObservability
from glassbox.services import SessionRepository
from glassbox.store.artifact_retention import inspect_artifact_state


def build_artifact_observability(
    workspace_root: Path,
    session_repository: SessionRepository,
) -> ArtifactObservability:
    report = inspect_artifact_state(workspace_root, session_repository)
    next_actions: list[str] = []
    if report.storage_warning is not None or report.candidates:
        next_actions.append("glassbox artifacts inspect")
        next_actions.append("glassbox artifacts prune --dry-run")
    return ArtifactObservability(
        protected_count=len(report.protected),
        candidate_count=len(report.candidates),
        missing_reference_count=len(report.missing_references),
        reclaimable_bytes=report.candidate_size_bytes,
        glassbox_size_bytes=report.glassbox_size_bytes,
        storage_warning_threshold_bytes=report.storage_warning_threshold_bytes,
        storage_warning=report.storage_warning,
        oldest_age_days=report.oldest_age_days,
        category_counts=report.category_counts,
        next_actions=next_actions,
    )


__all__ = ["build_artifact_observability"]
