"""Runtime-local models and protocols for handoff custody decisions."""

from typing import Protocol

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import EventEnvelope
from glassbox.core import HandoffProjectionRecord
from glassbox.core import SessionId


class HandoffDecisionRepository(Protocol):
    """Minimal repository surface needed to record custody decisions."""

    def get_handoff(
        self,
        session_id: SessionId,
        package_id: str,
    ) -> HandoffProjectionRecord | None: ...

    def append_event(self, event: EventEnvelope) -> EventEnvelope: ...


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
