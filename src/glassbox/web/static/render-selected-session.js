import {
  escHtml,
  renderGuidanceChip,
  renderStatusChip,
  shortId,
} from "./render-utils.js";
import { renderCompareInspector } from "./render-session-compare.js";

function renderRuntimeContextSummary(state) {
  const runtimeContext = state.runtimeContext;
  if (!runtimeContext) {
    return "";
  }

  const repository = runtimeContext.repository_context;
  const repositoryDetails = [
    ["Workspace summary", repository.workspace_name],
  ];

  if (repository.high_signal_paths.length > 0) {
    repositoryDetails.push(["High-signal paths", repository.high_signal_paths.join(", ")]);
  }
  if (repository.top_level_directories.length > 0) {
    let directoryLine = repository.top_level_directories.join(", ");
    if (repository.additional_directory_count > 0) {
      directoryLine += ` (+${repository.additional_directory_count} more)`;
    }
    repositoryDetails.push(["Top-level directories", directoryLine]);
  }
  if (repository.top_level_files.length > 0) {
    let fileLine = repository.top_level_files.join(", ");
    if (repository.additional_file_count > 0) {
      fileLine += ` (+${repository.additional_file_count} more)`;
    }
    repositoryDetails.push(["Top-level files", fileLine]);
  }
  if (repository.project_markers.length > 0) {
    repositoryDetails.push(["Project markers", repository.project_markers.join(", ")]);
  }

  const repositoryHtml = repositoryDetails.map(([label, value]) => `
    <div class="selected-session-item${label === "High-signal paths" || label === "Top-level directories" || label === "Top-level files" ? " selected-session-item-wide" : ""}">
      <div class="selected-session-label">${escHtml(label)}</div>
      <div class="selected-session-value">${escHtml(value)}</div>
    </div>
  `).join("");

  const runtimeNotesHtml = runtimeContext.runtime_notes.length > 0
    ? `<div class="selected-session-item selected-session-item-wide">
        <div class="selected-session-label">Runtime notes</div>
        <div class="selected-session-value">${runtimeContext.runtime_notes.map(note => {
          const suffix = note.inherited
            ? note.source_session_id
              ? ` (inherited from ${shortId(note.source_session_id)})`
              : " (inherited)"
            : "";
          return `<div>${escHtml(`[${note.category}] ${note.message}${suffix}`)}</div>`;
        }).join("")}${runtimeContext.additional_runtime_note_count > 0
          ? `<div>${escHtml(`+${runtimeContext.additional_runtime_note_count} more active note(s)`)}</div>`
          : ""}</div>
      </div>`
    : `<div class="selected-session-item selected-session-item-wide">
        <div class="selected-session-label">Runtime notes</div>
        <div class="selected-session-value">none</div>
      </div>`;

  const workingSetHtml = runtimeContext.working_set?.items?.length > 0
    ? `<div class="selected-session-item selected-session-item-wide">
        <div class="selected-session-label">Working set</div>
        <div class="selected-session-value">${runtimeContext.working_set.items.map(item => {
          const inheritedSuffix = item.inherited ? " (inherited)" : "";
          const reasonSuffix = item.reasons.length > 0 ? `: ${item.reasons.slice(0, 2).join("; ")}` : "";
          return `<div>${escHtml(`[${item.subject_kind}] ${item.subject}${inheritedSuffix} - ${item.summary}${reasonSuffix}`)}</div>`;
        }).join("")}${runtimeContext.working_set.additional_item_count > 0
          ? `<div>${escHtml(`+${runtimeContext.working_set.additional_item_count} more working-set item(s)`)}</div>`
          : ""}</div>
      </div>`
    : `<div class="selected-session-item selected-session-item-wide">
        <div class="selected-session-label">Working set</div>
        <div class="selected-session-value">none</div>
      </div>`;

  const artifactContextHtml = runtimeContext.artifact_context?.summaries?.length > 0
    ? `<div class="selected-session-item selected-session-item-wide">
        <div class="selected-session-label">Artifact-backed context</div>
        <div class="selected-session-value">${runtimeContext.artifact_context.summaries.map(summary => {
          const freshnessSuffix = summary.freshness ? ` (${summary.freshness})` : "";
          const inheritedSuffix = summary.inherited ? " (inherited)" : "";
          const failingTestsSuffix = summary.failing_tests.length > 0
            ? `: failing tests: ${summary.failing_tests.slice(0, 2).join(", ")}`
            : "";
          return `<div>${escHtml(`[${summary.summary_kind}] ${summary.summary}${freshnessSuffix}${inheritedSuffix}${failingTestsSuffix}`)}</div>`;
        }).join("")}${runtimeContext.artifact_context.additional_summary_count > 0
          ? `<div>${escHtml(`+${runtimeContext.artifact_context.additional_summary_count} more artifact-backed summary item(s)`)}</div>`
          : ""}</div>
      </div>`
    : `<div class="selected-session-item selected-session-item-wide">
        <div class="selected-session-label">Artifact-backed context</div>
        <div class="selected-session-value">none</div>
      </div>`;

  return `<div class="selected-session-runtime-context">
    <div class="selected-session-label">Runtime context</div>
    <div class="selected-session-grid">
      ${repositoryHtml}
      ${runtimeNotesHtml}
      ${workingSetHtml}
      ${artifactContextHtml}
    </div>
  </div>`;
}

