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

function renderGuidanceChip(tone, label) {
  return `<span class="guidance-chip guidance-chip-${escHtml(tone)}">${escHtml(label)}</span>`;
}

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

function activeSessionSummary(state) {
  const selectedSessionId = state.selectedSessionId ?? state.sessionId;
  return (state.sessionIndex ?? []).find(
    summary => summary.session_id === selectedSessionId,
  ) ?? null;
}

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

function renderLineageNavigator(state) {
  const parentHtml = state.parentSessionId
    ? `<button type="button" class="session-link-button" data-open-session-id="${escHtml(state.parentSessionId)}">Open ${escHtml(shortId(state.parentSessionId))}</button>`
    : `<span class="lineage-empty">Root session</span>`;

  const childHtml = (state.childSessions ?? []).length > 0
    ? `<div class="lineage-list">${state.childSessions.map(child => `
        <button type="button" class="session-link-button session-link-child" data-open-session-id="${escHtml(child.session_id)}">
          <span>${escHtml(shortId(child.session_id))}</span>
          <span>${escHtml(child.branch_label ?? child.status)}</span>
        </button>
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

function renderForkCard(state) {
  const forkSubmission = state.forkSubmission ?? {
    state: "idle",
    error: null,
  };
  const isBusy = forkSubmission.state === "submitting";
  let statusHtml = "";

  if (forkSubmission.state === "submitting") {
    statusHtml = `<div class="composer-status">Creating child session…</div>`;
  } else if (forkSubmission.state === "failed" && forkSubmission.error) {
    statusHtml = `<div class="composer-status composer-status-error">${escHtml(forkSubmission.error)}</div>`;
  }

  if (!state.canFork || (state.branchableTurns ?? []).length === 0) {
    return `<div class="composer-card composer-blocked composer-fork-card">
      <div class="composer-label">Fork Unavailable</div>
      <div class="composer-help">${escHtml(state.forkBlockedReason ?? "This session is inspect-only right now.")}</div>
      ${statusHtml}
    </div>`;
  }

  const selectedForkTurnId = state.selectedForkTurnId ?? state.branchableTurns[0]?.turn_id ?? "";
  const optionsHtml = state.branchableTurns.map(turn => {
    const label = turn.turn_id === state.latestForkPointTurnId
      ? `${turn.label} (latest stable)`
      : turn.label;
    return `<option value="${escHtml(turn.turn_id)}"${turn.turn_id === selectedForkTurnId ? " selected" : ""}>${escHtml(label)}</option>`;
  }).join("");

  return `<div class="composer-card composer-fork-card">
    <div class="composer-label">Create Forked Session</div>
    <div class="composer-help">Choose a stable completed turn boundary, create a child session, then open it immediately in the dashboard.</div>
    ${statusHtml}
    <form id="fork-form" class="composer-form">
      <label class="composer-help" for="fork-turn-select">Fork point</label>
      <select id="fork-turn-select" class="composer-select" ${isBusy ? "disabled" : ""}>
        ${optionsHtml}
      </select>
      <label class="composer-help" for="fork-branch-label">Branch label (optional)</label>
      <input id="fork-branch-label" class="composer-input composer-input-singleline" type="text" maxlength="120" placeholder="alt-path" ${isBusy ? "disabled" : ""} />
      <div class="composer-actions">
        <button id="fork-submit" class="btn btn-submit" type="submit" ${isBusy ? "disabled" : ""}>Create Fork</button>
      </div>
    </form>
  </div>`;
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

function latestActivitySummaryFromState(state) {
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

function nextActionSummaryFromState(state) {
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

function availabilitySummaryFromSessionSummary(summary) {
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
      tone: summary.last_sequence > 0 ? "live" : "actionable",
      label: summary.next_action_summary === "Send the next prompt"
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
    const availability = availabilitySummaryFromSessionSummary(summary);

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
      <div class="session-card-section-label">Next action</div>
      <div class="session-card-next">${escHtml(summary.next_action_summary)}</div>
      <div class="session-card-section-label">Last activity</div>
      <div class="session-card-summary">${escHtml(latestSummary)}</div>
      <div class="session-card-footer">
        ${renderGuidanceChip(availability.tone, availability.label)}
        <span class="session-card-detail">${escHtml(availability.detail)}</span>
      </div>
    </button>`;
  }).join("");
}

export function renderSelectedSessionSummary(state) {
  const availability = availabilitySummaryFromState(state);
  const stream = streamSummaryFromState(state);

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
    </div>
    ${renderRuntimeContextSummary(state)}
    ${renderLineageNavigator(state)}
  </div>`;
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

  let primaryCard = "";
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

    primaryCard = `<div class="composer-card composer-blocked">
      <div class="composer-label">Next Action Unavailable</div>
      <div class="composer-help">${escHtml(reason)}</div>
    </div>`;
  } else {
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

    primaryCard = `<div class="composer-card composer-${escHtml(mode)}">
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

  return `${primaryCard}${renderForkCard(state)}`;
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
    selectedSessionSummary: renderSelectedSessionSummary(state),
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
