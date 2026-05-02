"""Changeset projection read helpers for SQLite-backed stores."""

import json
import sqlite3
from datetime import datetime

from glassbox.core.ids import ChangesetId
from glassbox.core.ids import SessionId
from glassbox.core.models import ChangesetInventoryRecord
from glassbox.core.models import ChangesetReadinessRecord
from glassbox.core.models import ChangesetRecord
from glassbox.core.models import ChangesetReviewBriefRecord
from glassbox.core.models import ChangesetSourceRecord
from glassbox.core.models import ChangesetVerificationPostureRecord
from glassbox.core.types import ChangesetInventoryFreshness
from glassbox.core.types import ChangesetReadinessKind
from glassbox.core.types import ChangesetReadinessState
from glassbox.core.types import ChangesetRiskLevel
from glassbox.core.types import ChangesetSourceKind
from glassbox.core.types import ChangesetVerificationState


def list_changesets(
    connection: sqlite3.Connection,
    *,
    session_id: SessionId | None = None,
    include_archived: bool = False,
    limit: int | None = None,
) -> list[ChangesetRecord]:
    query = _changeset_select_sql() + " where 1 = 1"
    parameters: list[object] = []
    if session_id is not None:
        query += " and session_id = ?"
        parameters.append(str(session_id))
    if not include_archived:
        query += " and status != 'archived'"
    query += " order by updated_at desc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    rows = connection.execute(query, parameters).fetchall()
    return [_changeset_record_from_row(row) for row in rows]


def get_changeset(
    connection: sqlite3.Connection,
    changeset_id: ChangesetId,
) -> ChangesetRecord | None:
    row = connection.execute(
        _changeset_select_sql() + " where changeset_id = ?",
        (str(changeset_id),),
    ).fetchone()
    if row is None:
        return None
    return _changeset_record_from_row(row)


def list_changeset_sources(
    connection: sqlite3.Connection,
    session_id: SessionId,
    changeset_id: ChangesetId,
) -> list[ChangesetSourceRecord]:
    rows = connection.execute(
        """
        select
            session_id, changeset_id, source_kind, source_session_id, task_id,
            turn_id, branch_search_id, branch_candidate_id, verification_id,
            artifact_id, reason, limitation, created_at, last_sequence
        from changeset_sources
        where session_id = ? and changeset_id = ?
        order by last_sequence asc
        """,
        (str(session_id), str(changeset_id)),
    ).fetchall()
    return [_changeset_source_record_from_row(row) for row in rows]


def get_changeset_inventory(
    connection: sqlite3.Connection,
    session_id: SessionId,
    changeset_id: ChangesetId,
) -> ChangesetInventoryRecord | None:
    row = connection.execute(
        """
        select
            session_id, changeset_id, artifact_id, artifact_schema_version,
            freshness, changed_path_count, source_digest, previous_artifact_id,
            refreshed_by, risk_level, risk_summary, unresolved_risk_count,
            accepted_risk_count, task_id, turn_id, branch_search_id,
            branch_candidate_id, updated_at, last_sequence
        from changeset_inventories
        where session_id = ? and changeset_id = ?
        """,
        (str(session_id), str(changeset_id)),
    ).fetchone()
    if row is None:
        return None
    return _changeset_inventory_record_from_row(row)


def get_changeset_verification_posture(
    connection: sqlite3.Connection,
    session_id: SessionId,
    changeset_id: ChangesetId,
) -> ChangesetVerificationPostureRecord | None:
    row = connection.execute(
        """
        select
            session_id, changeset_id, state, summary, verification_id, artifact_id,
            task_id, turn_id, stale_count, missing_count, failed_count,
            accepted_risk_count, updated_at, last_sequence
        from changeset_verification_posture
        where session_id = ? and changeset_id = ?
        """,
        (str(session_id), str(changeset_id)),
    ).fetchone()
    if row is None:
        return None
    return _changeset_verification_record_from_row(row)


def list_changeset_review_briefs(
    connection: sqlite3.Connection,
    session_id: SessionId,
    changeset_id: ChangesetId,
) -> list[ChangesetReviewBriefRecord]:
    rows = connection.execute(
        """
        select
            session_id, changeset_id, artifact_id, artifact_schema_version,
            render_targets_json, inventory_artifact_id, verification_id,
            task_id, turn_id, created_by, redacted, local_only, created_at,
            last_sequence
        from changeset_review_briefs
        where session_id = ? and changeset_id = ?
        order by created_at desc, artifact_id asc
        """,
        (str(session_id), str(changeset_id)),
    ).fetchall()
    return [_changeset_review_brief_record_from_row(row) for row in rows]


def list_changeset_readiness(
    connection: sqlite3.Connection,
    session_id: SessionId,
    changeset_id: ChangesetId,
) -> list[ChangesetReadinessRecord]:
    rows = connection.execute(
        """
        select
            session_id, changeset_id, readiness_kind, state, reason,
            blockers_json, safe_next_actions_json, inventory_artifact_id,
            review_brief_artifact_id, verification_id, task_id, turn_id,
            accepted_risk_count, decided_by, updated_at, last_sequence
        from changeset_readiness
        where session_id = ? and changeset_id = ?
        order by readiness_kind asc
        """,
        (str(session_id), str(changeset_id)),
    ).fetchall()
    return [_changeset_readiness_record_from_row(row) for row in rows]


