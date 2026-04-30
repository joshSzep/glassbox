"""Branch-search SQLite schema migrations."""

import sqlite3


def ensure_branch_search_projection_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists branch_searches (
            session_id text not null,
            search_id text not null,
            parent_session_id text not null,
            task_id text,
            objective text not null,
            status text not null,
            selected_candidate_id text,
            abandoned_reason text,
            created_at text not null,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, search_id),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_branch_searches_session_updated
            on branch_searches (session_id, updated_at desc)
        """
    )
    connection.execute(
        """
        create table if not exists branch_candidates (
            session_id text not null,
            search_id text not null,
            candidate_id text not null,
            parent_session_id text not null,
            candidate_session_id text,
            strategy_label text not null,
            status text not null,
            verification_status text not null,
            selection_state text,
            verification_summary text,
            verification_id text,
            artifact_id text,
            created_at text not null,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, candidate_id),
            foreign key (session_id, search_id)
                references branch_searches(session_id, search_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_branch_candidates_search
            on branch_candidates (session_id, search_id, updated_at)
        """
    )
