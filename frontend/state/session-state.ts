import type { components } from "@/generated/api-types";
import type { SseEventEnvelope } from "@/api/sse";

export type ProjectionHealth = components["schemas"]["ProjectionHealthResponse"];
export type QueueCounts = components["schemas"]["SessionQueueCountsResponse"];
export type ProjectionHealthCounts =
  components["schemas"]["ProjectionHealthCountsAggregateResponse"];
export type RuntimeSummary = components["schemas"]["WorkspaceRuntimeSummaryResponse"];
export type RuntimeContext = components["schemas"]["RuntimeContextSnapshot"];
export type SessionAggregate = components["schemas"]["SessionAggregateResponse"];
export type SessionSnapshot = components["schemas"]["SessionSnapshotResponse"];
export type SessionSummary = components["schemas"]["OperatorSessionSummaryResponse"];
export type TranscriptMessage = components["schemas"]["TranscriptMessageResponse"];
export type ActiveToolCall = components["schemas"]["ActiveToolCallResponse"];
export type PendingApproval = components["schemas"]["PendingApprovalResponse"] & {
  resolution_decision?: string | null;
  resolution_error?: string | null;
  resolution_state?: "idle" | "pending" | "failed" | "resolved";
};
export type TurnMetrics = components["schemas"]["TurnMetricsResponse"];
export type BranchableTurn = components["schemas"]["BranchableTurnResponse"];
export type ChildSession = components["schemas"]["ChildSessionSummaryResponse"];

export type CurrentTurn = {
  error_message?: string;
  outcome?: string;
  status: string;
  trigger_message_id?: string;
  turn_id: string;
};

export type LiveOutputEntry = {
  chunk: string;
  stream: string;
  tool_call_id: string;
  turn_id: string;
};

export type EventLogEntry = {
  event_type: string;
  sequence: number;
};

export type ComparableSession = SessionFields & {
  createdAt: string | null;
  projectionHealth: ProjectionHealth | null;
  updatedAt: string | null;
};

export type SessionFields = {
  activeToolCalls: ActiveToolCall[];
  approvalMode: string | null;
  branchLabel: string | null;
  branchableTurns: BranchableTurn[];
  canFork: boolean;
  childSessions: ChildSession[];
  currentTurn: CurrentTurn | null;
  currentTurnPolicySummary: PolicySummary | null;
  cwd: string | null;
  dashboardUrl: string | null;
  forkBlockedReason: string | null;
  forkedFromSequence: number | null;
  forkedFromTurnId: string | null;
  lastSequence: number;
  latestForkPointSequence: number | null;
  latestForkPointTurnId: string | null;
  modelName: string | null;
  parentSessionId: string | null;
  pendingApprovalId: string | null;
  pendingApprovals: PendingApproval[];
  pendingQuestionId: string | null;
  pendingQuestionText: string | null;
  projectionHealth: ProjectionHealth | null;
  runtimeContext: RuntimeContext | null;
  selectedForkTurnId: string | null;
  sessionFailureMessage: string | null;
  sessionFailureRetryable: boolean | null;
  sessionId: string | null;
  sessionPolicySummary: PolicySummary | null;
  status: string;
  transcript: TranscriptMessage[];
  turnMetrics: TurnMetrics[];
};

export type PolicySummary = components["schemas"]["PolicyActivitySummaryResponse"];

export type DashboardState = SessionFields & {
  compareSession: ComparableSession | null;
  compareSessionId: string | null;
  eventLog: EventLogEntry[];
  liveOutput: LiveOutputEntry[];
  projectionHealthCounts: ProjectionHealthCounts;
  queueCounts: QueueCounts;
  runtimeSummary: RuntimeSummary;
  selectedQueue: string;
  selectedSessionId: string | null;
  sessionIndex: SessionSummary[];
  sessionIndexSort: string;
};

export function createDashboardState(): DashboardState {
  return {
    ...createEmptySessionFields(),
    compareSession: null,
    compareSessionId: null,
    eventLog: [],
    liveOutput: [],
    projectionHealthCounts: createEmptyProjectionHealthCounts(),
    queueCounts: createEmptyQueueCounts(),
    runtimeSummary: createEmptyRuntimeSummary(),
    selectedQueue: "all",
    selectedSessionId: null,
    sessionIndex: [],
    sessionIndexSort: "priority",
  };
}

export function createEmptyQueueCounts(): QueueCounts {
  return {
    action_needed: 0,
    active: 0,
    approvals: 0,
    degraded: 0,
    failures: 0,
    historical: 0,
    questions: 0,
    total: 0,
  };
}

export function createEmptyProjectionHealthCounts(): ProjectionHealthCounts {
  return {
    degraded: 0,
    ok: 0,
    stale: 0,
    unavailable: 0,
  };
}

