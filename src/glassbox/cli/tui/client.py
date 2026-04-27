"""Client adapter boundary used by the Textual app."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from glassbox.cli.interactive_client import InteractiveSessionClient
from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import QuestionId
from glassbox.core.types import ApprovalDecision


@dataclass(slots=True)
class TerminalClientAdapter:
    """Thin adapter between Textual app code and the session client protocol."""

    client: InteractiveSessionClient

    async def fetch_snapshot(self) -> InteractiveSessionSnapshot:
        return await self.client.fetch_snapshot()

    def stream_events(self, *, after_sequence: int = 0) -> AsyncIterator[EventEnvelope]:
        return self.client.stream_events(after_sequence=after_sequence)

    async def submit_message(self, text: str) -> None:
        await self.client.submit_message(text)

    async def submit_answer(self, question_id: QuestionId, answer: str) -> None:
        await self.client.submit_answer(question_id, answer)

    async def resolve_approval(
        self,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None:
        await self.client.resolve_approval(approval_id, decision)

    async def close(self) -> None:
        await self.client.aclose()
