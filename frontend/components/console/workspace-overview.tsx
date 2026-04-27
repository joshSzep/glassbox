import type { ReactNode } from "react";
import { ArrowLeft, CheckCircle2, RefreshCcw, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { QueueNavigation } from "@/components/console/workspace-overview/queue-navigation";
import { queueDescriptor } from "@/components/console/workspace-overview/queue-descriptors";
import { SessionAttentionRows } from "@/components/console/workspace-overview/session-attention-rows";
import { StatePanel } from "@/components/console/workspace-overview/state-panel";
import { WorkspaceStatusRail } from "@/components/console/workspace-overview/workspace-status-rail";
import { WorkspaceSummary } from "@/components/console/workspace-overview/workspace-summary";
import { buildAppRoute, type AppQueue } from "@/routing/app-route";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState } from "@/state/session-state";
import type { ConsoleFilters, LoadState } from "@/stores/dashboard-stores";

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