def _changeset_select_sql() -> str:
    return """
        select
            session_id, changeset_id, objective, summary, status, created_by,
            archived_by, archived_reason, replacement_changeset_id, task_id,
            turn_id, branch_search_id, branch_candidate_id,
            latest_inventory_artifact_id, latest_verification_id,
            latest_review_brief_artifact_id, risk_level, risk_summary,
            unresolved_risk_count, accepted_risk_count, created_at, updated_at,
            last_sequence
        from changesets
    """


def _changeset_record_from_row(row: sqlite3.Row) -> ChangesetRecord:
    return ChangesetRecord(
        session_id=row["session_id"],
        changeset_id=row["changeset_id"],
        objective=row["objective"],
        summary=row["summary"],
        status=row["status"],
        created_by=row["created_by"],
        archived_by=row["archived_by"],
        archived_reason=row["archived_reason"],
        replacement_changeset_id=row["replacement_changeset_id"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        branch_search_id=row["branch_search_id"],
        branch_candidate_id=row["branch_candidate_id"],
        latest_inventory_artifact_id=row["latest_inventory_artifact_id"],
        latest_verification_id=row["latest_verification_id"],
        latest_review_brief_artifact_id=row["latest_review_brief_artifact_id"],
        risk_level=ChangesetRiskLevel(row["risk_level"]),
        risk_summary=row["risk_summary"],
        unresolved_risk_count=row["unresolved_risk_count"],
        accepted_risk_count=row["accepted_risk_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
    )


def _changeset_source_record_from_row(row: sqlite3.Row) -> ChangesetSourceRecord:
    return ChangesetSourceRecord(
        session_id=row["session_id"],
        changeset_id=row["changeset_id"],
        source_kind=ChangesetSourceKind(row["source_kind"]),
        source_session_id=row["source_session_id"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        branch_search_id=row["branch_search_id"],
        branch_candidate_id=row["branch_candidate_id"],
        verification_id=row["verification_id"],
        artifact_id=row["artifact_id"],
        reason=row["reason"],
        limitation=row["limitation"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_sequence=row["last_sequence"],
    )


def _changeset_inventory_record_from_row(
    row: sqlite3.Row,
) -> ChangesetInventoryRecord:
    return ChangesetInventoryRecord(
        session_id=row["session_id"],
        changeset_id=row["changeset_id"],
        artifact_id=row["artifact_id"],
        artifact_schema_version=row["artifact_schema_version"],
        freshness=ChangesetInventoryFreshness(row["freshness"]),
        changed_path_count=row["changed_path_count"],
        source_digest=row["source_digest"],
        previous_artifact_id=row["previous_artifact_id"],
        refreshed_by=row["refreshed_by"],
        risk_level=ChangesetRiskLevel(row["risk_level"]),
        risk_summary=row["risk_summary"],
        unresolved_risk_count=row["unresolved_risk_count"],
        accepted_risk_count=row["accepted_risk_count"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        branch_search_id=row["branch_search_id"],
        branch_candidate_id=row["branch_candidate_id"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
    )


def _changeset_verification_record_from_row(
    row: sqlite3.Row,
) -> ChangesetVerificationPostureRecord:
    return ChangesetVerificationPostureRecord(
        session_id=row["session_id"],
        changeset_id=row["changeset_id"],
        state=ChangesetVerificationState(row["state"]),
        summary=row["summary"],
        verification_id=row["verification_id"],
        artifact_id=row["artifact_id"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        stale_count=row["stale_count"],
        missing_count=row["missing_count"],
        failed_count=row["failed_count"],
        accepted_risk_count=row["accepted_risk_count"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
    )


def _changeset_review_brief_record_from_row(
    row: sqlite3.Row,
) -> ChangesetReviewBriefRecord:
    return ChangesetReviewBriefRecord(
        session_id=row["session_id"],
        changeset_id=row["changeset_id"],
        artifact_id=row["artifact_id"],
        artifact_schema_version=row["artifact_schema_version"],
        render_targets=json.loads(row["render_targets_json"]),
        inventory_artifact_id=row["inventory_artifact_id"],
        verification_id=row["verification_id"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        created_by=row["created_by"],
        redacted=bool(row["redacted"]),
        local_only=bool(row["local_only"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        last_sequence=row["last_sequence"],
    )


def _changeset_readiness_record_from_row(
    row: sqlite3.Row,
) -> ChangesetReadinessRecord:
    return ChangesetReadinessRecord(
        session_id=row["session_id"],
        changeset_id=row["changeset_id"],
        readiness_kind=ChangesetReadinessKind(row["readiness_kind"]),
        state=ChangesetReadinessState(row["state"]),
        reason=row["reason"],
        blockers=json.loads(row["blockers_json"]),
        safe_next_actions=json.loads(row["safe_next_actions_json"]),
        inventory_artifact_id=row["inventory_artifact_id"],
        review_brief_artifact_id=row["review_brief_artifact_id"],
        verification_id=row["verification_id"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        accepted_risk_count=row["accepted_risk_count"],
        decided_by=row["decided_by"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
    )


__all__ = [
    "get_changeset",
    "get_changeset_inventory",
    "get_changeset_verification_posture",
    "list_changeset_readiness",
    "list_changeset_review_briefs",
    "list_changeset_sources",
    "list_changesets",
]
