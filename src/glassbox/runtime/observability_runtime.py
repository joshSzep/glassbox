"""Runtime-owner and event-transport observability collectors."""

import shlex
from pathlib import Path

from glassbox.runtime.daemon import RuntimeOwnerStatus
from glassbox.runtime.observability_models import EventTransportObservability
from glassbox.runtime.observability_models import RuntimeObservability
from glassbox.runtime.transport import RuntimeEventTransportStats


def build_runtime_observability(
    runtime_status: RuntimeOwnerStatus,
    *,
    event_transport_stats: RuntimeEventTransportStats,
    workspace_root: Path,
) -> RuntimeObservability:
    record = runtime_status.record
    dashboard_url = record.dashboard_url if record is not None else None
    health_url = _health_url(dashboard_url)
    event_transport = build_event_transport_observability(event_transport_stats)
    quoted_workspace_root = shlex.quote(str(workspace_root))
    next_actions: list[str] = []
    if runtime_status.state == "not_running":
        next_actions.append(f"glassbox daemon start --cwd {quoted_workspace_root}")
    elif runtime_status.state == "stale":
        next_actions.append(f"glassbox daemon stop --cwd {quoted_workspace_root}")
        next_actions.append(f"glassbox daemon start --cwd {quoted_workspace_root}")
    elif runtime_status.health != "ok":
        next_actions.append(f"inspect runtime health at {health_url}")
    next_actions.extend(event_transport.next_actions)
    return RuntimeObservability(
        state=runtime_status.state,
        health=runtime_status.health,
        dashboard_url=dashboard_url,
        health_url=health_url,
        event_transport=event_transport,
        next_actions=next_actions,
    )


def build_event_transport_observability(
    stats: RuntimeEventTransportStats,
) -> EventTransportObservability:
    next_actions: list[str] = []
    queue_pressure = _queue_pressure(stats.max_queue_depth, stats.queue_capacity)
    if stats.dropped_events > 0:
        next_actions.append(
            "refresh live clients or reconnect with the last observed sequence"
        )
    if queue_pressure >= 1:
        next_actions.append(
            "inspect slow live subscribers and reconnect lagging clients"
        )
    degraded = stats.dropped_events > 0 or queue_pressure >= 1
    return EventTransportObservability(
        state="degraded" if degraded else "healthy",
        subscriber_count=stats.subscriber_count,
        dropped_events=stats.dropped_events,
        queue_capacity=stats.queue_capacity,
        max_queue_depth=stats.max_queue_depth,
        queue_pressure=queue_pressure,
        last_published_sequence=stats.last_published_sequence,
        reconnect_mode="resume with /sessions/{session_id}/events?after=SEQUENCE",
        reconnect_hint=_reconnect_hint(stats.last_published_sequence),
        degraded=degraded,
        next_actions=next_actions,
    )


def _queue_pressure(max_queue_depth: int, queue_capacity: int) -> float:
    if queue_capacity <= 0:
        return 0.0
    return round(max_queue_depth / queue_capacity, 3)


def _reconnect_hint(last_published_sequence: int | None) -> str:
    if last_published_sequence is None:
        return "use the client's last observed sequence as the after cursor"
    return (
        f"latest published sequence is {last_published_sequence}; reconnect after "
        "the client's last observed sequence"
    )


def _health_url(dashboard_url: str | None) -> str | None:
    if dashboard_url is None:
        return None
    return dashboard_url.rstrip("/") + "/healthz"


__all__ = [
    "build_event_transport_observability",
    "build_runtime_observability",
]
