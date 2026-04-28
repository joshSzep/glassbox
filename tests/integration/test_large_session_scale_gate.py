"""Focused larger-session scale gate coverage for v7."""

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.observability import build_artifact_observability
from glassbox.runtime.observability import build_projection_observability
from glassbox.runtime.performance_budgets import PAYLOAD_SIZE_BUDGETS
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.web import create_app
from tests.integration.large_session_fixture import LargeSessionFixtureConfig
from tests.integration.large_session_fixture import append_large_session_fixture

_DETAIL_PAGE_LIMIT = 80


def test_large_session_scale_gate_pages_and_observability(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = open_database(tmp_path / "glassbox.sqlite3")
        initialize_database(connection)
        try:
            config = LargeSessionFixtureConfig()
            fixture = append_large_session_fixture(connection, tmp_path, config=config)
            repository = SQLiteSessionRepository(connection)
            runtime_context = _build_runtime_context(connection, tmp_path)
            app = create_app(runtime_context)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                pages = {
                    "session transcript page payload": await _get_page(
                        client,
                        fixture.session_id,
                        "transcript",
                    ),
                    "session event-log page payload": await _get_page(
                        client,
                        fixture.session_id,
                        "event-log",
                    ),
                    "session tool-call page payload": await _get_page(
                        client,
                        fixture.session_id,
                        "tool-calls",
                    ),
                    "session turn-metrics page payload": await _get_page(
                        client,
                        fixture.session_id,
                        "turn-metrics",
                    ),
                    "session artifact page payload": await _get_page(
                        client,
                        fixture.session_id,
                        "artifacts",
                    ),
                }

            assert pages["session transcript page payload"]["page"] == {
                "cursor": 0,
                "limit": _DETAIL_PAGE_LIMIT,
                "next_cursor": _DETAIL_PAGE_LIMIT,
                "has_more": True,
                "returned_count": _DETAIL_PAGE_LIMIT,
            }
            assert pages["session event-log page payload"]["page"]["has_more"] is True
            assert (
                pages["session event-log page payload"]["items"][-1]["sequence"] == 80
            )
            assert (
                pages["session tool-call page payload"]["page"]["returned_count"] == 80
            )
            assert (
                pages["session turn-metrics page payload"]["page"]["has_more"] is True
            )
            assert pages["session artifact page payload"]["page"] == {
                "cursor": 0,
                "limit": _DETAIL_PAGE_LIMIT,
                "next_cursor": None,
                "has_more": False,
                "returned_count": fixture.artifact_count,
            }

            payload_sizes = {
                surface: _json_size_bytes(payload) for surface, payload in pages.items()
            }
            _assert_payloads_within_budget(payload_sizes)

            projection_health = repository.inspect_session_projection_health(
                fixture.session_id
            )
            assert projection_health.state == "ok"
            assert projection_health.estimated_rebuild_event_count == 0
            assert projection_health.projected_progress_ratio == 1.0

            artifact_observability = build_artifact_observability(tmp_path, repository)
            assert artifact_observability.protected_count == fixture.artifact_count
            assert artifact_observability.candidate_count == 0
            assert artifact_observability.reclaimable_bytes == 0
            assert artifact_observability.glassbox_size_bytes > 0
            assert artifact_observability.category_counts == {
                "event_referenced_artifact": fixture.artifact_count
            }

            with connection:
                connection.execute(
                    "delete from session_state where session_id = ?",
                    (str(fixture.session_id),),
                )
            stale_health = repository.inspect_session_projection_health(
                fixture.session_id
            )
            assert stale_health.state == "stale"
            assert stale_health.estimated_rebuild_event_count == fixture.event_count
            assert stale_health.projected_progress_ratio == 0.0

            projection_observability = build_projection_observability(repository)
            assert projection_observability.degraded_count == 1
            assert (
                projection_observability.max_rebuild_event_count == fixture.event_count
            )
            assert (
                projection_observability.total_rebuild_event_count
                == fixture.event_count
            )
        finally:
            connection.close()

    asyncio.run(scenario())


async def _get_page(
    client: httpx.AsyncClient,
    session_id: object,
    page_name: str,
) -> dict[str, Any]:
    response = await client.get(
        f"/sessions/{session_id}/{page_name}",
        params={"limit": _DETAIL_PAGE_LIMIT},
    )
    assert response.status_code == 200
    return response.json()


def _json_size_bytes(payload: object) -> int:
    return len(
        json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    )


def _assert_payloads_within_budget(payload_sizes: Mapping[str, int]) -> None:
    budgets = {budget.surface: budget for budget in PAYLOAD_SIZE_BUDGETS}
    for surface, size_bytes in payload_sizes.items():
        budget = budgets[surface]
        assert size_bytes <= budget.budget_bytes, (
            f"{surface} serialized to {size_bytes} bytes; "
            f"budget is {budget.budget_bytes} bytes. {budget.guidance}"
        )
