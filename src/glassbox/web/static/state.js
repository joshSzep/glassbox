/**
 * Pure dashboard state model and event reducer.
 *
 * The browser keeps a local projection derived from the snapshot endpoint plus
 * incremental SSE events. This module is intentionally side-effect free so it
 * can be unit tested directly.
 */

/**
 * @typedef {{kind: string, text: string}} MessagePart
 * @typedef {{message_id: string, role: string, parts: MessagePart[], created_at?: string}} TranscriptMessage
 * @typedef {{tool_call_id: string, turn_id: string, tool_name: string, status: string, started_at?: string | null}} ActiveToolCall
 * @typedef {{approval_id: string, turn_id?: string, subject: string, reason: string, requested_at?: string, resolution_state?: string, resolution_decision?: string | null, resolution_error?: string | null}} PendingApproval
 * @typedef {{turn_id: string, status: string, trigger_message_id?: string, outcome?: string, error_message?: string}} CurrentTurn
 * @typedef {{turn_id: string, started_at?: string | null, completed_at?: string | null, turn_duration_ms?: number | null, model_call_count: number, model_duration_ms_total: number, model_input_tokens_total: number, model_output_tokens_total: number, tool_call_count: number, tool_duration_ms_total: number, succeeded_tool_call_count: number, failed_tool_call_count: number}} TurnMetrics
 * @typedef {{turn_id: string, tool_call_id: string, stream: string, chunk: string}} LiveOutputEntry
 * @typedef {{sequence: number, event_type: string}} EventLogEntry
 * @typedef {{workspace_name: string, high_signal_paths: string[], top_level_directories: string[], additional_directory_count: number, top_level_files: string[], additional_file_count: number, project_markers: string[]}} RepositoryContextSummary
 * @typedef {{category: string, message: string, inherited: boolean, source_session_id?: string | null}} RuntimeContextNote
 * @typedef {{repository_context: RepositoryContextSummary, runtime_notes: RuntimeContextNote[], additional_runtime_note_count: number}} RuntimeContextSummary
 * @typedef {{kind: "message" | "answer" | null, state: "idle" | "submitting" | "submitted" | "failed", error: string | null}} InteractionSubmission
 * @typedef {{state: "idle" | "submitting" | "failed", error: string | null}} ForkSubmission
 * @typedef {{session_id: string, status: string, branch_label: string | null, updated_at: string, latest_message_summary: string | null}} ChildSessionSummary
 * @typedef {{turn_id: string, sequence: number, created_at: string, label: string}} BranchableTurn
 * @typedef {{session_id: string, status: string, model_name: string, cwd: string, approval_mode: string, parent_session_id: string | null, forked_from_turn_id: string | null, forked_from_sequence: number | null, branch_label: string | null, child_session_count: number, can_fork: boolean, latest_fork_point_turn_id: string | null, latest_fork_point_sequence: number | null, fork_blocked_reason: string | null, dashboard_url: string | null, created_at: string, updated_at: string, last_sequence: number, pending_approval_id: string | null, pending_question_id: string | null, pending_question_text: string | null, session_failure_message: string | null, session_failure_retryable: boolean | null, latest_message_summary: string | null, next_action_summary: string}} SessionSummary
 *
 * @typedef {Object} DashboardState
 * @property {string | null} sessionId
 * @property {string} status
 * @property {string | null} modelName
 * @property {string | null} cwd
 * @property {string | null} approvalMode
 * @property {string | null} parentSessionId
 * @property {string | null} forkedFromTurnId
 * @property {number | null} forkedFromSequence
 * @property {string | null} branchLabel
 * @property {ChildSessionSummary[]} childSessions
 * @property {BranchableTurn[]} branchableTurns
 * @property {boolean} canFork
 * @property {string | null} latestForkPointTurnId
 * @property {number | null} latestForkPointSequence
 * @property {string | null} forkBlockedReason
 * @property {string | null} selectedForkTurnId
 * @property {string | null} dashboardUrl
 * @property {number} lastSequence
 * @property {string | null} pendingApprovalId
 * @property {string | null} pendingQuestionId
 * @property {string | null} pendingQuestionText
 * @property {string | null} sessionFailureMessage
 * @property {boolean | null} sessionFailureRetryable
 * @property {RuntimeContextSummary | null} runtimeContext
 * @property {CurrentTurn | null} currentTurn
 * @property {TurnMetrics[]} turnMetrics
 * @property {TranscriptMessage[]} transcript
 * @property {ActiveToolCall[]} activeToolCalls
 * @property {LiveOutputEntry[]} liveOutput
 * @property {PendingApproval[]} pendingApprovals
 * @property {EventLogEntry[]} eventLog
 * @property {InteractionSubmission} interactionSubmission
 * @property {ForkSubmission} forkSubmission
 * @property {SessionSummary[]} sessionIndex
 * @property {"idle" | "loading" | "loaded" | "failed"} sessionIndexState
 * @property {string | null} sessionIndexError
 * @property {string | null} selectedSessionId
 * @property {"idle" | "loading" | "loaded" | "failed"} sessionLoadState
 * @property {string | null} sessionLoadError
 * @property {"idle" | "index" | "loading" | "connecting" | "live" | "reconnecting" | "unavailable" | "historical"} streamState
 * @property {string | null} streamError
 * @property {number} streamRetryCount
 */

