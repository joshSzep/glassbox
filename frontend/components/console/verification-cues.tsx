import { FileSearch, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { DashboardState } from "@/state/session-state";

export function VerificationCues({ data }: { data: DashboardState }) {
  const artifactSummaries = data.runtimeContext?.artifact_context?.summaries ?? [];
  const workingSetItems = data.runtimeContext?.working_set?.items ?? [];
  const driftCount = artifactSummaries.filter(isDriftCue).length;
  const blockingCount = artifactSummaries.filter(isBlockingCue).length;
  const inheritedWorkingSetCount = workingSetItems.filter((item) => item.inherited).length;

  return (
    <section className="rounded-lg border bg-background p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-muted-foreground">
        <ShieldCheck className={operatorIconSizeClass} aria-hidden="true" />
        Verification cues
      </h3>

      <div className="mb-3 flex flex-wrap gap-2">
        <Badge variant={blockingCount > 0 ? "destructive" : "success"}>
          {blockingCount} blocking evidence
        </Badge>
        <Badge variant={driftCount > 0 ? "warning" : "muted"}>{driftCount} advisory drift</Badge>
        <Badge variant={inheritedWorkingSetCount > 0 ? "info" : "muted"}>
          {inheritedWorkingSetCount} inherited work items
        </Badge>
      </div>

      {artifactSummaries.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No replay or eval artifacts are retained in this snapshot.
        </p>
      ) : (
        <DataList density="compact">
          {artifactSummaries.map((artifact) => (
            <DataListItem key={`${artifact.artifact_kind}:${artifact.artifact_path}`}>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <DataListLabel>{artifact.summary_kind}</DataListLabel>
                  <DataListMeta>{artifact.summary}</DataListMeta>
                </div>
                <Badge variant={artifactBadgeVariant(artifact)}>{artifactCueLabel(artifact)}</Badge>
              </div>
              <div className="mt-2 grid gap-1 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1 break-all">
                  <FileSearch className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  <code>{artifact.artifact_path}</code>
                </span>
                {(artifact.target_paths ?? []).length > 0 ? (
                  <span className="break-all">
                    Targets: {(artifact.target_paths ?? []).join(", ")}
                  </span>
                ) : null}
                {(artifact.failing_tests ?? []).length > 0 ? (
                  <span className="break-all">
                    Failing tests: {(artifact.failing_tests ?? []).join(", ")}
                  </span>
                ) : null}
              </div>
            </DataListItem>
          ))}
        </DataList>
      )}

      {workingSetItems.length > 0 ? (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Working-set provenance
          </p>
          <DataList density="compact">
            {workingSetItems.map((item) => (
              <DataListItem key={`${item.subject_kind}:${item.subject}`}>
                <DataListLabel>{item.subject}</DataListLabel>
                <DataListMeta>
                  {item.inherited ? "inherited" : "current"} ·{" "}
                  {item.signal_types?.join(", ") || "unknown signal"} ·{" "}
                  {item.reasons?.join(", ") || item.summary}
                </DataListMeta>
              </DataListItem>
            ))}
          </DataList>
        </div>
      ) : null}
    </section>
  );
}

type ArtifactSummary = NonNullable<
  NonNullable<NonNullable<DashboardState["runtimeContext"]>["artifact_context"]>["summaries"]
>[number];

function isBlockingCue(artifact: ArtifactSummary): boolean {
  return (
    artifact.error_count > 0 ||
    artifact.failure_count > 0 ||
    (artifact.failing_tests ?? []).length > 0
  );
}

function isDriftCue(artifact: ArtifactSummary): boolean {
  return artifact.freshness === "stale" || artifact.inherited || artifact.timed_out;
}

function artifactBadgeVariant(artifact: ArtifactSummary) {
  if (isBlockingCue(artifact)) {
    return "destructive" as const;
  }
  if (isDriftCue(artifact)) {
    return "warning" as const;
  }
  return "success" as const;
}

function artifactCueLabel(artifact: ArtifactSummary): string {
  if (isBlockingCue(artifact)) {
    return "blocking evidence";
  }
  if (isDriftCue(artifact)) {
    return "advisory drift";
  }
  return "verified";
}
