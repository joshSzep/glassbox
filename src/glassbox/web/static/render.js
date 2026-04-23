/**
 * Pure dashboard pane renderers.
 *
 * These functions take the reducer state and return HTML strings for the
 * dashboard panes. They are side-effect free so frontend tests can validate
 * pane output without a browser DOM.
 */

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function shortId(value) {
  if (!value) {
    return "unknown";
  }
  return String(value).slice(0, 8);
}

function renderEmpty(message) {
  return `<p class="empty">${escHtml(message)}</p>`;
}

function renderStatusChip(status) {
  const statusText = status ? String(status) : "unknown";
  return `<span class="status-chip status-chip-${escHtml(statusText)}">${escHtml(statusText.replaceAll("_", " "))}</span>`;
}

function activeSessionSummary(state) {
  const selectedSessionId = state.selectedSessionId ?? state.sessionId;
  return (state.sessionIndex ?? []).find(
    summary => summary.session_id === selectedSessionId,
  ) ?? null;
}

function interactionMode(state) {
  if (state.status === "awaiting_user_input" && state.pendingQuestionId) {
    return "answer";
  }
  if (state.status === "running") {
    return "message";
  }
  return "blocked";
}

export function renderTranscriptPane(state) {
  if (state.transcript.length === 0) {
    return renderEmpty("No messages yet.");
  }

  return state.transcript.map(message => {
    const parts = (message.parts ?? [])
      .map(part => escHtml(part.text ?? ""))
      .join("\n");
    return `<div class="message">
      <div class="message-head">
        <div class="message-role ${escHtml(message.role)}">${escHtml(message.role)}</div>
        <div class="message-time">${escHtml(message.created_at ?? "live")}</div>
      </div>
      <div class="message-text">${parts}</div>
    </div>`;
  }).join("");
}

