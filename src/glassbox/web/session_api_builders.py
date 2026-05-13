"""Builder functions for session API response model families."""

from collections.abc import Sequence

from glassbox.core.models import ForkedSession
from glassbox.runtime.session_queries import SessionSnapshotView
from glassbox.runtime.session_queries import SessionSummaryView
from glassbox.web.session_api_actions import ForkSessionResponse
from glassbox.web.session_api_aggregate_builders import (
    build_operator_session_summary_response,
)
from glassbox.web.session_api_aggregate_builders import (
    build_provider_evidence_summary_response,
)
from glassbox.web.session_api_aggregate_builders import build_session_aggregate_response
from glassbox.web.session_api_snapshot import SessionSnapshotResponse
from glassbox.web.session_api_snapshot import SessionSummaryResponse


def build_fork_session_response(forked_session: ForkedSession) -> ForkSessionResponse:
    """Serialize a newly forked session into the HTTP response model."""

    return ForkSessionResponse.model_validate(forked_session.model_dump(mode="json"))


def build_session_summary_response(
    summary: SessionSummaryView,
) -> SessionSummaryResponse:
    """Serialize a session summary view into the HTTP response model."""

    return SessionSummaryResponse.model_validate(summary.model_dump(mode="json"))


def build_session_summary_responses(
    summaries: Sequence[SessionSummaryView],
) -> list[SessionSummaryResponse]:
    """Serialize multiple session summary views for the session index."""

    return [build_session_summary_response(summary) for summary in summaries]


def build_session_snapshot_response(
    snapshot: SessionSnapshotView,
) -> SessionSnapshotResponse:
    """Serialize a session snapshot view into the HTTP response model."""

    return SessionSnapshotResponse.model_validate(snapshot.model_dump(mode="json"))


__all__ = [
    "build_fork_session_response",
    "build_operator_session_summary_response",
    "build_provider_evidence_summary_response",
    "build_session_aggregate_response",
    "build_session_snapshot_response",
    "build_session_summary_response",
    "build_session_summary_responses",
]
