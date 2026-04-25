import {
  escHtml,
  renderGuidanceChip,
  renderStatusChip,
  shortId,
} from "./render-utils.js";
import { activeSessionSummary } from "./render-selected-session.js";

const QUEUE_ORDER = [
  ["all", "All sessions", "total"],
  ["approvals", "Approvals", "approvals"],
  ["questions", "Questions", "questions"],
  ["failures", "Failures", "failures"],
  ["degraded", "Degraded", "degraded"],
  ["active", "Active", "active"],
];

function lineageSummaryFromSessionSummary(summary) {
  if (summary.parent_session_id && summary.branch_label) {
    return `branch ${summary.branch_label} from ${shortId(summary.parent_session_id)}`;
  }
  if (summary.parent_session_id) {
    return `child of ${shortId(summary.parent_session_id)}`;
  }
  if (summary.child_session_count > 0) {
    return `${summary.child_session_count} child session${summary.child_session_count === 1 ? "" : "s"}`;
  }
  return "root session";
}

function availabilitySummaryFromSessionSummary(summary) {
  if (summary.projection_health?.degraded) {
    return {
      tone: "warning",
      label: "Projection degraded",
      detail: summary.projection_health?.detail
        ?? "Derived state is stale. Rebuild projections from canonical events.",
    };
  }

  if (summary.status === "awaiting_user_input") {
    return {
      tone: "actionable",
      label: "Browser action available",
      detail: summary.pending_question_text
        ? `Waiting on an ask_user answer: ${summary.pending_question_text}`
        : "Waiting on an ask_user answer from the operator.",
    };
  }

  if (summary.status === "awaiting_approval") {
    return {
      tone: "actionable",
      label: "Browser action available",
      detail: "Waiting on an approval decision from the operator.",
    };
  }

  if (summary.status === "running") {
    return {
      tone: summary.has_active_turn ? "live" : "actionable",
      label: summary.live_actionable === false
        ? "Historical inspection only"
        : summary.next_action_summary === "Send the next prompt"
        ? "Browser action available"
        : "Live session",
      detail: summary.next_action_summary,
    };
  }

  if (["completed", "cancelled", "failed"].includes(summary.status)) {
    return {
      tone: "historical",
      label: "Historical inspection only",
      detail: summary.session_failure_message
        ? `Failure: ${summary.session_failure_message}`
        : summary.next_action_summary,
    };
  }

  return {
    tone: "neutral",
    label: "Inspect session",
    detail: summary.next_action_summary,
  };
}

function formatQueueCount(state, queueKey) {
  return String(state.queueCounts?.[queueKey] ?? 0);
}

function renderQueueTabs(state) {
  return `<div class="console-queue-tabs">${QUEUE_ORDER.map(([queueKey, label, countKey]) => `
    <button
      type="button"
      class="queue-tab${state.selectedQueue === queueKey ? " selected" : ""}"
      data-queue="${escHtml(queueKey)}"
    >
      <span class="queue-tab-label">${escHtml(label)}</span>
      <span class="queue-tab-count">${escHtml(formatQueueCount(state, countKey))}</span>
    </button>
  `).join("")}</div>`;
}

function renderRuntimeHealthPanel(state) {
  const runtime = state.runtimeSummary ?? {};
  const runtimeState = runtime.state ?? "not_running";
  const healthLabel = runtime.health ? `${runtimeState} (${runtime.health})` : runtimeState;
  const projection = state.projectionHealthCounts ?? {};
  return `<div class="console-overview-grid">
    <div class="console-overview-card">
      <div class="console-overview-label">Runtime owner</div>
      <div class="console-overview-value">${escHtml(healthLabel)}</div>
      <div class="console-overview-detail">${escHtml(runtime.dashboard_url ?? runtime.workspace_root ?? "historical-only workspace view")}</div>
    </div>
    <div class="console-overview-card">
      <div class="console-overview-label">Projection health</div>
      <div class="console-overview-value">${escHtml(`${projection.ok ?? 0} ok / ${projection.degraded ?? 0} degraded`)}</div>
      <div class="console-overview-detail">${escHtml(`${projection.stale ?? 0} stale, ${projection.unavailable ?? 0} unavailable`)}</div>
    </div>
    <div class="console-overview-card">
      <div class="console-overview-label">Action needed</div>
      <div class="console-overview-value">${escHtml(String(state.queueCounts?.action_needed ?? 0))}</div>
      <div class="console-overview-detail">${escHtml(`${state.queueCounts?.approvals ?? 0} approvals, ${state.queueCounts?.questions ?? 0} questions, ${state.queueCounts?.failures ?? 0} failures`)}</div>
    </div>
  </div>`;
}

function renderSessionQueueChips(summary) {
  const chips = [
    summary.priority_bucket,
    ...(summary.queue_memberships ?? []).filter(queue => queue !== "active"),
  ].filter(Boolean);
  if (chips.length === 0) {
    return "";
  }
  return `<div class="session-card-queues">${chips.map(queue => renderGuidanceChip(
    queue === "degraded" || queue === "failures" ? "warning" : queue === "historical" ? "historical" : "neutral",
    queue.replace(/-/g, " "),
  )).join("")}</div>`;
}

