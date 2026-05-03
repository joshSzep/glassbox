"""SQLite DDL statements for schema bootstrap."""

BOOTSTRAP_STATEMENTS = (
    """
    create table if not exists schema_migrations (
        version integer primary key,
        applied_at text not null default current_timestamp
    )
    """,
    """
    create table if not exists sessions (
        session_id text primary key,
        status text not null,
        created_at text not null,
        updated_at text not null,
        cwd text not null,
        model_name text not null,
        approval_mode text not null,
        parent_session_id text,
        forked_from_turn_id text,
        forked_from_sequence integer,
        branch_label text,
        last_sequence integer not null default 0
    )
    """,
    """
    create index if not exists idx_sessions_status_updated
        on sessions (status, updated_at desc)
    """,
    """
    create table if not exists events (
        session_id text not null,
        sequence integer not null,
        event_id text not null,
        event_type text not null,
        event_version integer not null,
        created_at text not null,
        turn_id text,
        message_id text,
        tool_call_id text,
        approval_id text,
        task_id text,
        checkpoint_id text,
        compaction_id text,
        tool_attempt_id text,
        recovery_decision_id text,
        actor text,
        payload_json text not null,
        primary key (session_id, sequence),
        unique (event_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_events_session_created
        on events (session_id, created_at)
    """,
    """
    create index if not exists idx_events_session_type_sequence
        on events (session_id, event_type, sequence)
    """,
    """
    create index if not exists idx_events_turn
        on events (session_id, turn_id, sequence)
    """,
    """
    create index if not exists idx_events_message
        on events (session_id, message_id, sequence)
    """,
    """
    create index if not exists idx_events_tool_call
        on events (session_id, tool_call_id, sequence)
    """,
    """
    create index if not exists idx_events_approval
        on events (session_id, approval_id, sequence)
    """,
    """
    create index if not exists idx_events_task
        on events (session_id, task_id, sequence)
    """,
    """
    create index if not exists idx_events_checkpoint
        on events (session_id, checkpoint_id, sequence)
    """,
    """
    create index if not exists idx_events_compaction
        on events (session_id, compaction_id, sequence)
    """,
    """
    create index if not exists idx_events_tool_attempt
        on events (session_id, tool_attempt_id, sequence)
    """,
    """
    create index if not exists idx_events_recovery_decision
        on events (session_id, recovery_decision_id, sequence)
    """,
    """
    create table if not exists session_state (
        session_id text primary key,
        status text not null,
        current_turn_id text,
        pending_approval_id text,
        pending_question_id text,
        last_sequence integer not null,
        updated_at text not null,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create table if not exists transcript_messages (
        message_id text primary key,
        session_id text not null,
        turn_id text,
        role text not null,
        status text not null,
        created_at text not null,
        completed_at text,
        content_text text not null default '',
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_transcript_messages_session_created
        on transcript_messages (session_id, created_at)
    """,
    """
    create table if not exists tool_calls (
        tool_call_id text primary key,
        session_id text not null,
        turn_id text not null,
        tool_name text not null,
        status text not null,
        started_at text,
        completed_at text,
        summary text,
        exit_code integer,
        policy_outcome text,
        policy_risk_level text,
        policy_source_kind text,
        policy_source_label text,
        policy_reason text,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_tool_calls_session_status
        on tool_calls (session_id, status)
    """,
    """
    create index if not exists idx_tool_calls_session_turn
        on tool_calls (session_id, turn_id)
    """,
    """
    create table if not exists tool_attempts (
        tool_attempt_id text not null,
        session_id text not null,
        turn_id text not null,
        tool_call_id text,
        task_id text,
        tool_name text not null,
        status text not null,
        message text,
        started_at text,
        last_heartbeat_at text,
        heartbeat_expires_at text,
        completed_at text,
        completed_units integer,
        total_units integer,
        output_artifact_id text,
        safe_to_retry integer,
        retry_classification text,
        retry_requires_approval integer,
        retry_reason text,
        retry_policy_reason text,
        command_purpose text,
        command_review_relevance text,
        command_supports_verification integer,
        command_purpose_reason text,
        command_environment_json text,
        last_sequence integer not null,
        primary key (session_id, tool_attempt_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_tool_attempts_session_status
        on tool_attempts (session_id, status, last_sequence desc)
    """,
    """
    create index if not exists idx_tool_attempts_turn
        on tool_attempts (session_id, turn_id, last_sequence desc)
    """,
    """
    create index if not exists idx_tool_attempts_tool_call
        on tool_attempts (session_id, tool_call_id, last_sequence desc)
    """,
    """
    create table if not exists approvals (
        approval_id text primary key,
        session_id text not null,
        turn_id text not null,
        subject text not null,
        reason text not null,
        policy_outcome text,
        policy_risk_level text,
        policy_source_kind text,
        policy_source_label text,
        status text not null,
        requested_at text not null,
        resolved_at text,
        decided_by text,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_approvals_session_status
        on approvals (session_id, status)
    """,
    """
    create table if not exists runtime_notes (
        session_id text not null,
        sequence integer not null,
        source_session_id text,
        source_sequence integer,
        category text not null,
        message text not null,
        created_at text not null,
        primary key (session_id, sequence),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_runtime_notes_session_created
        on runtime_notes (session_id, created_at, sequence)
    """,
    """
    create table if not exists turn_metrics (
        session_id text not null,
        turn_id text not null,
        started_at text,
        completed_at text,
        turn_duration_ms integer,
        model_call_count integer not null default 0,
        model_duration_ms_total integer not null default 0,
        model_input_tokens_total integer not null default 0,
        model_output_tokens_total integer not null default 0,
        tool_call_count integer not null default 0,
        tool_duration_ms_total integer not null default 0,
        succeeded_tool_call_count integer not null default 0,
        failed_tool_call_count integer not null default 0,
        primary key (session_id, turn_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_turn_metrics_session_started
        on turn_metrics (session_id, started_at desc)
    """,
    """
    create table if not exists tasks (
        session_id text not null,
        task_id text not null,
        title text not null,
        goal text not null,
        status text not null,
        source_turn_id text,
        current_step_id text,
        blocked_reason text,
        blocked_detail text,
        created_at text not null,
        updated_at text not null,
        last_sequence integer not null,
        primary key (session_id, task_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_tasks_session_status_updated
        on tasks (session_id, status, updated_at desc)
    """,
    """
    create index if not exists idx_tasks_session_blocked
        on tasks (session_id, blocked_reason, updated_at desc)
    """,
    """
    create table if not exists task_steps (
        session_id text not null,
        task_id text not null,
        step_id text not null,
        title text not null,
        description text,
        step_order integer not null,
        status text not null,
        blocked_reason text,
        started_at text,
        completed_at text,
        summary text,
        failure_reason text,
        last_sequence integer not null,
        primary key (session_id, step_id),
        foreign key (session_id, task_id) references tasks(session_id, task_id)
    )
    """,
    """
    create index if not exists idx_task_steps_task_order
        on task_steps (session_id, task_id, step_order)
    """,
    """
    create index if not exists idx_task_steps_session_status
        on task_steps (session_id, status)
    """,
    """
    create table if not exists task_verifications (
        session_id text not null,
        task_id text not null,
        verification_id text not null,
        step_id text,
        check_name text not null,
        status text not null,
        started_at text,
        completed_at text,
        summary text,
        artifact_id text,
        last_sequence integer not null,
        primary key (session_id, verification_id),
        foreign key (session_id, task_id) references tasks(session_id, task_id)
    )
    """,
    """
    create index if not exists idx_task_verifications_task
        on task_verifications (session_id, task_id, started_at)
    """,
    """
    create table if not exists task_verification_ledger (
        session_id text not null,
        task_id text not null,
        verification_id text not null,
        step_id text,
        status text not null,
        check_name text not null,
        kind text,
        source text,
        command_json text not null,
        changed_paths_json text not null,
        eval_case_id text,
        eval_profile_id text,
        blocking integer not null default 1,
        attempt_count integer not null default 0,
        latest_attempt integer not null default 0,
        planned_sequence integer,
        started_sequence integer,
        last_success_sequence integer,
        latest_failed_sequence integer,
        latest_failed_summary text,
        latest_failed_category text,
        latest_failed_artifact_id text,
        latest_artifact_id text,
        accepted_risk_count integer not null default 0,
        accepted_risks_json text not null,
        residual_risk_reason text,
        summary text,
        updated_at text not null,
        last_sequence integer not null,
        primary key (session_id, verification_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_task_verification_ledger_task
        on task_verification_ledger (session_id, task_id, last_sequence)
    """,
    """
    create index if not exists idx_task_verification_ledger_status
        on task_verification_ledger (session_id, task_id, status)
    """,
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
    """,
    """
    create index if not exists idx_branch_searches_session_updated
        on branch_searches (session_id, updated_at desc)
    """,
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
    """,
    """
    create index if not exists idx_branch_candidates_search
        on branch_candidates (session_id, search_id, updated_at)
    """,
    """
    create table if not exists autonomy_budget_posture (
        session_id text not null,
        task_id text not null default '',
        scope text not null,
        mode text,
        budget_json text,
        usage_json text not null,
        remaining_json text,
        last_decision text not null,
        last_reason text,
        last_limit_name text,
        last_detail text,
        updated_at text not null,
        last_sequence integer not null,
        primary key (session_id, task_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_autonomy_budget_posture_session_updated
        on autonomy_budget_posture (session_id, updated_at desc)
    """,
    """
    create table if not exists background_jobs (
        job_id text primary key,
        session_id text not null,
        state text not null,
        kind text not null,
        job_type text not null,
        title text not null,
        requested_by text not null,
        payload_json text not null,
        priority integer not null,
        task_id text,
        parent_job_id text,
        worker_id text,
        claim_token text,
        attempt integer not null default 0,
        lease_expires_at text,
        last_heartbeat_at text,
        progress_message text,
        completed_units integer,
        total_units integer,
        failure_kind text,
        failure_message text,
        failure_artifact_id text,
        failure_artifact_path text,
        retryable integer not null default 0,
        next_retry_at text,
        cancellation_requested_by text,
        cancellation_reason text,
        cancelled_by text,
        recovery_reason text,
        recovery_detail text,
        retry_requested_by text,
        retry_reason text,
        retry_exhausted_reason text,
        retry_budget integer,
        abandoned_by text,
        abandoned_reason text,
        created_at text not null,
        updated_at text not null,
        started_at text,
        completed_at text,
        last_sequence integer not null,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_background_jobs_state_updated
        on background_jobs (state, updated_at desc)
    """,
    """
    create index if not exists idx_background_jobs_session_updated
        on background_jobs (session_id, updated_at desc)
    """,
    """
    create index if not exists idx_background_jobs_lease
        on background_jobs (state, lease_expires_at)
    """,
    """
    create table if not exists workspace_memory (
        memory_id text primary key,
        session_id text not null,
        kind text not null,
        state text not null,
        content text not null,
        summary text,
        provenance_json text not null,
        created_by text not null,
        created_at text not null,
        updated_at text not null,
        confirmed_by text,
        confirmed_at text,
        invalidated_by text,
        invalidated_at text,
        invalidation_reason text,
        last_used_at text,
        use_count integer not null default 0,
        tags_json text not null,
        redacted integer not null default 0,
        import_source text,
        pruned_by text,
        pruned_at text,
        prune_reason text,
        last_sequence integer not null,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_workspace_memory_state_updated
        on workspace_memory (state, updated_at desc)
    """,
    """
    create index if not exists idx_workspace_memory_kind_updated
        on workspace_memory (kind, updated_at desc)
    """,
    """
    create index if not exists idx_workspace_memory_session_sequence
        on workspace_memory (session_id, last_sequence)
    """,
    """
    create table if not exists provider_recovery (
        session_id text not null,
        sequence integer not null,
        turn_id text,
        task_id text,
        checkpoint_id text,
        provider text not null,
        model_name text not null,
        failure_kind text not null,
        action text not null,
        retryable integer not null,
        safe_to_continue integer not null,
        degraded integer not null default 0,
        attempt integer not null,
        max_attempts integer,
        backoff_seconds integer,
        next_retry_at text,
        reason text not null,
        operator_next_action text not null,
        created_at text not null,
        primary key (session_id, sequence),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_provider_recovery_session_sequence
        on provider_recovery (session_id, sequence desc)
    """,
    """
    create index if not exists idx_provider_recovery_session_action
        on provider_recovery (session_id, action, sequence desc)
    """,
    """
    create table if not exists long_run_events (
        session_id text not null,
        sequence integer not null,
        event_type text not null,
        task_id text,
        turn_id text,
        tool_call_id text,
        tool_attempt_id text,
        checkpoint_id text,
        compaction_id text,
        recovery_decision_id text,
        phase text,
        status text,
        summary text,
        created_at text not null,
        primary key (session_id, sequence),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_long_run_events_session_created
        on long_run_events (session_id, created_at, sequence)
    """,
    """
    create index if not exists idx_long_run_events_task
        on long_run_events (session_id, task_id, sequence)
    """,
    """
    create index if not exists idx_long_run_events_checkpoint
        on long_run_events (session_id, checkpoint_id, sequence)
    """,
    """
    create table if not exists task_checkpoints (
        checkpoint_id text not null,
        session_id text not null,
        task_id text,
        turn_id text,
        tool_attempt_id text,
        compaction_id text,
        artifact_id text,
        objective text not null,
        current_phase text,
        completed_step text,
        next_action text not null,
        blockers_json text not null,
        touched_files_json text not null,
        verification_status text,
        budget_status text,
        recovery_guidance text not null,
        source_start_sequence integer not null,
        source_end_sequence integer not null,
        created_at text not null,
        last_sequence integer not null,
        primary key (session_id, checkpoint_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_task_checkpoints_session_sequence
        on task_checkpoints (session_id, last_sequence desc)
    """,
    """
    create index if not exists idx_task_checkpoints_task_sequence
        on task_checkpoints (session_id, task_id, last_sequence desc)
    """,
    """
    create table if not exists context_compactions (
        compaction_id text not null,
        session_id text not null,
        scope text not null,
        task_id text,
        turn_id text,
        checkpoint_id text,
        artifact_id text not null,
        artifact_schema_version integer not null,
        source_start_sequence integer not null,
        source_end_sequence integer not null,
        summary text not null,
        freshness text not null,
        freshness_reason text,
        superseded_by_compaction_id text,
        limitations_json text not null,
        source_artifact_ids_json text not null,
        decision_count integer not null,
        unresolved_question_count integer not null,
        accepted_risk_count integer not null,
        created_at text not null,
        last_sequence integer not null,
        primary key (session_id, compaction_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_context_compactions_session_sequence
        on context_compactions (session_id, last_sequence desc)
    """,
    """
    create index if not exists idx_context_compactions_task_sequence
        on context_compactions (session_id, task_id, last_sequence desc)
    """,
    """
    create index if not exists idx_context_compactions_checkpoint
        on context_compactions (session_id, checkpoint_id, last_sequence desc)
    """,
)

