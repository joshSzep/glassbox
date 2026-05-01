"""Daemon-forwarded interactive session actions."""

from uuid import UUID

import httpx


async def request_cancel_via_daemon(
    *,
    dashboard_url: str,
    session_id: UUID,
    turn_id: UUID | None,
    reason: str | None,
) -> None:
    async with httpx.AsyncClient(
        base_url=dashboard_url,
        timeout=httpx.Timeout(5.0, connect=1.0, read=5.0, write=5.0),
    ) as client:
        response = await client.post(
            f"/sessions/{session_id}/cancel",
            json={
                "reason": reason,
                "turn_id": str(turn_id) if turn_id else None,
            },
        )
    if response.status_code in {404, 409, 422}:
        raise ValueError(response.json().get("detail", response.text))
    response.raise_for_status()


__all__ = ["request_cancel_via_daemon"]
