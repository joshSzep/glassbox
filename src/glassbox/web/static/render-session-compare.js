import {
  escHtml,
  renderStatusChip,
  shortId,
} from "./render-utils.js";

function compareRelationSummary(state, compareSession) {
  if (state.parentSessionId === compareSession.sessionId) {
    return state.forkedFromTurnId
      ? `Comparing the selected child session against its parent branch. Divergence started at ${shortId(state.forkedFromTurnId)} (${state.forkedFromSequence ?? "unknown"}).`
      : "Comparing the selected child session against its parent branch.";
  }

  if (compareSession.parentSessionId === state.sessionId) {
    return compareSession.forkedFromTurnId
      ? `Comparing the selected parent session against a child branch that diverged at ${shortId(compareSession.forkedFromTurnId)} (${compareSession.forkedFromSequence ?? "unknown"}).`
      : "Comparing the selected parent session against a child branch.";
  }

  if (state.parentSessionId && state.parentSessionId === compareSession.parentSessionId) {
    return `Comparing sibling branches that share parent ${shortId(state.parentSessionId)}.`;
  }

  return "Comparing persisted historical snapshots outside the current live session.";
}

function driftArtifactSummaries(sessionLike) {
  const summaries = sessionLike.runtimeContext?.artifact_context?.summaries ?? [];
  return summaries.filter(summary => /replay|eval|drift|baseline/i.test([
    summary.summary_kind,
    summary.source_tool_name,
    summary.artifact_kind,
    summary.summary,
  ].filter(Boolean).join(" ")));
}

function renderComparedSessionCard(label, sessionLike, { latestActivitySummaryFromState, nextActionSummaryFromState }) {
  const transcriptCount = (sessionLike.transcript ?? []).length;
  const branchableTurnCount = (sessionLike.branchableTurns ?? []).length;
  return `<div class="selected-session-item">
    <div class="selected-session-label">${escHtml(label)}</div>
    <div class="selected-session-value session-compare-card-head">
      <span>${escHtml(shortId(sessionLike.sessionId))}</span>
      ${renderStatusChip(sessionLike.status)}
    </div>
    <div class="selected-session-value">${escHtml(nextActionSummaryFromState(sessionLike))}</div>
    <div class="selected-session-value session-compare-detail">${escHtml(latestActivitySummaryFromState(sessionLike))}</div>
    <div class="selected-session-value session-compare-detail">${escHtml(`${transcriptCount} transcript message(s) · ${branchableTurnCount} branchable turn(s)`)}</div>
  </div>`;
}

function renderDriftArtifactGroup(label, sessionLike) {
  const summaries = driftArtifactSummaries(sessionLike);
  if (summaries.length === 0) {
    return `<div class="selected-session-item">
      <div class="selected-session-label">${escHtml(label)}</div>
      <div class="selected-session-value">No replay or eval drift artifacts are attached to this snapshot.</div>
    </div>`;
  }

  return `<div class="selected-session-item selected-session-item-wide">
    <div class="selected-session-label">${escHtml(label)}</div>
    <div class="session-compare-artifacts">${summaries.map(summary => `
      <div class="session-compare-artifact">
        <div class="session-compare-artifact-title">${escHtml(summary.summary_kind.replace(/_/g, " "))}</div>
        <div class="session-compare-detail">${escHtml(summary.summary)}</div>
        <div class="session-compare-detail">${escHtml(`${summary.source_tool_name || "unknown tool"} · ${summary.artifact_kind || "artifact"}`)}</div>
        <div class="session-compare-detail">${escHtml(summary.target_paths.length > 0 ? summary.target_paths.join(", ") : summary.artifact_path)}</div>
      </div>
    `).join("")}</div>
  </div>`;
}

export function renderCompareInspector(state, helpers) {
  if (state.compareSessionLoadState === "loading" && state.compareSessionId) {
    return `<div class="session-compare-panel">
      <div class="selected-session-eyebrow">Lineage compare</div>
      <p class="selected-session-copy">Loading comparison snapshot for ${escHtml(shortId(state.compareSessionId))}.</p>
    </div>`;
  }

  if (state.compareSessionLoadState === "failed") {
    return `<div class="session-compare-panel session-compare-panel-error">
      <div class="session-compare-head">
        <div>
          <div class="selected-session-eyebrow">Lineage compare</div>
          <h3>Comparison unavailable</h3>
        </div>
        <button type="button" class="session-compare-button" data-clear-compare="true">Clear comparison</button>
      </div>
      <p class="selected-session-copy">${escHtml(state.compareSessionLoadError ?? "The comparison snapshot could not be loaded.")}</p>
    </div>`;
  }

  if (!state.compareSession) {
    return "";
  }

  const compareSession = state.compareSession;
  const selectedDrift = driftArtifactSummaries(state);
  const compareDrift = driftArtifactSummaries(compareSession);

  return `<div class="session-compare-panel">
    <div class="session-compare-head">
      <div>
        <div class="selected-session-eyebrow">Lineage compare</div>
        <h3>Comparison session ${escHtml(shortId(compareSession.sessionId))}</h3>
      </div>
      <button type="button" class="session-compare-button" data-clear-compare="true">Clear comparison</button>
    </div>
    <p class="selected-session-copy">${escHtml(compareRelationSummary(state, compareSession))}</p>
    <div class="selected-session-grid">
      ${renderComparedSessionCard("Selected session", state, helpers)}
      ${renderComparedSessionCard("Compared session", compareSession, helpers)}
      <div class="selected-session-item">
        <div class="selected-session-label">Transcript delta</div>
        <div class="selected-session-value">${escHtml(`${state.transcript.length - compareSession.transcript.length > 0 ? "+" : ""}${state.transcript.length - compareSession.transcript.length} message(s)`)} </div>
        <div class="session-compare-detail">${escHtml(`${state.turnMetrics.length} vs ${compareSession.turnMetrics.length} turn metric rows`)}</div>
      </div>
      <div class="selected-session-item">
        <div class="selected-session-label">Replay / eval cues</div>
        <div class="selected-session-value">${escHtml(`${selectedDrift.length} current · ${compareDrift.length} compared`)}</div>
        <div class="session-compare-detail">Use snapshot-backed artifact summaries to inspect manifest drift, replay failures, or eval evidence without leaving the dashboard.</div>
      </div>
      ${renderDriftArtifactGroup("Selected session artifacts", state)}
      ${renderDriftArtifactGroup("Compared session artifacts", compareSession)}
    </div>
  </div>`;
}
