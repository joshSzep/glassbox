"""Handoff projection read helpers for SQLite-backed stores."""

import json
import sqlite3
from datetime import datetime
from enum import StrEnum

from glassbox.core.ids import ChangesetId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import HandoffProjectionRecord
from glassbox.core.types import HandoffCompatibilityState
from glassbox.core.types import HandoffCustodyState
from glassbox.core.types import HandoffIntent
from glassbox.core.types import HandoffPackageKind
from glassbox.core.types import HandoffRedactionPosture
from glassbox.core.types import HandoffSourceKind


def get_handoff(
    connection: sqlite3.Connection,
    session_id: SessionId,
    package_id: str,
) -> HandoffProjectionRecord | None:
    row = connection.execute(
        _handoff_select_sql() + " where h.session_id = ? and h.package_id = ?",
        (str(session_id), package_id),
    ).fetchone()
    if row is None:
        return None
    return _handoff_record_from_row(row)


def list_handoffs(
    connection: sqlite3.Connection,
    *,
    session_id: SessionId | None = None,
    task_id: TaskId | None = None,
    changeset_id: ChangesetId | None = None,
    source_kind: HandoffSourceKind | None = None,
    include_archived: bool = False,
    limit: int | None = None,
) -> list[HandoffProjectionRecord]:
    query = _handoff_select_sql()
    parameters: list[object] = []
    query += " where 1 = 1"
    if session_id is not None:
        query += " and h.session_id = ?"
        parameters.append(str(session_id))
    if task_id is not None:
        query += " and h.task_id = ?"
        parameters.append(str(task_id))
    if changeset_id is not None:
        query += " and h.changeset_id = ?"
        parameters.append(str(changeset_id))
    if source_kind is not None:
        query += " and h.source_kind = ?"
        parameters.append(source_kind.value)
    if not include_archived:
        query += " and h.archived = 0"
    query += " order by h.updated_at desc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    rows = connection.execute(query, parameters).fetchall()
    return [_handoff_record_from_row(row) for row in rows]


def _handoff_select_sql() -> str:
    return """
        select
            h.session_id, h.package_id, h.source_kind, h.source_id, h.task_id,
            h.changeset_id, h.package_kind, h.intent, h.artifact_id,
            h.package_digest, h.compatibility_state, h.redaction_posture,
            h.local_only_count, h.custody_state, h.expected_custodian,
            h.current_custodian, h.exported_by, h.decision_by,
            h.decision_reason, h.follow_up_intent, h.safe_next_actions_json,
            h.note, h.imported, h.archived, h.created_at, h.updated_at,
            h.last_event_type, h.last_sequence
        from handoffs h
    """


def _handoff_record_from_row(row: sqlite3.Row) -> HandoffProjectionRecord:
    return HandoffProjectionRecord(
        session_id=row["session_id"],
        package_id=row["package_id"],
        source_kind=HandoffSourceKind(row["source_kind"]),
        source_id=row["source_id"],
        task_id=row["task_id"],
        changeset_id=row["changeset_id"],
        package_kind=_optional_enum(HandoffPackageKind, row["package_kind"]),
        intent=_optional_enum(HandoffIntent, row["intent"]),
        artifact_id=row["artifact_id"],
        package_digest=row["package_digest"],
        compatibility_state=_optional_enum(
            HandoffCompatibilityState,
            row["compatibility_state"],
        ),
        redaction_posture=_optional_enum(
            HandoffRedactionPosture,
            row["redaction_posture"],
        ),
        local_only_count=row["local_only_count"],
        custody_state=HandoffCustodyState(row["custody_state"]),
        expected_custodian=row["expected_custodian"],
        current_custodian=row["current_custodian"],
        exported_by=row["exported_by"],
        decision_by=row["decision_by"],
        decision_reason=row["decision_reason"],
        follow_up_intent=_optional_enum(HandoffIntent, row["follow_up_intent"]),
        safe_next_actions=json.loads(row["safe_next_actions_json"]),
        note=row["note"],
        imported=bool(row["imported"]),
        archived=bool(row["archived"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_event_type=row["last_event_type"],
        last_sequence=row["last_sequence"],
    )


def _optional_enum[EnumT: StrEnum](
    enum_type: type[EnumT],
    value: str | None,
) -> EnumT | None:
    if value is None:
        return None
    return enum_type(value)


__all__ = ["get_handoff", "list_handoffs"]