function streamSummaryFromState(state) {
  if (state.streamState === "connecting") {
    return {
      tone: "live",
      label: "Connecting live stream",
      detail: "Snapshot loaded. Connecting to incremental live events for this session.",
    };
  }

  if (state.streamState === "live") {
    return {
      tone: "live",
      label: "Live stream connected",
      detail: "Streaming incremental events from the session runtime.",
    };
  }

  if (state.streamState === "reconnecting") {
    return {
      tone: "warning",
      label: "Reconnecting live stream",
      detail: state.streamRetryCount > 0
        ? `Snapshot still available. Retrying the live stream connection (attempt ${state.streamRetryCount}).`
        : "Snapshot still available. Retrying the live stream connection.",
    };
  }

  if (state.streamState === "unavailable") {
    return {
      tone: "warning",
      label: "Live stream unavailable",
      detail: state.streamError
        ?? "Showing the last persisted snapshot only. The owning runtime may no longer be active.",
    };
  }

  if (state.streamState === "historical") {
    return {
      tone: "historical",
      label: "Historical snapshot",
      detail: "This session is no longer expected to emit live events. You are viewing persisted history.",
    };
  }

  if (state.streamState === "loading") {
    return {
      tone: "neutral",
      label: "Loading snapshot",
      detail: "Fetching the latest persisted snapshot for this session.",
    };
  }

  return {
    tone: "neutral",
    label: "Stream state unknown",
    detail: "Snapshot access is available, but the live stream state is not established yet.",
  };
}

export function activeSessionSummary(state) {
  const selectedSessionId = state.selectedSessionId ?? state.sessionId;
  return (state.sessionIndex ?? []).find(
    summary => summary.session_id === selectedSessionId,
  ) ?? null;
}

