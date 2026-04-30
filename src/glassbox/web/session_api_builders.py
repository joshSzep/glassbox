"""Builder functions for session API response model families."""

from collections.abc import Sequence

from glassbox.core.models import ForkedSession
from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary
from glassbox.runtime.session_queries import SessionAggregateView
from glassbox.runtime.session_queries import SessionSnapshotView
from glassbox.runtime.session_queries import SessionSummaryView
from glassbox.web.session_api_actions import ForkSessionResponse
from glassbox.web.session_api_aggregate import OperatorSessionSummaryResponse
from glassbox.web.session_api_aggregate import ProviderEvidenceSummaryResponse
from glassbox.web.session_api_aggregate import SessionAggregateResponse
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


def build_operator_session_summary_response(
    summary: SessionSummaryView,
) -> OperatorSessionSummaryResponse:
    """Serialize an operator-console session summary into the HTTP model."""

    return OperatorSessionSummaryResponse.model_validate(
        summary.model_dump(mode="json")
    )


def build_session_aggregate_response(
    aggregate: SessionAggregateView,
) -> SessionAggregateResponse:
    """Serialize the operator-console aggregate response into HTTP payloads."""

    return SessionAggregateResponse.model_validate(aggregate.model_dump(mode="json"))


def build_provider_evidence_summary_response(
    evidence: ProviderCanaryEvidenceSummary,
) -> ProviderEvidenceSummaryResponse:
    """Serialize retained provider evidence for dashboard aggregate payloads."""

    return ProviderEvidenceSummaryResponse.model_validate(
        {"advisory": True, **evidence.model_dump(mode="json")}
    )


def build_session_snapshot_response(
    snapshot: SessionSnapshotView,
) -> SessionSnapshotResponse:
    """Serialize a session snapshot view into the HTTP response model."""

    return SessionSnapshotResponse.model_validate(snapshot.model_dump(mode="json"))
