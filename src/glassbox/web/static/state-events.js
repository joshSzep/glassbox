import {
  createIdleForkSubmission,
  createIdleInteractionSubmission,
} from "./state-core.js";
import {
  currentTurnLabel,
  upsertBranchableTurn,
  upsertRuntimeContextNote,
} from "./state-snapshot.js";

function appendLiveOutput(liveOutput, entry) {
  const next = [...liveOutput, entry];
  return next.slice(-200);
}

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

export function applyEvent(state, envelope) {
  const payload = envelope.payload ?? {};
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
