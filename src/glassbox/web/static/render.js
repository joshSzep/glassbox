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

export function renderTurnPane(state) {
  const turn = state.currentTurn;
  if (!turn) {
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

export function renderApprovalsPane(state) {
  if (state.pendingApprovals.length === 0) {
    return renderEmpty("No pending approvals.");
  }

  return state.pendingApprovals.map(approval => `
    <div class="approval-card" id="approval-${escHtml(approval.approval_id)}">
      <div class="approval-subject">${escHtml(approval.subject)}</div>
      <div class="approval-reason">${escHtml(approval.reason)}</div>
      <div class="approval-actions">
        <button class="btn btn-approve"
          data-approval-id="${escHtml(approval.approval_id)}"
          data-decision="approved">
          Approve
        </button>
        <button class="btn btn-deny"
          data-approval-id="${escHtml(approval.approval_id)}"
          data-decision="denied">
          Deny
        </button>
      </div>
    </div>
  `).join("");
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
    transcript: renderTranscriptPane(state),
    turn: renderTurnPane(state),
    toolCalls: renderToolCallsPane(state),
    liveOutput: renderLiveOutputPane(state),
    approvals: renderApprovalsPane(state),
    eventLog: renderEventLogPane(state),
  };
}