/**
 * @typedef {Object} SessionSnapshot
 * @property {string} session_id
 * @property {string} status
 * @property {string | null} current_turn_id
 * @property {string} model_name
 * @property {string} cwd
 * @property {string} approval_mode
 * @property {string | null} parent_session_id
 * @property {string | null} forked_from_turn_id
 * @property {number | null} forked_from_sequence
 * @property {string | null} branch_label
 * @property {ChildSessionSummary[]} child_sessions
 * @property {BranchableTurn[]} branchable_turns
 * @property {boolean} can_fork
 * @property {string | null} latest_fork_point_turn_id
 * @property {number | null} latest_fork_point_sequence
 * @property {string | null} fork_blocked_reason
 * @property {string | null} dashboard_url
 * @property {number} last_sequence
 * @property {string | null} pending_approval_id
 * @property {string | null} pending_question_id
 * @property {string | null} pending_question_text
 * @property {string | null} session_failure_message
 * @property {boolean | null} session_failure_retryable
 * @property {TranscriptMessage[]} transcript
 * @property {ActiveToolCall[]} active_tool_calls
 * @property {PendingApproval[]} pending_approvals
 * @property {TurnMetrics[]} turn_metrics
 * @property {RuntimeContextSummary | null} runtime_context
 */

/**
 * @typedef {Object} EventEnvelope
 * @property {string} session_id
 * @property {number} sequence
 * @property {string} event_type
 * @property {Record<string, unknown>} payload
 */

/** @returns {DashboardState} */
export function createState() {
  return {
    sessionId: null,
    status: "unknown",
    modelName: null,
    cwd: null,
    approvalMode: null,
    parentSessionId: null,
    forkedFromTurnId: null,
    forkedFromSequence: null,
    branchLabel: null,
    childSessions: [],
    branchableTurns: [],
    canFork: false,
    latestForkPointTurnId: null,
    latestForkPointSequence: null,
    forkBlockedReason: null,
    selectedForkTurnId: null,
    dashboardUrl: null,
    lastSequence: 0,
    pendingApprovalId: null,
    pendingQuestionId: null,
    pendingQuestionText: null,
    sessionFailureMessage: null,
    sessionFailureRetryable: null,
    runtimeContext: null,
    currentTurn: null,
    turnMetrics: [],
    transcript: [],
    activeToolCalls: [],
    liveOutput: [],
    pendingApprovals: [],
    eventLog: [],
    interactionSubmission: {
      kind: null,
      state: "idle",
      error: null,
    },
    forkSubmission: {
      state: "idle",
      error: null,
    },
    sessionIndex: [],
    sessionIndexState: "idle",
    sessionIndexError: null,
    selectedSessionId: null,
    sessionLoadState: "idle",
    sessionLoadError: null,
    streamState: "idle",
    streamError: null,
    streamRetryCount: 0,
  };
}

function createIdleInteractionSubmission() {
  return {
    kind: null,
    state: "idle",
    error: null,
  };
}

function createIdleForkSubmission() {
  return {
    state: "idle",
    error: null,
  };
}

function normalizeBranchableTurns(branchableTurns) {
  if (!Array.isArray(branchableTurns)) {
    return [];
  }

  return branchableTurns
    .filter(turn => turn && typeof turn.turn_id === "string")
    .map(turn => ({
      turn_id: turn.turn_id,
      sequence: Number.isFinite(turn.sequence) ? turn.sequence : 0,
      created_at: typeof turn.created_at === "string" ? turn.created_at : "",
      label: typeof turn.label === "string" ? turn.label : `Turn ${turn.turn_id.slice(0, 8)}`,
    }));
}

function defaultSelectedForkTurnId(snapshot) {
  const branchableTurns = normalizeBranchableTurns(snapshot.branchable_turns);
  if (typeof snapshot.latest_fork_point_turn_id === "string") {
    const latestTurn = branchableTurns.find(
      turn => turn.turn_id === snapshot.latest_fork_point_turn_id,
    );
    if (latestTurn) {
      return latestTurn.turn_id;
    }
  }

  return branchableTurns[0]?.turn_id ?? null;
}

function upsertBranchableTurn(branchableTurns, branchableTurn) {
  const next = [
    branchableTurn,
    ...branchableTurns.filter(turn => turn.turn_id !== branchableTurn.turn_id),
  ];
  return next.sort((left, right) => right.sequence - left.sequence);
}

function currentTurnLabel(state) {
  const currentTurnId = state.currentTurn?.turn_id ?? null;
  const triggerMessageId = state.currentTurn?.trigger_message_id ?? null;
  const transcriptMessage = triggerMessageId
    ? state.transcript.find(message => message.message_id === triggerMessageId)
    : null;
  const text = transcriptMessage?.parts?.map(part => part.text ?? "").join(" ").trim();
  if (text) {
    return text;
  }
  if (currentTurnId) {
    return `Turn ${currentTurnId.slice(0, 8)}`;
  }
  return "Completed turn";
}

