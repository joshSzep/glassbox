"""SQLite mutations for handoff projection rows."""

import json
import sqlite3
from typing import Any

from glassbox.core.events import EventEnvelope
from glassbox.core.types import HandoffSourceKind


def upsert_handoff_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    *,
    package_id: str,
    source_kind: str | None = None,
    source_id: str | None = None,
    task_id: str | None = None,
    changeset_id: str | None = None,
    package_kind: str | None = None,
    intent: str | None = None,
    artifact_id: str | None = None,
    package_digest: str | None = None,
    compatibility_state: str | None = None,
    redaction_posture: str | None = None,
    local_only_count: int | None = None,
    custody_state: str,
    expected_custodian: str | None = None,
    current_custodian: str | None = None,
    exported_by: str | None = None,
    decision_by: str | None = None,
    decision_reason: str | None = None,
    follow_up_intent: str | None = None,
    safe_next_actions: list[str] | None = None,
    note: str | None = None,
    imported: bool | None = None,
    archived: bool | None = None,
) -> None:
    values: dict[str, Any] = {
        "session_id": str(event.session_id),
        "package_id": package_id,
        "source_kind": source_kind or HandoffSourceKind.IMPORTED_PACKAGE.value,
        "source_id": source_id,
        "task_id": task_id,
        "changeset_id": changeset_id,
        "package_kind": package_kind,
        "intent": intent,
        "artifact_id": artifact_id,
        "package_digest": package_digest,
        "compatibility_state": compatibility_state,
        "redaction_posture": redaction_posture,
        "local_only_count": local_only_count if local_only_count is not None else 0,
        "custody_state": custody_state,
        "expected_custodian": expected_custodian,
        "current_custodian": current_custodian,
        "exported_by": exported_by,
        "decision_by": decision_by,
        "decision_reason": decision_reason,
        "follow_up_intent": follow_up_intent,
        "safe_next_actions_json": json.dumps(safe_next_actions or []),
        "note": note,
        "imported": int(bool(imported)),
        "archived": int(bool(archived)),
        "created_at": event.created_at.isoformat(),
        "updated_at": event.created_at.isoformat(),
        "last_event_type": event.payload.event_type,
        "last_sequence": event.sequence,
    }
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f"""
        insert into handoffs ({columns})
        values ({placeholders})
        on conflict(session_id, package_id) do update set
            source_kind = coalesce(excluded.source_kind, handoffs.source_kind),
            source_id = coalesce(excluded.source_id, handoffs.source_id),
            task_id = coalesce(excluded.task_id, handoffs.task_id),
            changeset_id = coalesce(excluded.changeset_id, handoffs.changeset_id),
            package_kind = coalesce(excluded.package_kind, handoffs.package_kind),
            intent = coalesce(excluded.intent, handoffs.intent),
            artifact_id = coalesce(excluded.artifact_id, handoffs.artifact_id),
            package_digest = coalesce(
                excluded.package_digest,
                handoffs.package_digest
            ),
            compatibility_state = coalesce(
                excluded.compatibility_state,
                handoffs.compatibility_state
            ),
            redaction_posture = coalesce(
                excluded.redaction_posture,
                handoffs.redaction_posture
            ),
            local_only_count = case
                when excluded.local_only_count > 0 then excluded.local_only_count
                else handoffs.local_only_count
            end,
            custody_state = excluded.custody_state,
            expected_custodian = coalesce(
                excluded.expected_custodian,
                handoffs.expected_custodian
            ),
            current_custodian = coalesce(
                excluded.current_custodian,
                handoffs.current_custodian
            ),
            exported_by = coalesce(excluded.exported_by, handoffs.exported_by),
            decision_by = coalesce(excluded.decision_by, handoffs.decision_by),
            decision_reason = coalesce(
                excluded.decision_reason,
                handoffs.decision_reason
            ),
            follow_up_intent = coalesce(
                excluded.follow_up_intent,
                handoffs.follow_up_intent
            ),
            safe_next_actions_json = case
                when excluded.safe_next_actions_json != '[]'
                then excluded.safe_next_actions_json
                else handoffs.safe_next_actions_json
            end,
            note = coalesce(excluded.note, handoffs.note),
            imported = case
                when excluded.imported = 1 then 1
                else handoffs.imported
            end,
            archived = case
                when excluded.archived = 1 then 1
                else handoffs.archived
            end,
            updated_at = excluded.updated_at,
            last_event_type = excluded.last_event_type,
            last_sequence = excluded.last_sequence
        """,
        tuple(values.values()),
    )


__all__ = ["upsert_handoff_projection"]
