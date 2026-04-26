import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  RefreshCcw,
  Server,
  ShieldAlert,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { operatorIconSizeClass, operatorStatusTokens } from "@/design-system/operator-status";
import { buildAppRoute, type AppQueue } from "@/routing/app-route";
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
  loadState: LoadState;
  onRefresh?: () => void;
  onSelectQueue?: (queue: ConsoleFilters["queue"]) => void;
  selectedQueue: ConsoleFilters["queue"];
};

export function WorkspaceOverview({
  data,
  error,
  loadState,
  onRefresh,
  onSelectQueue,
  selectedQueue,
}: WorkspaceOverviewProps) {
  const runtime = runtimeDescriptor(data.runtimeSummary.state);
  const RuntimeIcon = runtime.icon;
  const hasRows = data.sessionIndex.length > 0;

  return (
    <main className="min-h-screen bg-background px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-5">
        <header className="flex flex-col gap-3 border-b pb-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Glassbox</p>
            <h1 className="text-2xl font-semibold tracking-normal">Operator Console</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant={runtime.variant}>
              <RuntimeIcon className={operatorIconSizeClass} aria-hidden="true" />
              {runtime.label}
            </Badge>
            <Button
              aria-label="Refresh workspace"
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

        <section className="grid gap-4 xl:grid-cols-[20rem_minmax(0,1fr)]">
          <aside className="flex flex-col gap-4">
            <WorkspaceSummary data={data} loadState={loadState} />
            <QueueNavigation
              data={data}
              onSelectQueue={onSelectQueue}
              selectedQueue={selectedQueue}
            />
          </aside>

          <section className="flex min-w-0 flex-col gap-4">
            <QueueHeader
              data={data}
              error={error}
              loadState={loadState}
              selectedQueue={selectedQueue}
            />
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
              <SessionQueueTable sessions={data.sessionIndex} selectedQueue={selectedQueue} />
            ) : (
              <StatePanel
                icon={CheckCircle2}
                title="No sessions in this queue"
                tone="success"
                value="There is no operator work matching the current filter."
              />
            )}
          </section>
        </section>
      </div>
    </main>
  );
}

function WorkspaceSummary({ data, loadState }: { data: DashboardState; loadState: LoadState }) {
  const degradedCount = data.projectionHealthCounts.degraded + data.projectionHealthCounts.stale;
  return (
    <section
      className="rounded-lg border bg-card p-4 text-card-foreground shadow-sm"
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
        <MetricTile
          label="Projection"
          value={degradedCount}
          variant={degradedCount > 0 ? "warning" : "success"}
        />
        <MetricTile label="Runtime" value={runtimeShortLabel(data.runtimeSummary.state)} />
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
    <div className="min-h-16 rounded-md border bg-background p-3">
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
  return (
    <nav
      className="rounded-lg border bg-card p-3 text-card-foreground shadow-sm"
      aria-label="Action queues"
    >
      <div className="mb-2 flex items-center justify-between gap-3 px-1">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          Queues
        </h2>
        <Badge variant="muted">{data.queueCounts.total}</Badge>
      </div>
      <div className="grid gap-1">
        {queueDescriptors.map((queue) => {
          const selected = selectedQueue === queue.queue;
          const count = data.queueCounts[queue.countKey];
          return (
            <a
              aria-current={selected ? "page" : undefined}
              className={`grid min-h-14 rounded-md px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                selected ? "bg-accent text-accent-foreground" : "hover:bg-muted"
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
  const queueLabel =
    queueDescriptors.find((queue) => queue.queue === selectedQueue)?.label ?? "All";
  const degraded = data.projectionHealthCounts.degraded + data.projectionHealthCounts.stale;
  return (
    <section
      className="rounded-lg border bg-card p-4 text-card-foreground shadow-sm"
      aria-label="Queue status"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-normal">{queueLabel} sessions</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Server-prioritized aggregate rows from the selected queue.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={error === null ? "outline" : "destructive"}>{loadState}</Badge>
          <Badge variant={degraded > 0 ? "warning" : "success"}>{degraded} degraded</Badge>
        </div>
      </div>
    </section>
  );
}

function SessionQueueTable({
  selectedQueue,
  sessions,
}: {
  selectedQueue: ConsoleFilters["queue"];
  sessions: SessionSummary[];
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Session</TableHead>
          <TableHead>Next action</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Projection</TableHead>
          <TableHead>Model</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sessions.map((session) => (
          <SessionQueueRow
            key={session.session_id}
            selectedQueue={selectedQueue}
            session={session}
          />
        ))}
      </TableBody>
    </Table>
  );
}

function SessionQueueRow({
  selectedQueue,
  session,
}: {
  selectedQueue: ConsoleFilters["queue"];
  session: SessionSummary;
}) {
  const status = sessionDescriptor(session);
  const StatusIcon = status.icon;
  return (
    <TableRow>
      <TableCell className="min-w-64">
        <a
          className="font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          href={buildAppRoute({
            compareSessionId: null,
            queue: selectedQueue as AppQueue,
            selectedSessionId: session.session_id,
            tab: "overview",
          })}
        >
          {session.session_id}
        </a>
        <p className="mt-1 line-clamp-2 max-w-xl text-xs text-muted-foreground">
          {session.latest_message_summary ?? session.cwd ?? "No recent message"}
        </p>
      </TableCell>
      <TableCell className="min-w-56 text-sm">
        {session.next_action_summary ?? "Review session"}
      </TableCell>
      <TableCell>
        <Badge variant={status.badgeVariant}>
          <StatusIcon className={operatorIconSizeClass} aria-hidden="true" />
          {status.label}
        </Badge>
      </TableCell>
      <TableCell>
        <ProjectionBadge health={session.projection_health} />
      </TableCell>
      <TableCell className="text-sm text-muted-foreground">
        {session.model_name ?? "unknown"}
      </TableCell>
    </TableRow>
  );
}

function ProjectionBadge({ health }: { health: ProjectionHealth | null }) {
  if (health === null) {
    return <Badge variant="muted">unknown</Badge>;
  }
  const variant = health.degraded || health.state !== "ok" ? "warning" : "success";
  return <Badge variant={variant}>{health.state}</Badge>;
}

function StatePanel({
  icon: Icon,
  title,
  tone,
  value,
}: {
  icon: typeof AlertTriangle;
  title: string;
  tone: "destructive" | "info" | "success";
  value: string;
}) {
  return (
    <section className="grid min-h-80 place-items-center rounded-lg border bg-card p-8 text-center text-card-foreground shadow-sm">
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

function runtimeDescriptor(state: string) {
  if (state === "running") {
    return { icon: Server, label: "runtime online", variant: "success" as const };
  }
  if (state === "degraded") {
    return { icon: AlertTriangle, label: "runtime degraded", variant: "warning" as const };
  }
  return { icon: Activity, label: "runtime offline", variant: "muted" as const };
}

function runtimeShortLabel(state: string): string {
  return state.replaceAll("_", " ");
}
