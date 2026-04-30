"""Verification-ledger projection read helpers for SQLite-backed stores."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import TaskVerificationLedgerRecord
from glassbox.core.models import TaskVerificationLedgerSummary
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import VerificationCheckKind
from glassbox.core.types import VerificationFailureCategory
from glassbox.core.types import VerificationPlanSource


def list_task_verification_ledger(
    connection: sqlite3.Connection,
    session_id: SessionId,
    task_id: TaskId,
) -> list[TaskVerificationLedgerRecord]:
    """Read long-run verification ledger entries for a task."""

    rows = connection.execute(
        """
        select
            session_id,
            task_id,
            verification_id,
            step_id,
            status,
            check_name,
            kind,
            source,
            command_json,
            changed_paths_json,
            eval_case_id,
            eval_profile_id,
            blocking,
            attempt_count,
            latest_attempt,
            planned_sequence,
            started_sequence,
            last_success_sequence,
            latest_failed_sequence,
            latest_failed_summary,
            latest_failed_category,
            latest_failed_artifact_id,
            latest_artifact_id,
            accepted_risk_count,
            accepted_risks_json,
            residual_risk_reason,
            summary,
            updated_at,
            last_sequence
        from task_verification_ledger
        where session_id = ? and task_id = ?
        order by last_sequence asc, verification_id asc
        """,
        (str(session_id), str(task_id)),
    ).fetchall()
    return [_ledger_record_from_row(row) for row in rows]


def get_task_verification_ledger_summary(
    connection: sqlite3.Connection,
    session_id: SessionId,
    task_id: TaskId,
) -> TaskVerificationLedgerSummary:
    """Summarize the current verification posture for a task."""

    entries = list_task_verification_ledger(connection, session_id, task_id)
    passed = [
        entry for entry in entries if entry.status == TaskVerificationStatus.PASSED
    ]
    failed = [
        entry for entry in entries if entry.status == TaskVerificationStatus.FAILED
    ]
    running = [
        entry for entry in entries if entry.status == TaskVerificationStatus.RUNNING
    ]
    skipped = [
        entry for entry in entries if entry.status == TaskVerificationStatus.SKIPPED
    ]
    failed_history = [
        entry for entry in entries if entry.latest_failed_sequence is not None
    ]
    latest_success = max(
        passed,
        key=lambda entry: entry.last_success_sequence or entry.last_sequence,
        default=None,
    )
    latest_failed = max(
        failed_history,
        key=lambda entry: entry.latest_failed_sequence or entry.last_sequence,
        default=None,
    )
    accepted_risk_count = sum(entry.accepted_risk_count for entry in entries)
    return TaskVerificationLedgerSummary(
        task_id=task_id,
        total_count=len(entries),
        passed_count=len(passed),
        failed_count=len(failed),
        running_count=len(running),
        skipped_count=len(skipped),
        accepted_risk_count=accepted_risk_count,
        latest_success_verification_id=(
            latest_success.verification_id if latest_success else None
        ),
        latest_success_check_name=latest_success.check_name if latest_success else None,
        latest_success_sequence=(
            latest_success.last_success_sequence if latest_success else None
        ),
        latest_failed_verification_id=(
            latest_failed.verification_id if latest_failed else None
        ),
        latest_failed_check_name=latest_failed.check_name if latest_failed else None,
        latest_failed_sequence=(
            latest_failed.latest_failed_sequence if latest_failed else None
        ),
        latest_failed_summary=(
            latest_failed.latest_failed_summary if latest_failed else None
        ),
        current_posture=_current_posture(
            entries=entries,
            failed_count=len(failed),
            running_count=len(running),
            passed_count=len(passed),
            accepted_risk_count=accepted_risk_count,
        ),
    )


def _ledger_record_from_row(row: sqlite3.Row) -> TaskVerificationLedgerRecord:
    return TaskVerificationLedgerRecord(
        session_id=row["session_id"],
        task_id=row["task_id"],
        verification_id=row["verification_id"],
        step_id=row["step_id"],
        status=TaskVerificationStatus(row["status"]),
        check_name=row["check_name"],
        kind=VerificationCheckKind(row["kind"]) if row["kind"] else None,
        source=VerificationPlanSource(row["source"]) if row["source"] else None,
        command=_json_str_list(row["command_json"]),
        changed_paths=[
            Path(path) for path in _json_str_list(row["changed_paths_json"])
        ],
        eval_case_id=row["eval_case_id"],
        eval_profile_id=row["eval_profile_id"],
        blocking=bool(row["blocking"]),
        attempt_count=row["attempt_count"],
        latest_attempt=row["latest_attempt"],
        planned_sequence=row["planned_sequence"],
        started_sequence=row["started_sequence"],
        last_success_sequence=row["last_success_sequence"],
        latest_failed_sequence=row["latest_failed_sequence"],
        latest_failed_summary=row["latest_failed_summary"],
        latest_failed_category=(
            VerificationFailureCategory(row["latest_failed_category"])
            if row["latest_failed_category"]
            else None
        ),
        latest_failed_artifact_id=row["latest_failed_artifact_id"],
        latest_artifact_id=row["latest_artifact_id"],
        accepted_risk_count=row["accepted_risk_count"],
        accepted_risks=_json_str_list(row["accepted_risks_json"]),
        residual_risk_reason=row["residual_risk_reason"],
        summary=row["summary"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
    )


def _json_str_list(raw_json: str) -> list[str]:
    value: Any = json.loads(raw_json)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _current_posture(
    *,
    entries: list[TaskVerificationLedgerRecord],
    failed_count: int,
    running_count: int,
    passed_count: int,
    accepted_risk_count: int,
) -> str:
    if not entries:
        return "missing"
    if failed_count:
        return "failing"
    if running_count:
        return "running"
    if accepted_risk_count:
        return "accepted_with_risk"
    if passed_count == len(entries):
        return "verified"
    return "partial"


__all__ = [
    "get_task_verification_ledger_summary",
    "list_task_verification_ledger",
]
