import type {
  ActiveToolCall,
  BranchableTurn,
  CurrentTurn,
  DashboardState,
  EventLogEntry,
  LiveOutputEntry,
  PendingApproval,
  TranscriptMessage,
  TurnMetrics,
} from "@/state/session-types";

export type SessionNarrativeItem =
  | { kind: "message"; message: TranscriptMessage }
  | { kind: "tool-call"; toolCall: ActiveToolCall }
  | { kind: "approval"; approval: PendingApproval }
  | { kind: "question"; questionId: string; text: string | null; turnId: string | null }
  | { kind: "live-output"; output: LiveOutputEntry }
  | { kind: "failure"; message: string; retryable: boolean | null; turnId: string | null }
  | { kind: "metric"; metric: TurnMetrics }
  | { kind: "fork-boundary"; turn: BranchableTurn }
  | { kind: "event-evidence"; event: EventLogEntry };

export type SessionNarrativeTurnStatus =
  | "active"
  | "awaiting-approval"
  | "awaiting-answer"
  | "completed"
  | "failed"
  | "historical"
  | "partial"
  | "running"
  | "unknown";

export type SessionNarrativeTurn = {
  id: string;
  isFallback: boolean;
  items: SessionNarrativeItem[];
  sequence: number | null;
  status: SessionNarrativeTurnStatus;
  title: string;
  turnId: string | null;
};

export type SessionNarrative = {
  sessionId: string | null;
  turns: SessionNarrativeTurn[];
};

export type SessionNarrativeSource = Pick<
  DashboardState,
  | "activeToolCalls"
  | "branchableTurns"
  | "currentTurn"
  | "eventLog"
  | "forkedFromTurnId"
  | "latestForkPointTurnId"
  | "liveOutput"
  | "pendingApprovals"
  | "pendingQuestionId"
  | "pendingQuestionText"
  | "sessionFailureMessage"
  | "sessionFailureRetryable"
  | "sessionId"
  | "status"
  | "transcript"
  | "turnMetrics"
>;

export function buildSessionNarrative(source: SessionNarrativeSource): SessionNarrative {
  const groups = new Map<string, MutableNarrativeTurn>();
  const groupOrder: string[] = [];

  const ensureGroup = (input: EnsureGroupInput): MutableNarrativeTurn => {
    const id = input.turnId ?? input.fallbackId;
    const existing = groups.get(id);
    if (existing !== undefined) {
      existing.sequence = existing.sequence ?? input.sequence ?? null;
      existing.status = mergeStatus(existing.status, input.status);
      existing.title = input.title ?? existing.title;
      return existing;
    }

    const next: MutableNarrativeTurn = {
      id,
      isFallback: input.turnId === null,
      items: [],
      sequence: input.sequence ?? null,
      status: input.status,
      title: input.title ?? fallbackTitle(input.turnId, input.fallbackId),
      turnId: input.turnId,
    };
    groups.set(id, next);
    groupOrder.push(id);
    return next;
  };

  for (const metric of source.turnMetrics) {
    ensureGroup({
      fallbackId: `metric:${metric.turn_id}`,
      sequence: null,
      status: metric.failed_tool_call_count > 0 ? "failed" : "completed",
      title: `Turn ${metric.turn_id}`,
      turnId: metric.turn_id,
    }).items.push({ kind: "metric", metric });
  }

  for (const turn of source.branchableTurns) {
    ensureGroup({
      fallbackId: `fork:${turn.turn_id}`,
      sequence: turn.sequence,
      status: source.status === "completed" ? "historical" : "completed",
      title: turn.label,
      turnId: turn.turn_id,
    }).items.push({ kind: "fork-boundary", turn });
  }

  for (const toolCall of source.activeToolCalls) {
    ensureGroup({
      fallbackId: `tool:${toolCall.tool_call_id}`,
      sequence: null,
      status: "active",
      title: `Turn ${toolCall.turn_id}`,
      turnId: toolCall.turn_id,
    }).items.push({ kind: "tool-call", toolCall });
  }

  for (const approval of source.pendingApprovals) {
    ensureGroup({
      fallbackId: `approval:${approval.approval_id}`,
      sequence: null,
      status: "awaiting-approval",
      title: `Turn ${approval.turn_id}`,
      turnId: approval.turn_id,
    }).items.push({ kind: "approval", approval });
  }

  if (source.pendingQuestionId !== null) {
    const turnId = source.currentTurn?.turn_id ?? source.pendingApprovals[0]?.turn_id ?? null;
    ensureGroup({
      fallbackId: `question:${source.pendingQuestionId}`,
      sequence: null,
      status: "awaiting-answer",
      title: turnId === null ? "Pending question" : `Turn ${turnId}`,
      turnId,
    }).items.push({
      kind: "question",
      questionId: source.pendingQuestionId,
      text: source.pendingQuestionText,
      turnId,
    });
  }

  if (source.currentTurn !== null) {
    ensureCurrentTurn(source.currentTurn, source.status, ensureGroup);
  }

  for (const output of source.liveOutput) {
    ensureGroup({
      fallbackId: `live-output:${output.tool_call_id}`,
      sequence: null,
      status: "active",
      title: `Turn ${output.turn_id}`,
      turnId: output.turn_id,
    }).items.push({ kind: "live-output", output });
  }

  if (source.sessionFailureMessage !== null) {
    const turnId = source.currentTurn?.turn_id ?? source.turnMetrics.at(-1)?.turn_id ?? null;
    ensureGroup({
      fallbackId: "session-failure",
      sequence: null,
      status: "failed",
      title: turnId === null ? "Session failure" : `Turn ${turnId}`,
      turnId,
    }).items.push({
      kind: "failure",
      message: source.sessionFailureMessage,
      retryable: source.sessionFailureRetryable,
      turnId,
    });
  }

  if (source.transcript.length > 0) {
    const transcriptTurnId = inferTranscriptTurnId(source);
    const transcriptGroup = ensureGroup({
      fallbackId: "transcript-unassigned",
      sequence: null,
      status: source.status === "completed" ? "historical" : "partial",
      title:
        transcriptTurnId === null
          ? "Transcript messages without turn metadata"
          : `Turn ${transcriptTurnId}`,
      turnId: transcriptTurnId,
    });
    for (const message of source.transcript) {
      transcriptGroup.items.push({ kind: "message", message });
    }
  }

  if (source.eventLog.length > 0) {
    const eventGroup = ensureGroup({
      fallbackId: "event-evidence-unassigned",
      sequence: null,
      status: "partial",
      title: "Event evidence without turn metadata",
      turnId: null,
    });
    for (const event of source.eventLog) {
      eventGroup.items.push({ kind: "event-evidence", event });
    }
  }

  return {
    sessionId: source.sessionId,
    turns: groupOrder.map((id) => groups.get(id)).filter(isNarrativeTurn),
  };
}

