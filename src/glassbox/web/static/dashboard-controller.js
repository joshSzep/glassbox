import {
  applyEvent,
  beginLiveStreamConnection,
  beginSessionIndexLoad,
  beginSessionSelection,
  clearSessionSelection,
  createState,
  failSessionIndexLoad,
  failSessionSelection,
  hydrateFromSnapshot,
  hydrateSessionIndex,
  markHistoricalSnapshot,
  markLiveStreamConnected,
  markLiveStreamReconnecting,
  markLiveStreamUnavailable,
  selectForkTurn,
} from "./state.js";
import { resolvePendingApproval } from "./approval-actions.js";
import {
  submitPendingQuestionAnswer,
  submitSessionFork,
  submitSessionMessage,
} from "./interaction-actions.js";

function selectedSessionIdFromLocation(location) {
  return new URLSearchParams(location.search).get("session");
}

function nextDashboardUrl(location, sessionId) {
  const params = new URLSearchParams(location.search);
  if (sessionId) {
    params.set("session", sessionId);
  } else {
    params.delete("session");
  }
  const nextQuery = params.toString();
  return nextQuery ? `${location.pathname}?${nextQuery}` : location.pathname;
}

export function createDashboardController({
  windowImpl,
  fetchImpl,
  transport,
  domBindings,
}) {
  let state = createState();
  let eventSource = null;

  function getState() {
    return state;
  }

  function closeSSE() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }

  function renderAll() {
    domBindings.renderAll(state);
  }

  function syncState(updater) {
    state = updater(state);
    renderAll();
  }

  function applySelectedSnapshot(snapshot) {
    state = {
      ...hydrateFromSnapshot(snapshot),
      sessionIndex: [...state.sessionIndex],
      sessionIndexState: state.sessionIndexState,
      sessionIndexError: state.sessionIndexError,
    };
    domBindings.resetDrafts();
  }

  function shouldOpenLiveStream() {
    return ["running", "awaiting_user_input", "awaiting_approval"].includes(
      state.status,
    );
  }

  function connectSSE(sessionId, afterSequence, { reconnecting = false } = {}) {
    closeSSE();
    syncState(current => beginLiveStreamConnection(current, { reconnecting }));

    eventSource = transport.openSessionEventStream(
      sessionId,
      afterSequence,
      {
        onOpen: () => {
          syncState(current => markLiveStreamConnected(current));
        },
        onEnvelope: envelope => {
          syncState(current => applyEvent(current, envelope));
        },
        onError: () => {
          eventSource?.close();
          eventSource = null;

          if (state.sessionId !== sessionId) {
            return;
          }

          if (state.streamRetryCount >= 2) {
            syncState(current => markLiveStreamUnavailable(
              current,
              "Showing the last persisted snapshot only. The live stream could not be re-established.",
            ));
            return;
          }

          syncState(current => markLiveStreamReconnecting(
            current,
            "Snapshot still available while the dashboard retries the live stream.",
          ));
          windowImpl.setTimeout(
            () => connectSSE(sessionId, state.lastSequence, { reconnecting: true }),
            3000,
          );
        },
      },
    );
  }

  async function loadSessionIndex() {
    syncState(current => beginSessionIndexLoad(current));

    const response = await transport.fetchSessionIndex();
    if (!response.ok) {
      syncState(current => failSessionIndexLoad(
        current,
        `Recent sessions unavailable (${response.status})`,
      ));
      return;
    }

    const summaries = await response.json();
    syncState(current => hydrateSessionIndex(current, summaries));
  }

  async function loadSnapshot(sessionId) {
    syncState(current => beginSessionSelection(current, sessionId));
    closeSSE();

    const response = await transport.fetchSessionSnapshot(sessionId);
    if (!response.ok) {
      syncState(current => failSessionSelection(
        current,
        `Session not found (${response.status})`,
      ));
      return false;
    }

    const snapshot = await response.json();
    applySelectedSnapshot(snapshot);
    renderAll();

    if (!shouldOpenLiveStream()) {
      state = markHistoricalSnapshot(state);
      renderAll();
      return true;
    }

    connectSSE(sessionId, state.lastSequence);
    return true;
  }

  async function openSession(sessionId, { replaceHistory = false } = {}) {
    const nextUrl = nextDashboardUrl(windowImpl.location, sessionId);
    const historyMethod = replaceHistory ? "replaceState" : "pushState";
    windowImpl.history[historyMethod]({}, "", nextUrl);
    return loadSnapshot(sessionId);
  }

  async function syncFromLocation({ replaceHistory = true } = {}) {
    const requestedSessionId = selectedSessionIdFromLocation(windowImpl.location);
    if (!requestedSessionId) {
      closeSSE();
      state = clearSessionSelection(state);
      renderAll();
      if (replaceHistory) {
        windowImpl.history.replaceState({}, "", nextDashboardUrl(windowImpl.location, null));
      }
      return;
    }

    const loaded = await loadSnapshot(requestedSessionId);
    if (!loaded && replaceHistory) {
      windowImpl.history.replaceState(
        {},
        "",
        nextDashboardUrl(windowImpl.location, null),
      );
    }
  }

  async function handleResolveApproval(approvalId, decision) {
    await resolvePendingApproval({
      sessionId: state.sessionId,
      approvalId,
      decision,
      fetchImpl,
      syncState,
    });
  }

  async function handleSubmitComposer(mode, value) {
    if (!state.sessionId) {
      return;
    }

    let result = null;
    if (mode === "message") {
      result = await submitSessionMessage({
        sessionId: state.sessionId,
        text: value,
        fetchImpl,
        syncState,
      });
    } else if (mode === "answer" && state.pendingQuestionId) {
      result = await submitPendingQuestionAnswer({
        sessionId: state.sessionId,
        questionId: state.pendingQuestionId,
        answer: value,
        fetchImpl,
        syncState,
      });
    }

    if (result?.ok) {
      domBindings.clearDraftForMode(mode);
      domBindings.rerenderComposer(state);
    }
  }

  async function forkCurrentSession({ turnId, branchLabel } = {}) {
    if (!state.sessionId) {
      return { ok: false, error: "No session selected" };
    }

    const result = await submitSessionFork({
      sessionId: state.sessionId,
      turnId,
      branchLabel,
      fetchImpl,
      syncState,
    });
    if (!result.ok) {
      domBindings.rerenderComposer(state);
      return result;
    }

    domBindings.clearForkDraft();
    await loadSessionIndex();
    await openSession(result.data.child_session_id);
    return result;
  }

  function handleSelectForkTurn(turnId) {
    syncState(current => selectForkTurn(current, turnId));
  }

  async function init() {
    state = clearSessionSelection(state);
    renderAll();
    await loadSessionIndex();
    await syncFromLocation({ replaceHistory: true });
  }

  function destroy() {
    closeSSE();
  }

  return {
    destroy,
    forkCurrentSession,
    getState,
    handleResolveApproval,
    handleSelectForkTurn,
    handleSubmitComposer,
    init,
    openSession,
    syncFromLocation,
  };
}
