"""Projection health observability collector."""

from glassbox.runtime.observability_models import ProjectionObservability
from glassbox.services import SessionRepository


def build_projection_observability(
    session_repository: SessionRepository,
) -> ProjectionObservability:
    sessions = session_repository.list_sessions()
    counts = {"ok": 0, "stale": 0, "unavailable": 0}
    degraded_sessions: list[str] = []
    max_lag = 0
    max_rebuild_event_count = 0
    total_rebuild_event_count = 0
    for session in sessions:
        health = session_repository.inspect_session_projection_health(
            session.session_id
        )
        counts[health.state] = counts.get(health.state, 0) + 1
        max_lag = max(max_lag, health.lag)
        max_rebuild_event_count = max(
            max_rebuild_event_count,
            health.estimated_rebuild_event_count,
        )
        if health.degraded:
            degraded_sessions.append(str(session.session_id))
            total_rebuild_event_count += health.estimated_rebuild_event_count

    next_actions: list[str] = []
    if degraded_sessions:
        next_actions.append("glassbox projection check --all")
        next_actions.append("glassbox projection rebuild --all")
    return ProjectionObservability(
        session_count=len(sessions),
        ok_count=counts.get("ok", 0),
        stale_count=counts.get("stale", 0),
        unavailable_count=counts.get("unavailable", 0),
        degraded_count=len(degraded_sessions),
        max_lag=max_lag,
        max_rebuild_event_count=max_rebuild_event_count,
        total_rebuild_event_count=total_rebuild_event_count,
        degraded_sessions=degraded_sessions,
        next_actions=next_actions,
    )


__all__ = ["build_projection_observability"]
