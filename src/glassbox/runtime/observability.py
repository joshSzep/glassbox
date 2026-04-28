"""Workspace observability summaries for operators and contributors."""

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.daemon import RuntimeOwnerStatus
from glassbox.runtime.transport import RuntimeEventTransportStats
from glassbox.services import SessionRepository


class EventTransportObservability(BaseModel):
    """Live event delivery counters and reconnect guidance."""

    model_config = ConfigDict(extra="forbid")

    state: str
    subscriber_count: int
    dropped_events: int
    queue_capacity: int
    max_queue_depth: int
    queue_pressure: float
    last_published_sequence: int | None = None
    reconnect_mode: str
    reconnect_hint: str
    degraded: bool
    next_actions: list[str] = Field(default_factory=list)


class RuntimeObservability(BaseModel):
    """Runtime-owner health and live transport state."""

    model_config = ConfigDict(extra="forbid")

    state: str
    health: str | None
    dashboard_url: str | None = None
    health_url: str | None = None
    event_transport: EventTransportObservability
    next_actions: list[str] = Field(default_factory=list)


class ProjectionObservability(BaseModel):
    """Projection lag and repair guidance across retained sessions."""

    model_config = ConfigDict(extra="forbid")

    session_count: int
    ok_count: int
    stale_count: int
    unavailable_count: int
    degraded_count: int
    max_lag: int
    degraded_sessions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class VerificationObservability(BaseModel):
    """Retained eval-suite summary status."""

    model_config = ConfigDict(extra="forbid")

    summary_count: int
    latest_summary_path: str | None = None
    latest_suite_status: str | None = None
    latest_exit_code: int | None = None
    latest_profile_id: str | None = None
    latest_selected_case_count: int | None = None
    latest_passed_case_count: int | None = None
    latest_failed_case_count: int | None = None
    next_actions: list[str] = Field(default_factory=list)


class WorkspaceObservabilityReport(BaseModel):
    """Operator-facing summary of workspace health and inspection paths."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: str
    runtime: RuntimeObservability
    projections: ProjectionObservability
    verification: VerificationObservability
    next_actions: list[str] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _RetainedEvalSummary:
    path: Path
    payload: dict[str, Any]


def build_workspace_observability_report(
    *,
    workspace_root: Path,
    runtime_status: RuntimeOwnerStatus,
    session_repository: SessionRepository,
    event_transport_stats: RuntimeEventTransportStats,
) -> WorkspaceObservabilityReport:
    """Build one structured observability report for a workspace."""

    runtime = build_runtime_observability(
        runtime_status,
        event_transport_stats=event_transport_stats,
        workspace_root=workspace_root,
    )
    projections = build_projection_observability(session_repository)
    verification = build_verification_observability(workspace_root)
    next_actions = [
        action
        for section in (runtime, projections, verification)
        for action in section.next_actions
    ]
    return WorkspaceObservabilityReport(
        workspace_root=str(workspace_root),
        runtime=runtime,
        projections=projections,
        verification=verification,
        next_actions=next_actions,
    )


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


def build_projection_observability(
    session_repository: SessionRepository,
) -> ProjectionObservability:
    sessions = session_repository.list_sessions()
    counts = {"ok": 0, "stale": 0, "unavailable": 0}
    degraded_sessions: list[str] = []
    max_lag = 0
    for session in sessions:
        health = session_repository.inspect_session_projection_health(
            session.session_id
        )
        counts[health.state] = counts.get(health.state, 0) + 1
        max_lag = max(max_lag, health.lag)
        if health.degraded:
            degraded_sessions.append(str(session.session_id))

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
        degraded_sessions=degraded_sessions,
        next_actions=next_actions,
    )


def build_verification_observability(workspace_root: Path) -> VerificationObservability:
    summaries = _retained_eval_summaries(workspace_root)
    if not summaries:
        return VerificationObservability(
            summary_count=0,
            next_actions=["glassbox eval run"],
        )

    latest_summary = summaries[0]
    latest_path = latest_summary.path
    payload = latest_summary.payload
    latest_exit_code = _optional_int(payload.get("exit_code"))
    latest_profile_id = _optional_str(payload.get("profile_id"))
    latest_suite_status = "passed" if latest_exit_code == 0 else "failed"
    next_actions = [f"inspect eval summary {latest_path}"]
    if latest_exit_code not in (None, 0):
        next_actions.append(f"glassbox eval report {latest_profile_id or 'PROFILE_ID'}")

    return VerificationObservability(
        summary_count=len(summaries),
        latest_summary_path=str(latest_path),
        latest_suite_status=latest_suite_status,
        latest_exit_code=latest_exit_code,
        latest_profile_id=latest_profile_id,
        latest_selected_case_count=_optional_int(payload.get("selected_case_count")),
        latest_passed_case_count=_optional_int(payload.get("passed_case_count")),
        latest_failed_case_count=_optional_int(payload.get("failed_case_count")),
        next_actions=next_actions,
    )


def _retained_eval_summaries(workspace_root: Path) -> list[_RetainedEvalSummary]:
    summary_paths = sorted(
        (workspace_root / ".glassbox" / "evals").glob("**/summary.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [
        _RetainedEvalSummary(path=path, payload=_load_json_object(path))
        for path in summary_paths
    ]


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _health_url(dashboard_url: str | None) -> str | None:
    if dashboard_url is None:
        return None
    return dashboard_url.rstrip("/") + "/healthz"


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