/**
 * @param {SessionSnapshot} snapshot
 * @returns {CurrentTurn | null}
 */
function inferCurrentTurn(snapshot) {
  const activeToolCall = snapshot.active_tool_calls?.[0];
  if (activeToolCall?.turn_id) {
    return {
      turn_id: activeToolCall.turn_id,
      status: "running",
    };
  }

  const pendingApproval = snapshot.pending_approvals?.[0];
  if (pendingApproval?.turn_id) {
    return {
      turn_id: pendingApproval.turn_id,
      status: "awaiting_approval",
    };
  }

  if (typeof snapshot.current_turn_id === "string") {
    return {
      turn_id: snapshot.current_turn_id,
      status: typeof snapshot.status === "string" ? snapshot.status : "running",
    };
  }

  return null;
}

function normalizeRuntimeContext(snapshotRuntimeContext) {
  if (!snapshotRuntimeContext || !snapshotRuntimeContext.repository_context) {
    return null;
  }

  const repositoryContext = snapshotRuntimeContext.repository_context;
  return {
    repository_context: {
      workspace_name: typeof repositoryContext.workspace_name === "string"
        ? repositoryContext.workspace_name
        : "workspace",
      high_signal_paths: Array.isArray(repositoryContext.high_signal_paths)
        ? [...repositoryContext.high_signal_paths]
        : [],
      top_level_directories: Array.isArray(repositoryContext.top_level_directories)
        ? [...repositoryContext.top_level_directories]
        : [],
      additional_directory_count: Number.isFinite(repositoryContext.additional_directory_count)
        ? repositoryContext.additional_directory_count
        : 0,
      top_level_files: Array.isArray(repositoryContext.top_level_files)
        ? [...repositoryContext.top_level_files]
        : [],
      additional_file_count: Number.isFinite(repositoryContext.additional_file_count)
        ? repositoryContext.additional_file_count
        : 0,
      project_markers: Array.isArray(repositoryContext.project_markers)
        ? [...repositoryContext.project_markers]
        : [],
    },
    runtime_notes: Array.isArray(snapshotRuntimeContext.runtime_notes)
      ? snapshotRuntimeContext.runtime_notes
        .filter(note => note && typeof note.category === "string")
        .map(note => ({
          category: note.category,
          message: typeof note.message === "string" ? note.message : "",
          inherited: Boolean(note.inherited),
          source_session_id: typeof note.source_session_id === "string"
            ? note.source_session_id
            : null,
        }))
      : [],
    additional_runtime_note_count: Number.isFinite(snapshotRuntimeContext.additional_runtime_note_count)
      ? snapshotRuntimeContext.additional_runtime_note_count
      : 0,
  };
}

function runtimeContextNoteKey(note) {
  return [
    note.source_session_id ?? "local",
    note.category,
    note.message,
  ].join("\u0000");
}

function upsertRuntimeContextNote(runtimeContext, note) {
  if (!runtimeContext) {
    return runtimeContext;
  }

  const existingIndex = runtimeContext.runtime_notes.findIndex(
    existing => runtimeContextNoteKey(existing) === runtimeContextNoteKey(note),
  );
  if (existingIndex >= 0) {
    const nextNotes = [...runtimeContext.runtime_notes];
    nextNotes[existingIndex] = note;
    return {
      ...runtimeContext,
      runtime_notes: nextNotes,
    };
  }

  if (runtimeContext.additional_runtime_note_count > 0) {
    return {
      ...runtimeContext,
      additional_runtime_note_count: runtimeContext.additional_runtime_note_count + 1,
    };
  }

  if (runtimeContext.runtime_notes.length >= 8) {
    return {
      ...runtimeContext,
      additional_runtime_note_count: 1,
    };
  }

  return {
    ...runtimeContext,
    runtime_notes: [...runtimeContext.runtime_notes, note],
  };
}

/**
 * @param {SessionSnapshot} snapshot
 * @returns {DashboardState}
 */