export function createEmptyRuntimeSummary(): RuntimeSummary {
  return {
    dashboard_url: null,
    health: null,
    health_url: null,
    pid: null,
    session_index_url: null,
    started_at: null,
    state: "not_running",
    workspace_root: "",
  };
}

export function hydrateSessionAggregate(
  state: DashboardState,
  aggregate: SessionAggregate,
): DashboardState {
  return {
    ...state,
    projectionHealthCounts: { ...aggregate.projection_health_counts },
    queueCounts: { ...aggregate.queue_counts },
    runtimeSummary: { ...aggregate.runtime },
    selectedQueue: aggregate.queue ?? state.selectedQueue,
    sessionIndex: [...aggregate.sessions],
    sessionIndexSort: aggregate.sort,
  };
}

export function hydrateSessionSnapshot(snapshot: SessionSnapshot): DashboardState {
  return {
    ...createDashboardState(),
    ...normalizeSessionFields(snapshot),
    selectedSessionId: snapshot.session_id,
  };
}

export function hydrateSelectedSession(
  state: DashboardState,
  snapshot: SessionSnapshot,
): DashboardState {
  return {
    ...state,
    ...normalizeSessionFields(snapshot),
    selectedSessionId: snapshot.session_id,
  };
}

export function hydrateCompareSession(
  state: DashboardState,
  snapshot: SessionSnapshot,
): DashboardState {
  return {
    ...state,
    compareSession: normalizeComparableSession(snapshot),
    compareSessionId: snapshot.session_id,
  };
}

export function clearCompareSession(state: DashboardState): DashboardState {
  return {
    ...state,
    compareSession: null,
    compareSessionId: null,
  };
}

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
      return { ...next, turnMetrics: completedMetrics };
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

function createEmptySessionFields(): SessionFields {
  return {
    activeToolCalls: [],
    approvalMode: null,
    branchLabel: null,
    branchableTurns: [],
    canFork: false,
    childSessions: [],
    currentTurn: null,
    currentTurnPolicySummary: null,
    cwd: null,
    dashboardUrl: null,
    forkBlockedReason: null,
    forkedFromSequence: null,
    forkedFromTurnId: null,
    lastSequence: 0,
    latestForkPointSequence: null,
    latestForkPointTurnId: null,
    modelName: null,
    parentSessionId: null,
    pendingApprovalId: null,
    pendingApprovals: [],
    pendingQuestionId: null,
    pendingQuestionText: null,
    projectionHealth: null,
    runtimeContext: null,
    selectedForkTurnId: null,
    sessionFailureMessage: null,
    sessionFailureRetryable: null,
    sessionId: null,
    sessionPolicySummary: null,
    status: "unknown",
    transcript: [],
    turnMetrics: [],
  };
}

function normalizeSessionFields(snapshot: SessionSnapshot): SessionFields {
  const branchableTurns = [...snapshot.branchable_turns].sort(
    (left, right) => right.sequence - left.sequence,
  );
  return {
    activeToolCalls: [...snapshot.active_tool_calls],
    approvalMode: snapshot.approval_mode,
    branchLabel: snapshot.branch_label,
    branchableTurns,
    canFork: snapshot.can_fork,
    childSessions: [...snapshot.child_sessions],
    currentTurn: inferCurrentTurn(snapshot),
    currentTurnPolicySummary: snapshot.current_turn_policy_summary,
    cwd: snapshot.cwd,
    dashboardUrl: snapshot.dashboard_url,
    forkBlockedReason: snapshot.fork_blocked_reason,
    forkedFromSequence: snapshot.forked_from_sequence,
    forkedFromTurnId: snapshot.forked_from_turn_id,
    lastSequence: snapshot.last_sequence,
    latestForkPointSequence: snapshot.latest_fork_point_sequence,
    latestForkPointTurnId: snapshot.latest_fork_point_turn_id,
    modelName: snapshot.model_name,
    parentSessionId: snapshot.parent_session_id,
    pendingApprovalId: snapshot.pending_approval_id,
    pendingApprovals: snapshot.pending_approvals.map((approval) => ({
      ...approval,
      resolution_decision: null,
      resolution_error: null,
      resolution_state: "idle",
    })),
    pendingQuestionId: snapshot.pending_question_id,
    pendingQuestionText: snapshot.pending_question_text,
    projectionHealth: snapshot.projection_health,
    runtimeContext: cloneRuntimeContext(snapshot.runtime_context),
    selectedForkTurnId: defaultSelectedForkTurnId(
      branchableTurns,
      snapshot.latest_fork_point_turn_id,
    ),
    sessionFailureMessage: snapshot.session_failure_message,
    sessionFailureRetryable: snapshot.session_failure_retryable,
    sessionId: snapshot.session_id,
    sessionPolicySummary: snapshot.session_policy_summary,
    status: snapshot.status,
    transcript: [...snapshot.transcript],
    turnMetrics: [...snapshot.turn_metrics],
  };
}

