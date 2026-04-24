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
    selectedSessionId: null,
    sessionLoadState: "idle",
    sessionLoadError: null,
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
