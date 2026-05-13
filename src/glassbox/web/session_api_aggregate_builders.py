"""Builder functions for session aggregate API response models."""

from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary
from glassbox.runtime.session_queries import SessionAggregateView
from glassbox.runtime.session_queries import SessionSummaryView
from glassbox.web.session_api_aggregate_models import OperatorSessionSummaryResponse
from glassbox.web.session_api_aggregate_models import ProviderEvidenceSummaryResponse
from glassbox.web.session_api_aggregate_models import SessionAggregateResponse


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


__all__ = [
    "build_operator_session_summary_response",
    "build_provider_evidence_summary_response",
    "build_session_aggregate_response",
]
