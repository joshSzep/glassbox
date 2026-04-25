import { escHtml, renderEmpty, shortId } from "./render-utils.js";

function renderPolicyMeta(item) {
  if (!item?.policy_outcome || !item?.policy_risk_level) {
    return "";
  }

  const source = item.policy_source_kind && item.policy_source_label
    ? ` via ${item.policy_source_kind}:${item.policy_source_label}`
    : "";
  const reason = item.policy_reason ? `<div class="tool-policy-reason">${escHtml(item.policy_reason)}</div>` : "";
  return `<div class="tool-meta">policy ${escHtml(item.policy_outcome)} ${escHtml(item.policy_risk_level)}${escHtml(source)}</div>${reason}`;
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
      ${renderPolicyMeta(tool)}
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
