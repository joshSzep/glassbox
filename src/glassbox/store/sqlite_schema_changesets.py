"""Changeset SQLite schema migrations."""

import sqlite3


def ensure_changeset_projection_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists changesets (
            session_id text not null,
            changeset_id text not null,
            objective text not null,
            summary text,
            status text not null,
            created_by text not null,
            archived_by text,
            archived_reason text,
            replacement_changeset_id text,
            task_id text,
            turn_id text,
            branch_search_id text,
            branch_candidate_id text,
            latest_inventory_artifact_id text,
            latest_verification_id text,
            latest_review_brief_artifact_id text,
            created_at text not null,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, changeset_id),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_changesets_session_updated
            on changesets (session_id, updated_at desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_changesets_task
            on changesets (session_id, task_id, updated_at desc)
        """
    )
    connection.execute(
        """
        create table if not exists changeset_sources (
            session_id text not null,
            changeset_id text not null,
            source_kind text not null,
            source_session_id text,
            task_id text,
            turn_id text,
            branch_search_id text,
            branch_candidate_id text,
            verification_id text,
            artifact_id text,
            reason text not null,
            limitation text,
            created_at text not null,
            last_sequence integer not null,
            primary key (session_id, last_sequence),
            foreign key (session_id, changeset_id)
                references changesets(session_id, changeset_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_changeset_sources_changeset
            on changeset_sources (session_id, changeset_id, last_sequence)
        """
    )
    connection.execute(
        """
        create table if not exists changeset_inventories (
            session_id text not null,
            changeset_id text not null,
            artifact_id text not null,
            artifact_schema_version integer not null,
            freshness text not null,
            changed_path_count integer not null,
            source_digest text,
            previous_artifact_id text,
            refreshed_by text not null,
            task_id text,
            turn_id text,
            branch_search_id text,
            branch_candidate_id text,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, changeset_id),
            foreign key (session_id, changeset_id)
                references changesets(session_id, changeset_id)
        )
        """
    )
    connection.execute(
        """
        create table if not exists changeset_verification_posture (
            session_id text not null,
            changeset_id text not null,
            state text not null,
            summary text not null,
            verification_id text,
            artifact_id text,
            task_id text,
            turn_id text,
            stale_count integer not null,
            missing_count integer not null,
            failed_count integer not null,
            accepted_risk_count integer not null,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, changeset_id),
            foreign key (session_id, changeset_id)
                references changesets(session_id, changeset_id)
        )
        """
    )
    connection.execute(
        """
        create table if not exists changeset_review_briefs (
            session_id text not null,
            changeset_id text not null,
            artifact_id text not null,
            artifact_schema_version integer not null,
            render_targets_json text not null,
            inventory_artifact_id text,
            verification_id text,
            task_id text,
            turn_id text,
            created_by text not null,
            redacted integer not null,
            local_only integer not null,
            created_at text not null,
            last_sequence integer not null,
            primary key (session_id, changeset_id, artifact_id),
            foreign key (session_id, changeset_id)
                references changesets(session_id, changeset_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_changeset_review_briefs_changeset
            on changeset_review_briefs (session_id, changeset_id, created_at desc)
        """
    )
    connection.execute(
        """
        create table if not exists changeset_readiness (
            session_id text not null,
            changeset_id text not null,
            readiness_kind text not null,
            state text not null,
            reason text not null,
            blockers_json text not null,
            safe_next_actions_json text not null,
            inventory_artifact_id text,
            review_brief_artifact_id text,
            verification_id text,
            task_id text,
            turn_id text,
            accepted_risk_count integer not null,
            decided_by text not null,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, changeset_id, readiness_kind),
            foreign key (session_id, changeset_id)
                references changesets(session_id, changeset_id)
        )
        """
    )


__all__ = ["ensure_changeset_projection_schema"]
