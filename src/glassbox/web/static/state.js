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
 * @typedef {{turn_id: string, tool_call_id: string, stream: string, chunk: string}} LiveOutputEntry
 * @typedef {{sequence: number, event_type: string}} EventLogEntry
 *
 * @typedef {Object} DashboardState
 * @property {string | null} sessionId
 * @property {string} status
 * @property {string | null} modelName
 * @property {string | null} cwd
 * @property {string | null} approvalMode
 * @property {number} lastSequence
 * @property {string | null} pendingApprovalId
 * @property {string | null} pendingQuestionId
 * @property {CurrentTurn | null} currentTurn
 * @property {TranscriptMessage[]} transcript
 * @property {ActiveToolCall[]} activeToolCalls
 * @property {LiveOutputEntry[]} liveOutput
 * @property {PendingApproval[]} pendingApprovals
 * @property {EventLogEntry[]} eventLog
 */

/**
 * @typedef {Object} SessionSnapshot
 * @property {string} session_id
 * @property {string} status
 * @property {string} model_name
 * @property {string} cwd
 * @property {string} approval_mode
 * @property {number} last_sequence
 * @property {string | null} pending_approval_id
 * @property {string | null} pending_question_id
 * @property {TranscriptMessage[]} transcript
 * @property {ActiveToolCall[]} active_tool_calls
 * @property {PendingApproval[]} pending_approvals
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
    lastSequence: 0,
    pendingApprovalId: null,
    pendingQuestionId: null,
    currentTurn: null,
    transcript: [],
    activeToolCalls: [],
    liveOutput: [],
    pendingApprovals: [],
    eventLog: [],
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
    lastSequence: snapshot.last_sequence ?? 0,
    pendingApprovalId: snapshot.pending_approval_id ?? null,
    pendingQuestionId: snapshot.pending_question_id ?? null,
    currentTurn: inferCurrentTurn(snapshot),
    transcript: [...(snapshot.transcript ?? [])],
    activeToolCalls: [...(snapshot.active_tool_calls ?? [])],
    liveOutput: [],
    pendingApprovals: [...(snapshot.pending_approvals ?? [])],
    eventLog: [],
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
        cwd: typeof payload.cwd === "string" ? payload.cwd : next.cwd,
        modelName: (
          typeof payload.model_name === "string" ? payload.model_name : next.modelName
        ),
        approvalMode: (
          typeof payload.approval_mode === "string"
            ? payload.approval_mode
            : next.approvalMode
        ),
      };
    case "SessionResumed":
      return {
        ...next,
        status: "running",
      };
    case "SessionCompleted":
      return {
        ...next,
        status: "completed",
        currentTurn: null,
        pendingApprovalId: null,
        pendingQuestionId: null,
      };
    case "SessionFailed":
      return {
        ...next,
        status: "failed",
        currentTurn: next.currentTurn,
      };
    case "TurnStarted":
      if (typeof payload.turn_id !== "string") {
        return next;
      }
      return {
        ...next,
        currentTurn: {
          turn_id: payload.turn_id,
          status: "running",
          trigger_message_id: (
            typeof payload.trigger_message_id === "string"
              ? payload.trigger_message_id
              : undefined
          ),
        },
      };
    case "TurnStatusChanged":
      if (typeof payload.turn_id !== "string" || typeof payload.status !== "string") {
        return next;
      }
      return {
        ...next,
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
      };
    case "UserAnswerProvided":
      return {
        ...next,
        status: "running",
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
      };
    case "TurnCompleted":
      if (typeof payload.turn_id !== "string") {
        return next;
      }
      if (payload.outcome === "awaiting_approval") {
        return {
          ...next,
          status: "awaiting_approval",
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
        started_at: undefined,
      };
      const existing = next.activeToolCalls.find(
        item => item.tool_call_id === toolCall.tool_call_id,
      );
      return {
        ...next,
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
        activeToolCalls: next.activeToolCalls.filter(
          item => item.tool_call_id !== payload.tool_call_id,
        ),
      };
    default:
      return next;
  }
}
