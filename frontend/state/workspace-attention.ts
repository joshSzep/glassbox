import type {
  DashboardState,
  SessionSummary,
  WorkspaceAttentionSummary,
} from "@/state/session-types";

export function createHealthyWorkspaceAttentionSummary(): WorkspaceAttentionSummary {
  return {
    actionLabel: "View workspace",
    detail:
      "No approvals, questions, failures, degraded projections, or recovery cues need attention.",
    kind: "healthy",
    level: "healthy",
    target: { kind: "none" },
    title: "No workspace action needed",
  };
}

export function buildWorkspaceAttentionSummary(data: DashboardState): WorkspaceAttentionSummary {
  const approval = findSession(
    data.sessionIndex,
    (session) => hasQueue(session, "approvals") || session.pending_approval_id !== null,
  );
  if (approval !== undefined) {
    return {
      actionLabel: "Open session",
      detail: approval.next_action_summary || `Review approval ${approval.pending_approval_id}.`,
      kind: "approval",
      level: "action",
      target: { kind: "session", queue: "approvals", sessionId: approval.session_id },
      title: "Approval needed",
    };
  }

  const question = findSession(
    data.sessionIndex,
    (session) => hasQueue(session, "questions") || session.pending_question_id !== null,
  );
  if (question !== undefined) {
    return {
      actionLabel: "Open question",
      detail:
        question.next_action_summary ||
        question.pending_question_text ||
        "Answer the blocked turn.",
      kind: "question",
      level: "action",
      target: { kind: "session", queue: "questions", sessionId: question.session_id },
      title: "Answer needed",
    };
  }

  const failure = findSession(
    data.sessionIndex,
    (session) =>
      hasQueue(session, "failures") ||
      session.status === "failed" ||
      session.session_failure_message !== null,
  );
  if (failure !== undefined) {
    return {
      actionLabel: "Inspect failure",
      detail: failure.session_failure_message || failure.next_action_summary,
      kind: "failure",
      level: failure.session_failure_retryable ? "action" : "warning",
      target: { kind: "session", queue: "failures", sessionId: failure.session_id },
      title: failure.session_failure_retryable ? "Retryable failure" : "Failure needs review",
    };
  }

  const retryableJobs = data.runtimeSummary.background_job_retryable_count ?? 0;
  if (retryableJobs > 0) {
    return {
      actionLabel: "List retryable jobs",
      detail: `${retryableJobs} background job${retryableJobs === 1 ? "" : "s"} can be inspected for retry.`,
      kind: "job",
      level: "warning",
      target: { command: "uv run glassbox job list --state failed --cwd .", kind: "command" },
      title: "Retryable background job",
    };
  }

  const failedJobs = data.runtimeSummary.background_job_failed_count ?? 0;
  if (failedJobs > 0) {
    return {
      actionLabel: "List failed jobs",
      detail: `${failedJobs} background job${failedJobs === 1 ? "" : "s"} failed; inspect before continuing related work.`,
      kind: "job",
      level: "warning",
      target: { command: "uv run glassbox job list --state failed --cwd .", kind: "command" },
      title: "Background job failure",
    };
  }

  const degradedProjection = findSession(
    data.sessionIndex,
    (session) => hasQueue(session, "degraded") || session.projection_health.degraded,
  );
  const projectionAlerts =
    data.projectionHealthCounts.unavailable +
    data.projectionHealthCounts.degraded +
    data.projectionHealthCounts.stale;
  if (projectionAlerts > 0 || degradedProjection !== undefined) {
    return {
      actionLabel: degradedProjection === undefined ? "Check projections" : "Open degraded queue",
      detail:
        degradedProjection?.projection_health.detail ||
        `${projectionAlerts} projection health alert${projectionAlerts === 1 ? "" : "s"} can make dashboard summaries stale.`,
      kind: "projection",
      level: data.projectionHealthCounts.unavailable > 0 ? "action" : "warning",
      target:
        degradedProjection === undefined
          ? { command: "uv run glassbox projection check --all --cwd .", kind: "command" }
          : { kind: "queue", queue: "degraded" },
      title:
        data.projectionHealthCounts.unavailable > 0
          ? "Projection unavailable"
          : "Projection attention",
    };
  }

  if (data.runtimeSummary.state === "degraded" || data.runtimeSummary.health === "degraded") {
    return {
      actionLabel: "Check daemon",
      detail:
        "The workspace runtime reports degraded health; inspect daemon state before relying on live updates.",
      kind: "runtime",
      level: "warning",
      target: { command: "uv run glassbox daemon status --cwd .", kind: "command" },
      title: "Runtime degraded",
    };
  }

  return createHealthyWorkspaceAttentionSummary();
}

function findSession(
  sessions: SessionSummary[],
  predicate: (session: SessionSummary) => boolean,
): SessionSummary | undefined {
  return sessions.find(predicate);
}

function hasQueue(session: SessionSummary, queue: string): boolean {
  return session.queue_memberships.includes(queue);
}