export function hydrateFromSnapshot(snapshot) {
  const branchableTurns = normalizeBranchableTurns(snapshot.branchable_turns);
  return {
    ...createState(),
    sessionId: snapshot.session_id,
    selectedSessionId: snapshot.session_id,
    status: snapshot.status,
    modelName: snapshot.model_name,
    cwd: snapshot.cwd,
    approvalMode: snapshot.approval_mode,
    parentSessionId: snapshot.parent_session_id ?? null,
    forkedFromTurnId: snapshot.forked_from_turn_id ?? null,
    forkedFromSequence: snapshot.forked_from_sequence ?? null,
    branchLabel: snapshot.branch_label ?? null,
    childSessions: [...(snapshot.child_sessions ?? [])],
    branchableTurns,
    canFork: Boolean(snapshot.can_fork),
    latestForkPointTurnId: snapshot.latest_fork_point_turn_id ?? null,
    latestForkPointSequence: snapshot.latest_fork_point_sequence ?? null,
    forkBlockedReason: snapshot.fork_blocked_reason ?? null,
    selectedForkTurnId: defaultSelectedForkTurnId(snapshot),
    dashboardUrl: snapshot.dashboard_url ?? null,
    lastSequence: snapshot.last_sequence ?? 0,
    pendingApprovalId: snapshot.pending_approval_id ?? null,
    pendingQuestionId: snapshot.pending_question_id ?? null,
    pendingQuestionText: snapshot.pending_question_text ?? null,
    sessionFailureMessage: snapshot.session_failure_message ?? null,
    sessionFailureRetryable: snapshot.session_failure_retryable ?? null,
    runtimeContext: normalizeRuntimeContext(snapshot.runtime_context),
    currentTurn: inferCurrentTurn(snapshot),
    turnMetrics: [...(snapshot.turn_metrics ?? [])],
    transcript: [...(snapshot.transcript ?? [])],
    activeToolCalls: [...(snapshot.active_tool_calls ?? [])],
    liveOutput: [],
    pendingApprovals: [...(snapshot.pending_approvals ?? [])],
    eventLog: [],
    interactionSubmission: createIdleInteractionSubmission(),
    forkSubmission: createIdleForkSubmission(),
    sessionLoadState: "loaded",
  };
}

export function selectForkTurn(state, turnId) {
  const selectedTurn = state.branchableTurns.find(turn => turn.turn_id === turnId);
  return {
    ...state,
    selectedForkTurnId: selectedTurn?.turn_id ?? state.selectedForkTurnId,
  };
}

export function beginSessionIndexLoad(state) {
  return {
    ...state,
    sessionIndexState: "loading",
    sessionIndexError: null,
  };
}

export function hydrateSessionIndex(state, sessionIndex) {
  return {
    ...state,
    sessionIndex: [...sessionIndex],
    sessionIndexState: "loaded",
    sessionIndexError: null,
  };
}

export function failSessionIndexLoad(state, errorMessage) {
  return {
    ...state,
    sessionIndexState: "failed",
    sessionIndexError: errorMessage,
  };
}

export function beginSessionSelection(state, sessionId) {
  return {
    ...state,
    selectedSessionId: sessionId,
    sessionLoadState: sessionId ? "loading" : "idle",
    sessionLoadError: null,
    streamState: sessionId ? "loading" : "index",
    streamError: null,
    streamRetryCount: 0,
    sessionId: sessionId ? state.sessionId : null,
  };
}

export function clearSessionSelection(state) {
  return {
    ...createState(),
    sessionIndex: [...state.sessionIndex],
    sessionIndexState: state.sessionIndexState,
    sessionIndexError: state.sessionIndexError,
    streamState: "index",
  };
}

export function failSessionSelection(state, errorMessage) {
  return {
    ...state,
    sessionId: null,
    status: "unknown",
    currentTurn: null,
    pendingApprovalId: null,
    pendingQuestionId: null,
    pendingQuestionText: null,
    sessionFailureMessage: null,
    sessionFailureRetryable: null,
    turnMetrics: [],
    transcript: [],
    activeToolCalls: [],
    liveOutput: [],
    pendingApprovals: [],
    eventLog: [],
    interactionSubmission: createIdleInteractionSubmission(),
    sessionLoadState: "failed",
    sessionLoadError: errorMessage,
    streamState: "index",
    streamError: null,
    streamRetryCount: 0,
  };
}

export function beginLiveStreamConnection(state, { reconnecting = false } = {}) {
  return {
    ...state,
    streamState: reconnecting ? "reconnecting" : "connecting",
    streamError: reconnecting
      ? state.streamError
      : null,
  };
}

export function markLiveStreamConnected(state) {
  return {
    ...state,
    streamState: "live",
    streamError: null,
    streamRetryCount: 0,
  };
}

export function markLiveStreamReconnecting(state, errorMessage) {
  return {
    ...state,
    streamState: "reconnecting",
    streamError: errorMessage,
    streamRetryCount: state.streamRetryCount + 1,
  };
}

export function markLiveStreamUnavailable(state, errorMessage) {
  return {
    ...state,
    streamState: "unavailable",
    streamError: errorMessage,
  };
}

export function markHistoricalSnapshot(state) {
  return {
    ...state,
    streamState: "historical",
    streamError: null,
    streamRetryCount: 0,
  };
}

/**
 * @param {LiveOutputEntry[]} liveOutput
 * @param {LiveOutputEntry} entry
 * @returns {LiveOutputEntry[]}
 */
function appendLiveOutput(liveOutput, entry) {
  const next = [...liveOutput, entry];
  return next.slice(-200);
}

/**
 * @param {TranscriptMessage[]} transcript
 * @param {TranscriptMessage} message
 * @returns {TranscriptMessage[]}
 */
function upsertTranscriptMessage(transcript, message) {
  const existingIndex = transcript.findIndex(
    item => item.message_id === message.message_id,
  );
  if (existingIndex === -1) {
    return [...transcript, message];
  }

  return transcript.map((item, index) =>
    index === existingIndex ? message : item,
  );
}

/**
 * @param {PendingApproval[]} approvals
 * @param {PendingApproval} approval
 * @returns {PendingApproval[]}
 */