function renderLineageNavigator(state) {
  const compareButtonLabel = sessionId => {
    if (state.compareSessionId !== sessionId) {
      return "Compare";
    }
    if (state.compareSessionLoadState === "loading") {
      return "Comparing…";
    }
    if (state.compareSessionLoadState === "failed") {
      return "Retry compare";
    }
    return "Comparing";
  };

  const parentHtml = state.parentSessionId
    ? `<div class="session-link-actions">
        <button type="button" class="session-link-button" data-open-session-id="${escHtml(state.parentSessionId)}">Open ${escHtml(shortId(state.parentSessionId))}</button>
        <button type="button" class="session-compare-button${state.compareSessionId === state.parentSessionId ? " selected" : ""}" data-compare-session-id="${escHtml(state.parentSessionId)}">${escHtml(compareButtonLabel(state.parentSessionId))}</button>
      </div>`
    : `<span class="lineage-empty">Root session</span>`;

  const childHtml = (state.childSessions ?? []).length > 0
    ? `<div class="lineage-list">${state.childSessions.map(child => `
        <div class="session-link-actions">
          <button type="button" class="session-link-button session-link-child" data-open-session-id="${escHtml(child.session_id)}">
            <span>${escHtml(shortId(child.session_id))}</span>
            <span>${escHtml(child.branch_label ?? child.status)}</span>
          </button>
          <button type="button" class="session-compare-button${state.compareSessionId === child.session_id ? " selected" : ""}" data-compare-session-id="${escHtml(child.session_id)}">${escHtml(compareButtonLabel(child.session_id))}</button>
        </div>
      `).join("")}</div>`
    : `<span class="lineage-empty">No child sessions yet</span>`;

  const sourceHtml = state.forkedFromTurnId
    ? `<div class="selected-session-lineage-copy">Forked from turn ${escHtml(shortId(state.forkedFromTurnId))} at sequence ${escHtml(String(state.forkedFromSequence ?? "unknown"))}${state.branchLabel ? ` as ${escHtml(state.branchLabel)}` : ""}.</div>`
    : `<div class="selected-session-lineage-copy">This session has no parent branch.</div>`;

  return `<div class="selected-session-lineage">
    <div class="selected-session-item">
      <div class="selected-session-label">Parent session</div>
      <div class="selected-session-value">${parentHtml}</div>
    </div>
    <div class="selected-session-item">
      <div class="selected-session-label">Child sessions</div>
      <div class="selected-session-value">${childHtml}</div>
    </div>
    <div class="selected-session-item selected-session-item-wide">
      <div class="selected-session-label">Branch source</div>
      <div class="selected-session-value">${sourceHtml}</div>
    </div>
  </div>`;
}

export function latestActivitySummaryFromState(state) {
  const latestMessage = state.transcript?.[state.transcript.length - 1] ?? null;
  if (!latestMessage) {
    return "No transcript yet.";
  }

  const text = (latestMessage.parts ?? [])
    .map(part => part.text ?? "")
    .join(" ")
    .trim()
    .replace(/\s+/g, " ");
  if (!text) {
    return latestMessage.role ?? "activity recorded";
  }

  return `${latestMessage.role}: ${text}`;
}

export function nextActionSummaryFromState(state) {
  if (state.status === "awaiting_user_input") {
    if (state.pendingQuestionText) {
      return `Answer pending question: ${state.pendingQuestionText}`;
    }
    return "Answer pending question";
  }

  if (state.status === "awaiting_approval") {
    return "Resolve pending approval";
  }

  if (state.status === "running") {
    if (state.currentTurn?.turn_id) {
      return "Wait for the current turn to finish";
    }
    return "Send the next prompt";
  }

  if (state.status === "failed") {
    if (state.sessionFailureMessage) {
      return `Review failure: ${state.sessionFailureMessage}`;
    }
    return "Review failed session";
  }

  if (state.status === "completed") {
    return "Inspect completed session";
  }

  if (state.status === "cancelled") {
    return "Inspect cancelled session";
  }

  return "Inspect session";
}