export function renderSessionBrowserPane(state) {
  const queueTabs = renderQueueTabs(state);

  if (state.sessionIndexState === "loading") {
    return `${queueTabs}<p class="empty">Loading operator console…</p>`;
  }

  if (state.sessionIndexState === "failed") {
    return `${queueTabs}<div class="session-browser-empty">
      <div class="session-browser-title">Unable to load recent sessions</div>
      <div class="session-browser-help">${escHtml(state.sessionIndexError ?? "Unknown error")}</div>
    </div>`;
  }

  if ((state.sessionIndex ?? []).length === 0) {
    return `${queueTabs}<div class="session-browser-empty">
      <div class="session-browser-title">No sessions in this queue</div>
      <div class="session-browser-help">Select another operator queue or start a Glassbox session to populate the console.</div>
    </div>`;
  }

  const selectedSessionId = state.selectedSessionId ?? state.sessionId;
  const cards = state.sessionIndex.map(summary => {
    const isSelected = summary.session_id === selectedSessionId;
    const latestSummary = summary.latest_message_summary ?? "No transcript yet";
    const availability = availabilitySummaryFromSessionSummary(summary);
    const projectionState = summary.projection_health?.state ?? "ok";
    const updatedAt = summary.updated_at ?? "unknown";

    return `<button
      type="button"
      class="session-card${isSelected ? " selected" : ""}"
      data-session-id="${escHtml(summary.session_id)}"
    >
      <div class="session-card-head">
        <span class="session-card-id">${escHtml(summary.session_id.slice(0, 8))}</span>
        ${renderStatusChip(summary.status)}
      </div>
      <div class="session-card-meta">${escHtml(summary.model_name)} · ${escHtml(summary.approval_mode)}</div>
      <div class="session-card-path">${escHtml(summary.cwd)}</div>
      <div class="session-card-lineage">${escHtml(lineageSummaryFromSessionSummary(summary))}</div>
      ${renderSessionQueueChips(summary)}
      <div class="session-card-section-label">Next action</div>
      <div class="session-card-next">${escHtml(summary.next_action_summary)}</div>
      <div class="session-card-section-label">Last activity</div>
      <div class="session-card-summary">${escHtml(latestSummary)}</div>
      <div class="session-card-section-label">Operator state</div>
      <div class="session-card-summary">${escHtml(`Projection ${projectionState} · Updated ${updatedAt}`)}</div>
      <div class="session-card-footer">
        ${renderGuidanceChip(availability.tone, availability.label)}
        <span class="session-card-detail">${escHtml(availability.detail)}</span>
      </div>
    </button>`;
  }).join("");

  return `${queueTabs}${cards}`;
}

export function renderLandingPane(state) {
  const selectedSummary = activeSessionSummary(state);

  if (state.sessionLoadState === "loading" && state.selectedSessionId) {
    return `<div class="landing-state">
      <div class="landing-eyebrow">Loading session</div>
      <h2>Opening ${escHtml(state.selectedSessionId.slice(0, 8))}…</h2>
      <p class="landing-copy">Fetching the latest snapshot and connecting the dashboard stream.</p>
    </div>`;
  }

  if (state.sessionLoadState === "failed") {
    return `<div class="landing-state landing-state-error">
      <div class="landing-eyebrow">Session unavailable</div>
      <h2>Choose another recent session</h2>
      <p class="landing-copy">${escHtml(state.sessionLoadError ?? "The selected session could not be loaded.")}</p>
      <p class="landing-copy">The dashboard has recovered to the session index so you can choose another session without editing the URL.</p>
    </div>`;
  }

  if (selectedSummary) {
    return `<div class="landing-state">
      <div class="landing-eyebrow">Session selected</div>
      <h2>Open ${escHtml(selectedSummary.session_id.slice(0, 8))} from the browser</h2>
      <p class="landing-copy">The dashboard will load the transcript, live events, approvals, and next action controls for the selected session.</p>
      ${renderRuntimeHealthPanel(state)}
      <div class="landing-summary-row">
        ${renderStatusChip(selectedSummary.status)}
        <span class="landing-summary-text">${escHtml(selectedSummary.next_action_summary)}</span>
      </div>
    </div>`;
  }

  return `<div class="landing-state">
    <div class="landing-eyebrow">Operator console</div>
    <h2>What needs attention now</h2>
    <p class="landing-copy">Use the queue tabs to inspect approvals, pending questions, failures, degraded projections, and live sessions without opening every session individually.</p>
    ${renderRuntimeHealthPanel(state)}
    <div class="landing-summary-row">
      ${renderGuidanceChip("neutral", `Queue: ${(state.selectedQueue ?? "all").replace(/-/g, " ")}`)}
      <span class="landing-summary-text">${escHtml(`${state.queueCounts?.total ?? 0} total session(s) in workspace, ${state.queueCounts?.action_needed ?? 0} needing operator attention`)}</span>
    </div>
  </div>`;
}
