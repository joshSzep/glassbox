"""Client-neutral contracts for interactive terminal sessions."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.models import SessionState
from glassbox.core.types import ApprovalDecision


class InteractiveClientErrorKind(StrEnum):
    UNKNOWN_SESSION = "unknown_session"
    HISTORICAL_ONLY = "historical_only"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    STREAM_UNAVAILABLE = "stream_unavailable"


class InteractiveClientError(ValueError):
    """Normalized error raised by interactive session clients."""

    def __init__(self, kind: InteractiveClientErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


class ReviewLoopAction(StrEnum):
    STATUS = "status"
    OPERATOR_QUEUE = "operator_queue"
    NEXT_ACTIONS = "next_actions"
    WORKUP_GUIDE = "workup_guide"
    REFRESH_INVENTORY = "refresh_inventory"
    GENERATE_BRIEF = "generate_brief"
    PREVIEW_VERIFICATION = "preview_verification"
    EVIDENCE_GRAPH = "evidence_graph"
    INSPECT_HANDOFF = "inspect_handoff"
    MAINTENANCE_CHECKS = "maintenance_checks"
    SHOW_FEEDBACK_STATUS = "show_feedback_status"
    RECORD_FEEDBACK_FIXUP = "record_feedback_fixup"


@dataclass(frozen=True, slots=True)
class ReviewLoopActionResult:
    """Terminal-friendly summary of one review-loop action."""

    action: ReviewLoopAction | str
    headline: str
    changeset_id: str | None = None
    details: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    safe_next_actions: tuple[str, ...] = ()
    dashboard_path: str | None = None


@dataclass(frozen=True, slots=True)
class InteractiveSessionSnapshot:
    """Client-neutral session state used by terminal UI entrypoints."""

    state: SessionState
    cwd: str | None = None
    model_name: str | None = None
    approval_mode: str | None = None
    dashboard_url: str | None = None
    pending_question_text: str | None = None

    @property
    def session_id(self) -> SessionId:
        return self.state.session_id

    @property
    def last_sequence(self) -> int:
        return self.state.last_sequence


class InteractiveSessionClient(Protocol):
    """Common mutation and event-stream boundary for terminal clients."""

    @property
    def session_id(self) -> SessionId: ...

    async def fetch_snapshot(self) -> InteractiveSessionSnapshot: ...

    async def submit_message(self, text: str) -> None: ...

    async def submit_answer(self, question_id: QuestionId, answer: str) -> None: ...

    async def resolve_approval(
        self,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None: ...

    async def cancel_turn(
        self,
        turn_id: TurnId | None = None,
        *,
        reason: str | None = None,
    ) -> None: ...

    async def create_review_changeset(
        self,
        *,
        objective: str | None = None,
    ) -> ReviewLoopActionResult: ...

    async def run_review_action(
        self,
        action: ReviewLoopAction,
        *,
        changeset_id: str | None = None,
    ) -> ReviewLoopActionResult: ...

    def stream_events(
        self, *, after_sequence: int = 0
    ) -> AsyncIterator[EventEnvelope]: ...

    async def aclose(self) -> None: ...
