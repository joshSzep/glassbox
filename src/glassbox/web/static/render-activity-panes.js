import { escHtml, renderEmpty, shortId } from "./render-utils.js";

function renderPolicySummary(summary) {
  if (!summary || summary.total_decisions === 0) {
    return "";
  }

  const highestRisk = summary.highest_risk_level ?? "n/a";
  return `<div class="turn-policy-summary">
    <div class="detail-row"><span class="detail-label">Policy decisions</span><span class="detail-value">${escHtml(String(summary.total_decisions))}</span></div>
    <div class="detail-row"><span class="detail-label">Allow / approve / blocked</span><span class="detail-value">${escHtml(`${summary.allow_count} / ${summary.approve_count} / ${summary.blocked_count}`)}</span></div>
    <div class="detail-row"><span class="detail-label">Highest risk</span><span class="detail-value">${escHtml(highestRisk)}</span></div>
  </div>`;
}

function eventLabel(eventType) {
  switch (eventType) {
    case "TurnStarted":
      return "Turn started";
    case "TurnCompleted":
      return "Turn completed";
    case "TurnFailed":
      return "Turn failed";
    case "ModelCallStarted":
      return "Model call started";
    case "ModelCallCompleted":
      return "Model call completed";
    case "ToolExecutionStarted":
      return "Tool call started";
    case "ToolExecutionCompleted":
      return "Tool call completed";
    case "ToolArtifactRecorded":
      return "Artifact recorded";
    case "ReplayArtifactRecorded":
      return "Replay artifact recorded";
    case "ApprovalRequested":
      return "Approval requested";
    case "ApprovalResolved":
      return "Approval resolved";
    case "UserQuestionAsked":
      return "Ask-user question";
    case "UserAnswerProvided":
      return "Ask-user answer";
    case "SessionFailed":
      return "Session failed";
    default:
      return eventType;
  }
}

function renderTurnTimeline(state) {
  const recent = (state.eventLog ?? []).slice(-10).reverse();
  if (recent.length === 0) {
    return "";
  }

  return `<div class="turn-timeline">
    <div class="turn-timeline-label">Recent timeline</div>
    <div class="turn-timeline-list">${recent.map(event => `
      <div class="turn-timeline-entry">
        <span class="turn-timeline-seq">#${escHtml(String(event.sequence))}</span>
        <span class="turn-timeline-text">${escHtml(eventLabel(event.event_type))}</span>
      </div>
    `).join("")}</div>
  </div>`;
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
        ${renderTurnTimeline(state)}
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

  const latestMetrics = (state.turnMetrics ?? []).find(metrics => metrics.turn_id === turn.turn_id);
  const metricsHtml = latestMetrics
    ? `<div class="turn-metrics-inline">
        <div class="detail-row"><span class="detail-label">Model calls</span><span class="detail-value">${escHtml(String(latestMetrics.model_call_count ?? 0))}</span></div>
        <div class="detail-row"><span class="detail-label">Tool calls</span><span class="detail-value">${escHtml(String(latestMetrics.tool_call_count ?? 0))}</span></div>
        <div class="detail-row"><span class="detail-label">Token total</span><span class="detail-value">${escHtml(String((latestMetrics.model_input_tokens_total ?? 0) + (latestMetrics.model_output_tokens_total ?? 0)))}</span></div>
      </div>`
    : "";
  const policyHtml = renderPolicySummary(state.currentTurnPolicySummary);

  return `<div class="turn-card status-${escHtml(turn.status)}">
    ${detailHtml}
    ${errorHtml}
    ${metricsHtml}
    ${policyHtml}
    ${renderTurnTimeline(state)}
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
