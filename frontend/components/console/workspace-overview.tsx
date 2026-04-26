import type { ComponentProps, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Database,
  RadioTower,
  RefreshCcw,
  Server,
  ShieldAlert,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { operatorIconSizeClass, operatorStatusTokens } from "@/design-system/operator-status";
import { buildAppRoute, type AppQueue } from "@/routing/app-route";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState, ProjectionHealth, SessionSummary } from "@/state/session-state";
import type { ConsoleFilters, LoadState } from "@/stores/dashboard-stores";

type QueueDescriptor = {
  countKey: keyof DashboardState["queueCounts"];
  description: string;
  label: string;
  queue: ConsoleFilters["queue"];
};

const queueDescriptors: QueueDescriptor[] = [
  {
    countKey: "total",
    description: "Every server-prioritized session row",
    label: "All",
    queue: "all",
  },
  {
    countKey: "approvals",
    description: "Commands waiting on explicit approval",
    label: "Approvals",
    queue: "approvals",
  },
  {
    countKey: "questions",
    description: "ask_user prompts awaiting an answer",
    label: "Questions",
    queue: "questions",
  },
  {
    countKey: "failures",
    description: "Failed sessions that may need recovery",
    label: "Failures",
    queue: "failures",
  },
  {
    countKey: "degraded",
    description: "Projection or runtime health needs attention",
    label: "Degraded",
    queue: "degraded",
  },
  {
    countKey: "active",
    description: "Live work with current or recent turns",
    label: "Active",
    queue: "active",
  },
  {
    countKey: "historical",
    description: "Recent completed or archived sessions",
    label: "Historical",
    queue: "historical",
  },
];

export type WorkspaceOverviewProps = {
  data: DashboardState;
  error: string | null;
  inspector?: ReactNode;
  loadState: LoadState;
  onRefresh?: () => void;
  onSelectQueue?: (queue: ConsoleFilters["queue"]) => void;
  onSelectSession?: (sessionId: string) => void;
  selectedQueue: ConsoleFilters["queue"];
  selectedSessionId?: string | null;
  stream?: SessionStreamState;
};

