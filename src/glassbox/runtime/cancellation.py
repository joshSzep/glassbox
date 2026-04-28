"""Cooperative cancellation primitives for live turn execution."""

import asyncio
from dataclasses import dataclass

from glassbox.core.events import CancellationStage
from glassbox.core.ids import TurnId


class TurnCancellationRequested(Exception):
    """Raised when a live turn observes an accepted cancellation request."""

    def __init__(self, *, stage: CancellationStage, reason: str) -> None:
        super().__init__(reason)
        self.stage = stage
        self.reason = reason


@dataclass(slots=True)
class TurnCancellationSnapshot:
    """Immutable-ish view of the current cancellation request state."""

    turn_id: TurnId
    requested: bool
    reason: str | None


class TurnCancellationController:
    """Own cooperative cancellation state for one live turn."""

    def __init__(self, turn_id: TurnId) -> None:
        self._turn_id = turn_id
        self._event = asyncio.Event()
        self._reason: str | None = None

    @property
    def turn_id(self) -> TurnId:
        return self._turn_id

    @property
    def requested(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str | None:
        return self._reason

    def request(self, reason: str | None = None) -> bool:
        """Request cancellation and return whether this was a repeated request."""

        repeated = self._event.is_set()
        if self._reason is None:
            self._reason = reason or "operator requested cancellation"
        self._event.set()
        return repeated

    async def wait(self) -> TurnCancellationSnapshot:
        await self._event.wait()
        return self.snapshot()

    def snapshot(self) -> TurnCancellationSnapshot:
        return TurnCancellationSnapshot(
            turn_id=self._turn_id,
            requested=self.requested,
            reason=self._reason,
        )

    def raise_if_requested(self, stage: CancellationStage) -> None:
        if not self.requested:
            return
        raise TurnCancellationRequested(
            stage=stage,
            reason=self._reason or "operator requested cancellation",
        )
