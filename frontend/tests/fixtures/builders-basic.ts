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
    artifact_context: { additional_summary_count: 0, summaries: [] },
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
    working_set: { additional_item_count: 0, items: [] },
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
    projection_health_counts: { degraded: 0, ok: sessions.length, stale: 0, unavailable: 0 },
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
    created_at: "2026-04-23T00:00:00Z",
    current_turn_id: null,
    current_turn_policy_summary: null,
    cwd: `/tmp/${sessionId}`,
    dashboard_url: null,
    fork_blocked_reason: "This session has no completed fork point.",
    forked_from_sequence: null,
    forked_from_turn_id: null,
    last_sequence: 4,
    latest_fork_point_sequence: null,
    latest_fork_point_turn_id: null,
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