V3_BASELINE_SCHEMA_STATEMENTS = (
    """
    create table if not exists sessions (
        session_id text primary key,
        status text not null,
        created_at text not null,
        updated_at text not null,
        cwd text not null,
        model_name text not null,
        approval_mode text not null,
        last_sequence integer not null default 0
    )
    """,
    """
    create index if not exists idx_sessions_status_updated
        on sessions (status, updated_at desc)
    """,
    """
    create table if not exists events (
        session_id text not null,
        sequence integer not null,
        event_id text not null,
        event_type text not null,
        event_version integer not null,
        created_at text not null,
        turn_id text,
        message_id text,
        tool_call_id text,
        approval_id text,
        actor text,
        payload_json text not null,
        primary key (session_id, sequence),
        unique (event_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_events_session_created
        on events (session_id, created_at)
    """,
    """
    create index if not exists idx_events_session_type_sequence
        on events (session_id, event_type, sequence)
    """,
    """
    create index if not exists idx_events_turn
        on events (session_id, turn_id, sequence)
    """,
    """
    create index if not exists idx_events_message
        on events (session_id, message_id, sequence)
    """,
    """
    create index if not exists idx_events_tool_call
        on events (session_id, tool_call_id, sequence)
    """,
    """
    create index if not exists idx_events_approval
        on events (session_id, approval_id, sequence)
    """,
    """
    create table if not exists session_state (
        session_id text primary key,
        status text not null,
        current_turn_id text,
        pending_approval_id text,
        pending_question_id text,
        last_sequence integer not null,
        updated_at text not null,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create table if not exists transcript_messages (
        message_id text primary key,
        session_id text not null,
        turn_id text,
        role text not null,
        status text not null,
        created_at text not null,
        completed_at text,
        content_text text not null default '',
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_transcript_messages_session_created
        on transcript_messages (session_id, created_at)
    """,
    """
    create table if not exists tool_calls (
        tool_call_id text primary key,
        session_id text not null,
        turn_id text not null,
        tool_name text not null,
        status text not null,
        started_at text,
        completed_at text,
        summary text,
        exit_code integer,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_tool_calls_session_status
        on tool_calls (session_id, status)
    """,
    """
    create index if not exists idx_tool_calls_session_turn
        on tool_calls (session_id, turn_id)
    """,
    """
    create table if not exists tool_attempts (
        tool_attempt_id text not null,
        session_id text not null,
        turn_id text not null,
        tool_call_id text,
        task_id text,
        tool_name text not null,
        status text not null,
        message text,
        started_at text,
        last_heartbeat_at text,
        heartbeat_expires_at text,
        completed_at text,
        completed_units integer,
        total_units integer,
        output_artifact_id text,
        safe_to_retry integer,
        retry_classification text,
        retry_requires_approval integer,
        retry_reason text,
        retry_policy_reason text,
        command_purpose text,
        command_review_relevance text,
        command_supports_verification integer,
        command_purpose_reason text,
        command_environment_json text,
        last_sequence integer not null,
        primary key (session_id, tool_attempt_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_tool_attempts_session_status
        on tool_attempts (session_id, status, last_sequence desc)
    """,
    """
    create index if not exists idx_tool_attempts_turn
        on tool_attempts (session_id, turn_id, last_sequence desc)
    """,
    """
    create index if not exists idx_tool_attempts_tool_call
        on tool_attempts (session_id, tool_call_id, last_sequence desc)
    """,
    """
    create table if not exists approvals (
        approval_id text primary key,
        session_id text not null,
        turn_id text not null,
        subject text not null,
        reason text not null,
        status text not null,
        requested_at text not null,
        resolved_at text,
        decided_by text,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_approvals_session_status
        on approvals (session_id, status)
    """,
    """
    create table if not exists runtime_notes (
        session_id text not null,
        sequence integer not null,
        category text not null,
        message text not null,
        created_at text not null,
        primary key (session_id, sequence),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_runtime_notes_session_created
        on runtime_notes (session_id, created_at, sequence)
    """,
    """
    create table if not exists turn_metrics (
        session_id text not null,
        turn_id text not null,
        started_at text,
        completed_at text,
        turn_duration_ms integer,
        model_call_count integer not null default 0,
        model_duration_ms_total integer not null default 0,
        model_input_tokens_total integer not null default 0,
        model_output_tokens_total integer not null default 0,
        tool_call_count integer not null default 0,
        tool_duration_ms_total integer not null default 0,
        succeeded_tool_call_count integer not null default 0,
        failed_tool_call_count integer not null default 0,
        primary key (session_id, turn_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_turn_metrics_session_started
        on turn_metrics (session_id, started_at desc)
    """,
)
