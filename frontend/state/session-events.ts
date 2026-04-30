import type { SseEventEnvelope } from "@/api/sse";
import {
  appendLiveOutput,
  booleanOrNull,
  createEmptyPolicySummary,
  currentTurnLabel,
  durationBetween,
  incrementPolicySummary,
  makeTurnMetrics,
  numberOrNull,
  stringOrNull,
  stringOrUndefined,
  updateTurnMetrics,
  upsertActiveToolCall,
  upsertBranchableTurn,
  upsertPendingApproval,
  upsertRuntimeContextNote,
  upsertTranscriptMessage,
  upsertTurnMetrics,
} from "@/state/session-event-helpers";
import type {
  ActiveToolCall,
  BranchableTurn,
  DashboardState,
  ProviderRecovery,
  TranscriptMessage,
} from "@/state/session-types";

export function applySessionEvent(
  state: DashboardState,
  envelope: SseEventEnvelope,
): DashboardState {
  const payload = envelope.payload;
  const next: DashboardState = {
    ...state,
    eventLog: [...state.eventLog, { event_type: envelope.event_type, sequence: envelope.sequence }],
    lastSequence: Math.max(state.lastSequence, envelope.sequence),
  };

  switch (envelope.event_type) {
    case "SessionStarted":
      return {
        ...next,
        approvalMode: stringOrNull(payload.approval_mode) ?? next.approvalMode,
        branchLabel: stringOrNull(payload.branch_label),
        canFork: false,
        cwd: stringOrNull(payload.cwd) ?? next.cwd,
        dashboardUrl: stringOrNull(payload.dashboard_url),
        forkBlockedReason: "Wait for the current turn to finish before creating a fork.",
        forkedFromSequence: numberOrNull(payload.forked_from_sequence),
        forkedFromTurnId: stringOrNull(payload.forked_from_turn_id),
        modelName: stringOrNull(payload.model_name) ?? next.modelName,
        parentSessionId: stringOrNull(payload.parent_session_id),
        sessionFailureMessage: null,
        sessionFailureRetryable: null,
        status: "running",
      };
    case "SessionCompleted":
      return {
        ...next,
        canFork: next.branchableTurns.length > 0,
        currentTurn: null,
        forkBlockedReason:
          next.branchableTurns.length > 0 ? null : "This session has no completed fork point.",
        pendingApprovalId: null,
        pendingQuestionId: null,
        pendingQuestionText: null,
        status: "completed",
      };
    case "SessionFailed":
      return {
        ...next,
        currentTurn: null,
        pendingApprovalId: null,
        pendingQuestionId: null,
        pendingQuestionText: null,
        sessionFailureMessage: stringOrNull(payload.error_message) ?? next.sessionFailureMessage,
        sessionFailureRetryable: booleanOrNull(payload.retryable),
        status: "failed",
      };
    case "UserMessageReceived": {
      const messageId = stringOrNull(payload.message_id);
      if (messageId === null) {
        return next;
      }
      return {
        ...next,
        transcript: upsertTranscriptMessage(next.transcript, {
          created_at: envelope.created_at,
          message_id: messageId,
          parts: [{ kind: "text", text: stringOrNull(payload.text) ?? "" }],
          role: "user",
        }),
      };
    }
    case "AssistantMessageCompleted": {
      const messageId = stringOrNull(payload.message_id);
      if (messageId === null) {
        return next;
      }
      return {
        ...next,
        transcript: upsertTranscriptMessage(next.transcript, {
          created_at: envelope.created_at,
          message_id: messageId,
          parts: Array.isArray(payload.parts) ? (payload.parts as TranscriptMessage["parts"]) : [],
          role: "assistant",
        }),
      };
    }
    case "TurnStarted": {
      const turnId = stringOrNull(payload.turn_id);
      if (turnId === null) {
        return next;
      }
      return {
        ...next,
        canFork: false,
        currentTurn: {
          status: "running",
          trigger_message_id: stringOrUndefined(payload.trigger_message_id),
          turn_id: turnId,
        },
        currentTurnPolicySummary: createEmptyPolicySummary(),
        forkBlockedReason: `Wait for turn ${turnId.slice(0, 8)} to finish before creating a fork.`,
        turnMetrics: upsertTurnMetrics(
          next.turnMetrics,
          makeTurnMetrics(turnId, { started_at: envelope.created_at }),
        ),
      };
    }
    case "TurnCompleted": {
      const turnId = stringOrNull(payload.turn_id);
      if (turnId === null) {
        return next;
      }
      const completedMetrics = updateTurnMetrics(next.turnMetrics, turnId, (metrics) => ({
        ...metrics,
        completed_at: envelope.created_at,
        turn_duration_ms: durationBetween(metrics.started_at, envelope.created_at),
      }));
      if (payload.outcome === "completed") {
        const branchableTurn: BranchableTurn = {
          created_at: envelope.created_at,
          label: currentTurnLabel(next),
          sequence: envelope.sequence,
          turn_id: turnId,
        };
        return {
          ...next,
          branchableTurns: upsertBranchableTurn(next.branchableTurns, branchableTurn),
          canFork: true,
          currentTurn: { outcome: "completed", status: "completed", turn_id: turnId },
          forkBlockedReason: null,
          latestForkPointSequence: envelope.sequence,
          latestForkPointTurnId: turnId,
          selectedForkTurnId: next.selectedForkTurnId ?? turnId,
          status: "running",
          turnMetrics: completedMetrics,
        };
      }
      if (payload.outcome === "awaiting_approval" || payload.outcome === "awaiting_user_input") {
        return {
          ...next,
          currentTurn: { outcome: payload.outcome, status: payload.outcome, turn_id: turnId },
          status: payload.outcome,
          turnMetrics: completedMetrics,
        };
      }
      if (payload.outcome === "cancelled") {
        return {
          ...next,
          activeToolCalls: [],
          canFork: true,
          currentTurn: { outcome: "cancelled", status: "cancelled", turn_id: turnId },
          forkBlockedReason: null,
          pendingApprovalId: null,
          pendingApprovals: [],
          pendingQuestionId: null,
          pendingQuestionText: null,
          status: "running",
          turnMetrics: completedMetrics,
        };
      }
      return { ...next, turnMetrics: completedMetrics };
    }
    case "CancellationRequested": {
      const turnId = stringOrNull(payload.turn_id);
      return {
        ...next,
        currentTurn:
          turnId === null
            ? next.currentTurn
            : { ...next.currentTurn, status: "cancelling", turn_id: turnId },
        forkBlockedReason: "Cancellation is pending for the active turn.",
      };
    }
    case "TurnCancelled": {
      const turnId = stringOrNull(payload.turn_id);
      if (turnId === null) {
        return next;
      }
      return {
        ...next,
        activeToolCalls: [],
        currentTurn: { outcome: "cancelled", status: "cancelled", turn_id: turnId },
        pendingApprovalId: null,
        pendingApprovals: [],
        pendingQuestionId: null,
        pendingQuestionText: null,
        status: "running",
      };
    }
    case "ApprovalRequested": {
      const approvalId = stringOrNull(payload.approval_id);
      if (approvalId === null) {
        return next;
      }
      const turnId = stringOrNull(payload.turn_id) ?? "unknown";
      return {
        ...next,
        canFork: false,
        currentTurn: {
          ...next.currentTurn,
          status: "awaiting_approval",
          turn_id: turnId,
        },
        forkBlockedReason: "Resolve the pending approval before creating a fork.",
        pendingApprovalId: approvalId,
        pendingApprovals: upsertPendingApproval(next.pendingApprovals, {
          approval_id: approvalId,
          policy_outcome: stringOrNull(payload.policy_outcome),
          policy_risk_level: stringOrNull(payload.policy_risk_level),
          policy_source_kind: stringOrNull(payload.policy_source_kind),
          policy_source_label: stringOrNull(payload.policy_source_label),
          reason: stringOrNull(payload.reason) ?? "",
          requested_at: envelope.created_at,
          resolution_decision: null,
          resolution_error: null,
          resolution_state: "idle",
          subject: stringOrNull(payload.subject) ?? "",
          turn_id: turnId,
        }),
        status: "awaiting_approval",
      };
    }
    case "ApprovalResolved":
      return {
        ...next,
        currentTurn: next.currentTurn ? { ...next.currentTurn, status: "running" } : null,
        forkBlockedReason: "Wait for the current turn to finish before creating a fork.",
        pendingApprovalId:
          next.pendingApprovalId === payload.approval_id ? null : next.pendingApprovalId,
        pendingApprovals: next.pendingApprovals.filter(
          (approval) => approval.approval_id !== payload.approval_id,
        ),
        status: "running",
      };
    case "UserQuestionAsked":
      return {
        ...next,
        canFork: false,
        currentTurn: next.currentTurn
          ? { ...next.currentTurn, status: "awaiting_user_input" }
          : next.currentTurn,
        forkBlockedReason: "Answer the pending question before creating a fork.",
        pendingQuestionId: stringOrNull(payload.question_id) ?? next.pendingQuestionId,
        pendingQuestionText: stringOrNull(payload.question) ?? next.pendingQuestionText,
        status: "awaiting_user_input",
      };
    case "UserAnswerProvided":
      return {
        ...next,
        currentTurn: next.currentTurn ? { ...next.currentTurn, status: "running" } : null,
        forkBlockedReason: "Wait for the current turn to finish before creating a fork.",
        pendingQuestionId:
          next.pendingQuestionId === payload.question_id ? null : next.pendingQuestionId,
        pendingQuestionText:
          next.pendingQuestionId === payload.question_id ? null : next.pendingQuestionText,
        status: "running",
      };
    case "ToolExecutionStarted": {
      const toolCallId = stringOrNull(payload.tool_call_id);
      const turnId = stringOrNull(payload.turn_id);
      const toolName = stringOrNull(payload.tool_name);
      if (toolCallId === null || turnId === null || toolName === null) {
        return next;
      }
      const activeToolCall: ActiveToolCall = {
        completed_at: null,
        policy_outcome: stringOrNull(payload.policy_outcome),
        policy_reason: stringOrNull(payload.policy_reason),
        policy_risk_level: stringOrNull(payload.policy_risk_level),
        policy_source_kind: stringOrNull(payload.policy_source_kind),
        policy_source_label: stringOrNull(payload.policy_source_label),
        started_at: envelope.created_at,
        status: "running",
        summary: null,
        tool_call_id: toolCallId,
        tool_name: toolName,
        turn_id: turnId,
      };
      return {
        ...next,
        activeToolCalls: upsertActiveToolCall(next.activeToolCalls, activeToolCall),
        currentTurn: {
          ...next.currentTurn,
          status: next.currentTurn?.status ?? "running",
          turn_id: turnId,
        },
        currentTurnPolicySummary: incrementPolicySummary(
          next.currentTurnPolicySummary,
          activeToolCall.policy_outcome,
          activeToolCall.policy_risk_level,
        ),
        sessionPolicySummary: incrementPolicySummary(
          next.sessionPolicySummary,
          activeToolCall.policy_outcome,
          activeToolCall.policy_risk_level,
        ),
        turnMetrics: updateTurnMetrics(next.turnMetrics, turnId, (metrics) => ({
          ...metrics,
          tool_call_count: metrics.tool_call_count + 1,
        })),
      };
    }
    case "ToolOutputChunk": {
      const turnId = stringOrNull(payload.turn_id);
      const toolCallId = stringOrNull(payload.tool_call_id);
      const stream = stringOrNull(payload.stream);
      const chunk = stringOrNull(payload.chunk);
      if (turnId === null || toolCallId === null || stream === null || chunk === null) {
        return next;
      }
      return {
        ...next,
        liveOutput: appendLiveOutput(next.liveOutput, {
          chunk,
          stream,
          tool_call_id: toolCallId,
          turn_id: turnId,
        }),
      };
    }
    case "ToolExecutionCompleted": {
      const turnId = stringOrNull(payload.turn_id) ?? "unknown";
      const toolCallId = stringOrNull(payload.tool_call_id);
      const activeToolCall = next.activeToolCalls.find((item) => item.tool_call_id === toolCallId);
      return {
        ...next,
        activeToolCalls: next.activeToolCalls.filter((item) => item.tool_call_id !== toolCallId),
        turnMetrics: updateTurnMetrics(next.turnMetrics, turnId, (metrics) => ({
          ...metrics,
          failed_tool_call_count:
            metrics.failed_tool_call_count + (payload.success === false ? 1 : 0),
          succeeded_tool_call_count:
            metrics.succeeded_tool_call_count + (payload.success === false ? 0 : 1),
          tool_duration_ms_total:
            metrics.tool_duration_ms_total +
            (durationBetween(activeToolCall?.started_at ?? null, envelope.created_at) ?? 0),
        })),
      };
    }
    case "ToolExecutionCancelled": {
      const toolCallId = stringOrNull(payload.tool_call_id);
      return {
        ...next,
        activeToolCalls: next.activeToolCalls.map((item) =>
          item.tool_call_id === toolCallId
            ? { ...item, status: "cancelled", summary: stringOrNull(payload.summary) }
            : item,
        ),
      };
    }
    case "ModelCallCompleted": {
      const turnId = stringOrNull(payload.turn_id);
      if (turnId === null) {
        return next;
      }
      return {
        ...next,
        turnMetrics: updateTurnMetrics(next.turnMetrics, turnId, (metrics) => ({
          ...metrics,
          model_call_count: metrics.model_call_count + 1,
          model_duration_ms_total:
            metrics.model_duration_ms_total + (numberOrNull(payload.duration_ms) ?? 0),
          model_input_tokens_total:
            metrics.model_input_tokens_total + (numberOrNull(payload.input_tokens) ?? 0),
          model_output_tokens_total:
            metrics.model_output_tokens_total + (numberOrNull(payload.output_tokens) ?? 0),
        })),
      };
    }
    case "ProviderRecoveryRecorded": {
      const provider = stringOrNull(payload.provider);
      const modelName = stringOrNull(payload.model_name);
      const failureKind = stringOrNull(payload.failure_kind);
      const action = stringOrNull(payload.action);
      const reason = stringOrNull(payload.reason);
      const operatorNextAction = stringOrNull(payload.operator_next_action);
      if (
        provider === null ||
        modelName === null ||
        failureKind === null ||
        action === null ||
        reason === null ||
        operatorNextAction === null
      ) {
        return next;
      }
      const recovery: ProviderRecovery = {
        action,
        attempt: numberOrNull(payload.attempt) ?? 1,
        backoff_seconds: numberOrNull(payload.backoff_seconds),
        checkpoint_id: stringOrNull(payload.checkpoint_id),
        created_at: envelope.created_at,
        degraded: booleanOrNull(payload.degraded) ?? false,
        failure_kind: failureKind,
        last_sequence: envelope.sequence,
        max_attempts: numberOrNull(payload.max_attempts),
        model_name: modelName,
        next_retry_at: stringOrNull(payload.next_retry_at),
        operator_next_action: operatorNextAction,
        provider,
        reason,
        retryable: booleanOrNull(payload.retryable) ?? false,
        safe_to_continue: booleanOrNull(payload.safe_to_continue) ?? false,
        session_id: envelope.session_id,
        task_id: stringOrNull(payload.task_id),
        turn_id: stringOrNull(payload.turn_id),
      };
      return {
        ...next,
        latestProviderRecovery: recovery,
      };
    }
    case "RuntimeNoteRecorded":
    case "RuntimeNoteImported":
      if (typeof payload.category !== "string" || typeof payload.message !== "string") {
        return next;
      }
      return {
        ...next,
        runtimeContext: upsertRuntimeContextNote(next.runtimeContext, {
          category: payload.category,
          inherited: envelope.event_type === "RuntimeNoteImported" || Boolean(payload.inherited),
          message: payload.message,
          source_session_id: stringOrNull(payload.source_session_id) ?? next.sessionId,
        }),
      };
    default:
      return next;
  }
}
