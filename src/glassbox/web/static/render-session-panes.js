import {
  escHtml,
  renderGuidanceChip,
  renderStatusChip,
  shortId,
} from "./render-utils.js";

const QUEUE_ORDER = [
  ["all", "All sessions", "total"],
  ["approvals", "Approvals", "approvals"],
  ["questions", "Questions", "questions"],
  ["failures", "Failures", "failures"],
  ["degraded", "Degraded", "degraded"],
  ["active", "Active", "active"],
];

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