function normalizeComparableSession(snapshot: SessionSnapshot): ComparableSession {
  return {
    ...normalizeSessionFields(snapshot),
    createdAt: snapshot.created_at,
    updatedAt: snapshot.updated_at,
  };
}

function inferCurrentTurn(snapshot: SessionSnapshot): CurrentTurn | null {
  const activeToolCall = snapshot.active_tool_calls[0];
  if (activeToolCall !== undefined) {
    return { status: "running", turn_id: activeToolCall.turn_id };
  }

  const pendingApproval = snapshot.pending_approvals[0];
  if (pendingApproval !== undefined) {
    return { status: "awaiting_approval", turn_id: pendingApproval.turn_id };
  }

  if (snapshot.current_turn_id !== null) {
    return { status: snapshot.status, turn_id: snapshot.current_turn_id };
  }

  return null;
}

function defaultSelectedForkTurnId(
  branchableTurns: BranchableTurn[],
  latestForkPointTurnId: string | null,
): string | null {
  if (latestForkPointTurnId !== null) {
    const latestTurn = branchableTurns.find((turn) => turn.turn_id === latestForkPointTurnId);
    if (latestTurn !== undefined) {
      return latestTurn.turn_id;
    }
  }
  return branchableTurns[0]?.turn_id ?? null;
}

function cloneRuntimeContext(runtimeContext: RuntimeContext): RuntimeContext {
  return {
    ...runtimeContext,
    artifact_context: runtimeContext.artifact_context
      ? {
          ...runtimeContext.artifact_context,
          summaries: [...(runtimeContext.artifact_context.summaries ?? [])],
        }
      : undefined,
    repository_context: {
      ...runtimeContext.repository_context,
      high_signal_paths: [...(runtimeContext.repository_context.high_signal_paths ?? [])],
      project_markers: [...(runtimeContext.repository_context.project_markers ?? [])],
      top_level_directories: [...(runtimeContext.repository_context.top_level_directories ?? [])],
      top_level_files: [...(runtimeContext.repository_context.top_level_files ?? [])],
    },
    runtime_notes: [...(runtimeContext.runtime_notes ?? [])],
    working_set: runtimeContext.working_set
      ? {
          ...runtimeContext.working_set,
          items: [...(runtimeContext.working_set.items ?? [])],
        }
      : undefined,
  };
}

function upsertTranscriptMessage(
  transcript: TranscriptMessage[],
  message: TranscriptMessage,
): TranscriptMessage[] {
  const existingIndex = transcript.findIndex((item) => item.message_id === message.message_id);
  if (existingIndex === -1) {
    return [...transcript, message];
  }
  return transcript.map((item, index) => (index === existingIndex ? message : item));
}

function upsertPendingApproval(
  pendingApprovals: PendingApproval[],
  approval: PendingApproval,
): PendingApproval[] {
  const existingIndex = pendingApprovals.findIndex(
    (item) => item.approval_id === approval.approval_id,
  );
  if (existingIndex === -1) {
    return [...pendingApprovals, approval];
  }
  return pendingApprovals.map((item, index) => (index === existingIndex ? approval : item));
}

function upsertActiveToolCall(
  activeToolCalls: ActiveToolCall[],
  toolCall: ActiveToolCall,
): ActiveToolCall[] {
  const existingIndex = activeToolCalls.findIndex(
    (item) => item.tool_call_id === toolCall.tool_call_id,
  );
  if (existingIndex === -1) {
    return [...activeToolCalls, toolCall];
  }
  return activeToolCalls.map((item, index) => (index === existingIndex ? toolCall : item));
}

function appendLiveOutput(
  liveOutput: LiveOutputEntry[],
  entry: LiveOutputEntry,
): LiveOutputEntry[] {
  return [...liveOutput, entry].slice(-200);
}

function upsertTurnMetrics(turnMetrics: TurnMetrics[], metrics: TurnMetrics): TurnMetrics[] {
  const existingIndex = turnMetrics.findIndex((item) => item.turn_id === metrics.turn_id);
  if (existingIndex === -1) {
    return [metrics, ...turnMetrics];
  }
  return turnMetrics.map((item, index) =>
    index === existingIndex ? { ...item, ...metrics } : item,
  );
}

