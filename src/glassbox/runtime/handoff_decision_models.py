"""Runtime-local models for handoff custody decisions."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import HandoffProjectionRecord
from glassbox.runtime.handoff_repository_contracts import HandoffDecisionRepository


class HandoffDecisionResult(BaseModel):
    """Result returned by CLI and API custody decision actions."""

    model_config = ConfigDict(extra="forbid")

    record: HandoffProjectionRecord
    event_type: str = Field(min_length=1, max_length=120)
    non_claims: list[str] = Field(default_factory=list, max_length=20)


__all__ = [
    "HandoffDecisionRepository",
    "HandoffDecisionResult",
]
