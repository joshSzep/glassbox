import type { ComponentProps } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  Brain,
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
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState } from "@/state/session-state";
import type { ConsoleFilters, LoadState } from "@/stores/dashboard-stores";

export function WorkspaceStatusRail({
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
  const knowledge = knowledgePostureDescriptor(data);
  const KnowledgeIcon = knowledge.icon;
  const backgroundJobs = backgroundJobDescriptor(data);
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

        <div className="grid min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-5 xl:min-w-[52rem]">
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
            icon={KnowledgeIcon}
            label="Knowledge posture"
            value={knowledge.label}
            variant={knowledge.variant}
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
          <Badge variant={backgroundJobs.variant}>{backgroundJobs.label}</Badge>
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

function knowledgePostureDescriptor(data: DashboardState) {
  const status = data.knowledgePosture?.overall_status ?? "missing";
  if (status === "degraded") {
    return { icon: AlertTriangle, label: "knowledge degraded", variant: "warning" as const };
  }
  if (status === "stale" || status === "invalidated") {
    return { icon: RefreshCcw, label: `knowledge ${status}`, variant: "warning" as const };
  }
  if (status === "missing" || status === "historical-only") {
    return { icon: Brain, label: `knowledge ${status}`, variant: "muted" as const };
  }
  if (status === "advisory") {
    return { icon: Brain, label: "knowledge advisory", variant: "info" as const };
  }
  return { icon: Brain, label: "knowledge fresh", variant: "success" as const };
}

function backgroundJobDescriptor(data: DashboardState) {
  const failed = data.runtimeSummary.background_job_failed_count ?? 0;
  const retryable = data.runtimeSummary.background_job_retryable_count ?? 0;
  const abandoned = data.runtimeSummary.background_job_abandoned_count ?? 0;
  if (retryable > 0) {
    return {
      label: `${retryable} retryable job${retryable === 1 ? "" : "s"}`,
      variant: "warning" as const,
    };
  }
  if (failed > 0) {
    return {
      label: `${failed} failed job${failed === 1 ? "" : "s"}`,
      variant: "destructive" as const,
    };
  }
  if (abandoned > 0) {
    return {
      label: `${abandoned} abandoned job${abandoned === 1 ? "" : "s"}`,
      variant: "muted" as const,
    };
  }
  return { label: "Jobs healthy", variant: "success" as const };
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
  if (stream.deliveryMode === "replaying_history") {
    return { icon: RefreshCcw, label: "stream replaying history", variant: "info" as const };
  }
  if (stream.deliveryMode === "degraded") {
    return { icon: AlertTriangle, label: "stream degraded", variant: "warning" as const };
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
