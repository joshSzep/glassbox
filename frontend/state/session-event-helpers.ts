import type {
  ActiveToolCall,
  BranchableTurn,
  DashboardState,
  LiveOutputEntry,
  PendingApproval,
  PolicySummary,
  RuntimeContext,
  TranscriptMessage,
  TurnMetrics,
} from "@/state/session-types";

export function upsertTranscriptMessage(
  transcript: TranscriptMessage[],
  message: TranscriptMessage,
): TranscriptMessage[] {
  const existingIndex = transcript.findIndex((item) => item.message_id === message.message_id);
  if (existingIndex === -1) {
    return [...transcript, message];
  }
  return transcript.map((item, index) => (index === existingIndex ? message : item));
}

export function upsertPendingApproval(
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

export function upsertActiveToolCall(
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

export function appendLiveOutput(
  liveOutput: LiveOutputEntry[],
  entry: LiveOutputEntry,
): LiveOutputEntry[] {
  return [...liveOutput, entry].slice(-200);
}

export function upsertTurnMetrics(turnMetrics: TurnMetrics[], metrics: TurnMetrics): TurnMetrics[] {
  const existingIndex = turnMetrics.findIndex((item) => item.turn_id === metrics.turn_id);
  if (existingIndex === -1) {
    return [metrics, ...turnMetrics];
  }
  return turnMetrics.map((item, index) =>
    index === existingIndex ? { ...item, ...metrics } : item,
  );
}

export function updateTurnMetrics(
  turnMetrics: TurnMetrics[],
  turnId: string,
  updater: (metrics: TurnMetrics) => TurnMetrics,
): TurnMetrics[] {
  const existing = turnMetrics.find((item) => item.turn_id === turnId) ?? makeTurnMetrics(turnId);
  return upsertTurnMetrics(turnMetrics, updater(existing));
}

export function makeTurnMetrics(turnId: string, overrides: Partial<TurnMetrics> = {}): TurnMetrics {
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

export function upsertBranchableTurn(
  branchableTurns: BranchableTurn[],
  branchableTurn: BranchableTurn,
): BranchableTurn[] {
  return [
    branchableTurn,
    ...branchableTurns.filter((turn) => turn.turn_id !== branchableTurn.turn_id),
  ].sort((left, right) => right.sequence - left.sequence);
}

export function currentTurnLabel(state: DashboardState): string {
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

export function durationBetween(startedAt: string | null, endedAt: string | null): number | null {
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

export function createEmptyPolicySummary(): PolicySummary {
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

export function incrementPolicySummary(
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

export function upsertRuntimeContextNote(
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

export function stringOrNull(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

export function stringOrUndefined(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

export function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function booleanOrNull(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}