export function WorkspaceOverview({
  data,
  error,
  inspector,
  loadState,
  onRefresh,
  onSelectQueue,
  onSelectSession,
  selectedQueue,
  selectedSessionId = null,
  stream,
}: WorkspaceOverviewProps) {
  const hasRows = data.sessionIndex.length > 0;
  const hasSelectedInspector = inspector !== undefined && selectedSessionId !== null;

  return (
    <main className="min-h-screen bg-surface-subtle px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-5">
        <WorkspaceStatusRail
          data={data}
          error={error}
          loadState={loadState}
          onRefresh={onRefresh}
          selectedQueue={selectedQueue}
          selectedSessionId={selectedSessionId}
          stream={stream}
        />

        <section
          aria-label="Console frame"
          className="grid gap-4 xl:grid-cols-[20rem_minmax(0,1fr)]"
        >
          <aside className={`${hasSelectedInspector ? "hidden xl:flex" : "flex"} flex-col gap-4`}>
            <WorkspaceSummary data={data} loadState={loadState} />
            <QueueNavigation
              data={data}
              onSelectQueue={onSelectQueue}
              selectedQueue={selectedQueue}
            />
          </aside>

          <section className="flex min-w-0 flex-col gap-4">
            {hasSelectedInspector ? (
              <MobileReturnToQueues
                onSelectQueue={onSelectQueue}
                selectedQueue={selectedQueue}
                selectedSessionId={selectedSessionId}
              />
            ) : null}
            <div className={hasSelectedInspector ? "hidden xl:block" : undefined}>
              <QueueHeader
                data={data}
                error={error}
                loadState={loadState}
                selectedQueue={selectedQueue}
              />
            </div>
            <div
              className={
                inspector === undefined
                  ? "min-w-0"
                  : "grid min-w-0 gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(28rem,0.9fr)]"
              }
            >
              <div className={hasSelectedInspector ? "hidden min-w-0 xl:block" : "min-w-0"}>
                {error !== null ? (
                  <StatePanel
                    icon={ShieldAlert}
                    title="Workspace aggregate unavailable"
                    tone="destructive"
                    value={error}
                  />
                ) : loadState === "loading" && !hasRows ? (
                  <StatePanel
                    icon={RefreshCcw}
                    title="Loading workspace queues"
                    tone="info"
                    value="Fetching aggregate session state."
                  />
                ) : hasRows ? (
                  <SessionAttentionRows
                    onSelectSession={onSelectSession}
                    selectedQueue={selectedQueue}
                    selectedSessionId={selectedSessionId}
                    sessions={data.sessionIndex}
                  />
                ) : (
                  <StatePanel
                    icon={CheckCircle2}
                    title="No sessions in this queue"
                    tone="success"
                    value="There is no operator work matching the current filter."
                  />
                )}
              </div>
              {inspector}
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}

function MobileReturnToQueues({
  onSelectQueue,
  selectedQueue,
  selectedSessionId,
}: {
  onSelectQueue?: (queue: ConsoleFilters["queue"]) => void;
  selectedQueue: ConsoleFilters["queue"];
  selectedSessionId: string;
}) {
  const queue = queueDescriptor(selectedQueue);
  return (
    <a
      className="flex min-w-0 items-center justify-between gap-3 rounded-md border border-border/80 bg-card p-3 text-sm font-medium text-card-foreground shadow-sm hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring xl:hidden"
      href={buildAppRoute({
        compareSessionId: null,
        queue: selectedQueue as AppQueue,
        selectedSessionId: null,
        tab: "overview",
      })}
      onClick={(event) => {
        if (onSelectQueue === undefined) {
          return;
        }
        event.preventDefault();
        onSelectQueue(selectedQueue);
      }}
    >
      <span className="flex min-w-0 items-center gap-2">
        <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="truncate">Back to {queue.label} queue</span>
      </span>
      <Badge className="max-w-[12rem] justify-start" variant="info">
        <span className="truncate">{selectedSessionId}</span>
      </Badge>
    </a>
  );
}

function WorkspaceStatusRail({
  data,
  error,
  loadState,
  onRefresh,
  selectedQueue,
  selectedSessionId,
  stream,
}: {
  data: DashboardState;
  error: string | null;
  loadState: LoadState;
  onRefresh?: () => void;
  selectedQueue: ConsoleFilters["queue"];
  selectedSessionId: string | null;
  stream?: SessionStreamState;
}) {
  const runtime = runtimeDescriptor(data.runtimeSummary.state, data.runtimeSummary.health);
  const RuntimeIcon = runtime.icon;
  const projection = projectionSummaryDescriptor(data);
  const ProjectionIcon = projection.icon;
  const streamStatus = streamDescriptor(stream, selectedSessionId);
  const StreamIcon = streamStatus.icon;
  const refresh = refreshDescriptor(loadState, error);
  const RefreshIcon = refresh.icon;

  return (
    <header
      className="rounded-lg border border-border/80 bg-card px-4 py-3 text-card-foreground shadow-sm"
      aria-label="Workspace status rail"
      aria-live="polite"
    >
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-medium text-muted-foreground">Glassbox</p>
          <h1 className="mt-0.5 text-2xl font-semibold tracking-normal">Operator Console</h1>
          <p className="mt-1 break-all text-sm text-muted-foreground">
            {data.runtimeSummary.workspace_root || "Local workspace"}
          </p>
        </div>

        <div className="grid min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:min-w-[44rem]">
          <RailFact
            icon={RuntimeIcon}
            label="Runtime owner"
            value={runtime.label}
            variant={runtime.variant}
          />
          <RailFact
            icon={ProjectionIcon}
            label="Projection health"
            value={projection.label}
            variant={projection.variant}
          />
          <RailFact
            icon={StreamIcon}
            label="Browser stream"
            value={streamStatus.label}
            variant={streamStatus.variant}
          />
          <RailFact
            icon={RefreshIcon}
            label="Last refresh"
            value={refresh.label}
            variant={refresh.variant}
          />
        </div>
      </div>

      <Separator className="my-3" />

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 flex-wrap items-center gap-2 text-sm">
          <Badge variant="outline">Queue {selectedQueue}</Badge>
          <Badge
            className="max-w-full justify-start"
            variant={selectedSessionId ? "info" : "muted"}
          >
            <span className="truncate">
              {selectedSessionId ? `Session ${selectedSessionId}` : "No session selected"}
            </span>
          </Badge>
          {data.queueCounts.action_needed > 0 ? (
            <Badge variant="warning">{data.queueCounts.action_needed} actions</Badge>
          ) : (
            <Badge variant="success">No blocking actions</Badge>
          )}
        </div>
        <Button
          aria-label="Refresh workspace"
          className="w-full justify-center md:w-auto"
          onClick={onRefresh}
          size="sm"
          type="button"
          variant="outline"
        >
          <RefreshCcw className="h-4 w-4" aria-hidden="true" />
          Refresh
        </Button>
      </div>
    </header>
  );
}

function RailFact({
  icon: Icon,
  label,
  value,
  variant,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  variant: NonNullable<ComponentProps<typeof Badge>["variant"]>;
}) {
  return (
    <div className="min-h-16 rounded-md border border-border/70 bg-surface p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <Badge className="mt-2 max-w-full justify-start" variant={variant}>
        <Icon className={operatorIconSizeClass} aria-hidden="true" />
        <span className="truncate">{value}</span>
      </Badge>
    </div>
  );
}

function WorkspaceSummary({ data, loadState }: { data: DashboardState; loadState: LoadState }) {
  return (
    <section
      className="rounded-md border border-border/80 bg-card p-4 text-card-foreground shadow-sm"
      aria-label="Workspace overview"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
            Workspace
          </h2>
          <p className="mt-1 break-all text-sm font-medium">
            {data.runtimeSummary.workspace_root || "Local workspace"}
          </p>
        </div>
        <Badge variant={loadState === "failed" ? "destructive" : "outline"}>{loadState}</Badge>
      </div>
      <Separator className="my-3" />
      <div className="grid grid-cols-2 gap-2">
        <MetricTile label="Total" value={data.queueCounts.total} />
        <MetricTile label="Action" value={data.queueCounts.action_needed} variant="warning" />
        <MetricTile label="Approvals" value={data.queueCounts.approvals} />
        <MetricTile label="Questions" value={data.queueCounts.questions} />
      </div>
    </section>
  );
}

function MetricTile({
  label,
  value,
  variant = "outline",
}: {
  label: string;
  value: number | string;
  variant?: "outline" | "success" | "warning";
}) {
  return (
    <div className="min-h-16 rounded-md border border-border/70 bg-surface p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <Badge className="mt-2 justify-start" variant={variant}>
        {value}
      </Badge>
    </div>
  );
}

function QueueNavigation({
  data,
  onSelectQueue,
  selectedQueue,
}: {
  data: DashboardState;
  onSelectQueue?: (queue: ConsoleFilters["queue"]) => void;
  selectedQueue: ConsoleFilters["queue"];
}) {
  const priority = queuePrioritySummary(data);
  const PriorityIcon = priority.icon;
  return (
    <nav
      className="rounded-md border border-border/80 bg-card p-3 text-card-foreground shadow-sm"
      aria-label="Action queues"
    >
      <div className="mb-2 flex items-center justify-between gap-3 px-1">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          Queues
        </h2>
        <Badge variant="muted">{data.queueCounts.total}</Badge>
      </div>
      <section
        className="mb-3 rounded-md border border-border/70 bg-surface p-3"
        aria-label="Queue priority summary"
      >
        <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
          Top priority
        </p>
        <Badge className="mt-2 max-w-full justify-start" variant={priority.variant}>
          <PriorityIcon className={operatorIconSizeClass} aria-hidden="true" />
          <span className="truncate">{priority.label}</span>
        </Badge>
        <p className="mt-2 text-xs text-muted-foreground">{priority.description}</p>
      </section>
      <div className="grid gap-1">
        {queueDescriptors.map((queue) => {
          const selected = selectedQueue === queue.queue;
          const count = data.queueCounts[queue.countKey];
          return (
            <a
              aria-current={selected ? "page" : undefined}
              className={`grid min-h-density-row rounded-md px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                selected ? "bg-accent text-accent-foreground" : "hover:bg-surface-raised"
              }`}
              href={buildAppRoute({
                compareSessionId: null,
                queue: queue.queue as AppQueue,
                selectedSessionId: null,
                tab: "overview",
              })}
              key={queue.queue}
              onClick={(event) => {
                if (onSelectQueue === undefined) {
                  return;
                }
                event.preventDefault();
                onSelectQueue(queue.queue);
              }}
            >
              <span className="flex items-center justify-between gap-3 text-sm font-medium">
                {queue.label}
                <Badge variant={count > 0 ? "warning" : "muted"}>{count}</Badge>
              </span>
              <span className="mt-1 text-xs text-muted-foreground">{queue.description}</span>
            </a>
          );
        })}
      </div>
    </nav>
  );
}

function QueueHeader({
  data,
  error,
  loadState,
  selectedQueue,
}: {
  data: DashboardState;
  error: string | null;
  loadState: LoadState;
  selectedQueue: ConsoleFilters["queue"];
}) {
  const queue = queueDescriptor(selectedQueue);
  const count = data.queueCounts[queue.countKey];
  const hiddenCount = Math.max(data.queueCounts.total - count, 0);
  return (
    <section
      className="rounded-md border border-border/80 bg-card p-4 text-card-foreground shadow-sm"
      aria-label="Queue status"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-normal">{queue.label} sessions</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Showing {count} of {data.queueCounts.total} server-prioritized sessions.
            {hiddenCount > 0 ? ` ${hiddenCount} rows are hidden by the current queue filter.` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={error === null ? "outline" : "destructive"}>{loadState}</Badge>
          <Badge variant={count > 0 ? "info" : "muted"}>{count} shown</Badge>
          <Badge variant={data.queueCounts.action_needed > 0 ? "warning" : "success"}>
            {data.queueCounts.action_needed} actions
          </Badge>
        </div>
      </div>
    </section>
  );
}

function SessionAttentionRows({
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

function queueDescriptor(queue: ConsoleFilters["queue"]): QueueDescriptor {
  return queueDescriptors.find((descriptor) => descriptor.queue === queue) ?? queueDescriptors[0];
}

function queuePrioritySummary(data: DashboardState) {
  if (data.queueCounts.approvals > 0) {
    return {
      description: "Review approval risk before prompts, forks, or passive evidence.",
      icon: operatorStatusTokens.approval.icon,
      label: `${data.queueCounts.approvals} approvals`,
      variant: "warning" as const,
    };
  }
  if (data.queueCounts.questions > 0) {
    return {
      description: "Answer pending ask_user questions before sending new prompts.",
      icon: operatorStatusTokens.question.icon,
      label: `${data.queueCounts.questions} questions`,
      variant: "info" as const,
    };
  }
  if (data.queueCounts.failures > 0) {
    return {
      description: "Inspect retryability and failure summaries before lower-priority work.",
      icon: operatorStatusTokens.failed.icon,
      label: `${data.queueCounts.failures} failures`,
      variant: "destructive" as const,
    };
  }
  if (data.queueCounts.degraded > 0) {
    return {
      description: "Projection health needs attention; canonical events remain authoritative.",
      icon: operatorStatusTokens.degraded.icon,
      label: `${data.queueCounts.degraded} degraded`,
      variant: "warning" as const,
    };
  }
  if (data.queueCounts.active > 0) {
    return {
      description: "Active work is available after urgent queues are clear.",
      icon: operatorStatusTokens.active.icon,
      label: `${data.queueCounts.active} active`,
      variant: "success" as const,
    };
  }
  if (data.queueCounts.historical > 0) {
    return {
      description: "Only historical snapshots remain for inspection.",
      icon: operatorStatusTokens.historical.icon,
      label: `${data.queueCounts.historical} historical`,
      variant: "muted" as const,
    };
  }
  return {
    description: "All queues are clear for this workspace.",
    icon: CheckCircle2,
    label: "queues clear",
    variant: "success" as const,
  };
}

function attentionDetail(session: SessionSummary): string {
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

function StatePanel({
  icon: Icon,
  title,
  tone,
  value,
}: {
  icon: LucideIcon;
  title: string;
  tone: "destructive" | "info" | "success";
  value: string;
}) {
  return (
    <section className="grid min-h-80 place-items-center rounded-md border border-border/80 bg-card p-8 text-center text-card-foreground shadow-sm">
      <div className="max-w-sm">
        <Badge variant={tone === "destructive" ? "destructive" : tone}>
          <Icon className={operatorIconSizeClass} aria-hidden="true" />
          {title}
        </Badge>
        <p className="mt-4 text-sm text-muted-foreground">{value}</p>
      </div>
    </section>
  );
}

function sessionDescriptor(session: SessionSummary) {
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

function runtimeDescriptor(state: string, health: string | null) {
  if (state === "running") {
    return { icon: Server, label: "runtime online", variant: "success" as const };
  }
  if (state === "degraded" || health === "degraded") {
    return { icon: AlertTriangle, label: "runtime degraded", variant: "warning" as const };
  }
  return { icon: Activity, label: "runtime offline", variant: "muted" as const };
}

function projectionSummaryDescriptor(data: DashboardState) {
  const counts = data.projectionHealthCounts;
  if (counts.unavailable > 0) {
    return {
      icon: ShieldAlert,
      label: `${counts.unavailable} projection missing`,
      variant: "destructive" as const,
    };
  }
  const degraded = counts.degraded + counts.stale;
  if (degraded > 0) {
    return {
      icon: AlertTriangle,
      label: `${degraded} projection alerts`,
      variant: "warning" as const,
    };
  }
  return { icon: Database, label: "projection fresh", variant: "success" as const };
}

function streamDescriptor(
  stream: SessionStreamState | undefined,
  selectedSessionId: string | null,
) {
  if (selectedSessionId === null) {
    return { icon: RadioTower, label: "no session selected", variant: "muted" as const };
  }
  if (stream === undefined) {
    return { icon: RadioTower, label: "stream idle", variant: "muted" as const };
  }
  if (stream.status === "live") {
    return { icon: RadioTower, label: "stream live", variant: "success" as const };
  }
  if (stream.status === "connecting" || stream.status === "reconnecting") {
    return {
      icon: RefreshCcw,
      label: stream.status.replaceAll("_", " "),
      variant: "info" as const,
    };
  }
  return {
    icon: AlertTriangle,
    label: stream.status.replaceAll("_", " "),
    variant: stream.status === "historical_snapshot" ? ("muted" as const) : ("warning" as const),
  };
}

function refreshDescriptor(loadState: LoadState, error: string | null) {
  if (error !== null || loadState === "failed") {
    return { icon: ShieldAlert, label: "refresh failed", variant: "destructive" as const };
  }
  if (loadState === "loading") {
    return { icon: RefreshCcw, label: "refreshing", variant: "info" as const };
  }
  if (loadState === "loaded") {
    return { icon: CheckCircle2, label: "aggregate loaded", variant: "success" as const };
  }
  return { icon: Activity, label: "not loaded", variant: "muted" as const };
}
