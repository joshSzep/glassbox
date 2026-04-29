import type {
  DashboardState,
  ProjectionHealthCounts,
  QueueCounts,
  RuntimeSummary,
  SessionFields,
} from "@/state/session-types";

export function createDashboardState(): DashboardState {
  return {
    ...createEmptySessionFields(),
    compareSession: null,
    compareSessionId: null,
    eventLog: [],
    liveOutput: [],
    projectionHealthCounts: createEmptyProjectionHealthCounts(),
    queueCounts: createEmptyQueueCounts(),
    runtimeSummary: createEmptyRuntimeSummary(),
    selectedQueue: "all",
    selectedSessionId: null,
    sessionIndex: [],
    sessionIndexSort: "priority",
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
