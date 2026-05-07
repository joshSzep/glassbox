"""Review feedback projection read helpers for SQLite-backed stores."""

import sqlite3
from datetime import datetime

from glassbox.core.ids import ArtifactId
from glassbox.core.ids import ChangesetId
from glassbox.core.ids import ReviewFeedbackId
from glassbox.core.ids import SessionId
from glassbox.core.models import ReviewFeedbackFixupInventoryRecord
from glassbox.core.models import ReviewFeedbackFixupPathRecord
from glassbox.core.models import ReviewFeedbackRecord
from glassbox.core.models import ReviewFeedbackScopeRecord
from glassbox.core.types import ChangesetInventoryFreshness
from glassbox.core.types import ReviewFeedbackDisposition
from glassbox.core.types import ReviewFeedbackKind
from glassbox.core.types import ReviewFeedbackProvenance
from glassbox.core.types import ReviewFeedbackScopeKind
from glassbox.core.types import ReviewFixupSourceKind


def list_review_feedback(
    connection: sqlite3.Connection,
    *,
    session_id: SessionId | None = None,
    changeset_id: ChangesetId | None = None,
    disposition: ReviewFeedbackDisposition | None = None,
    include_archived: bool = False,
    file_path: str | None = None,
    limit: int | None = None,
) -> list[ReviewFeedbackRecord]:
    query = _feedback_select_sql()
    parameters: list[object] = []
    query += " where 1 = 1"
    if file_path is not None:
        query += """
            and exists (
                select 1
                from review_feedback_scopes s
                where s.session_id = f.session_id
                    and s.feedback_id = f.feedback_id
                    and s.file_path = ?
            )
        """
        parameters.append(file_path)
    if session_id is not None:
        query += " and f.session_id = ?"
        parameters.append(str(session_id))
    if changeset_id is not None:
        query += " and f.changeset_id = ?"
        parameters.append(str(changeset_id))
    if disposition is not None:
        query += " and f.disposition = ?"
        parameters.append(disposition.value)
    elif not include_archived:
        query += " and f.disposition != 'archived'"
    query += " order by f.updated_at desc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    rows = connection.execute(query, parameters).fetchall()
    return [_feedback_record_from_row(row) for row in rows]


def get_review_feedback(
    connection: sqlite3.Connection,
    feedback_id: ReviewFeedbackId,
) -> ReviewFeedbackRecord | None:
    row = connection.execute(
        _feedback_select_sql() + " where f.feedback_id = ?",
        (str(feedback_id),),
    ).fetchone()
    if row is None:
        return None
    return _feedback_record_from_row(row)


def list_review_feedback_scopes(
    connection: sqlite3.Connection,
    session_id: SessionId,
    feedback_id: ReviewFeedbackId,
) -> list[ReviewFeedbackScopeRecord]:
    rows = connection.execute(
        """
        select
            session_id, feedback_id, changeset_id, scope_kind, reason,
            source_session_id, task_id, turn_id, artifact_id, verification_id,
            branch_search_id, branch_candidate_id, file_path, line_start,
            line_end, created_at, last_sequence
        from review_feedback_scopes
        where session_id = ? and feedback_id = ?
        order by last_sequence asc
        """,
        (str(session_id), str(feedback_id)),
    ).fetchall()
    return [_scope_record_from_row(row) for row in rows]


def list_review_feedback_fixup_inventories(
    connection: sqlite3.Connection,
    session_id: SessionId,
    feedback_id: ReviewFeedbackId,
) -> list[ReviewFeedbackFixupInventoryRecord]:
    rows = connection.execute(
        """
        select
            session_id, feedback_id, changeset_id, artifact_id,
            artifact_schema_version, source_kind, source_summary, source_digest,
            inventory_freshness, changed_path_count, matched_scope_path_count,
            stale, stale_reason, recorded_by, task_id, turn_id, verification_id,
            created_at, last_sequence
        from review_feedback_fixup_inventories
        where session_id = ? and feedback_id = ?
        order by created_at desc
        """,
        (str(session_id), str(feedback_id)),
    ).fetchall()
    return [_fixup_inventory_record_from_row(row) for row in rows]


def list_review_feedback_fixup_paths(
    connection: sqlite3.Connection,
    session_id: SessionId,
    feedback_id: ReviewFeedbackId,
    artifact_id: ArtifactId,
) -> list[ReviewFeedbackFixupPathRecord]:
    rows = connection.execute(
        """
        select
            session_id, feedback_id, changeset_id, artifact_id, path,
            change_kind, generated, test_file, docs_file, policy_sensitive,
            risk_level, provenance_confidence, matches_feedback_scope,
            summary, last_sequence
        from review_feedback_fixup_paths
        where session_id = ? and feedback_id = ? and artifact_id = ?
        order by matches_feedback_scope desc, path asc
        """,
        (str(session_id), str(feedback_id), str(artifact_id)),
    ).fetchall()
    return [_fixup_path_record_from_row(row) for row in rows]


