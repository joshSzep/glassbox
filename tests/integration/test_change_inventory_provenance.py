"""Integration coverage for change inventory provenance from retained events."""

from pathlib import Path

from glassbox.core import EventEnvelope
from glassbox.core import ModelToolCallRequested
from glassbox.core import SessionStarted
from glassbox.core import TaskCheckpointCreated
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.runtime.change_inventory import change_inventory_from_diff_summary
from glassbox.store import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.tools.workflow import DiffFileSummary
from glassbox.tools.workflow import DiffSummaryResult
from glassbox.tools.workflow import DiffSummaryScope


def test_change_inventory_marks_mixed_glassbox_and_manual_edits(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        session_id = _seed_provenance_events(repository, tmp_path)
        events = repository.read_session_events(session_id)

        artifact = change_inventory_from_diff_summary(
            DiffSummaryResult(
                scope=DiffSummaryScope.WORKSPACE,
                files=[
                    DiffFileSummary(
                        path="src/glassbox/runtime/change_inventory.py",
                        change_kind="modified",
                        insertions=16,
                        deletions=2,
                    ),
                    DiffFileSummary(
                        path="tests/integration/test_change_inventory_provenance.py",
                        change_kind="modified",
                        insertions=20,
                        deletions=0,
                        test_file=True,
                    ),
                    DiffFileSummary(
                        path="docs/manual-note.md",
                        change_kind="modified",
                        insertions=1,
                        deletions=0,
                        docs_file=True,
                    ),
                ],
            ),
            provenance_events=events,
        )
    finally:
        connection.close()

    by_path = {entry.path: entry for entry in artifact.paths}

    assert (
        by_path["src/glassbox/runtime/change_inventory.py"].provenance_confidence
        == "direct"
    )
    assert (
        by_path[
            "tests/integration/test_change_inventory_provenance.py"
        ].provenance_confidence
        == "direct"
    )
    assert by_path["docs/manual-note.md"].provenance_confidence == "unknown"
    assert artifact.summary.provenance_direct_path_count == 2
    assert artifact.summary.provenance_unknown_path_count == 1
    assert artifact.summary.externally_modified_path_count == 1


def _seed_provenance_events(
    repository: SQLiteSessionRepository,
    tmp_path: Path,
):
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    checkpoint_id = new_task_checkpoint_id()
    task_id = new_task_id()
    repository.append_events(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(tmp_path),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ModelToolCallRequested(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="apply_patch",
                    arguments_json=(
                        '{"patch":"*** Update File: '
                        'src/glassbox/runtime/change_inventory.py"}'
                    ),
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskCheckpointCreated(
                    checkpoint_id=checkpoint_id,
                    objective="attach provenance",
                    completed_step="added integration coverage",
                    next_action="run focused tests",
                    recovery_guidance="rerun the change inventory tests",
                    task_id=task_id,
                    turn_id=turn_id,
                    touched_files=[
                        "tests/integration/test_change_inventory_provenance.py"
                    ],
                ),
            ),
        ]
    )
    return session_id
