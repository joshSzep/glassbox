"""API models for handoff custody decisions."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import HandoffIntent
from glassbox.core import HandoffProjectionRecord
from glassbox.runtime.handoff_guidance import HandoffGuidance


class HandoffRecordResponse(BaseModel):
    """Projected handoff record plus dashboard action state."""

    model_config = ConfigDict(extra="forbid")

    record: HandoffProjectionRecord
    action_state: str = Field(min_length=1, max_length=120)


class HandoffListResponse(BaseModel):
    """Bounded list of projected handoff records."""

    model_config = ConfigDict(extra="forbid")

    items: list[HandoffRecordResponse] = Field(default_factory=list, max_length=500)


class HandoffAcceptRequest(BaseModel):
    """Request to accept local custody or imported follow-up."""

    model_config = ConfigDict(extra="forbid")

    accepted_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    follow_up_intent: HandoffIntent | None = None


class HandoffRejectRequest(BaseModel):
    """Request to reject local custody with a retained reason."""

    model_config = ConfigDict(extra="forbid")

    rejected_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class HandoffArchiveRequest(BaseModel):
    """Request to archive a handoff as historical workflow evidence."""

    model_config = ConfigDict(extra="forbid")

    archived_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class HandoffDecisionResponse(BaseModel):
    """Response for a recorded handoff custody decision."""

    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1, max_length=120)
    handoff: HandoffRecordResponse
    non_claims: list[str] = Field(default_factory=list, max_length=20)


class HandoffGuidanceResponse(BaseModel):
    """Dashboard/API fork-or-continue guidance."""

    model_config = ConfigDict(extra="forbid")

    guidance: HandoffGuidance


__all__ = [
    "HandoffAcceptRequest",
    "HandoffArchiveRequest",
    "HandoffDecisionResponse",
    "HandoffGuidanceResponse",
    "HandoffListResponse",
    "HandoffRecordResponse",
    "HandoffRejectRequest",
]
