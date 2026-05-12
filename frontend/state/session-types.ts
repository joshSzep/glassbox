import type { components } from "@/generated/api-types";

export type ProjectionHealth = components["schemas"]["ProjectionHealthResponse"];
export type ProviderEvidence = components["schemas"]["ProviderEvidenceSummaryResponse"];
export type KnowledgePosture = components["schemas"]["WorkspaceKnowledgePosture"];
export type OperatorQueueCounts = components["schemas"]["OperatorQueueCountsView"];
export type OperatorQueueItem = components["schemas"]["OperatorQueueItem"];
export type QueueCounts = components["schemas"]["SessionQueueCountsResponse"];
export type ProjectionHealthCounts =
  components["schemas"]["ProjectionHealthCountsAggregateResponse"];
export type RuntimeSummary = components["schemas"]["WorkspaceRuntimeSummaryResponse"];
export type RuntimeContext = components["schemas"]["RuntimeContextSnapshot"];
export type LongRunStatus = components["schemas"]["LongRunStatusResponse"];
export type CheckpointAbsence = components["schemas"]["CheckpointAbsenceResponse"];
export type ProviderRecovery = components["schemas"]["ProviderRecoveryResponse"];
export type SessionAggregate = components["schemas"]["SessionAggregateResponse"];
export type SessionSnapshot = components["schemas"]["SessionSnapshotResponse"];
export type SessionSummary = components["schemas"]["OperatorSessionSummaryResponse"];
export type TaskCheckpoint = components["schemas"]["TaskCheckpointResponse"];
export type TranscriptMessage = components["schemas"]["TranscriptMessageResponse"];
export type ActiveToolCall = components["schemas"]["ActiveToolCallResponse"];
export type ToolAttempt = components["schemas"]["ToolAttemptResponse"];
export type PendingApproval = components["schemas"]["PendingApprovalResponse"] & {
  resolution_decision?: string | null;
  resolution_error?: string | null;
  resolution_state?: "idle" | "pending" | "failed" | "resolved";
};
export type TurnMetrics = components["schemas"]["TurnMetricsResponse"];
export type BranchableTurn = components["schemas"]["BranchableTurnResponse"];
export type ChildSession = components["schemas"]["ChildSessionSummaryResponse"];
export type PolicySummary = components["schemas"]["PolicyActivitySummaryResponse"];

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

export type WorkspaceAttentionLevel = "action" | "healthy" | "info" | "warning";

export type WorkspaceAttentionTarget =
  | { kind: "command"; command: string }
  | { kind: "none" }
  | { kind: "queue"; queue: string }
  | { kind: "session"; queue: string; sessionId: string };

export type WorkspaceAttentionSummary = {
  actionLabel: string;
  detail: string;
  kind:
    | "approval"
    | "failure"
    | "healthy"
    | "job"
    | "projection"
    | "provider"
    | "question"
    | "runtime";
  level: WorkspaceAttentionLevel;
  target: WorkspaceAttentionTarget;
  title: string;
};

export type SessionFields = {
  activeToolCalls: ActiveToolCall[];
  approvalMode: string | null;
  branchLabel: string | null;
  branchableTurns: BranchableTurn[];
  budgetPosture: components["schemas"]["AutonomyBudgetPostureRecord"] | null;
  canFork: boolean;
  checkpointAbsence: CheckpointAbsence | null;
  childSessions: ChildSession[];
  checkpointHistory: TaskCheckpoint[];
  currentTurn: CurrentTurn | null;
  currentTurnPolicySummary: PolicySummary | null;
  cwd: string | null;
  dashboardUrl: string | null;
  forkBlockedReason: string | null;
  forkedFromSequence: number | null;
  forkedFromTurnId: string | null;
  lastSequence: number;
  latestCheckpoint: TaskCheckpoint | null;
  latestProviderRecovery: ProviderRecovery | null;
  latestForkPointSequence: number | null;
  latestForkPointTurnId: string | null;
  longRunStatus: LongRunStatus | null;
  modelName: string | null;
  parentSessionId: string | null;
  pendingApprovalId: string | null;
  pendingApprovals: PendingApproval[];
  pendingQuestionId: string | null;
  pendingQuestionText: string | null;
  projectionHealth: ProjectionHealth | null;
  recentToolAttempts: ToolAttempt[];
  runtimeContext: RuntimeContext | null;
  selectedForkTurnId: string | null;
  sessionFailureMessage: string | null;
  sessionFailureRetryable: boolean | null;
  sessionId: string | null;
  sessionPolicySummary: PolicySummary | null;
  status: string;
  transcript: TranscriptMessage[];
  turnRecoveryPosture: components["schemas"]["TurnRecoveryPostureResponse"] | null;
  turnMetrics: TurnMetrics[];
};

export type ComparableSession = SessionFields & {
  createdAt: string | null;
  projectionHealth: ProjectionHealth | null;
  updatedAt: string | null;
};

export type DashboardState = SessionFields & {
  compareSession: ComparableSession | null;
  compareSessionId: string | null;
  eventLog: EventLogEntry[];
  liveOutput: LiveOutputEntry[];
  operatorQueue: OperatorQueueItem[];
  operatorQueueCounts: OperatorQueueCounts;
  operatorQueueSchemaVersion: string;
  projectionHealthCounts: ProjectionHealthCounts;
  providerEvidence: ProviderEvidence;
  knowledgePosture: KnowledgePosture | null;
  queueCounts: QueueCounts;
  runtimeSummary: RuntimeSummary;
  selectedQueue: string;
  selectedSessionId: string | null;
  sessionIndex: SessionSummary[];
  sessionIndexSort: string;
  workspaceAttention: WorkspaceAttentionSummary;
};
