import type { components } from "@/generated/api-types";

export function makeProjectionHealth(
  overrides: Partial<components["schemas"]["ProjectionHealthResponse"]> = {},
): components["schemas"]["ProjectionHealthResponse"] {
  return {
    canonical_last_sequence: 4,
    degraded: false,
    detail: null,
    estimated_rebuild_event_count: 0,
    lag: 0,
    projected_last_sequence: 4,
    projected_progress_ratio: 1,
    state: "ok",
    ...overrides,
  };
}

export function makeRuntimeContext(
  overrides: Partial<components["schemas"]["RuntimeContextSnapshot"]> = {},
): components["schemas"]["RuntimeContextSnapshot"] {
  return {
    additional_runtime_note_count: 0,
    additional_workspace_memory_count: 0,
    artifact_context: { additional_summary_count: 0, summaries: [] },
    context_compactions: {
      additional_item_count: 0,
      items: [],
      stale_item_count: 0,
      stale_items: [],
    },
    repository_context: {
      additional_directory_count: 0,
      additional_file_count: 0,
      high_signal_paths: ["src/glassbox"],
      project_markers: ["pyproject.toml"],
      top_level_directories: ["src", "tests"],
      top_level_files: ["README.md"],
      workspace_name: "glassbox",
    },
    runtime_notes: [],
    workspace_memory: [],
    workspace_memory_context_bytes: 0,
    repository_index: null,
    working_set: { additional_item_count: 0, items: [] },
    ...overrides,
  };
}

export function makeProviderEvidence(
  overrides: Partial<components["schemas"]["ProviderEvidenceSummaryResponse"]> = {},
): components["schemas"]["ProviderEvidenceSummaryResponse"] {
  return {
    advisory: true,
    configured_model_name: null,
    diagnostics_state: null,
    failed_count: 0,
    freshness_policy_version: "provider-evidence-freshness.v1",
    freshness_status: "missing",
    identity_matches_current_config: null,
    latest_generated_at: null,
    latest_status: "missing",
    latest_summary_path: null,
    matrix_entry_count: 0,
    missing_scenarios: [],
    model_name: null,
    next_actions: [],
    passed_count: 0,
    provider: null,
    scenario_count: 0,
    schema_version: null,
    skipped_count: 0,
    stale: false,
    stale_after_seconds: 604800,
    summary_count: 0,
    warning_count: 0,
    ...overrides,
  };
}

export function makeKnowledgePosture(
  overrides: Partial<components["schemas"]["WorkspaceKnowledgePosture"]> = {},
): components["schemas"]["WorkspaceKnowledgePosture"] {
  return {
    cues: [],
    next_actions: [],
    overall_status: "missing",
    ...overrides,
  };
}

export function makeSessionSummary(
  sessionId: string,
  overrides: Partial<components["schemas"]["OperatorSessionSummaryResponse"]> = {},
): components["schemas"]["OperatorSessionSummaryResponse"] {
  return {
    action_needed: false,
    approval_behavior: "confirm: risky actions request approval",
    approval_mode: "confirm",
    branch_label: null,
    budget_posture: null,
    can_fork: false,
    child_session_count: 0,
    checkpoint_absence: null,
    created_at: "2026-04-23T00:00:00Z",
    cwd: `/tmp/${sessionId}`,
    dashboard_url: null,
    fork_blocked_reason: "This session has no completed fork point.",
    forked_from_sequence: null,
    forked_from_turn_id: null,
    has_active_turn: true,
    historical_only: false,
    last_sequence: 4,
    latest_fork_point_sequence: null,
    latest_fork_point_turn_id: null,
    latest_checkpoint: null,
    long_run_status: makeLongRunStatus(),
    latest_message_summary: "user: Inspect the repository",
    live_actionable: true,
    model_name: "openai:gpt-5.4",
    next_action_summary: "Send the next prompt",
    parent_session_id: null,
    pending_approval_id: null,
    pending_question_id: null,
    pending_question_text: null,
    priority_bucket: "active",
    priority_rank: 10,
    projection_health: makeProjectionHealth(),
    queue_memberships: ["active"],
    session_failure_message: null,
    session_failure_retryable: null,
    session_id: sessionId,
    status: "running",
    updated_at: "2026-04-23T00:00:01Z",
    ...overrides,
  };
}