function updateTurnMetrics(
  turnMetrics: TurnMetrics[],
  turnId: string,
  updater: (metrics: TurnMetrics) => TurnMetrics,
): TurnMetrics[] {
  const existing = turnMetrics.find((item) => item.turn_id === turnId) ?? makeTurnMetrics(turnId);
  return upsertTurnMetrics(turnMetrics, updater(existing));
}

function makeTurnMetrics(turnId: string, overrides: Partial<TurnMetrics> = {}): TurnMetrics {
  return {
    completed_at: null,
    failed_tool_call_count: 0,
    model_call_count: 0,
    model_duration_ms_total: 0,
    model_input_tokens_total: 0,
    model_output_tokens_total: 0,
    started_at: null,
    succeeded_tool_call_count: 0,
    tool_call_count: 0,
    tool_duration_ms_total: 0,
    turn_duration_ms: null,
    turn_id: turnId,
    ...overrides,
  };
}

function upsertBranchableTurn(
  branchableTurns: BranchableTurn[],
  branchableTurn: BranchableTurn,
): BranchableTurn[] {
  return [
    branchableTurn,
    ...branchableTurns.filter((turn) => turn.turn_id !== branchableTurn.turn_id),
  ].sort((left, right) => right.sequence - left.sequence);
}

function currentTurnLabel(state: DashboardState): string {
  const triggerMessageId = state.currentTurn?.trigger_message_id ?? null;
  const triggerMessage = triggerMessageId
    ? state.transcript.find((message) => message.message_id === triggerMessageId)
    : null;
  const triggerText = triggerMessage?.parts
    .map((part) => part.text)
    .join(" ")
    .trim();
  if (triggerText) {
    return triggerText;
  }
  if (state.currentTurn?.turn_id) {
    return `Turn ${state.currentTurn.turn_id.slice(0, 8)}`;
  }
  return "Completed turn";
}

function durationBetween(startedAt: string | null, endedAt: string | null): number | null {
  if (startedAt === null || endedAt === null) {
    return null;
  }
  const started = Date.parse(startedAt);
  const ended = Date.parse(endedAt);
  if (Number.isNaN(started) || Number.isNaN(ended)) {
    return null;
  }
  return Math.max(ended - started, 0);
}

function createEmptyPolicySummary(): PolicySummary {
  return {
    allow_count: 0,
    approve_count: 0,
    blocked_count: 0,
    command_count: 0,
    deny_count: 0,
    highest_risk_level: null,
    read_only_count: 0,
    total_decisions: 0,
    workspace_write_count: 0,
  };
}

function incrementPolicySummary(
  summary: PolicySummary | null,
  outcome: string | null | undefined,
  riskLevel: string | null | undefined,
): PolicySummary | null {
  if (typeof outcome !== "string" || typeof riskLevel !== "string") {
    return summary;
  }

  const next = { ...(summary ?? createEmptyPolicySummary()) };
  next.total_decisions += 1;
  if (outcome === "allow") next.allow_count += 1;
  if (outcome === "approve") next.approve_count += 1;
  if (outcome === "deny") next.deny_count += 1;
  if (outcome === "blocked") next.blocked_count += 1;
  if (riskLevel === "read_only") next.read_only_count += 1;
  if (riskLevel === "workspace_write") next.workspace_write_count += 1;
  if (riskLevel === "command") next.command_count += 1;

  const riskRanks: Record<string, number> = {
    command: 2,
    read_only: 0,
    workspace_write: 1,
  };
  const currentRank = next.highest_risk_level ? (riskRanks[next.highest_risk_level] ?? -1) : -1;
  const nextRank = riskRanks[riskLevel] ?? -1;
  if (nextRank > currentRank) {
    next.highest_risk_level = riskLevel;
  }
  return next;
}

function upsertRuntimeContextNote(
  runtimeContext: RuntimeContext | null,
  note: NonNullable<RuntimeContext["runtime_notes"]>[number],
): RuntimeContext | null {
  if (runtimeContext === null) {
    return runtimeContext;
  }
  const runtimeNotes = runtimeContext.runtime_notes ?? [];
  const existingIndex = runtimeNotes.findIndex(
    (existing) =>
      existing.category === note.category &&
      existing.message === note.message &&
      (existing.source_session_id ?? null) === (note.source_session_id ?? null),
  );
  if (existingIndex >= 0) {
    return {
      ...runtimeContext,
      runtime_notes: runtimeNotes.map((existing, index) =>
        index === existingIndex ? note : existing,
      ),
    };
  }
  return {
    ...runtimeContext,
    runtime_notes: [...runtimeNotes, note].slice(0, 8),
    additional_runtime_note_count:
      runtimeNotes.length >= 8
        ? runtimeContext.additional_runtime_note_count + 1
        : runtimeContext.additional_runtime_note_count,
  };
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function stringOrUndefined(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function booleanOrNull(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}
