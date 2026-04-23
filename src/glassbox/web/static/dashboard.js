/**
 * Glassbox dashboard — browser entry point.
 *
 * Handles DOM manipulation, snapshot loading, SSE subscription, and approval
 * actions.  All state logic lives in ./state.js.
 *
 * On load:
 *   1. Read ?session=<uuid> from the query string.
 *   2. Fetch the snapshot from GET /sessions/<id>.
 *   3. Hydrate the state model from the snapshot.
 *   4. Render the full UI.
 *   5. Open an SSE connection to GET /sessions/<id>/events?after=<last_seq>
 *      and apply incremental updates via the reducer.
 */

import { applyEvent, createState, hydrateFromSnapshot } from "./state.js";
import { resolvePendingApproval } from "./approval-actions.js";
import {
  submitPendingQuestionAnswer,
  submitSessionMessage,
} from "./interaction-actions.js";
import {
  renderApprovalsPane,
  renderDashboardPanes,
} from "./render.js";

// ---------------------------------------------------------------------------
// Module-level state
// ---------------------------------------------------------------------------

let state = createState();
const drafts = {
  message: "",
  answer: "",
};

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function byId(id) { return document.getElementById(id); }

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

function renderStatus() {
  const badge = byId("status-badge");
  badge.textContent = state.status;
  badge.className = state.status;
}

function renderTranscript() {
  const el = byId("transcript-list");
  el.innerHTML = renderDashboardPanes(state).transcript;
  el.scrollTop = el.scrollHeight;
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
      resolveApproval(btn.dataset.approvalId, btn.dataset.decision);
    });
  });
}

function renderComposer() {
  const el = byId("composer-pane-body");
  el.innerHTML = renderDashboardPanes(state).composer;

  const form = byId("interaction-form");
  const input = byId("interaction-input");
  if (!form || !input) {
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
}

function renderEventLog() {
  const el = byId("event-log-list");
  el.innerHTML = renderDashboardPanes(state).eventLog;
  el.scrollTop = el.scrollHeight;
}

function renderAll() {
  renderStatus();
  renderTranscript();
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

// ---------------------------------------------------------------------------
// Snapshot load
// ---------------------------------------------------------------------------

async function loadSnapshot(sessionId) {
  const resp = await fetch(`/sessions/${sessionId}`);
  if (!resp.ok) {
    setError(`Session not found (${resp.status})`);
    return;
  }
  const snap = await resp.json();
  state = hydrateFromSnapshot(snap);
  document.title = `Glassbox – ${sessionId.slice(0, 8)}`;
  byId("session-id-display").textContent = sessionId.slice(0, 8) + "\u2026";
  renderAll();
  connectSSE(sessionId, state.lastSequence);
}

// ---------------------------------------------------------------------------
// SSE connection
// ---------------------------------------------------------------------------

function connectSSE(sessionId, afterSequence) {
  const indicator = byId("sse-indicator");
  const url = `/sessions/${sessionId}/events?after=${afterSequence}`;
  const es = new EventSource(url);

  es.onopen = () => {
    indicator.textContent = "\u25cf live";
    indicator.className = "connected";
  };

  function handleFrame(evt) {
    try {
      const envelope = JSON.parse(evt.data);
      syncState(current => applyEvent(current, envelope));
    } catch { /* ignore parse errors */ }
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
    indicator.textContent = "\u2715 disconnected";
    indicator.className = "error";
    es.close();
    setTimeout(() => connectSSE(sessionId, state.lastSequence), 3000);
  };
}

// ---------------------------------------------------------------------------
// Approval resolution
// ---------------------------------------------------------------------------

async function resolveApproval(approvalId, decision) {
  await resolvePendingApproval({
    sessionId: state.sessionId,
    approvalId,
    decision,
    fetchImpl: fetch,
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
      fetchImpl: fetch,
      syncState,
    });
  } else if (mode === "answer" && state.pendingQuestionId) {
    result = await submitPendingQuestionAnswer({
      sessionId: state.sessionId,
      questionId: state.pendingQuestionId,
      answer: value,
      fetchImpl: fetch,
      syncState,
    });
  }

  if (result?.ok) {
    drafts[mode] = "";
    renderComposer();
  }
}

// ---------------------------------------------------------------------------
// Error display
// ---------------------------------------------------------------------------

function setError(msg) {
  byId("status-badge").textContent = "error";
  byId("transcript-list").innerHTML =
    `<p style="color:var(--red)">${escHtml(msg)}</p>`;
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

const params = new URLSearchParams(window.location.search);
const sessionId = params.get("session");
if (!sessionId) {
  document.addEventListener("DOMContentLoaded", () => {
    setError("No ?session=<id> in URL. Open this page from a Glassbox session.");
  });
} else {
  document.addEventListener("DOMContentLoaded", () => loadSnapshot(sessionId));
}
