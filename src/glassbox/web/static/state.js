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
 * @typedef {{kind: "message" | "answer" | null, state: "idle" | "submitting" | "submitted" | "failed", error: string | null}} InteractionSubmission
 *
 * @typedef {Object} DashboardState
 * @property {string | null} sessionId
 * @property {string} status
 * @property {string | null} modelName
 * @property {string | null} cwd
 * @property {string | null} approvalMode
 * @property {string | null} dashboardUrl
 * @property {number} lastSequence
 * @property {string | null} pendingApprovalId
 * @property {string | null} pendingQuestionId
 * @property {string | null} pendingQuestionText
 * @property {string | null} sessionFailureMessage
 * @property {boolean | null} sessionFailureRetryable
 * @property {CurrentTurn | null} currentTurn
 * @property {TurnMetrics[]} turnMetrics
 * @property {TranscriptMessage[]} transcript
 * @property {ActiveToolCall[]} activeToolCalls
 * @property {LiveOutputEntry[]} liveOutput
 * @property {PendingApproval[]} pendingApprovals
 * @property {EventLogEntry[]} eventLog
 * @property {InteractionSubmission} interactionSubmission
 */

/**
 * @typedef {Object} SessionSnapshot
 * @property {string} session_id
 * @property {string} status
 * @property {string | null} current_turn_id
 * @property {string} model_name
 * @property {string} cwd
 * @property {string} approval_mode
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
    dashboardUrl: null,
    lastSequence: 0,
    pendingApprovalId: null,
    pendingQuestionId: null,
    pendingQuestionText: null,
    sessionFailureMessage: null,
    sessionFailureRetryable: null,
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
  };
}

function createIdleInteractionSubmission() {
  return {
    kind: null,
    state: "idle",
    error: null,
  };
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

/**
 * @param {SessionSnapshot} snapshot
 * @returns {DashboardState}
 */
export function hydrateFromSnapshot(snapshot) {
  return {
    sessionId: snapshot.session_id,
    status: snapshot.status,
    modelName: snapshot.model_name,
    cwd: snapshot.cwd,
    approvalMode: snapshot.approval_mode,
    dashboardUrl: snapshot.dashboard_url ?? null,
    lastSequence: snapshot.last_sequence ?? 0,
    pendingApprovalId: snapshot.pending_approval_id ?? null,
    pendingQuestionId: snapshot.pending_question_id ?? null,
    pendingQuestionText: snapshot.pending_question_text ?? null,
    sessionFailureMessage: snapshot.session_failure_message ?? null,
    sessionFailureRetryable: snapshot.session_failure_retryable ?? null,
    currentTurn: inferCurrentTurn(snapshot),
    turnMetrics: [...(snapshot.turn_metrics ?? [])],
    transcript: [...(snapshot.transcript ?? [])],
    activeToolCalls: [...(snapshot.active_tool_calls ?? [])],
    liveOutput: [],
    pendingApprovals: [...(snapshot.pending_approvals ?? [])],
    eventLog: [],
    interactionSubmission: createIdleInteractionSubmission(),
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
        sessionFailureMessage: null,
        sessionFailureRetryable: null,
      };
    case "SessionResumed":
      return {
        ...next,
        status: "running",
        interactionSubmission: createIdleInteractionSubmission(),
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
      };
    case "TurnStarted":
      if (typeof payload.turn_id !== "string") {
        return next;
      }
      return {
        ...next,
        interactionSubmission: createIdleInteractionSubmission(),
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
        return {
          ...next,
          status: "running",
          interactionSubmission: createIdleInteractionSubmission(),
          turnMetrics: completedTurnMetrics,
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
