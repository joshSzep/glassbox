"""Aggregate freshness ranking for workspace knowledge posture."""

from glassbox.runtime.knowledge_posture_models import KnowledgePostureCue
from glassbox.runtime.knowledge_posture_models import KnowledgePostureStatus


def overall_status(cues: list[KnowledgePostureCue]) -> KnowledgePostureStatus:
    statuses = {cue.status for cue in cues}
    for candidate in (
        "degraded",
        "stale",
        "invalidated",
        "missing",
        "advisory",
        "historical-only",
    ):
        if candidate in statuses:
            return candidate
    return "fresh"


__all__ = ["overall_status"]
