import { createDashboardState, createEmptyProviderEvidence } from "@/state/session-initial-state";
import type {
  BranchableTurn,
  ComparableSession,
  CurrentTurn,
  DashboardState,
  RuntimeContext,
  SessionAggregate,
  SessionFields,
  SessionSnapshot,
} from "@/state/session-types";
import { buildWorkspaceAttentionSummary } from "@/state/workspace-attention";

export function hydrateSessionAggregate(
  state: DashboardState,
  aggregate: SessionAggregate,
): DashboardState {
  const nextState = {
    ...state,
    projectionHealthCounts: { ...aggregate.projection_health_counts },
    providerEvidence: {
      ...createEmptyProviderEvidence(),
      ...(aggregate.provider_evidence ?? {}),
      missing_scenarios: [...(aggregate.provider_evidence?.missing_scenarios ?? [])],
      next_actions: [...(aggregate.provider_evidence?.next_actions ?? [])],
    },
    queueCounts: { ...aggregate.queue_counts },
    runtimeSummary: { ...aggregate.runtime },
    selectedQueue: aggregate.queue ?? state.selectedQueue,
    sessionIndex: [...aggregate.sessions],
    sessionIndexSort: aggregate.sort,
  };
  return {
    ...nextState,
    workspaceAttention: buildWorkspaceAttentionSummary(nextState),
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

function normalizeSessionFields(snapshot: SessionSnapshot): SessionFields {
  const branchableTurns = [...snapshot.branchable_turns].sort(
    (left, right) => right.sequence - left.sequence,
  );
  return {
    activeToolCalls: [...snapshot.active_tool_calls],
    approvalMode: snapshot.approval_mode,
    branchLabel: snapshot.branch_label,
    branchableTurns,
    budgetPosture: snapshot.budget_posture ?? null,
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
    longRunStatus: snapshot.long_run_status ?? null,
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
    recentToolAttempts: [...(snapshot.recent_tool_attempts ?? [])],
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
    context_compactions: runtimeContext.context_compactions
      ? {
          ...runtimeContext.context_compactions,
          items: [...(runtimeContext.context_compactions.items ?? [])],
          stale_items: [...(runtimeContext.context_compactions.stale_items ?? [])],
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