def _feedback_select_sql() -> str:
    return """
        select
            f.session_id, f.feedback_id, f.changeset_id, f.feedback_kind,
            f.provenance, f.disposition, f.summary, f.body, f.source_label,
            f.reviewer_label, f.created_by, f.updated_by, f.resolved_by,
            f.archived_by, f.accepted_by, f.source_session_id, f.task_id,
            f.turn_id, f.artifact_id, f.verification_id, f.resolution_summary,
            f.residual_risk, f.risk_summary, f.acceptance_reason,
            f.archived_reason, f.replacement_feedback_id, f.reopened_count,
            f.created_at, f.updated_at, f.last_sequence
        from review_feedback f
    """


def _feedback_record_from_row(row: sqlite3.Row) -> ReviewFeedbackRecord:
    return ReviewFeedbackRecord(
        session_id=row["session_id"],
        feedback_id=row["feedback_id"],
        changeset_id=row["changeset_id"],
        feedback_kind=ReviewFeedbackKind(row["feedback_kind"]),
        provenance=ReviewFeedbackProvenance(row["provenance"]),
        disposition=ReviewFeedbackDisposition(row["disposition"]),
        summary=row["summary"],
        body=row["body"],
        source_label=row["source_label"],
        reviewer_label=row["reviewer_label"],
        created_by=row["created_by"],
        updated_by=row["updated_by"],
        resolved_by=row["resolved_by"],
        archived_by=row["archived_by"],
        accepted_by=row["accepted_by"],
        source_session_id=row["source_session_id"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        artifact_id=row["artifact_id"],
        verification_id=row["verification_id"],
        resolution_summary=row["resolution_summary"],
        residual_risk=row["residual_risk"],
        risk_summary=row["risk_summary"],
        acceptance_reason=row["acceptance_reason"],
        archived_reason=row["archived_reason"],
        replacement_feedback_id=row["replacement_feedback_id"],
        reopened_count=row["reopened_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
    )


def _scope_record_from_row(row: sqlite3.Row) -> ReviewFeedbackScopeRecord:
    return ReviewFeedbackScopeRecord(
        session_id=row["session_id"],
        feedback_id=row["feedback_id"],
        changeset_id=row["changeset_id"],
        scope_kind=ReviewFeedbackScopeKind(row["scope_kind"]),
        reason=row["reason"],
        source_session_id=row["source_session_id"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        artifact_id=row["artifact_id"],
        verification_id=row["verification_id"],
        branch_search_id=row["branch_search_id"],
        branch_candidate_id=row["branch_candidate_id"],
        file_path=row["file_path"],
        line_start=row["line_start"],
        line_end=row["line_end"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_sequence=row["last_sequence"],
    )


def _fixup_inventory_record_from_row(
    row: sqlite3.Row,
) -> ReviewFeedbackFixupInventoryRecord:
    return ReviewFeedbackFixupInventoryRecord(
        session_id=row["session_id"],
        feedback_id=row["feedback_id"],
        changeset_id=row["changeset_id"],
        artifact_id=row["artifact_id"],
        artifact_schema_version=row["artifact_schema_version"],
        source_kind=ReviewFixupSourceKind(row["source_kind"]),
        source_summary=row["source_summary"],
        source_digest=row["source_digest"],
        inventory_freshness=ChangesetInventoryFreshness(row["inventory_freshness"]),
        changed_path_count=row["changed_path_count"],
        matched_scope_path_count=row["matched_scope_path_count"],
        stale=bool(row["stale"]),
        stale_reason=row["stale_reason"],
        recorded_by=row["recorded_by"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        verification_id=row["verification_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_sequence=row["last_sequence"],
    )


def _fixup_path_record_from_row(row: sqlite3.Row) -> ReviewFeedbackFixupPathRecord:
    return ReviewFeedbackFixupPathRecord(
        session_id=row["session_id"],
        feedback_id=row["feedback_id"],
        changeset_id=row["changeset_id"],
        artifact_id=row["artifact_id"],
        path=row["path"],
        change_kind=row["change_kind"],
        generated=bool(row["generated"]),
        test_file=bool(row["test_file"]),
        docs_file=bool(row["docs_file"]),
        policy_sensitive=bool(row["policy_sensitive"]),
        risk_level=row["risk_level"],
        provenance_confidence=row["provenance_confidence"],
        matches_feedback_scope=bool(row["matches_feedback_scope"]),
        summary=row["summary"],
        last_sequence=row["last_sequence"],
    )


__all__ = [
    "get_review_feedback",
    "list_review_feedback_fixup_inventories",
    "list_review_feedback_fixup_paths",
    "list_review_feedback",
    "list_review_feedback_scopes",
]
