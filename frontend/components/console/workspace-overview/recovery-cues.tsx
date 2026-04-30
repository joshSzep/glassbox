import { AlertTriangle, CheckCircle2, TerminalSquare } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { DashboardState } from "@/state/session-state";

type RecoveryCue = {
  commands: string[];
  detail: string;
  label: string;
  state: string;
  tone: "info" | "muted" | "success" | "warning";
};

export function RecoveryCues({ data }: { data: DashboardState }) {
  const cues = recoveryCues(data);
  const activeCueCount = cues.filter((cue) => cue.tone === "warning").length;

  return (
    <section
      aria-label="Recovery cues"
      className="rounded-md border border-border/80 bg-card p-3 text-card-foreground shadow-sm"
    >
      <div className="mb-2 flex items-center justify-between gap-3 px-1">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          Recovery Cues
        </h2>
        <Badge variant={activeCueCount > 0 ? "warning" : "success"}>
          {activeCueCount > 0 ? `${activeCueCount} active` : "read-only"}
        </Badge>
      </div>
      <DataList density="compact">
        {cues.map((cue) => (
          <DataListItem key={cue.label}>
            <DataListLabel className="flex items-center gap-2">
              {cue.tone === "warning" ? (
                <AlertTriangle className={operatorIconSizeClass} aria-hidden="true" />
              ) : cue.tone === "success" ? (
                <CheckCircle2 className={operatorIconSizeClass} aria-hidden="true" />
              ) : (
                <TerminalSquare className={operatorIconSizeClass} aria-hidden="true" />
              )}
              {cue.label}
            </DataListLabel>
            <DataListMeta>
              <Badge className="mr-2" variant={cue.tone}>
                {cue.state}
              </Badge>
              {cue.detail}
            </DataListMeta>
            {cue.commands.map((command) => (
              <code
                className="mt-1 block overflow-x-auto rounded-md border border-border/70 bg-surface-raised px-2 py-1 text-xs text-muted-foreground first:mt-0"
                key={command}
              >
                {command}
              </code>
            ))}
          </DataListItem>
        ))}
      </DataList>
    </section>
  );
}

function recoveryCues(data: DashboardState): RecoveryCue[] {
  const projectionAlerts =
    data.projectionHealthCounts.unavailable +
    data.projectionHealthCounts.degraded +
    data.projectionHealthCounts.stale;
  const retryableJobs = data.runtimeSummary.background_job_retryable_count ?? 0;
  const failedJobs = data.runtimeSummary.background_job_failed_count ?? 0;
  const abandonedJobs = data.runtimeSummary.background_job_abandoned_count ?? 0;
  const runtimeUnhealthy =
    data.runtimeSummary.state === "degraded" || data.runtimeSummary.health === "degraded";
  const runtimeOffline = data.runtimeSummary.state !== "running" && data.queueCounts.total > 0;

  return [
    {
      commands: ["uv run glassbox daemon status --cwd ."],
      detail: runtimeUnhealthy
        ? "Runtime owner health is degraded; inspect owner metadata and logs before acting on live state."
        : runtimeOffline
          ? "Sessions exist but no running runtime owner is reported; inspect before expecting live updates."
          : "Inspect runtime ownership, dashboard URL, health URL, owner metadata, and logs.",
      label: "Daemon state",
      state: runtimeUnhealthy ? "degraded" : runtimeOffline ? "offline" : "check",
      tone: runtimeUnhealthy || runtimeOffline ? "warning" : "info",
    },
    {
      commands: ["uv run glassbox projection check --all --cwd ."],
      detail:
        projectionAlerts > 0
          ? `${projectionAlerts} projection health alert${projectionAlerts === 1 ? "" : "s"} can make dashboard summaries stale.`
          : "Confirm derived projections still match canonical event sequences.",
      label: "Projection health",
      state: projectionAlerts > 0 ? "attention" : "healthy",
      tone: projectionAlerts > 0 ? "warning" : "success",
    },
    {
      commands: ["uv run glassbox job list --state failed --cwd ."],
      detail:
        retryableJobs + failedJobs + abandonedJobs > 0
          ? `${retryableJobs} retryable, ${failedJobs} failed, and ${abandonedJobs} abandoned background job${retryableJobs + failedJobs + abandonedJobs === 1 ? "" : "s"} need inspection.`
          : "List failed background jobs before retrying or abandoning work.",
      label: "Background jobs",
      state: retryableJobs + failedJobs + abandonedJobs > 0 ? "attention" : "check",
      tone: retryableJobs + failedJobs + abandonedJobs > 0 ? "warning" : "info",
    },
    {
      commands: ["uv run glassbox repo index status --cwd ."],
      detail:
        "Check whether rebuildable repository intelligence is fresh, stale, missing, or failed.",
      label: "Repository index",
      state: "safe check",
      tone: "info",
    },
    {
      commands: ["uv run glassbox artifacts inspect --json --cwd ."],
      detail:
        "Inspect protected, event-referenced, orphaned, reclaimable, and missing artifact pressure.",
      label: "Artifact pressure",
      state: "safe check",
      tone: "info",
    },
    {
      commands: ["uv run glassbox memory list --state invalidated --cwd ."],
      detail: "Review invalid workspace memory before pruning or changing retrieval posture.",
      label: "Workspace memory",
      state: "safe check",
      tone: "info",
    },
    providerEvidenceCue(data),
  ];
}

function providerEvidenceCue(data: DashboardState): RecoveryCue {
  const evidence = data.providerEvidence;
  const model = evidence.model_name ?? evidence.configured_model_name ?? "not configured";
  const provider = evidence.provider ?? "provider";
  const status = evidence.freshness_status;
  const tone = providerTone(status);
  const nextAction = evidence.next_actions?.[0];
  const actionDetail =
    nextAction === undefined ? "Run diagnostics or inspect retained canary evidence." : nextAction;

  return {
    commands: [
      "uv run glassbox provider diagnostics --cwd .",
      "uv run glassbox provider canary evidence --cwd .",
    ],
    detail: `${provider} ${model}: advisory ${status} evidence, canary ${evidence.latest_status}. Next: ${actionDetail}`,
    label: "Provider evidence",
    state: status,
    tone,
  };
}

function providerTone(status: string): RecoveryCue["tone"] {
  if (status === "fresh") {
    return "success";
  }
  if (status === "missing" || status === "credentialless") {
    return "info";
  }
  return "warning";
}