function upsertPendingApproval(approvals, approval) {
  const existingIndex = approvals.findIndex(
    item => item.approval_id === approval.approval_id,
  );
  if (existingIndex === -1) {
    return [...approvals, approval];
  }

  return approvals.map((item, index) =>
    index === existingIndex ? approval : item,
  );
}

function makeTurnMetrics(turnId, overrides = {}) {
  return {
    turn_id: turnId,
    started_at: null,
    completed_at: null,
    turn_duration_ms: null,
    model_call_count: 0,
    model_duration_ms_total: 0,
    model_input_tokens_total: 0,
    model_output_tokens_total: 0,
    tool_call_count: 0,
    tool_duration_ms_total: 0,
    succeeded_tool_call_count: 0,
    failed_tool_call_count: 0,
    ...overrides,
  };
}

function upsertTurnMetrics(turnMetrics, metrics) {
  const existingIndex = turnMetrics.findIndex(item => item.turn_id === metrics.turn_id);
  if (existingIndex === -1) {
    return [metrics, ...turnMetrics];
  }

  return turnMetrics.map((item, index) =>
    index === existingIndex ? { ...item, ...metrics } : item,
  );
}

function updateTurnMetrics(turnMetrics, turnId, updater) {
  const existing = turnMetrics.find(item => item.turn_id === turnId)
    ?? makeTurnMetrics(turnId);
  return upsertTurnMetrics(turnMetrics, updater(existing));
}

function durationBetween(startedAt, endedAt) {
  if (!startedAt || !endedAt) {
    return null;
  }

  const started = Date.parse(startedAt);
  const ended = Date.parse(endedAt);
  if (Number.isNaN(started) || Number.isNaN(ended)) {
    return null;
  }

  return Math.max(ended - started, 0);
}

/**
 * @param {PendingApproval[]} approvals
 * @param {string} approvalId
 * @param {(approval: PendingApproval) => PendingApproval} updater
 * @returns {PendingApproval[]}
 */
function updatePendingApproval(approvals, approvalId, updater) {
  let changed = false;
  const next = approvals.map(approval => {
    if (approval.approval_id !== approvalId) {
      return approval;
    }
    changed = true;
    return updater(approval);
  });

  return changed ? next : approvals;
}

/**
 * @param {DashboardState} state
 * @param {string} approvalId
 * @param {string} decision
 * @returns {DashboardState}
 */
export function beginApprovalResolution(state, approvalId, decision) {
  return {
    ...state,
    pendingApprovals: updatePendingApproval(
      state.pendingApprovals,
      approvalId,
      approval => ({
        ...approval,
        resolution_state: "submitting",
        resolution_decision: decision,
        resolution_error: null,
      }),
    ),
  };
}

/**
 * @param {DashboardState} state
 * @param {string} approvalId
 * @param {string} decision
 * @returns {DashboardState}
 */
export function confirmApprovalResolution(state, approvalId, decision) {
  return {
    ...state,
    pendingApprovals: updatePendingApproval(
      state.pendingApprovals,
      approvalId,
      approval => ({
        ...approval,
        resolution_state: "submitted",
        resolution_decision: decision,
        resolution_error: null,
      }),
    ),
  };
}

/**
 * @param {DashboardState} state
 * @param {string} approvalId
 * @param {string} errorMessage
 * @returns {DashboardState}
 */
export function failApprovalResolution(state, approvalId, errorMessage) {
  return {
    ...state,
    pendingApprovals: updatePendingApproval(
      state.pendingApprovals,
      approvalId,
      approval => ({
        ...approval,
        resolution_state: "failed",
        resolution_error: errorMessage,
      }),
    ),
  };
}

export function beginInteractionSubmission(state, kind) {
  return {
    ...state,
    interactionSubmission: {
      kind,
      state: "submitting",
      error: null,
    },
  };
}

export function confirmInteractionSubmission(state, kind) {
  return {
    ...state,
    interactionSubmission: {
      kind,
      state: "submitted",
      error: null,
    },
  };
}

export function failInteractionSubmission(state, kind, errorMessage) {
  return {
    ...state,
    interactionSubmission: {
      kind,
      state: "failed",
      error: errorMessage,
    },
  };
}

export function beginForkSubmission(state) {
  return {
    ...state,
    forkSubmission: {
      state: "submitting",
      error: null,
    },
  };
}

export function confirmForkSubmission(state) {
  return {
    ...state,
    forkSubmission: {
      state: "idle",
      error: null,
    },
  };
}

export function failForkSubmission(state, errorMessage) {
  return {
    ...state,
    forkSubmission: {
      state: "failed",
      error: errorMessage,
    },
  };
}

/**
 * @param {DashboardState} state
 * @param {EventEnvelope} envelope
 * @returns {DashboardState}
 */
