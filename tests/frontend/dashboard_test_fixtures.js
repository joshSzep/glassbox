export function makeSessionSummary(sessionId, overrides = {}) {
  return {
    session_id: sessionId,
    status: "running",
    model_name: "openai:gpt-5.4",
    cwd: `/tmp/${sessionId}`,
    approval_mode: "confirm",
    parent_session_id: null,
    forked_from_turn_id: null,
    forked_from_sequence: null,
    branch_label: null,
    child_session_count: 0,
    can_fork: false,
    latest_fork_point_turn_id: null,
    latest_fork_point_sequence: null,
    fork_blocked_reason: "This session has no completed fork point.",
    dashboard_url: null,
    created_at: "2026-04-23T00:00:00Z",
    updated_at: "2026-04-23T00:00:01Z",
    last_sequence: 4,
    pending_approval_id: null,
    pending_question_id: null,
    pending_question_text: null,
    session_failure_message: null,
    session_failure_retryable: null,
    latest_message_summary: "user: Inspect the repository",
    next_action_summary: "Send the next prompt",
    ...overrides,
  };
}

export function makeSessionAggregate(sessions = [], overrides = {}) {
  return {
    queue: "all",
    status: null,
    sort: "priority",
    limit: null,
    queue_counts: {
      total: sessions.length,
      approvals: 0,
      questions: 0,
      failures: 0,
      degraded: 0,
      active: sessions.filter(summary => ["running", "awaiting_approval", "awaiting_user_input"].includes(summary.status)).length,
      action_needed: sessions.filter(summary => summary.pending_approval_id || summary.pending_question_id || summary.status === "failed").length,
      historical: sessions.filter(summary => ["completed", "cancelled", "failed"].includes(summary.status)).length,
    },
    projection_health_counts: {
      ok: sessions.length,
      stale: 0,
      unavailable: 0,
      degraded: 0,
    },
    runtime: {
      workspace_root: "/tmp/workspace",
      state: "not_running",
      health: null,
      pid: null,
      dashboard_url: null,
      health_url: null,
      session_index_url: null,
      started_at: null,
    },
    sessions,
    ...overrides,
  };
}

export function makeSessionSnapshot(sessionId, overrides = {}) {
  return {
    session_id: sessionId,
    status: "running",
    current_turn_id: null,
    model_name: "openai:gpt-5.4",
    cwd: `/tmp/${sessionId}`,
    approval_mode: "confirm",
    parent_session_id: null,
    forked_from_turn_id: null,
    forked_from_sequence: null,
    branch_label: null,
    child_sessions: [],
    branchable_turns: [],
    can_fork: false,
    latest_fork_point_turn_id: null,
    latest_fork_point_sequence: null,
    fork_blocked_reason: "This session has no completed fork point.",
    dashboard_url: null,
    last_sequence: 4,
    pending_approval_id: null,
    pending_question_id: null,
    pending_question_text: null,
    session_failure_message: null,
    session_failure_retryable: null,
    runtime_context: null,
    transcript: [
      {
        message_id: "message-1",
        role: "user",
        parts: [{ kind: "text", text: "Inspect the repository" }],
      },
    ],
    active_tool_calls: [],
    pending_approvals: [],
    turn_metrics: [],
    ...overrides,
  };
}

export function makeHistoricalSnapshot(sessionId, overrides = {}) {
  return {
    ...makeSessionSnapshot(sessionId),
    status: "completed",
    session_failure_message: null,
    session_failure_retryable: null,
    ...overrides,
  };
}