export function renderSessionBrowserPane(state) {
  if (state.sessionIndexState === "loading") {
    return renderEmpty("Loading recent sessions…");
  }

  if (state.sessionIndexState === "failed") {
    return `<div class="session-browser-empty">
      <div class="session-browser-title">Unable to load recent sessions</div>
      <div class="session-browser-help">${escHtml(state.sessionIndexError ?? "Unknown error")}</div>
    </div>`;
  }

  if ((state.sessionIndex ?? []).length === 0) {
    return `<div class="session-browser-empty">
      <div class="session-browser-title">No recent sessions</div>
      <div class="session-browser-help">Start a Glassbox chat session, then return here to inspect it from the browser.</div>
    </div>`;
  }

  const selectedSessionId = state.selectedSessionId ?? state.sessionId;
  return state.sessionIndex.map(summary => {
    const isSelected = summary.session_id === selectedSessionId;
    const latestSummary = summary.latest_message_summary ?? "No transcript yet";
    const pendingSummary = summary.pending_question_text
      ? `Question: ${summary.pending_question_text}`
      : summary.next_action_summary;

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
      <div class="session-card-summary">${escHtml(latestSummary)}</div>
      <div class="session-card-next">${escHtml(pendingSummary)}</div>
    </button>`;
  }).join("");
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
    </div>`;
  }

  if (selectedSummary) {
    return `<div class="landing-state">
      <div class="landing-eyebrow">Session selected</div>
      <h2>Open ${escHtml(selectedSummary.session_id.slice(0, 8))} from the browser</h2>
      <p class="landing-copy">The dashboard will load the transcript, live events, approvals, and next action controls for the selected session.</p>
      <div class="landing-summary-row">
        ${renderStatusChip(selectedSummary.status)}
        <span class="landing-summary-text">${escHtml(selectedSummary.next_action_summary)}</span>
      </div>
    </div>`;
  }

  return `<div class="landing-state">
    <div class="landing-eyebrow">Standalone dashboard</div>
    <h2>Choose a recent session</h2>
    <p class="landing-copy">Open any recent Glassbox session from the browser without copying a session ID into the URL first.</p>
  </div>`;
}

export function renderTurnPane(state) {
  const turn = state.currentTurn;
  if (!turn) {
    if (state.status === "failed" && state.sessionFailureMessage) {
      const retryableHtml = state.sessionFailureRetryable
        ? `<div class="turn-error">Retryable: yes</div>`
        : "";
      return `<div class="turn-card status-failed">
        <div class="detail-row">
          <span class="detail-label">Status</span>
          <span class="detail-value">failed</span>
        </div>
        <div class="turn-error">${escHtml(state.sessionFailureMessage)}</div>
        ${retryableHtml}
      </div>`;
    }
    return renderEmpty("No active turn.");
  }

  const details = [
    ["Turn", shortId(turn.turn_id)],
    ["Status", turn.status],
    ["Active tools", String(state.activeToolCalls.length)],
  ];

  if (turn.outcome) {
    details.push(["Outcome", turn.outcome]);
  }
  if (turn.trigger_message_id) {
    details.push(["Triggered by", shortId(turn.trigger_message_id)]);
  }

  const detailHtml = details.map(([label, value]) => `
    <div class="detail-row">
      <span class="detail-label">${escHtml(label)}</span>
      <span class="detail-value">${escHtml(value)}</span>
    </div>
  `).join("");

  const errorHtml = turn.error_message
    ? `<div class="turn-error">${escHtml(turn.error_message)}</div>`
    : "";

  return `<div class="turn-card status-${escHtml(turn.status)}">
    ${detailHtml}
    ${errorHtml}
  </div>`;
}

function formatMetricValue(value, suffix = "") {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${escHtml(String(value))}${suffix}`;
}

export function renderMetricsPane(state) {
  if ((state.turnMetrics ?? []).length === 0) {
    return renderEmpty("No runtime metrics yet.");
  }

  return state.turnMetrics.map(metrics => {
    const details = [
      ["Turn", shortId(metrics.turn_id)],
      ["Turn duration", formatMetricValue(metrics.turn_duration_ms, " ms")],
      ["Model calls", String(metrics.model_call_count ?? 0)],
      ["Model latency", formatMetricValue(metrics.model_duration_ms_total, " ms")],
      ["Input tokens", String(metrics.model_input_tokens_total ?? 0)],
      ["Output tokens", String(metrics.model_output_tokens_total ?? 0)],
      ["Tool calls", String(metrics.tool_call_count ?? 0)],
      ["Tool runtime", formatMetricValue(metrics.tool_duration_ms_total, " ms")],
    ];

    const detailHtml = details.map(([label, value]) => `
      <div class="detail-row">
        <span class="detail-label">${escHtml(label)}</span>
        <span class="detail-value">${value}</span>
      </div>
    `).join("");

    return `<div class="turn-card">
      ${detailHtml}
    </div>`;
  }).join("");
}

export function renderToolCallsPane(state) {
  if (state.activeToolCalls.length === 0) {
    return renderEmpty("No active tool calls.");
  }

  return state.activeToolCalls.map(tool => `
    <div class="tool-card">
      <div class="tool-name">${escHtml(tool.tool_name)}</div>
      <div class="tool-meta">call ${escHtml(shortId(tool.tool_call_id))}</div>
      <div class="tool-meta">turn ${escHtml(shortId(tool.turn_id))}</div>
      <div class="tool-status">${escHtml(tool.status)}</div>
    </div>
  `).join("");
}

export function renderLiveOutputPane(state) {
  if (state.liveOutput.length === 0) {
    return renderEmpty("No live output yet.");
  }

  return state.liveOutput.map(entry => `
    <div class="output-line output-${escHtml(entry.stream)}">
      <span class="output-stream">${escHtml(entry.stream)}</span>
      <span class="output-chunk">${escHtml(entry.chunk)}</span>
    </div>
  `).join("");
}

export function renderComposerPane(state) {
  const mode = interactionMode(state);
  const interaction = state.interactionSubmission ?? {
    kind: null,
    state: "idle",
    error: null,
  };
  const isBusy = interaction.state === "submitting" || interaction.state === "submitted";

  if (mode === "blocked") {
    let reason = "Session actions are currently unavailable.";
    if (state.status === "awaiting_approval") {
      reason = [
        "Resolve the pending approval below before sending a new prompt or ",
        "answering the model's question.",
      ].join("");
    } else if (state.status === "completed") {
      reason = "This session is complete and cannot accept new input.";
    } else if (state.status === "failed") {
      reason = "This session failed. Start a new session or inspect the failure details.";
    }

    return `<div class="composer-card composer-blocked">
      <div class="composer-label">Next Action Unavailable</div>
      <div class="composer-help">${escHtml(reason)}</div>
    </div>`;
  }

  const questionDetails = mode === "answer"
     ? `<div class="composer-question">${escHtml(state.pendingQuestionText ?? "Answer the pending model question.")}</div>
       <div class="composer-help">Question ID ${escHtml(state.pendingQuestionId ?? "unknown")}</div>
       <div class="composer-help">This sends an answer to the model's pending ask_user question. It does not start a new prompt.</div>`
     : `<div class="composer-help">Send a fresh user prompt after the previous turn has completed. Use this instead of answering a pending question or resolving an approval.</div>`;
  const buttonLabel = mode === "answer" ? "Send Answer" : "Send Prompt";
  const heading = mode === "answer" ? "Answer Pending Question" : "Continue Session";
  let statusHtml = "";

  if (interaction.state === "submitting") {
    statusHtml = `<div class="composer-status">Sending ${escHtml(interaction.kind ?? mode)}…</div>`;
  } else if (interaction.state === "submitted") {
    statusHtml = `<div class="composer-status">Request sent. Waiting for session update…</div>`;
  } else if (interaction.state === "failed" && interaction.error) {
    statusHtml = `<div class="composer-status composer-status-error">${escHtml(interaction.error)}</div>`;
  }

  return `<div class="composer-card composer-${escHtml(mode)}">
    <div class="composer-label">${escHtml(heading)}</div>
    ${questionDetails}
    ${statusHtml}
    <form id="interaction-form" class="composer-form" data-mode="${escHtml(mode)}">
      <textarea
        id="interaction-input"
        class="composer-input"
        rows="4"
        placeholder="${escHtml(mode === "answer" ? "Type your answer" : "Type the next prompt")}"
        ${isBusy ? "disabled" : ""}
      ></textarea>
      <div class="composer-actions">
        <button
          id="interaction-submit"
          class="btn btn-submit"
          type="submit"
          ${isBusy ? "disabled" : ""}
        >${escHtml(buttonLabel)}</button>
      </div>
    </form>
  </div>`;
}

export function renderApprovalsPane(state) {
  if (state.pendingApprovals.length === 0) {
    return renderEmpty("No pending approvals.");
  }

  return state.pendingApprovals.map(approval => {
    const resolutionState = approval.resolution_state ?? "idle";
    const resolutionDecision = approval.resolution_decision ?? null;
    const disabled = resolutionState === "submitting" || resolutionState === "submitted";
    let statusHtml = "";

    if (resolutionState === "submitting") {
      statusHtml = `<div class="approval-status">Submitting ${escHtml(resolutionDecision ?? "decision")}…</div>`;
    } else if (resolutionState === "submitted") {
      statusHtml = `<div class="approval-status">Decision sent. Waiting for session update…</div>`;
    } else if (resolutionState === "failed") {
      statusHtml = `<div class="approval-status approval-status-error">${escHtml(approval.resolution_error ?? "Resolution failed")}</div>`;
    }

    return `
    <div class="approval-card approval-${escHtml(resolutionState)}" id="approval-${escHtml(approval.approval_id)}">
      <div class="approval-subject">${escHtml(approval.subject)}</div>
      <div class="approval-reason">${escHtml(approval.reason)}</div>
      ${statusHtml}
      <div class="approval-actions">
        <button class="btn btn-approve"
          data-approval-id="${escHtml(approval.approval_id)}"
          data-decision="approved"
          ${disabled ? "disabled" : ""}>
          Approve
        </button>
        <button class="btn btn-deny"
          data-approval-id="${escHtml(approval.approval_id)}"
          data-decision="denied"
          ${disabled ? "disabled" : ""}>
          Deny
        </button>
      </div>
    </div>
  `;
  }).join("");
}

export function renderEventLogPane(state) {
  const recent = state.eventLog.slice(-50);
  if (recent.length === 0) {
    return renderEmpty("No events yet.");
  }

  return recent.map(event => `
    <div class="event-entry">
      <span class="event-seq">${event.sequence}</span>
      <span class="event-type">${escHtml(event.event_type)}</span>
    </div>
  `).join("");
}

export function renderDashboardPanes(state) {
  return {
    composer: renderComposerPane(state),
    landing: renderLandingPane(state),
    sessionBrowser: renderSessionBrowserPane(state),
    transcript: renderTranscriptPane(state),
    turn: renderTurnPane(state),
    metrics: renderMetricsPane(state),
    toolCalls: renderToolCallsPane(state),
    liveOutput: renderLiveOutputPane(state),
    approvals: renderApprovalsPane(state),
    eventLog: renderEventLogPane(state),
  };
}
