import { FileSearch, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { DashboardState } from "@/state/session-state";

export function VerificationCues({ data }: { data: DashboardState }) {
  const artifactSummaries = data.runtimeContext?.artifact_context?.summaries ?? [];
  const workingSetItems = data.runtimeContext?.working_set?.items ?? [];
  const blockingArtifacts = artifactSummaries.filter(isBlockingCue);
  const advisoryArtifacts = artifactSummaries.filter(
    (artifact) => !isBlockingCue(artifact) && isDriftCue(artifact),
  );
  const verifiedArtifacts = artifactSummaries.filter(
    (artifact) => !isBlockingCue(artifact) && !isDriftCue(artifact),
  );
  const inheritedWorkingSetCount = workingSetItems.filter((item) => item.inherited).length;
  const missingArtifactCount = artifactSummaries.length === 0 ? 1 : 0;

  return (
    <section className="rounded-lg border bg-background p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-muted-foreground">
        <ShieldCheck className={operatorIconSizeClass} aria-hidden="true" />
        Verification cues
      </h3>

      <div
        className="mb-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Verification summary"
      >
        <VerificationSummary
          detail="Replay or eval evidence that should block optimistic triage."
          label="Blocking evidence"
          value={String(blockingArtifacts.length)}
          variant={blockingArtifacts.length > 0 ? "destructive" : "success"}
        />
        <VerificationSummary
          detail="Stale, inherited, or timed-out artifacts that need judgment."
          label="Advisory drift"
          value={String(advisoryArtifacts.length)}
          variant={advisoryArtifacts.length > 0 ? "warning" : "muted"}
        />
        <VerificationSummary
          detail="Working-set items inherited from parent context."
          label="Inherited working set"
          value={String(inheritedWorkingSetCount)}
          variant={inheritedWorkingSetCount > 0 ? "info" : "muted"}
        />
        <VerificationSummary
          detail="Snapshots without retained replay or eval artifacts."
          label={missingArtifactCount > 0 ? "Missing artifacts" : "Verified artifacts"}
          value={String(missingArtifactCount > 0 ? missingArtifactCount : verifiedArtifacts.length)}
          variant={missingArtifactCount > 0 ? "muted" : "success"}
        />
      </div>

      {artifactSummaries.length === 0 ? (
        <div className="rounded-md border bg-card p-3 text-sm text-muted-foreground">
          No replay or eval artifacts are retained in this snapshot. Use CLI replay/eval commands
          for authoritative reproduction when artifact evidence is missing.
        </div>
      ) : (
        <div className="space-y-4">
          <ArtifactGroup
            artifacts={blockingArtifacts}
            empty="No blocking replay or eval evidence."
            title="Blocking evidence"
          />
          <ArtifactGroup
            artifacts={advisoryArtifacts}
            empty="No advisory drift artifacts."
            title="Advisory drift"
          />
          <ArtifactGroup
            artifacts={verifiedArtifacts}
            empty="No verified artifact summaries."
            title="Verified state"
          />
        </div>
      )}

      {workingSetItems.length > 0 ? (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Working-set provenance
          </p>
          <p className="mb-2 text-sm text-muted-foreground">
            {inheritedWorkingSetCount > 0
              ? `${inheritedWorkingSetCount} inherited item${inheritedWorkingSetCount === 1 ? "" : "s"} may explain drift before current-session changes.`
              : "Working-set items are current to this session."}
          </p>
          <DataList density="compact">
            {workingSetItems.map((item) => (
              <DataListItem key={`${item.subject_kind}:${item.subject}`}>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <DataListLabel>{item.subject}</DataListLabel>
                    <DataListMeta>{item.summary}</DataListMeta>
                  </div>
                  <Badge variant={item.inherited ? "info" : "outline"}>
                    {item.inherited ? "inherited working set" : "current working set"}
                  </Badge>
                </div>
                <p className="mt-2 break-all text-xs text-muted-foreground">
                  {item.signal_types?.join(", ") || "unknown signal"} ·{" "}
                  {item.reasons?.join(", ") || "no recorded reason"}
                </p>
              </DataListItem>
            ))}
          </DataList>
        </div>
      ) : null}
    </section>
  );
}

function VerificationSummary({
  detail,
  label,
  value,
  variant,
}: {
  detail: string;
  label: string;
  value: string;
  variant: "destructive" | "info" | "muted" | "success" | "warning";
}) {
  return (
    <div className="rounded-md border bg-card p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <Badge variant={variant}>{value}</Badge>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function ArtifactGroup({
  artifacts,
  empty,
  title,
}: {
  artifacts: ArtifactSummary[];
  empty: string;
  title: string;
}) {
  return (
    <section>
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        {title}
      </p>
      {artifacts.length === 0 ? (
        <p className="rounded-md border bg-card p-3 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <DataList density="compact">
          {artifacts.map((artifact) => (
            <ArtifactRow
              artifact={artifact}
              key={`${artifact.artifact_kind}:${artifact.artifact_path}`}
            />
          ))}
        </DataList>
      )}
    </section>
  );
}

function ArtifactRow({ artifact }: { artifact: ArtifactSummary }) {
  return (
    <DataListItem>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <DataListLabel>{artifact.summary_kind}</DataListLabel>
          <DataListMeta>{artifact.summary}</DataListMeta>
        </div>
        <Badge variant={artifactBadgeVariant(artifact)}>{artifactCueLabel(artifact)}</Badge>
      </div>
      <div className="mt-2 grid gap-2 text-xs text-muted-foreground">
        <span className="inline-flex min-w-0 items-center gap-1 break-all">
          <FileSearch className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <code
            aria-label={`Copyable artifact path ${artifact.artifact_path}`}
            className="select-all break-all"
          >
            {artifact.artifact_path}
          </code>
        </span>
        <span className="break-words">
          {artifact.source_tool_name} · {artifact.freshness}
          {artifact.timed_out ? " · timed out" : ""}
          {artifact.inherited ? " · inherited" : ""}
        </span>
        {(artifact.target_paths ?? []).length > 0 ? (
          <span className="break-all">Targets: {(artifact.target_paths ?? []).join(", ")}</span>
        ) : null}
        {(artifact.failing_tests ?? []).length > 0 ? (
          <span className="break-all">
            Failing tests: {(artifact.failing_tests ?? []).join(", ")}
          </span>
        ) : null}
      </div>
    </DataListItem>
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
