import {
  createEmptyProjectionHealthCounts,
  createEmptyQueueCounts,
  createEmptyRuntimeSummary,
  createState,
} from "./state-core.js";

export function beginSessionAggregateLoad(state, { queue = state.selectedQueue ?? "all" } = {}) {
  return {
    ...state,
    selectedQueue: queue,
    sessionIndexState: "loading",
    sessionIndexError: null,
  };
}

export function beginSessionIndexLoad(state) {
  return beginSessionAggregateLoad(state);
}

export function hydrateSessionAggregate(state, aggregate) {
  return {
    ...state,
    sessionIndex: [...(aggregate.sessions ?? [])],
    sessionIndexState: "loaded",
    sessionIndexError: null,
    selectedQueue: aggregate.queue ?? state.selectedQueue ?? "all",
    queueCounts: { ...(aggregate.queue_counts ?? createEmptyQueueCounts()) },
    projectionHealthCounts: {
      ...(aggregate.projection_health_counts ?? createEmptyProjectionHealthCounts()),
    },
    runtimeSummary: { ...(aggregate.runtime ?? createEmptyRuntimeSummary()) },
    sessionIndexSort: aggregate.sort ?? state.sessionIndexSort,
  };
}

export function hydrateSessionIndex(state, sessionIndex) {
  if (Array.isArray(sessionIndex)) {
    return {
      ...state,
      sessionIndex: [...sessionIndex],
      sessionIndexState: "loaded",
      sessionIndexError: null,
    };
  }
  return hydrateSessionAggregate(state, sessionIndex);
}

export function failSessionAggregateLoad(
  state,
  errorMessage,
  { queue = state.selectedQueue ?? "all" } = {},
) {
  return {
    ...state,
    selectedQueue: queue,
    sessionIndexState: "failed",
    sessionIndexError: errorMessage,
  };
}

export function failSessionIndexLoad(state, errorMessage) {
  return failSessionAggregateLoad(state, errorMessage);
}

export function beginSessionSelection(state, sessionId) {
  return {
    ...state,
    selectedSessionId: sessionId,
    sessionLoadState: sessionId ? "loading" : "idle",
    sessionLoadError: null,
    compareSessionId: null,
    compareSession: null,
    compareSessionLoadState: "idle",
    compareSessionLoadError: null,
    streamState: sessionId ? "loading" : "index",
    streamError: null,
    streamRetryCount: 0,
    sessionId: sessionId ? state.sessionId : null,
  };
}

export function beginCompareSessionSelection(state, sessionId) {
  return {
    ...state,
    compareSessionId: sessionId,
    compareSession: null,
    compareSessionLoadState: sessionId ? "loading" : "idle",
    compareSessionLoadError: null,
  };
}

export function clearCompareSessionSelection(state) {
  return {
    ...state,
    compareSessionId: null,
    compareSession: null,
    compareSessionLoadState: "idle",
    compareSessionLoadError: null,
  };
}

export function clearSessionSelection(state) {
  return {
    ...createState(),
    sessionIndex: [...state.sessionIndex],
    sessionIndexState: state.sessionIndexState,
    sessionIndexError: state.sessionIndexError,
    selectedQueue: state.selectedQueue,
    queueCounts: { ...state.queueCounts },
    projectionHealthCounts: { ...state.projectionHealthCounts },
    runtimeSummary: { ...state.runtimeSummary },
    sessionIndexSort: state.sessionIndexSort,
    streamState: "index",
  };
}

export function failSessionSelection(state, errorMessage) {
  return {
    ...state,
    sessionId: null,
    status: "unknown",
    currentTurn: null,
    pendingApprovalId: null,
    pendingQuestionId: null,
    pendingQuestionText: null,
    sessionFailureMessage: null,
    sessionFailureRetryable: null,
    turnMetrics: [],
    transcript: [],
    activeToolCalls: [],
    liveOutput: [],
    pendingApprovals: [],
    eventLog: [],
    interactionSubmission: {
      kind: null,
      state: "idle",
      error: null,
    },
    compareSessionId: null,
    compareSession: null,
    compareSessionLoadState: "idle",
    compareSessionLoadError: null,
    sessionLoadState: "failed",
    sessionLoadError: errorMessage,
    streamState: "index",
    streamError: null,
    streamRetryCount: 0,
  };
}

export function failCompareSessionSelection(state, errorMessage) {
  return {
    ...state,
    compareSession: null,
    compareSessionLoadState: "failed",
    compareSessionLoadError: errorMessage,
  };
}

export function beginLiveStreamConnection(state, { reconnecting = false } = {}) {
  return {
    ...state,
    streamState: reconnecting ? "reconnecting" : "connecting",
    streamError: reconnecting
      ? state.streamError
      : null,
  };
}

export function markLiveStreamConnected(state) {
  return {
    ...state,
    streamState: "live",
    streamError: null,
    streamRetryCount: 0,
  };
}

export function markLiveStreamReconnecting(state, errorMessage) {
  return {
    ...state,
    streamState: "reconnecting",
    streamError: errorMessage,
    streamRetryCount: state.streamRetryCount + 1,
  };
}

export function markLiveStreamUnavailable(state, errorMessage) {
  return {
    ...state,
    streamState: "unavailable",
    streamError: errorMessage,
  };
}

export function markHistoricalSnapshot(state) {
  return {
    ...state,
    streamState: "historical",
    streamError: null,
    streamRetryCount: 0,
  };
}