function availabilitySummaryFromState(state) {
  if (state.status === "awaiting_user_input") {
    return {
      tone: "actionable",
      label: "Browser action available",
      detail: state.pendingQuestionText
        ? `Waiting on an ask_user answer: ${state.pendingQuestionText}`
        : "Waiting on an ask_user answer from the operator.",
    };
  }

  if (state.status === "awaiting_approval") {
    const pendingSubject = state.pendingApprovals?.[0]?.subject ?? null;
    return {
      tone: "actionable",
      label: "Browser action available",
      detail: pendingSubject
        ? `Waiting on approval for ${pendingSubject}.`
        : "Waiting on an approval decision from the operator.",
    };
  }

  if (state.status === "running") {
    if (state.currentTurn?.turn_id) {
      return {
        tone: "live",
        label: "Live session",
        detail: `Turn ${shortId(state.currentTurn.turn_id)} is still running. Wait before sending the next prompt.`,
      };
    }
    return {
      tone: "actionable",
      label: "Browser action available",
      detail: "The session is idle and ready for the next prompt from the browser.",
    };
  }

  if (state.status === "failed") {
    return {
      tone: "historical",
      label: "Historical inspection only",
      detail: state.sessionFailureMessage
        ? `The session failed: ${state.sessionFailureMessage}`
        : "This session failed and is no longer actionable from the browser.",
    };
  }

  if (state.status === "completed") {
    return {
      tone: "historical",
      label: "Historical inspection only",
      detail: "This session is complete and can only be inspected from the dashboard.",
    };
  }

  if (state.status === "cancelled") {
    return {
      tone: "historical",
      label: "Historical inspection only",
      detail: "This session was cancelled and can only be inspected from the dashboard.",
    };
  }

  return {
    tone: "neutral",
    label: "Inspect session",
    detail: "Open the session details to understand its current state.",
  };
}

export function renderSelectedSessionSummary(state) {
  const availability = availabilitySummaryFromState(state);
  const stream = streamSummaryFromState(state);
  const selectedSummary = activeSessionSummary(state);
  const projectionHealth = selectedSummary?.projection_health?.state ?? "ok";
  const operatorPriority = selectedSummary?.priority_bucket ?? "selected session";

  return `<div class="selected-session-summary">
    <div class="selected-session-head">
      <div>
        <div class="selected-session-eyebrow">Selected session</div>
        <h2>${escHtml(shortId(state.sessionId))}</h2>
      </div>
      ${renderStatusChip(state.status)}
    </div>
    <p class="selected-session-copy">${escHtml(availability.detail)}</p>
    <div class="selected-session-stream-state">
      ${renderGuidanceChip(stream.tone, stream.label)}
      <span class="selected-session-stream-detail">${escHtml(stream.detail)}</span>
    </div>
    <div class="selected-session-grid">
      <div class="selected-session-item">
        <div class="selected-session-label">Next action</div>
        <div class="selected-session-value">${escHtml(nextActionSummaryFromState(state))}</div>
      </div>
      <div class="selected-session-item">
        <div class="selected-session-label">Availability</div>
        <div class="selected-session-value">${renderGuidanceChip(availability.tone, availability.label)}</div>
      </div>
      <div class="selected-session-item">
        <div class="selected-session-label">Live state</div>
        <div class="selected-session-value">${renderGuidanceChip(stream.tone, stream.label)}</div>
      </div>
      <div class="selected-session-item">
        <div class="selected-session-label">Last activity</div>
        <div class="selected-session-value">${escHtml(latestActivitySummaryFromState(state))}</div>
      </div>
      <div class="selected-session-item">
        <div class="selected-session-label">Session mode</div>
        <div class="selected-session-value">${escHtml(state.approvalMode ?? "unknown")}</div>
      </div>
      <div class="selected-session-item">
        <div class="selected-session-label">Projection health</div>
        <div class="selected-session-value">${renderGuidanceChip(projectionHealth === "ok" ? "neutral" : "warning", projectionHealth)}</div>
      </div>
      <div class="selected-session-item">
        <div class="selected-session-label">Operator priority</div>
        <div class="selected-session-value">${escHtml(operatorPriority.replace(/-/g, " "))}</div>
      </div>
    </div>
    ${renderRuntimeContextSummary(state)}
    ${renderLineageNavigator(state)}
    ${renderCompareInspector(state, { latestActivitySummaryFromState, nextActionSummaryFromState })}
  </div>`;
}