export function makeSessionAggregate(
  sessions: components["schemas"]["OperatorSessionSummaryResponse"][] = [],
  overrides: Partial<components["schemas"]["SessionAggregateResponse"]> = {},
): components["schemas"]["SessionAggregateResponse"] {
  return {
    limit: null,
    knowledge_posture: makeKnowledgePosture(),
    projection_health_counts: { degraded: 0, ok: sessions.length, stale: 0, unavailable: 0 },
    provider_evidence: makeProviderEvidence(),
    queue: "all",
    queue_counts: {
      action_needed: sessions.filter((session) => session.action_needed).length,
      active: sessions.filter((session) => session.queue_memberships.includes("active")).length,
      approvals: sessions.filter((session) => session.queue_memberships.includes("approvals"))
        .length,
      degraded: 0,
      failures: sessions.filter((session) => session.queue_memberships.includes("failures")).length,
      historical: sessions.filter((session) => session.historical_only).length,
      questions: sessions.filter((session) => session.queue_memberships.includes("questions"))
        .length,
      total: sessions.length,
    },
    runtime: {
      background_job_abandoned_count: 0,
      background_job_failed_count: 0,
      background_job_retryable_count: 0,
      dashboard_url: null,
      health: null,
      health_url: null,
      pid: null,
      session_index_url: null,
      started_at: null,
      state: "not_running",
      workspace_root: "/tmp/workspace",
    },
    sessions,
    sort: "priority",
    status: null,
    ...overrides,
  };
}

export function makeSessionSnapshot(
  sessionId: string,
  overrides: Partial<components["schemas"]["SessionSnapshotResponse"]> = {},
): components["schemas"]["SessionSnapshotResponse"] {
  return {
    active_tool_calls: [],
    approval_behavior: "confirm: risky actions request approval",
    approval_mode: "confirm",
    branch_label: null,
    branchable_turns: [],
    budget_posture: null,
    can_fork: false,
    child_sessions: [],
    checkpoint_absence: null,
    created_at: "2026-04-23T00:00:00Z",
    current_turn_id: null,
    current_turn_policy_summary: null,
    checkpoint_history: [],
    cwd: `/tmp/${sessionId}`,
    dashboard_url: null,
    fork_blocked_reason: "This session has no completed fork point.",
    forked_from_sequence: null,
    forked_from_turn_id: null,
    last_sequence: 4,
    latest_fork_point_sequence: null,
    latest_fork_point_turn_id: null,
    latest_checkpoint: null,
    long_run_status: makeLongRunStatus(),
    model_name: "openai:gpt-5.4",
    parent_session_id: null,
    pending_approval_id: null,
    pending_approvals: [],
    pending_question_id: null,
    pending_question_text: null,
    projection_health: makeProjectionHealth(),
    runtime_context: makeRuntimeContext(),
    session_failure_message: null,
    session_failure_retryable: null,
    session_id: sessionId,
    session_policy_summary: {
      allow_count: 0,
      approve_count: 0,
      blocked_count: 0,
      command_count: 0,
      deny_count: 0,
      highest_risk_level: null,
      read_only_count: 0,
      total_decisions: 0,
      workspace_write_count: 0,
    },
    status: "running",
    transcript: [
      {
        created_at: "2026-04-23T00:00:00Z",
        message_id: "message-1",
        parts: [{ kind: "text", text: "Inspect the repository" }],
        role: "user",
      },
    ],
    turn_metrics: [],
    updated_at: "2026-04-23T00:00:01Z",
    ...overrides,
  };
}

export function makeLongRunStatus(
  overrides: Partial<components["schemas"]["LongRunStatusResponse"]> = {},
): components["schemas"]["LongRunStatusResponse"] {
  return {
    current_attempt_id: null,
    current_attempt_status: null,
    current_attempt_tool_name: null,
    current_phase: null,
    elapsed_seconds: 1,
    heartbeat_age_seconds: null,
    heartbeat_at: null,
    heartbeat_expires_at: null,
    last_event_at: "2026-04-23T00:00:01Z",
    last_event_sequence: 4,
    last_event_type: "SessionStarted",
    progress_summary: "waiting for the next durable progress event",
    state: "healthy",
    stuck_reason: null,
    ...overrides,
  };
}
