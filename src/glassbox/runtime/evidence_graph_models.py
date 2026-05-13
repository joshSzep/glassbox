"""Runtime-local evidence graph response helpers."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import NextActionTargetKind


class EvidenceGraphSummary(BaseModel):
    """Compact count summary for a derived evidence graph."""

    model_config = ConfigDict(extra="forbid")

    graph_id: str
    target_kind: NextActionTargetKind
    target_id: str | None = None
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    claim_count: int = Field(ge=0)
    stale_claim_count: int = Field(ge=0)
    missing_claim_count: int = Field(ge=0)
    contradicted_claim_count: int = Field(ge=0)
    manual_only_claim_count: int = Field(ge=0)
    accepted_risk_claim_count: int = Field(ge=0)
    limitation_count: int = Field(ge=0)


__all__ = ["EvidenceGraphSummary"]