type MutableNarrativeTurn = SessionNarrativeTurn;

type EnsureGroupInput = {
  fallbackId: string;
  sequence: number | null;
  status: SessionNarrativeTurnStatus;
  title?: string;
  turnId: string | null;
};

function ensureCurrentTurn(
  currentTurn: CurrentTurn,
  sessionStatus: string,
  ensureGroup: (input: EnsureGroupInput) => MutableNarrativeTurn,
) {
  ensureGroup({
    fallbackId: `current:${currentTurn.turn_id}`,
    sequence: null,
    status: statusFromCurrentTurn(currentTurn, sessionStatus),
    title: `Turn ${currentTurn.turn_id}`,
    turnId: currentTurn.turn_id,
  });
}

function inferTranscriptTurnId(source: SessionNarrativeSource): string | null {
  const explicitTurnIds = new Set<string>();
  for (const metric of source.turnMetrics) {
    explicitTurnIds.add(metric.turn_id);
  }
  for (const turn of source.branchableTurns) {
    explicitTurnIds.add(turn.turn_id);
  }
  for (const toolCall of source.activeToolCalls) {
    explicitTurnIds.add(toolCall.turn_id);
  }
  for (const approval of source.pendingApprovals) {
    explicitTurnIds.add(approval.turn_id);
  }
  for (const output of source.liveOutput) {
    explicitTurnIds.add(output.turn_id);
  }
  if (source.currentTurn !== null) {
    explicitTurnIds.add(source.currentTurn.turn_id);
  }

  if (explicitTurnIds.size === 1) {
    return [...explicitTurnIds][0] ?? null;
  }
  if (source.transcript.length === 1 && source.currentTurn !== null) {
    return source.currentTurn.turn_id;
  }
  return null;
}

function statusFromCurrentTurn(
  currentTurn: CurrentTurn,
  sessionStatus: string,
): SessionNarrativeTurnStatus {
  if (currentTurn.status === "awaiting_approval") {
    return "awaiting-approval";
  }
  if (currentTurn.status === "failed" || sessionStatus === "failed") {
    return "failed";
  }
  if (sessionStatus === "completed") {
    return "historical";
  }
  if (currentTurn.status === "running") {
    return "running";
  }
  return "unknown";
}

function mergeStatus(
  currentStatus: SessionNarrativeTurnStatus,
  nextStatus: SessionNarrativeTurnStatus,
): SessionNarrativeTurnStatus {
  const priority: SessionNarrativeTurnStatus[] = [
    "failed",
    "awaiting-approval",
    "awaiting-answer",
    "active",
    "running",
    "partial",
    "completed",
    "historical",
    "unknown",
  ];
  return priority.indexOf(nextStatus) < priority.indexOf(currentStatus)
    ? nextStatus
    : currentStatus;
}

function fallbackTitle(turnId: string | null, fallbackId: string): string {
  return turnId === null ? fallbackId : `Turn ${turnId}`;
}

function isNarrativeTurn(turn: MutableNarrativeTurn | undefined): turn is SessionNarrativeTurn {
  return turn !== undefined;
}
