import { escHtml, renderEmpty, shortId } from "./render-utils.js";

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
