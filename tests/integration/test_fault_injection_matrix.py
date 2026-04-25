"""Fault-injection matrix for runtime, store, and transport boundaries."""

import asyncio
import sqlite3
from pathlib import Path

import pytest

from glassbox.core import EventEnvelope
from glassbox.core import ToolArtifactRecorded
from glassbox.core import UserMessageReceived
from glassbox.core import new_artifact_id
from glassbox.core import new_message_id
from glassbox.runtime import EventBus
from glassbox.store.artifacts import artifact_relative_path
from glassbox.store.artifacts import record_text_artifact
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import inspect_session_projection_health
from glassbox.store.sqlite import read_events_by_correlation_id
from glassbox.store.sqlite import read_session_events
from glassbox.store.sqlite import rebuild_session_projections
from tests.integration.fault_test_support import append_representative_completed_session
from tests.integration.fault_test_support import open_initialized_database
from tests.integration.fault_test_support import projection_snapshot


def test_projection_failure_rolls_back_canonical_append_and_recovers(
    tmp_path: Path,
) -> None:
    connection = open_initialized_database(tmp_path)
    try:
        ids = append_representative_completed_session(connection, tmp_path)
        events_before_failure = read_session_events(connection, ids.session_id)
        injected_event = EventEnvelope(
            session_id=ids.session_id,
            sequence=0,
            payload=UserMessageReceived(
                message_id=new_message_id(),
                text="continue after projection failure",
            ),
        )
        connection.execute(
            """
            create trigger injected_transcript_projection_failure
            before insert on transcript_messages
            begin
                select raise(fail, 'injected transcript projection failure');
            end
            """
        )
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError, match="injected transcript"):
            append_events(connection, [injected_event])

        events_after_failure = read_session_events(connection, ids.session_id)
        health_after_failure = inspect_session_projection_health(
            connection,
            ids.session_id,
        )

        connection.execute("drop trigger injected_transcript_projection_failure")
        connection.commit()
        recovered_events = append_events(connection, [injected_event])
        events_after_recovery = read_session_events(connection, ids.session_id)
    finally:
        connection.close()

    assert events_after_failure == events_before_failure
    assert health_after_failure.state == "ok"
    assert health_after_failure.canonical_last_sequence == len(events_before_failure)
    assert recovered_events[0].sequence == len(events_before_failure) + 1
    assert events_after_recovery == [*events_before_failure, recovered_events[0]]


def test_projection_corruption_reports_diagnostic_and_rebuild_preserves_events(
    tmp_path: Path,
) -> None:
    connection = open_initialized_database(tmp_path)
    try:
        ids = append_representative_completed_session(connection, tmp_path)
        events_before_corruption = read_session_events(connection, ids.session_id)
        snapshot_before_corruption = projection_snapshot(connection, ids.session_id)
        connection.execute(
            """
            update session_state
            set last_sequence = last_sequence + 5
            where session_id = ?
            """,
            (str(ids.session_id),),
        )
        connection.commit()

        corrupted_health = inspect_session_projection_health(
            connection,
            ids.session_id,
        )

        rebuild_session_projections(connection, ids.session_id)
        events_after_rebuild = read_session_events(connection, ids.session_id)
        snapshot_after_rebuild = projection_snapshot(connection, ids.session_id)
        recovered_health = inspect_session_projection_health(connection, ids.session_id)
    finally:
        connection.close()

    assert corrupted_health.state == "stale"
    assert corrupted_health.degraded is True
    assert (
        corrupted_health.detail
        == "session_state projection is ahead of canonical events"
    )
    assert events_after_rebuild == events_before_corruption
    assert snapshot_after_rebuild == snapshot_before_corruption
    assert recovered_health.state == "ok"


def test_artifact_write_failure_leaves_no_event_and_retry_recovers(
    tmp_path: Path,
) -> None:
    connection = open_initialized_database(tmp_path)
    try:
        ids = append_representative_completed_session(connection, tmp_path)
        artifact_id = new_artifact_id()
        artifact_path = artifact_relative_path(ids.session_id, artifact_id, ".log")
        blocking_directory = tmp_path / artifact_path
        blocking_directory.mkdir(parents=True)

        with pytest.raises(IsADirectoryError):
            record_text_artifact(
                connection,
                tmp_path,
                ids.session_id,
                ids.turn_id,
                ids.tool_call_id,
                "fault_log",
                "partial diagnostic\n",
                suffix=".log",
                artifact_id=artifact_id,
            )

        events_after_failure = read_events_by_correlation_id(
            connection,
            ids.session_id,
            tool_call_id=ids.tool_call_id,
        )

        blocking_directory.rmdir()
        recovered_artifact, recovered_event = record_text_artifact(
            connection,
            tmp_path,
            ids.session_id,
            ids.turn_id,
            ids.tool_call_id,
            "fault_log",
            "recovered diagnostic\n",
            suffix=".log",
            artifact_id=artifact_id,
        )
        events_after_recovery = read_events_by_correlation_id(
            connection,
            ids.session_id,
            tool_call_id=ids.tool_call_id,
        )
    finally:
        connection.close()

    assert all(
        not isinstance(event.payload, ToolArtifactRecorded)
        for event in events_after_failure
    )
    assert isinstance(recovered_event.payload, ToolArtifactRecorded)
    assert recovered_artifact.absolute_path.is_file()
    assert recovered_artifact.absolute_path.read_text() == "recovered diagnostic\n"
    assert isinstance(events_after_recovery[-1].payload, ToolArtifactRecorded)


def test_event_transport_backpressure_records_drops_and_reconnects() -> None:
    async def scenario() -> None:
        transport: EventBus[str] = EventBus(subscriber_queue_size=1)

        async with transport.subscribe() as slow_subscription:
            transport.publish("stale-before-reconnect")
            transport.publish("fresh-before-reconnect")

            assert await slow_subscription.get() == "fresh-before-reconnect"
            assert transport.stats().subscriber_count == 1
            assert transport.stats().dropped_events == 1

        assert transport.stats().subscriber_count == 0

        async with transport.subscribe() as reconnected_subscription:
            transport.publish("after-reconnect")

            assert await reconnected_subscription.get() == "after-reconnect"
            assert transport.stats().subscriber_count == 1
            assert transport.stats().dropped_events == 1

        assert transport.stats().subscriber_count == 0

    asyncio.run(scenario())
