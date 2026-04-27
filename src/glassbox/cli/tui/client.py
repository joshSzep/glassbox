"""Client adapter boundary used by the Textual app."""

from dataclasses import dataclass

from glassbox.cli.interactive_client import InteractiveSessionClient
from glassbox.cli.interactive_client import InteractiveSessionSnapshot


@dataclass(slots=True)
class TerminalClientAdapter:
    """Thin adapter between Textual app code and the session client protocol."""

    client: InteractiveSessionClient

    async def fetch_snapshot(self) -> InteractiveSessionSnapshot:
        return await self.client.fetch_snapshot()

    async def close(self) -> None:
        await self.client.aclose()
