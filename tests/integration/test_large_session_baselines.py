"""Larger-session baseline characterization for v7 read-path hardening."""

import json
from collections.abc import Mapping
from pathlib import Path

from glassbox.runtime.performance_budgets import PAYLOAD_SIZE_BUDGETS
from glassbox.runtime.session_queries import OPERATOR_SORT_PRIORITY
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import WorkspaceRuntimeSummaryView
from glassbox.store.artifact_retention import inspect_artifact_state
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.web.session_api import build_session_aggregate_response
from glassbox.web.session_api import build_session_snapshot_response
from tests.integration.fault_test_support import open_initialized_database
from tests.integration.large_session_fixture import LargeSessionFixtureConfig
from tests.integration.large_session_fixture import append_large_session_fixture


def test_larger_session_baseline_read_paths_have_bounded_shapes(
    tmp_path: Path,
) -> None:
    connection = open_initialized_database(tmp_path)
    try:
        config = LargeSessionFixtureConfig()
        fixture = append_large_session_fixture(connection, tmp_path, config=config)
        repository = SQLiteSessionRepository(connection)
        artifacts = FilesystemArtifactRepository(connection, tmp_path)
        query_service = SessionQueryService(repository, artifacts)
        runtime = WorkspaceRuntimeSummaryView(
            workspace_root=str(tmp_path),
            state="stopped",
            health=None,
        )

        snapshot = query_service.get_session_snapshot(
            fixture.session_id,
            turn_metrics_limit=config.turn_count,
        )
        aggregate = query_service.get_session_aggregate(
            runtime=runtime,
            sort=OPERATOR_SORT_PRIORITY,
            limit=25,
        )
        projection_health = repository.inspect_session_projection_health(
            fixture.session_id
        )
        transcript = repository.list_transcript_messages(fixture.session_id)
        event_log = repository.read_session_events(fixture.session_id)
        artifact_report = inspect_artifact_state(tmp_path, repository)

        snapshot_payload = build_session_snapshot_response(snapshot).model_dump(
            mode="json"
        )
        aggregate_payload = build_session_aggregate_response(aggregate).model_dump(
            mode="json"
        )
        transcript_payload = [message.model_dump(mode="json") for message in transcript]
        event_log_payload = [event.model_dump(mode="json") for event in event_log]
        artifact_payload = artifact_report.to_json_payload()

        assert projection_health.state == "ok"
        assert snapshot.last_sequence == fixture.event_count
        assert len(snapshot.transcript) == fixture.transcript_message_count
        assert len(snapshot.turn_metrics) == config.turn_count
        assert snapshot.session_policy_summary.command_count == 0
        assert (
            snapshot.session_policy_summary.read_only_count == fixture.tool_call_count
        )
        assert len(transcript) == fixture.transcript_message_count
        assert len(event_log) == fixture.event_count
        assert len(artifact_report.protected) == fixture.artifact_count
        assert artifact_report.candidates == []
        assert len(aggregate.sessions) == 1

        payload_sizes = {
            "dashboard render-critical payload": _json_size_bytes(aggregate_payload),
            "session snapshot payload": _json_size_bytes(snapshot_payload),
            "transcript payload": _json_size_bytes(transcript_payload),
            "event-log payload": _json_size_bytes(event_log_payload),
            "artifact inspection payload": _json_size_bytes(artifact_payload),
        }
        _assert_payloads_within_budget(payload_sizes)
    finally:
        connection.close()


def _json_size_bytes(payload: object) -> int:
    return len(
        json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


def _assert_payloads_within_budget(payload_sizes: Mapping[str, int]) -> None:
    budgets = {budget.surface: budget for budget in PAYLOAD_SIZE_BUDGETS}
    for surface, size_bytes in payload_sizes.items():
        budget = budgets[surface]
        assert size_bytes <= budget.budget_bytes, (
            f"{surface} serialized to {size_bytes} bytes; "
            f"budget is {budget.budget_bytes} bytes. {budget.guidance}"
        )
