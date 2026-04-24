/**
 * Glassbox dashboard — browser entry point.
 *
 * Handles DOM manipulation, session index loading, snapshot loading, SSE
 * subscription, and approval actions. All state logic lives in ./state.js.
 *
 * On load:
 *   1. Fetch the recent-session index from GET /sessions.
 *   2. Read ?session=<uuid> from the query string, if present.
 *   3. Fetch the selected snapshot from GET /sessions/<id>.
 *   4. Hydrate the state model from the snapshot.
 *   5. Render the full UI.
 *   6. Open an SSE connection to GET /sessions/<id>/events?after=<last_seq>
 *      and apply incremental updates via the reducer.
 */

import {
  applyEvent,
  beginSessionIndexLoad,
  beginLiveStreamConnection,
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
import {
  renderApprovalsPane,
  renderDashboardPanes,
} from "./render.js";

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

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

export function createDashboardApp({
  windowImpl = window,
  documentImpl = document,
  fetchImpl = fetch,
  EventSourceImpl = EventSource,
} = {}) {
  let state = createState();
  let eventSource = null;
  const drafts = {
    message: "",
    answer: "",
    forkBranchLabel: "",
  };

  function byId(id) {
    return documentImpl.getElementById(id);
  }

  function hasActiveSession() {
    return Boolean(state.sessionId);
  }

  function indicatorPresentation() {
    if (state.streamState === "loading") {
      return { text: "○ loading", className: "" };
    }

    if (state.streamState === "connecting") {
      return { text: "○ connecting", className: "" };
    }

    if (state.streamState === "live") {
      return { text: "● live", className: "connected" };
    }

    if (state.streamState === "reconnecting") {
      return { text: "○ reconnecting", className: "warning" };
    }

    if (state.streamState === "unavailable") {
      return { text: "✕ live unavailable", className: "error" };
    }

    if (state.streamState === "historical") {
      return { text: "◌ historical snapshot", className: "historical" };
    }

    if (state.streamState === "index") {
      return { text: "○ index mode", className: "" };
    }

    return { text: "○ waiting", className: "" };
  }

  function renderIndicator() {
    const indicator = byId("sse-indicator");
    const presentation = indicatorPresentation();
    indicator.textContent = presentation.text;
    indicator.className = presentation.className;
  }

  function closeSSE() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }

  function applySelectedSnapshot(snapshot) {
    state = {
      ...hydrateFromSnapshot(snapshot),
      sessionIndex: [...state.sessionIndex],
      sessionIndexState: state.sessionIndexState,
      sessionIndexError: state.sessionIndexError,
    };
    drafts.message = "";
    drafts.answer = "";
    drafts.forkBranchLabel = "";
  }

  function renderStatus() {
    const badge = byId("status-badge");
    if (!hasActiveSession()) {
      badge.textContent = state.sessionLoadState === "failed"
        ? "unavailable"
        : "no session";
      badge.className = state.sessionLoadState === "failed" ? "failed" : "idle";
      return;
    }

    badge.textContent = state.status;
    badge.className = state.status;
  }

  function renderHeader() {
    const sessionDisplay = byId("session-id-display");
    if (hasActiveSession()) {
      sessionDisplay.textContent = state.sessionId.slice(0, 8) + "\u2026";
      documentImpl.title = `Glassbox – ${state.sessionId.slice(0, 8)}`;
      return;
    }

    sessionDisplay.textContent = state.selectedSessionId
      ? `${state.selectedSessionId.slice(0, 8)} pending`
      : "standalone dashboard";
    documentImpl.title = "Glassbox Dashboard";
  }

  function renderPrimaryPane() {
    const title = byId("primary-pane-title");
    const el = byId("transcript-list");
    const panes = renderDashboardPanes(state);

    if (hasActiveSession()) {
      title.textContent = "Transcript";
      el.innerHTML = `${panes.selectedSessionSummary}${panes.transcript}`;
      el.querySelectorAll("[data-open-session-id]").forEach(btn => {
        btn.addEventListener("click", () => {
          void openSession(btn.dataset.openSessionId);
        });
      });
      el.scrollTop = el.scrollHeight;
      return;
    }

    title.textContent = "Session Browser";
    el.innerHTML = panes.landing;
    el.scrollTop = 0;
  }

  function renderSessionBrowser() {
    const el = byId("session-browser-list");
    el.innerHTML = renderDashboardPanes(state).sessionBrowser;
    el.querySelectorAll("[data-session-id]").forEach(btn => {
      btn.addEventListener("click", () => {
        void openSession(btn.dataset.sessionId);
      });
    });
  }

  function renderTurn() {
    byId("turn-status").innerHTML = renderDashboardPanes(state).turn;
  }

  function renderMetrics() {
    byId("metrics-list").innerHTML = renderDashboardPanes(state).metrics;
  }

  function renderToolCalls() {
    byId("tool-calls-list").innerHTML = renderDashboardPanes(state).toolCalls;
  }

  function renderLiveOutput() {
    const el = byId("live-output-list");
    el.innerHTML = renderDashboardPanes(state).liveOutput;
    el.scrollTop = el.scrollHeight;
  }

  function renderApprovals() {
    const el = byId("approvals-list");
    el.innerHTML = renderApprovalsPane(state);

    el.querySelectorAll(".btn[data-approval-id]").forEach(btn => {
      btn.addEventListener("click", () => {
        void resolveApproval(btn.dataset.approvalId, btn.dataset.decision);
      });
    });
  }

  function renderComposer() {
    const el = byId("composer-pane-body");
    el.innerHTML = renderDashboardPanes(state).composer;

    const form = byId("interaction-form");
    const input = byId("interaction-input");
    if (!form || !input) {
      const forkForm = byId("fork-form");
      const forkTurnSelect = byId("fork-turn-select");
      const forkBranchLabel = byId("fork-branch-label");
      if (forkTurnSelect) {
        forkTurnSelect.value = state.selectedForkTurnId ?? "";
        forkTurnSelect.addEventListener("change", () => {
          syncState(current => selectForkTurn(current, forkTurnSelect.value));
        });
      }
      if (forkBranchLabel) {
        forkBranchLabel.value = drafts.forkBranchLabel;
        forkBranchLabel.addEventListener("input", () => {
          drafts.forkBranchLabel = forkBranchLabel.value;
        });
      }
      if (forkForm) {
        forkForm.addEventListener("submit", async event => {
          event.preventDefault();
          await forkCurrentSession({
            turnId: forkTurnSelect?.value ?? state.selectedForkTurnId,
            branchLabel: forkBranchLabel?.value ?? drafts.forkBranchLabel,
          });
        });
      }
      return;
    }

    const mode = form.dataset.mode;
    if (mode === "message" || mode === "answer") {
      input.value = drafts[mode] ?? "";
      input.addEventListener("input", () => {
        drafts[mode] = input.value;
      });
    }

    form.addEventListener("submit", async event => {
      event.preventDefault();
      await submitComposer(form.dataset.mode, input.value);
    });

    const forkForm = byId("fork-form");
    const forkTurnSelect = byId("fork-turn-select");
    const forkBranchLabel = byId("fork-branch-label");
    if (forkTurnSelect) {
      forkTurnSelect.value = state.selectedForkTurnId ?? "";
      forkTurnSelect.addEventListener("change", () => {
        syncState(current => selectForkTurn(current, forkTurnSelect.value));
      });
    }
    if (forkBranchLabel) {
      forkBranchLabel.value = drafts.forkBranchLabel;
      forkBranchLabel.addEventListener("input", () => {
        drafts.forkBranchLabel = forkBranchLabel.value;
      });
    }
    if (forkForm) {
      forkForm.addEventListener("submit", async event => {
        event.preventDefault();
        await forkCurrentSession({
          turnId: forkTurnSelect?.value ?? state.selectedForkTurnId,
          branchLabel: forkBranchLabel?.value ?? drafts.forkBranchLabel,
        });
      });
    }
  }

  function renderEventLog() {
    const el = byId("event-log-list");
    el.innerHTML = renderDashboardPanes(state).eventLog;
    el.scrollTop = el.scrollHeight;
  }

  function renderSessionVisibility() {
    documentImpl.querySelectorAll(".session-detail-pane, #pane-composer").forEach(el => {
      el.classList.toggle("session-hidden", !hasActiveSession());
    });
  }

  function renderAll() {
    renderHeader();
    renderStatus();
    renderIndicator();
    renderPrimaryPane();
    renderSessionBrowser();
    renderSessionVisibility();
    renderComposer();
    renderTurn();
    renderMetrics();
    renderToolCalls();
    renderLiveOutput();
    renderApprovals();
    renderEventLog();
  }

  function syncState(updater) {
    state = updater(state);
    renderAll();
  }

  function shouldOpenLiveStream() {
    return ["running", "awaiting_user_input", "awaiting_approval"].includes(
      state.status,
    );
  }

  function connectSSE(sessionId, afterSequence, { reconnecting = false } = {}) {
    closeSSE();
    syncState(current => beginLiveStreamConnection(current, { reconnecting }));

    const url = `/sessions/${sessionId}/events?after=${afterSequence}`;
    const es = new EventSourceImpl(url);
    eventSource = es;

    es.onopen = () => {
      syncState(current => markLiveStreamConnected(current));
    };

    function handleFrame(evt) {
      try {
        const envelope = JSON.parse(evt.data);
        syncState(current => applyEvent(current, envelope));
      } catch {
        // ignore parse errors
      }
    }

    es.onmessage = handleFrame;

    [
      "SessionStarted", "SessionResumed", "SessionCompleted", "SessionFailed",
      "UserMessageReceived", "AssistantMessageCompleted",
      "ApprovalRequested", "ApprovalResolved",
      "UserQuestionAsked", "UserAnswerProvided",
      "TurnStarted", "TurnStatusChanged", "TurnCompleted", "TurnFailed",
      "ToolExecutionStarted", "ToolExecutionCompleted",
      "ToolOutputChunk",
      "ModelCallStarted", "ModelCallCompleted",
    ].forEach(name => es.addEventListener(name, handleFrame));

    es.onerror = () => {
      es.close();
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
    };
  }

  async function loadSessionIndex() {
    syncState(current => beginSessionIndexLoad(current));

    const resp = await fetchImpl("/sessions");
    if (!resp.ok) {
      syncState(current => failSessionIndexLoad(
        current,
        `Recent sessions unavailable (${resp.status})`,
      ));
      return;
    }

    const summaries = await resp.json();
    syncState(current => hydrateSessionIndex(current, summaries));
  }

  async function loadSnapshot(sessionId) {
    syncState(current => beginSessionSelection(current, sessionId));
    closeSSE();

    const resp = await fetchImpl(`/sessions/${sessionId}`);
    if (!resp.ok) {
      syncState(current => failSessionSelection(
        current,
        `Session not found (${resp.status})`,
      ));
      return false;
    }

    const snap = await resp.json();
    applySelectedSnapshot(snap);
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

  async function resolveApproval(approvalId, decision) {
    await resolvePendingApproval({
      sessionId: state.sessionId,
      approvalId,
      decision,
      fetchImpl,
      syncState,
    });
  }

  async function submitComposer(mode, value) {
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
      drafts[mode] = "";
      renderComposer();
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
      renderComposer();
      return result;
    }

    drafts.forkBranchLabel = "";
    await loadSessionIndex();
    await openSession(result.data.child_session_id);
    return result;
  }

  async function init() {
    state = clearSessionSelection(state);
    renderAll();
    await loadSessionIndex();
    await syncFromLocation({ replaceHistory: true });
  }

  return {
    init,
    openSession,
    forkCurrentSession,
    syncFromLocation,
    getState: () => state,
    destroy: () => closeSSE(),
  };
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    const app = createDashboardApp();
    void app.init();
    window.addEventListener("popstate", () => {
      void app.syncFromLocation({ replaceHistory: false });
    });
  });
}
