import { Badge } from "@/components/ui/badge";
import { operatorIconSizeClass, operatorStatusTokens } from "@/design-system/operator-status";
import { buildAppRoute, type AppQueue } from "@/routing/app-route";
import type { ProjectionHealth, SessionSummary } from "@/state/session-state";
import type { ConsoleFilters } from "@/stores/dashboard-stores";

export function SessionAttentionRows({
  onSelectSession,
  selectedQueue,
  selectedSessionId,
  sessions,
}: {
  onSelectSession?: (sessionId: string) => void;
  selectedQueue: ConsoleFilters["queue"];
  selectedSessionId: string | null;
  sessions: SessionSummary[];
}) {
  return (
    <div className="grid gap-2" aria-label="Session attention rows">
      {sessions.map((session) => (
        <SessionAttentionRow
          key={session.session_id}
          onSelectSession={onSelectSession}
          selected={selectedSessionId === session.session_id}
          selectedQueue={selectedQueue}
          session={session}
        />
      ))}
    </div>
  );
}

function SessionAttentionRow({
  onSelectSession,
  selected,
  selectedQueue,
  session,
}: {
  onSelectSession?: (sessionId: string) => void;
  selected: boolean;
  selectedQueue: ConsoleFilters["queue"];
  session: SessionSummary;
}) {
  const status = sessionDescriptor(session);
  const StatusIcon = status.icon;
  const detail = attentionDetail(session);
  return (
    <a
      aria-current={selected ? "page" : undefined}
      className={`grid min-h-attention-row min-w-0 gap-3 rounded-md border border-border/80 bg-card p-4 text-card-foreground shadow-sm transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:grid-cols-[minmax(0,1fr)_auto] ${
        selected ? "border-primary bg-accent/60" : ""
      }`}
      data-state={selected ? "selected" : undefined}
      href={buildAppRoute({
        compareSessionId: null,
        queue: selectedQueue as AppQueue,
        selectedSessionId: session.session_id,
        tab: "overview",
      })}
      onClick={(event) => {
        if (onSelectSession === undefined) {
          return;
        }
        event.preventDefault();
        onSelectSession(session.session_id);
      }}
    >
      <div className="min-w-0">
        <p className="break-words text-base font-semibold tracking-normal">
          {session.next_action_summary || "Review session"}
        </p>
        <p className="mt-1 break-words text-sm text-muted-foreground">{detail}</p>
        <div className="mt-3 flex min-w-0 flex-wrap gap-2 text-xs text-muted-foreground">
          <span className="break-all rounded-md border border-border/70 bg-surface px-2 py-1 font-mono text-[0.75rem] text-foreground">
            {session.session_id}
          </span>
          <span className="rounded-md border border-border/70 bg-surface px-2 py-1">
            {actionabilityLabel(session)}
          </span>
          <span className="break-words rounded-md border border-border/70 bg-surface px-2 py-1">
            {lineageHint(session)}
          </span>
          <span className="break-words rounded-md border border-border/70 bg-surface px-2 py-1">
            {session.model_name ?? "unknown model"}
          </span>
          <span className="rounded-md border border-border/70 bg-surface px-2 py-1">
            updated {formatUpdatedAt(session.updated_at)}
          </span>
        </div>
      </div>

      <div className="flex min-w-0 flex-wrap items-start gap-2 sm:max-w-52 sm:justify-end">
        <Badge variant={status.badgeVariant}>
          <StatusIcon className={operatorIconSizeClass} aria-hidden="true" />
          {status.label}
        </Badge>
        <ProjectionBadge health={session.projection_health} />
      </div>
    </a>
  );
}

function ProjectionBadge({ health }: { health: ProjectionHealth | null }) {
  if (health === null) {
    return <Badge variant="muted">unknown</Badge>;
  }
  const variant = health.degraded || health.state !== "ok" ? "warning" : "success";
  return <Badge variant={variant}>{health.state}</Badge>;
}

function attentionDetail(session: SessionSummary): string {
  if (session.turn_recovery_posture != null) {
    const posture = session.turn_recovery_posture;
    const safeText =
      posture.safe_to_resume === true
        ? "exact resume safe"
        : posture.safe_to_resume === false
          ? "exact resume unsafe"
          : "resume safety unknown";
    return `Turn ${posture.turn_id}: ${posture.state}; ${safeText}. ${posture.reason ?? posture.next_action}`;
  }
  if (session.pending_approval_id !== null) {
    return `Approval ${session.pending_approval_id}: ${session.latest_message_summary ?? "review the requested action"}`;
  }
  if (session.pending_question_id !== null) {
    return `Question ${session.pending_question_text ?? session.pending_question_id}: answer before sending new prompts.`;
  }
  if (session.session_failure_message !== null) {
    return `${session.session_failure_retryable ? "Retryable failure" : "Failure"}: ${session.session_failure_message}`;
  }
  if (session.projection_health?.degraded || session.projection_health?.state !== "ok") {
    return `Projection ${session.projection_health?.state ?? "unknown"}: canonical events remain authoritative.`;
  }
  if (session.historical_only) {
    return session.latest_message_summary ?? "Historical snapshot is inspectable.";
  }
  return session.latest_message_summary ?? session.cwd ?? "Inspect the latest session state.";
}

function actionabilityLabel(session: SessionSummary): string {
  if (session.historical_only) {
    return "historical only";
  }
  return session.live_actionable ? "live actionable" : "inspect only";
}

function lineageHint(session: SessionSummary): string {
  if (session.branch_label !== null) {
    return `branch ${session.branch_label}`;
  }
  if (session.parent_session_id !== null) {
    return `parent ${session.parent_session_id}`;
  }
  if (session.child_session_count > 0) {
    return `${session.child_session_count} child sessions`;
  }
  if (session.latest_fork_point_turn_id !== null) {
    return "fork point available";
  }
  return "root session";
}

function formatUpdatedAt(value: string): string {
  return value
    .replace("T", " ")
    .replace(/\.\d+Z$/, "Z")
    .replace(/Z$/, " UTC");
}

function sessionDescriptor(session: SessionSummary) {
  if (
    session.turn_recovery_posture != null &&
    ["incomplete", "recoverable", "non_resumable", "abandoned"].includes(
      session.turn_recovery_posture.state,
    )
  ) {
    return operatorStatusTokens.actionNeeded;
  }
  if (session.session_failure_message !== null || session.status === "failed") {
    return operatorStatusTokens.failed;
  }
  if (session.pending_approval_id !== null) {
    return operatorStatusTokens.approval;
  }
  if (session.pending_question_id !== null) {
    return operatorStatusTokens.question;
  }
  if (session.action_needed) {
    return operatorStatusTokens.actionNeeded;
  }
  if (session.historical_only) {
    return operatorStatusTokens.historical;
  }
  if (session.projection_health?.degraded) {
    return operatorStatusTokens.degraded;
  }
  if (session.has_active_turn || session.status === "running") {
    return operatorStatusTokens.active;
  }
  return operatorStatusTokens.unknown;
}
