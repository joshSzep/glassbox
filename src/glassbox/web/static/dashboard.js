/**
 * Glassbox dashboard — browser-side logic.
 *
 * On load:
 *   1. Read ?session=<uuid> from the query string.
 *   2. Fetch the snapshot from GET /sessions/<id>.
 *   3. Hydrate the UI from the snapshot.
 *   4. Open an SSE connection to GET /sessions/<id>/events?after=<last_seq>
 *      and apply incremental updates.
 *
 * The event reducer is intentionally minimal for the initial version.
 * GBX-091 will expand it into a full client-state model.
 */

"use strict";

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

function formatTime(iso) {
  try { return new Date(iso).toLocaleTimeString(); } catch { return iso; }
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let state = {
  sessionId: null,
  lastSequence: 0,
  status: "unknown",
  transcript: [],
  pendingApprovals: [],
  eventLog: [],   // [{sequence, event_type}]
};

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
  if (state.transcript.length === 0) {
    el.innerHTML = '<p class="empty">No messages yet.</p>';
    return;
  }
  el.innerHTML = state.transcript.map(msg => {
    const parts = (msg.parts || []).map(p => escHtml(p.text || "")).join("\n");
    return `<div class="message">
      <div class="message-role ${escHtml(msg.role)}">${escHtml(msg.role)}</div>
      <div class="message-text">${parts}</div>
    </div>`;
  }).join("");
  el.scrollTop = el.scrollHeight;
}

function renderApprovals() {
  const el = byId("approvals-list");
  if (state.pendingApprovals.length === 0) {
    el.innerHTML = '<p class="empty">No pending approvals.</p>';
    return;
  }
  el.innerHTML = state.pendingApprovals.map(a => `
    <div class="approval-card" id="approval-${escHtml(a.approval_id)}">
      <div class="approval-subject">${escHtml(a.subject)}</div>
      <div class="approval-reason">${escHtml(a.reason)}</div>
      <div class="approval-actions">
        <button class="btn btn-approve"
          onclick="resolveApproval('${escHtml(a.approval_id)}','approved')">
          Approve
        </button>
        <button class="btn btn-deny"
          onclick="resolveApproval('${escHtml(a.approval_id)}','denied')">
          Deny
        </button>
      </div>
    </div>
  `).join("");
}

function renderEventLog() {
  const el = byId("event-log-list");
  const recent = state.eventLog.slice(-50);
  el.innerHTML = recent.map(e =>
    `<div class="event-entry">
      <span class="event-seq">${e.sequence}</span>
      <span class="event-type">${escHtml(e.event_type)}</span>
    </div>`
  ).join("");
  el.scrollTop = el.scrollHeight;
}

function renderAll() {
  renderStatus();
  renderTranscript();
  renderApprovals();
  renderEventLog();
}

// ---------------------------------------------------------------------------
// Snapshot hydration
// ---------------------------------------------------------------------------

async function loadSnapshot(sessionId) {
  const resp = await fetch(`/sessions/${sessionId}`);
  if (!resp.ok) {
    setError(`Session not found (${resp.status})`);
    return;
  }
  const snap = await resp.json();
  state.sessionId = sessionId;
  state.lastSequence = snap.last_sequence ?? 0;
  state.status = snap.status;
  state.transcript = snap.transcript ?? [];
  state.pendingApprovals = snap.pending_approvals ?? [];
  document.title = `Glassbox – ${sessionId.slice(0, 8)}`;
  byId("session-id-display").textContent = sessionId.slice(0, 8) + "…";
  renderAll();
  connectSSE(sessionId, state.lastSequence);
}

// ---------------------------------------------------------------------------
// Event reducer — incremental SSE updates
// ---------------------------------------------------------------------------

function applyEvent(env) {
  const { event_type, payload, sequence } = env;
  state.lastSequence = Math.max(state.lastSequence, sequence);
  state.eventLog.push({ sequence, event_type });

  switch (event_type) {
    case "SessionStarted":
    case "SessionResumed":
      state.status = "running";
      break;
    case "SessionCompleted":
      state.status = "completed";
      break;
    case "SessionFailed":
      state.status = "failed";
      break;
    case "UserMessageReceived":
      // Full transcript reload deferred to next snapshot poll.
      // For now push a lightweight entry.
      state.transcript.push({
        role: "user",
        parts: [{ text: payload.text ?? "" }],
      });
      break;
    case "ApprovalRequested":
      state.status = "awaiting_approval";
      state.pendingApprovals.push({
        approval_id: payload.approval_id,
        subject: payload.subject ?? "",
        reason: payload.reason ?? "",
      });
      break;
    case "ApprovalResolved":
      state.status = "running";
      state.pendingApprovals = state.pendingApprovals.filter(
        a => a.approval_id !== payload.approval_id
      );
      break;
    default:
      break;
  }
  renderAll();
}

// ---------------------------------------------------------------------------
// SSE connection
// ---------------------------------------------------------------------------

function connectSSE(sessionId, afterSequence) {
  const indicator = byId("sse-indicator");
  const url = `/sessions/${sessionId}/events?after=${afterSequence}`;
  const es = new EventSource(url);

  es.onopen = () => {
    indicator.textContent = "● live";
    indicator.className = "connected";
  };

  es.onmessage = evt => {
    try { applyEvent(JSON.parse(evt.data)); } catch { /* ignore parse errors */ }
  };

  // Named event frames (event: <EventType>)
  const knownEvents = [
    "SessionStarted", "SessionResumed", "SessionCompleted", "SessionFailed",
    "UserMessageReceived", "ApprovalRequested", "ApprovalResolved",
    "TurnStarted", "TurnCompleted", "TurnFailed",
    "ToolCallStarted", "ToolCallCompleted", "ToolCallFailed",
  ];
  knownEvents.forEach(name => {
    es.addEventListener(name, evt => {
      try { applyEvent(JSON.parse(evt.data)); } catch { /* ignore */ }
    });
  });

  es.onerror = () => {
    indicator.textContent = "✕ disconnected";
    indicator.className = "error";
    es.close();
    // Reconnect after 3 s using the latest known sequence.
    setTimeout(() => connectSSE(sessionId, state.lastSequence), 3000);
  };
}

// ---------------------------------------------------------------------------
// Approval resolution
// ---------------------------------------------------------------------------

async function resolveApproval(approvalId, decision) {
  const card = byId(`approval-${approvalId}`);
  if (card) {
    card.querySelectorAll(".btn").forEach(b => { b.disabled = true; });
  }
  await fetch(`/sessions/${state.sessionId}/approvals/${approvalId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  });
  // The SSE stream will deliver the ApprovalResolved event and update UI.
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

document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get("session");
  if (!sessionId) {
    setError("No ?session=<id> in URL. Open this page from a Glassbox session.");
    return;
  }
  loadSnapshot(sessionId);
});
