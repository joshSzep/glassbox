export function createState() {
  return {
    sessionId: null,
    status: "unknown",
    modelName: null,
    cwd: null,
    approvalMode: null,
    parentSessionId: null,
    forkedFromTurnId: null,
    forkedFromSequence: null,
    branchLabel: null,
    childSessions: [],
    branchableTurns: [],
    canFork: false,
    latestForkPointTurnId: null,
    latestForkPointSequence: null,
    forkBlockedReason: null,
    selectedForkTurnId: null,
    dashboardUrl: null,
    lastSequence: 0,
    pendingApprovalId: null,
    pendingQuestionId: null,
    pendingQuestionText: null,
    sessionFailureMessage: null,
    sessionFailureRetryable: null,
    runtimeContext: null,
    currentTurn: null,
    turnMetrics: [],
    transcript: [],
    activeToolCalls: [],
    liveOutput: [],
    pendingApprovals: [],
    eventLog: [],
    interactionSubmission: createIdleInteractionSubmission(),
    forkSubmission: createIdleForkSubmission(),
    sessionIndex: [],
    sessionIndexState: "idle",
    sessionIndexError: null,
    selectedQueue: "all",
    queueCounts: createEmptyQueueCounts(),
    projectionHealthCounts: createEmptyProjectionHealthCounts(),
    runtimeSummary: createEmptyRuntimeSummary(),
    sessionIndexSort: "priority",
    selectedSessionId: null,
    sessionLoadState: "idle",
    sessionLoadError: null,
    compareSessionId: null,
    compareSession: null,
    compareSessionLoadState: "idle",
    compareSessionLoadError: null,
    streamState: "idle",
    streamError: null,
    streamRetryCount: 0,
  };
}

export function createIdleInteractionSubmission() {
  return {
    kind: null,
    state: "idle",
    error: null,
  };
}

export function createIdleForkSubmission() {
  return {
    state: "idle",
    error: null,
  };
}

export function createEmptyQueueCounts() {
  return {
    total: 0,
    approvals: 0,
    questions: 0,
    failures: 0,
    degraded: 0,
    active: 0,
    action_needed: 0,
    historical: 0,
  };
}

export function createEmptyProjectionHealthCounts() {
  return {
    ok: 0,
    stale: 0,
    unavailable: 0,
    degraded: 0,
  };
}

export function createEmptyRuntimeSummary() {
  return {
    workspace_root: null,
    state: "not_running",
    health: null,
    pid: null,
    dashboard_url: null,
    health_url: null,
    session_index_url: null,
    started_at: null,
  };
}
