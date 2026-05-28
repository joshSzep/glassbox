"""Narrow repository protocols for local handoff runtime helpers."""

from collections.abc import Sequence
from typing import Protocol
from typing import runtime_checkable

from glassbox.core import EventEnvelope
from glassbox.core import HandoffProjectionRecord
from glassbox.core import ProjectionHealth
from glassbox.core import SessionId
from glassbox.core import SessionRecord
from glassbox.core import SessionState


@runtime_checkable
class HandoffRecordReadRepository(Protocol):
    """Projected handoff record reads needed by handoff runtime helpers."""

    def get_handoff(
        self,
        session_id: SessionId,
        package_id: str,
    ) -> HandoffProjectionRecord | None: ...


@runtime_checkable
class HandoffEventAppendRepository(Protocol):
    """Single-event append surface for durable handoff decisions."""

    def append_event(self, event: EventEnvelope) -> EventEnvelope: ...


@runtime_checkable
class HandoffEventBatchAppendRepository(Protocol):
    """Batch append surface for inspection-only handoff imports."""

    def append_events(
        self,
        events: Sequence[EventEnvelope],
    ) -> list[EventEnvelope]: ...


@runtime_checkable
class HandoffDecisionRepository(
    HandoffRecordReadRepository,
    HandoffEventAppendRepository,
    Protocol,
):
    """Minimal repository surface needed to record custody decisions."""


@runtime_checkable
class HandoffGuidanceRepository(HandoffRecordReadRepository, Protocol):
    """Projection reads needed to derive fork-or-continue guidance."""

    def get_session(self, session_id: SessionId) -> SessionRecord | None: ...

    def get_session_state(self, session_id: SessionId) -> SessionState | None: ...

    def inspect_session_projection_health(
        self,
        session_id: SessionId,
    ) -> ProjectionHealth: ...


@runtime_checkable
class HandoffImportInspectionRepository(HandoffEventBatchAppendRepository, Protocol):
    """Append-only repository surface for inspection-focused package imports."""


__all__ = [
    "HandoffDecisionRepository",
    "HandoffEventAppendRepository",
    "HandoffEventBatchAppendRepository",
    "HandoffGuidanceRepository",
    "HandoffImportInspectionRepository",
    "HandoffRecordReadRepository",
]