export function applyEvent(state, envelope) {
  const payload = envelope.payload ?? {};
  /** @type {DashboardState} */
  const next = {
    ...state,
    lastSequence: Math.max(state.lastSequence, envelope.sequence ?? 0),
    eventLog: [
      ...state.eventLog,
      {
        sequence: envelope.sequence ?? 0,
        event_type: envelope.event_type,
      },
    ],
  };

  switch (envelope.event_type) {
    case "SessionStarted":
      return {
        ...next,
        status: "running",
        interactionSubmission: createIdleInteractionSubmission(),
        forkSubmission: createIdleForkSubmission(),
        cwd: typeof payload.cwd === "string" ? payload.cwd : next.cwd,
        modelName: (
          typeof payload.model_name === "string" ? payload.model_name : next.modelName
        ),
        approvalMode: (
          typeof payload.approval_mode === "string"
            ? payload.approval_mode
            : next.approvalMode
        ),
        dashboardUrl: (
          typeof payload.dashboard_url === "string"
            ? payload.dashboard_url
            : next.dashboardUrl
        ),
        parentSessionId: (
          typeof payload.parent_session_id === "string"
            ? payload.parent_session_id
            : next.parentSessionId
        ),
        forkedFromTurnId: (
          typeof payload.forked_from_turn_id === "string"
            ? payload.forked_from_turn_id
            : next.forkedFromTurnId
        ),
        forkedFromSequence: Number.isFinite(payload.forked_from_sequence)
          ? payload.forked_from_sequence
          : next.forkedFromSequence,
        branchLabel: (
          typeof payload.branch_label === "string"
            ? payload.branch_label
            : next.branchLabel
        ),
        canFork: false,
        forkBlockedReason: "Wait for the current turn to finish before creating a fork.",
        sessionFailureMessage: null,
        sessionFailureRetryable: null,
      };
    case "SessionResumed":
      return {
        ...next,
        status: "running",
        interactionSubmission: createIdleInteractionSubmission(),
        canFork: false,
        forkBlockedReason: "Wait for the current turn to finish before creating a fork.",
      };
    case "SessionCompleted":
      return {
        ...next,
        status: "completed",
        currentTurn: null,
        pendingApprovalId: null,
        pendingQuestionId: null,
        pendingQuestionText: null,
        interactionSubmission: createIdleInteractionSubmission(),
        canFork: next.branchableTurns.length > 0,
        forkBlockedReason: next.branchableTurns.length > 0
          ? null
          : "This session has no completed fork point.",
      };
    case "SessionFailed":
      return {
        ...next,
        status: "failed",
        sessionFailureMessage: (
          typeof payload.error_message === "string"
            ? payload.error_message
            : next.sessionFailureMessage
        ),
        sessionFailureRetryable: (
          typeof payload.retryable === "boolean"
            ? payload.retryable
            : next.sessionFailureRetryable
        ),
        currentTurn: null,
        pendingApprovalId: null,
        pendingQuestionId: null,
        pendingQuestionText: null,
        interactionSubmission: createIdleInteractionSubmission(),
        forkBlockedReason: next.canFork
          ? null
          : next.forkBlockedReason,
      };
    case "TurnStarted":
      if (typeof payload.turn_id !== "string") {
        return next;
      }
      return {
        ...next,
        interactionSubmission: createIdleInteractionSubmission(),
        canFork: false,
        forkBlockedReason: `Wait for turn ${payload.turn_id.slice(0, 8)} to finish before creating a fork.`,
        currentTurn: {
          turn_id: payload.turn_id,
          status: "running",
          trigger_message_id: (
            typeof payload.trigger_message_id === "string"
              ? payload.trigger_message_id
              : undefined
          ),
        },
          turnMetrics: upsertTurnMetrics(
            next.turnMetrics,
            makeTurnMetrics(payload.turn_id, {
              started_at: typeof envelope.created_at === "string" ? envelope.created_at : null,
            }),
          ),
      };
    case "TurnStatusChanged":
      if (typeof payload.turn_id !== "string" || typeof payload.status !== "string") {
        return next;
      }
      return {
        ...next,
        interactionSubmission: createIdleInteractionSubmission(),
        canFork: false,
        forkBlockedReason: "Wait for the current turn to finish before creating a fork.",
        currentTurn: {
          turn_id: payload.turn_id,
          status: payload.status,
        },
      };
    case "UserMessageReceived":
      if (typeof payload.message_id !== "string") {
        return next;
      }
      return {
        ...next,
        interactionSubmission: createIdleInteractionSubmission(),
        transcript: upsertTranscriptMessage(next.transcript, {
          message_id: payload.message_id,
          role: "user",
          parts: [
            {
              kind: "text",
              text: typeof payload.text === "string" ? payload.text : "",
            },
          ],
        }),
      };
    case "AssistantMessageCompleted":
      if (typeof payload.message_id !== "string") {
        return next;
      }
      return {
        ...next,
        interactionSubmission: createIdleInteractionSubmission(),
        transcript: upsertTranscriptMessage(next.transcript, {
          message_id: payload.message_id,
          role: "assistant",
          parts: Array.isArray(payload.parts) ? payload.parts : [],
        }),
      };
    case "ApprovalRequested": {
      if (typeof payload.approval_id !== "string") {
        return next;
      }
      const approval = {
        approval_id: payload.approval_id,
        turn_id: typeof payload.turn_id === "string" ? payload.turn_id : undefined,
        subject: typeof payload.subject === "string" ? payload.subject : "",
        reason: typeof payload.reason === "string" ? payload.reason : "",
        resolution_state: "idle",
        resolution_decision: null,
        resolution_error: null,
      };
      return {
        ...next,
        status: "awaiting_approval",
        pendingApprovalId: payload.approval_id,
        canFork: false,
        forkBlockedReason: "Resolve the pending approval before creating a fork.",
        currentTurn: {
          turn_id: typeof payload.turn_id === "string" ? payload.turn_id : "unknown",
          status: "awaiting_approval",
        },
        pendingApprovals: upsertPendingApproval(next.pendingApprovals, approval),
      };
    }
    case "ApprovalResolved":
      return {
        ...next,
        status: "running",
        interactionSubmission: createIdleInteractionSubmission(),
        canFork: false,
        forkBlockedReason: "Wait for the current turn to finish before creating a fork.",
        currentTurn: next.currentTurn
          ? {
              ...next.currentTurn,
              status: "running",
            }
          : next.currentTurn,
        pendingApprovalId: (
          next.pendingApprovalId === payload.approval_id
            ? null
            : next.pendingApprovalId
        ),
        pendingApprovals: next.pendingApprovals.filter(
          approval => approval.approval_id !== payload.approval_id,
        ),
      };
    case "UserQuestionAsked":
      return {
        ...next,
        status: "awaiting_user_input",
        interactionSubmission: createIdleInteractionSubmission(),
        canFork: false,
        forkBlockedReason: "Answer the pending question before creating a fork.",
        currentTurn: next.currentTurn
          ? {
              ...next.currentTurn,
              status: "awaiting_user_input",
            }
          : next.currentTurn,
        pendingQuestionId: (
          typeof payload.question_id === "string"
            ? payload.question_id
            : next.pendingQuestionId
        ),
        pendingQuestionText: (
          typeof payload.question === "string"
            ? payload.question
            : next.pendingQuestionText
        ),
      };
    case "UserAnswerProvided":
      return {
        ...next,
        status: "running",
        interactionSubmission: createIdleInteractionSubmission(),
        canFork: false,
        forkBlockedReason: "Wait for the current turn to finish before creating a fork.",
        currentTurn: next.currentTurn
          ? {
              ...next.currentTurn,
              status: "running",
            }
          : next.currentTurn,
        pendingQuestionId: (
          next.pendingQuestionId === payload.question_id
            ? null
            : next.pendingQuestionId
        ),
        pendingQuestionText: (
          next.pendingQuestionId === payload.question_id
            ? null
            : next.pendingQuestionText
        ),
      };
    case "TurnCompleted":
      if (typeof payload.turn_id !== "string") {
        return next;
      }
      const completedAt = typeof envelope.created_at === "string" ? envelope.created_at : null;
      const completedTurnMetrics = updateTurnMetrics(
        next.turnMetrics,
        payload.turn_id,
        metrics => ({
          ...metrics,
          completed_at: completedAt,
          turn_duration_ms: durationBetween(metrics.started_at, completedAt),
        }),
      );
      if (payload.outcome === "awaiting_approval") {
        return {
          ...next,
          status: "awaiting_approval",
          interactionSubmission: createIdleInteractionSubmission(),
          turnMetrics: completedTurnMetrics,
          currentTurn: {
            turn_id: payload.turn_id,
            status: "awaiting_approval",
            outcome: payload.outcome,
          },
        };
      }
      if (payload.outcome === "awaiting_user_input") {
        return {
          ...next,
          status: "awaiting_user_input",
          interactionSubmission: createIdleInteractionSubmission(),
          turnMetrics: completedTurnMetrics,
          currentTurn: {
            turn_id: payload.turn_id,
            status: "awaiting_user_input",
            outcome: payload.outcome,
          },
        };
      }
      if (payload.outcome === "completed") {
        const nextLatestForkPointTurnId = payload.turn_id;
        const nextLatestForkPointSequence = envelope.sequence ?? 0;
        const branchableTurn = {
          turn_id: payload.turn_id,
          sequence: nextLatestForkPointSequence,
          created_at: typeof envelope.created_at === "string" ? envelope.created_at : "",
          label: currentTurnLabel(next),
        };
        const selectedForkTurnId = (
          !state.selectedForkTurnId
          || state.selectedForkTurnId === state.latestForkPointTurnId
        )
          ? nextLatestForkPointTurnId
          : state.selectedForkTurnId;
        return {
          ...next,
          status: "running",
          interactionSubmission: createIdleInteractionSubmission(),
          turnMetrics: completedTurnMetrics,
          branchableTurns: upsertBranchableTurn(next.branchableTurns, branchableTurn),
          canFork: true,
          latestForkPointTurnId: nextLatestForkPointTurnId,
          latestForkPointSequence: nextLatestForkPointSequence,
          forkBlockedReason: null,
          selectedForkTurnId,
          currentTurn: {
            turn_id: payload.turn_id,
            status: "completed",
            outcome: payload.outcome,
          },
        };
      }
      return next;
    case "TurnFailed":
      if (typeof payload.turn_id !== "string") {
        return next;
      }
      return {
        ...next,
        status: "failed",
        interactionSubmission: createIdleInteractionSubmission(),
        canFork: false,
        forkBlockedReason: next.branchableTurns.length > 0
          ? next.forkBlockedReason
          : "This session has no completed fork point.",
        turnMetrics: updateTurnMetrics(next.turnMetrics, payload.turn_id, metrics => ({
          ...metrics,
          completed_at: typeof envelope.created_at === "string" ? envelope.created_at : null,
          turn_duration_ms: durationBetween(
            metrics.started_at,
            typeof envelope.created_at === "string" ? envelope.created_at : null,
          ),
        })),
        currentTurn: {
          turn_id: payload.turn_id,
          status: "failed",
          error_message: (
            typeof payload.error_message === "string"
              ? payload.error_message
              : undefined
          ),
        },
      };
    case "ToolExecutionStarted": {
      if (
        typeof payload.tool_call_id !== "string"
        || typeof payload.turn_id !== "string"
        || typeof payload.tool_name !== "string"
      ) {
        return next;
      }
      const toolCall = {
        tool_call_id: payload.tool_call_id,
        turn_id: payload.turn_id,
        tool_name: payload.tool_name,
        status: "running",
        started_at: typeof envelope.created_at === "string" ? envelope.created_at : undefined,
      };
      const existing = next.activeToolCalls.find(
        item => item.tool_call_id === toolCall.tool_call_id,
      );
      return {
        ...next,
        turnMetrics: updateTurnMetrics(next.turnMetrics, payload.turn_id, metrics => ({
          ...metrics,
          tool_call_count: metrics.tool_call_count + 1,
        })),
        currentTurn: {
          turn_id: payload.turn_id,
          status: next.currentTurn?.status ?? "running",
        },
        activeToolCalls: existing
          ? next.activeToolCalls.map(item =>
              item.tool_call_id === toolCall.tool_call_id ? toolCall : item,
            )
          : [...next.activeToolCalls, toolCall],
      };
    }
    case "ToolOutputChunk":
      if (
        typeof payload.turn_id !== "string"
        || typeof payload.tool_call_id !== "string"
        || typeof payload.stream !== "string"
        || typeof payload.chunk !== "string"
      ) {
        return next;
      }
      return {
        ...next,
        liveOutput: appendLiveOutput(next.liveOutput, {
          turn_id: payload.turn_id,
          tool_call_id: payload.tool_call_id,
          stream: payload.stream,
          chunk: payload.chunk,
        }),
      };
    case "ToolExecutionCompleted":
      return {
        ...next,
        turnMetrics: updateTurnMetrics(
          next.turnMetrics,
          typeof payload.turn_id === "string" ? payload.turn_id : "unknown",
          metrics => {
            const activeToolCall = next.activeToolCalls.find(
              item => item.tool_call_id === payload.tool_call_id,
            );
            const toolDuration = durationBetween(
              activeToolCall?.started_at ?? null,
              typeof envelope.created_at === "string" ? envelope.created_at : null,
            ) ?? 0;
            return {
              ...metrics,
              tool_duration_ms_total: metrics.tool_duration_ms_total + toolDuration,
              succeeded_tool_call_count: metrics.succeeded_tool_call_count + (payload.success ? 1 : 0),
              failed_tool_call_count: metrics.failed_tool_call_count + (payload.success ? 0 : 1),
            };
          },
        ),
        activeToolCalls: next.activeToolCalls.filter(
          item => item.tool_call_id !== payload.tool_call_id,
        ),
      };
    case "RuntimeNoteRecorded":
    case "RuntimeNoteImported":
      if (typeof payload.category !== "string" || typeof payload.message !== "string") {
        return next;
      }
      return {
        ...next,
        runtimeContext: upsertRuntimeContextNote(next.runtimeContext, {
          category: payload.category,
          message: payload.message,
          inherited: envelope.event_type === "RuntimeNoteImported" || Boolean(payload.inherited),
          source_session_id: typeof payload.source_session_id === "string"
            ? payload.source_session_id
            : next.sessionId,
        }),
      };
    case "ModelCallStarted":
      if (typeof payload.turn_id !== "string") {
        return next;
      }
      return {
        ...next,
        turnMetrics: updateTurnMetrics(next.turnMetrics, payload.turn_id, metrics => metrics),
      };
    case "ModelCallCompleted":
      if (typeof payload.turn_id !== "string") {
        return next;
      }
      return {
        ...next,
        turnMetrics: updateTurnMetrics(next.turnMetrics, payload.turn_id, metrics => ({
          ...metrics,
          model_call_count: metrics.model_call_count + 1,
          model_duration_ms_total: metrics.model_duration_ms_total + (payload.duration_ms ?? 0),
          model_input_tokens_total: metrics.model_input_tokens_total + (payload.input_tokens ?? 0),
          model_output_tokens_total: metrics.model_output_tokens_total + (payload.output_tokens ?? 0),
        })),
      };
    default:
      return next;
  }
}
