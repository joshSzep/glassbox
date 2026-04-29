"""Branch-search projection read helpers for SQLite-backed stores."""

import sqlite3
from datetime import datetime

from glassbox.core.ids import BranchSearchId
from glassbox.core.ids import SessionId
from glassbox.core.models import BranchCandidateRecord
from glassbox.core.models import BranchSearchRecord
from glassbox.core.types import BranchCandidateStatus
from glassbox.core.types import BranchCandidateVerificationStatus
from glassbox.core.types import BranchSearchStatus


def list_branch_searches(
    connection: sqlite3.Connection,
    *,
    session_id: SessionId | None = None,
    limit: int | None = None,
) -> list[BranchSearchRecord]:
    """Read branch-search summaries."""

    query = _branch_search_select_sql() + " where 1 = 1"
    parameters: list[object] = []
    if session_id is not None:
        query += " and branch_searches.session_id = ?"
        parameters.append(str(session_id))
    query += """
        group by branch_searches.session_id, branch_searches.search_id
        order by branch_searches.updated_at desc
    """
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    rows = connection.execute(query, parameters).fetchall()
    return [_branch_search_record_from_row(row) for row in rows]


def get_branch_search(
    connection: sqlite3.Connection,
    search_id: BranchSearchId,
) -> BranchSearchRecord | None:
    """Read one branch-search summary."""

    row = connection.execute(
        _branch_search_select_sql()
        + """
        where branch_searches.search_id = ?
        group by branch_searches.session_id, branch_searches.search_id
        """,
        (str(search_id),),
    ).fetchone()
    if row is None:
        return None
    return _branch_search_record_from_row(row)


def list_branch_candidates(
    connection: sqlite3.Connection,
    session_id: SessionId,
    search_id: BranchSearchId,
) -> list[BranchCandidateRecord]:
    """Read candidate rows for a branch search."""

    rows = connection.execute(
        """
        select
            search_id,
            candidate_id,
            parent_session_id,
            candidate_session_id,
            strategy_label,
            status,
            verification_status,
            selection_state,
            verification_summary,
            verification_id,
            artifact_id,
            created_at,
            updated_at,
            last_sequence
        from branch_candidates
        where session_id = ? and search_id = ?
        order by created_at asc, candidate_id asc
        """,
        (str(session_id), str(search_id)),
    ).fetchall()
    return [_branch_candidate_record_from_row(row) for row in rows]


def _branch_search_select_sql() -> str:
    return """
        select
            branch_searches.search_id,
            branch_searches.session_id,
            branch_searches.parent_session_id,
            branch_searches.task_id,
            branch_searches.objective,
            branch_searches.status,
            branch_searches.selected_candidate_id,
            branch_searches.abandoned_reason,
            branch_searches.created_at,
            branch_searches.updated_at,
            branch_searches.last_sequence,
            count(branch_candidates.candidate_id) as candidate_count
        from branch_searches
        left join branch_candidates
          on branch_candidates.session_id = branch_searches.session_id
         and branch_candidates.search_id = branch_searches.search_id
    """


def _branch_search_record_from_row(row: sqlite3.Row) -> BranchSearchRecord:
    return BranchSearchRecord(
        search_id=row["search_id"],
        session_id=row["session_id"],
        parent_session_id=row["parent_session_id"],
        task_id=row["task_id"],
        status=BranchSearchStatus(row["status"]),
        objective=row["objective"],
        selected_candidate_id=row["selected_candidate_id"],
        abandoned_reason=row["abandoned_reason"],
        candidate_count=row["candidate_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
    )


def _branch_candidate_record_from_row(row: sqlite3.Row) -> BranchCandidateRecord:
    return BranchCandidateRecord(
        search_id=row["search_id"],
        candidate_id=row["candidate_id"],
        parent_session_id=row["parent_session_id"],
        candidate_session_id=row["candidate_session_id"],
        strategy_label=row["strategy_label"],
        status=BranchCandidateStatus(row["status"]),
        verification_status=BranchCandidateVerificationStatus(
            row["verification_status"]
        ),
        selection_state=(
            BranchCandidateStatus(row["selection_state"])
            if row["selection_state"]
            else None
        ),
        verification_summary=row["verification_summary"],
        verification_id=row["verification_id"],
        artifact_id=row["artifact_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
    )


__all__ = [
    "get_branch_search",
    "list_branch_candidates",
    "list_branch_searches",
]
