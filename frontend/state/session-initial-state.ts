import type {
  DashboardState,
  ProjectionHealthCounts,
  ProviderEvidence,
  QueueCounts,
  RuntimeSummary,
  SessionFields,
} from "@/state/session-types";
import { createHealthyWorkspaceAttentionSummary } from "@/state/workspace-attention";

export function createDashboardState(): DashboardState {
  return {
    ...createEmptySessionFields(),
    compareSession: null,
    compareSessionId: null,
    eventLog: [],
    liveOutput: [],
    projectionHealthCounts: createEmptyProjectionHealthCounts(),
    providerEvidence: createEmptyProviderEvidence(),
    queueCounts: createEmptyQueueCounts(),
    runtimeSummary: createEmptyRuntimeSummary(),
    selectedQueue: "all",
    selectedSessionId: null,
    sessionIndex: [],
    sessionIndexSort: "priority",
    workspaceAttention: createHealthyWorkspaceAttentionSummary(),
  };
}

export function createEmptyQueueCounts(): QueueCounts {
  return {
    action_needed: 0,
    active: 0,
    approvals: 0,
    degraded: 0,
    failures: 0,
    historical: 0,
    questions: 0,
    total: 0,
  };
}

export function createEmptyProjectionHealthCounts(): ProjectionHealthCounts {
  return {
    degraded: 0,
    ok: 0,
    stale: 0,
    unavailable: 0,
  };
}

export function createEmptyProviderEvidence(): ProviderEvidence {
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
  };
}

export function createEmptyRuntimeSummary(): RuntimeSummary {
  return {
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
    workspace_root: "",
  };
}

export function createEmptySessionFields(): SessionFields {
  return {
    activeToolCalls: [],
    approvalMode: null,
    branchLabel: null,
    branchableTurns: [],
    budgetPosture: null,
    canFork: false,
    childSessions: [],
    currentTurn: null,
    currentTurnPolicySummary: null,
    cwd: null,
    dashboardUrl: null,
    forkBlockedReason: null,
    forkedFromSequence: null,
    forkedFromTurnId: null,
    lastSequence: 0,
    latestForkPointSequence: null,
    latestForkPointTurnId: null,
    modelName: null,
    parentSessionId: null,
    pendingApprovalId: null,
    pendingApprovals: [],
    pendingQuestionId: null,
    pendingQuestionText: null,
    projectionHealth: null,
    runtimeContext: null,
    selectedForkTurnId: null,
    sessionFailureMessage: null,
    sessionFailureRetryable: null,
    sessionId: null,
    sessionPolicySummary: null,
    status: "unknown",
    transcript: [],
    turnMetrics: [],
  };
}
