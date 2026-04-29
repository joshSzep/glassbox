"""Branch-search projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import BranchCandidateExecuted
from glassbox.core.events import BranchCandidateForked
from glassbox.core.events import BranchCandidatePlanned
from glassbox.core.events import BranchCandidateRejected
from glassbox.core.events import BranchCandidatesCompared
from glassbox.core.events import BranchCandidateSelected
from glassbox.core.events import BranchCandidateVerified
from glassbox.core.events import BranchSearchAbandoned
from glassbox.core.events import BranchSearchStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.types import BranchCandidateStatus
from glassbox.core.types import BranchCandidateVerificationStatus
from glassbox.core.types import BranchSearchStatus


def _apply_branch_search_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, BranchSearchStarted):
        connection.execute(
            """
            insert into branch_searches (
                session_id, search_id, parent_session_id, task_id, objective,
                status, created_at, updated_at, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, search_id) do update set
                parent_session_id = excluded.parent_session_id,
                task_id = excluded.task_id,
                objective = excluded.objective,
                status = excluded.status,
                updated_at = excluded.updated_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.search_id),
                str(payload.parent_session_id),
                str(payload.task_id) if payload.task_id else None,
                payload.objective,
                BranchSearchStatus.RUNNING.value,
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        return
    if isinstance(payload, BranchCandidatePlanned):
        parent_session_id = _parent_session_id(
            connection, event, str(payload.search_id)
        )
        connection.execute(
            """
            insert into branch_candidates (
                session_id, search_id, candidate_id, parent_session_id,
                strategy_label, status, verification_status, created_at, updated_at,
                last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, candidate_id) do update set
                search_id = excluded.search_id,
                strategy_label = excluded.strategy_label,
                status = excluded.status,
                updated_at = excluded.updated_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.search_id),
                str(payload.candidate_id),
                parent_session_id,
                payload.strategy_label,
                BranchCandidateStatus.PLANNED.value,
                BranchCandidateVerificationStatus.NOT_RUN.value,
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        _touch_search(connection, event, str(payload.search_id))
        return
    if isinstance(payload, BranchCandidateForked):
        _update_candidate(
            connection,
            event,
            payload.search_id,
            payload.candidate_id,
            status=BranchCandidateStatus.FORKED,
            candidate_session_id=str(payload.candidate_session_id),
        )
        return
    if isinstance(payload, BranchCandidateExecuted):
        _update_candidate(
            connection,
            event,
            payload.search_id,
            payload.candidate_id,
            status=BranchCandidateStatus.EXECUTED,
        )
        return
    if isinstance(payload, BranchCandidateVerified):
        _update_candidate(
            connection,
            event,
            payload.search_id,
            payload.candidate_id,
            status=BranchCandidateStatus.VERIFIED,
            verification_status=payload.verification_status,
            verification_summary=payload.summary,
            verification_id=str(payload.verification_id)
            if payload.verification_id
            else None,
            artifact_id=str(payload.artifact_id) if payload.artifact_id else None,
        )
        return
    if isinstance(payload, BranchCandidatesCompared):
        _touch_search(connection, event, str(payload.search_id))
        return
    if isinstance(payload, BranchCandidateSelected):
        _update_candidate(
            connection,
            event,
            payload.search_id,
            payload.candidate_id,
            status=BranchCandidateStatus.SELECTED,
            selection_state=BranchCandidateStatus.SELECTED,
        )
        connection.execute(
            """
            update branch_searches
            set selected_candidate_id = ?, status = ?, updated_at = ?,
                last_sequence = ?
            where session_id = ? and search_id = ?
            """,
            (
                str(payload.candidate_id),
                BranchSearchStatus.COMPLETED.value,
                event.created_at.isoformat(),
                event.sequence,
                str(event.session_id),
                str(payload.search_id),
            ),
        )
        return
    if isinstance(payload, BranchCandidateRejected):
        _update_candidate(
            connection,
            event,
            payload.search_id,
            payload.candidate_id,
            status=BranchCandidateStatus.REJECTED,
            selection_state=BranchCandidateStatus.REJECTED,
        )
        return
    if isinstance(payload, BranchSearchAbandoned):
        connection.execute(
            """
            update branch_searches
            set status = ?, abandoned_reason = ?, updated_at = ?, last_sequence = ?
            where session_id = ? and search_id = ?
            """,
            (
                BranchSearchStatus.ABANDONED.value,
                payload.reason,
                event.created_at.isoformat(),
                event.sequence,
                str(event.session_id),
                str(payload.search_id),
            ),
        )


def _update_candidate(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    search_id,
    candidate_id,
    *,
    status: BranchCandidateStatus,
    candidate_session_id: str | None = None,
    verification_status: BranchCandidateVerificationStatus | None = None,
    selection_state: BranchCandidateStatus | None = None,
    verification_summary: str | None = None,
    verification_id: str | None = None,
    artifact_id: str | None = None,
) -> None:
    assignments = ["status = ?", "updated_at = ?", "last_sequence = ?"]
    parameters: list[object] = [
        status.value,
        event.created_at.isoformat(),
        event.sequence,
    ]
    optional_values = {
        "candidate_session_id": candidate_session_id,
        "verification_status": verification_status.value
        if verification_status
        else None,
        "selection_state": selection_state.value if selection_state else None,
        "verification_summary": verification_summary,
        "verification_id": verification_id,
        "artifact_id": artifact_id,
    }
    for column_name, value in optional_values.items():
        if value is None:
            continue
        assignments.append(f"{column_name} = ?")
        parameters.append(value)
    parameters.extend([str(event.session_id), str(candidate_id)])
    connection.execute(
        f"""
        update branch_candidates
        set {", ".join(assignments)}
        where session_id = ? and candidate_id = ?
        """,
        parameters,
    )
    _touch_search(connection, event, str(search_id))


def _touch_search(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    search_id: str,
) -> None:
    connection.execute(
        """
        update branch_searches
        set updated_at = ?, last_sequence = ?
        where session_id = ? and search_id = ?
        """,
        (
            event.created_at.isoformat(),
            event.sequence,
            str(event.session_id),
            search_id,
        ),
    )


def _parent_session_id(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    search_id: str,
) -> str:
    row = connection.execute(
        """
        select parent_session_id from branch_searches
        where session_id = ? and search_id = ?
        """,
        (str(event.session_id), search_id),
    ).fetchone()
    return row["parent_session_id"] if row is not None else str(event.session_id)


__all__ = ["_apply_branch_search_projection"]
