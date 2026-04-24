import { createState } from "./state-core.js";

export function beginSessionIndexLoad(state) {
  return {
    ...state,
    sessionIndexState: "loading",
    sessionIndexError: null,
  };
}

export function hydrateSessionIndex(state, sessionIndex) {
  return {
    ...state,
    sessionIndex: [...sessionIndex],
    sessionIndexState: "loaded",
    sessionIndexError: null,
  };
}

export function failSessionIndexLoad(state, errorMessage) {
  return {
    ...state,
    sessionIndexState: "failed",
    sessionIndexError: errorMessage,
  };
}

export function beginSessionSelection(state, sessionId) {
  return {
    ...state,
    selectedSessionId: sessionId,
    sessionLoadState: sessionId ? "loading" : "idle",
    sessionLoadError: null,
    streamState: sessionId ? "loading" : "index",
    streamError: null,
    streamRetryCount: 0,
    sessionId: sessionId ? state.sessionId : null,
  };
}

export function clearSessionSelection(state) {
  return {
    ...createState(),
    sessionIndex: [...state.sessionIndex],
    sessionIndexState: state.sessionIndexState,
    sessionIndexError: state.sessionIndexError,
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
    sessionLoadState: "failed",
    sessionLoadError: errorMessage,
    streamState: "index",
    streamError: null,
    streamRetryCount: 0,
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
