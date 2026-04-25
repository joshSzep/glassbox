import {
  applyEvent,
  beginLiveStreamConnection,
  beginSessionAggregateLoad,
  beginSessionSelection,
  clearSessionSelection,
  createState,
  failSessionAggregateLoad,
  failSessionSelection,
  hydrateFromSnapshot,
  hydrateSessionAggregate,
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

function dashboardLocationState(location) {
  const params = new URLSearchParams(location.search);
  return {
    sessionId: params.get("session"),
    queue: params.get("queue") ?? "all",
  };
}

function nextDashboardUrl(location, { sessionId, queue }) {
  const params = new URLSearchParams(location.search);
  if (sessionId) {
    params.set("session", sessionId);
  } else {
    params.delete("session");
  }
  if (queue && queue !== "all") {
    params.set("queue", queue);
  } else {
    params.delete("queue");
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

  function updateLocation({ sessionId, queue }, { replaceHistory = false } = {}) {
    const historyMethod = replaceHistory ? "replaceState" : "pushState";
    windowImpl.history[historyMethod](
      {},
      "",
      nextDashboardUrl(windowImpl.location, { sessionId, queue }),
    );
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

  async function loadSessionAggregate(queue = state.selectedQueue ?? "all") {
    syncState(current => beginSessionAggregateLoad(current, { queue }));

    const response = await transport.fetchSessionAggregate({ queue, sort: "priority" });
    if (!response.ok) {
      syncState(current => failSessionAggregateLoad(
        current,
        `Operator console unavailable (${response.status})`,
        { queue },
      ));
      return false;
    }

    const aggregate = await response.json();
    syncState(current => hydrateSessionAggregate(current, aggregate));
    return true;
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
    updateLocation({
      sessionId,
      queue: state.selectedQueue,
    }, { replaceHistory });
    return loadSnapshot(sessionId);
  }

  async function selectQueue(queue, { replaceHistory = false } = {}) {
    updateLocation({
      sessionId: state.selectedSessionId ?? state.sessionId,
      queue,
    }, { replaceHistory });
    await loadSessionAggregate(queue);
  }

  async function syncFromLocation({ replaceHistory = true } = {}) {
    const { sessionId: requestedSessionId, queue: requestedQueue } = dashboardLocationState(windowImpl.location);

    if (
      state.sessionIndexState === "idle"
      || state.selectedQueue !== requestedQueue
    ) {
      await loadSessionAggregate(requestedQueue);
    }

    if (!requestedSessionId) {
      closeSSE();
      state = clearSessionSelection(state);
      renderAll();
      if (replaceHistory) {
        updateLocation(
          { sessionId: null, queue: requestedQueue },
          { replaceHistory: true },
        );
      }
      return;
    }

    const loaded = await loadSnapshot(requestedSessionId);
    if (!loaded && replaceHistory) {
      updateLocation(
        { sessionId: null, queue: requestedQueue },
        { replaceHistory: true },
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
    await loadSessionAggregate(state.selectedQueue);
    await openSession(result.data.child_session_id);
    return result;
  }

  function handleSelectForkTurn(turnId) {
    syncState(current => selectForkTurn(current, turnId));
  }

  async function init() {
    state = clearSessionSelection(state);
    renderAll();
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
    selectQueue,
    syncFromLocation,
  };
}
