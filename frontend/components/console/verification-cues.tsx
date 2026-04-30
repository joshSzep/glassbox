import { FileSearch, ShieldCheck } from "lucide-react";

import {
  artifactBadgeVariant,
  artifactCueLabel,
  deriveVerificationCueAnalysis,
  type ArtifactSummary,
} from "@/components/console/verification-cues-analysis";
import {
  EvidenceCueList,
  VerificationSummary,
  WorkingSetProvenance,
} from "@/components/console/verification-cues-sections";
import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { DashboardState } from "@/state/session-state";

export function VerificationCues({ data }: { data: DashboardState }) {
  const analysis = deriveVerificationCueAnalysis(data);

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
          value={String(analysis.blockingArtifacts.length)}
          variant={analysis.blockingArtifacts.length > 0 ? "destructive" : "success"}
        />
        <VerificationSummary
          detail="Stale, inherited, timed-out, or provider-canary evidence that needs judgment."
          label="Advisory evidence"
          value={String(analysis.advisoryArtifacts.length)}
          variant={analysis.advisoryArtifacts.length > 0 ? "warning" : "muted"}
        />
        <VerificationSummary
          detail="Policy decisions with retained source or risk evidence."
          label="Policy cues"
          value={String(analysis.policyCueCount)}
          variant={analysis.policyCueCount > 0 ? "info" : "muted"}
        />
        <VerificationSummary
          detail="Snapshots without retained replay, eval, provider, or release artifacts."
          label={analysis.missingArtifactCount > 0 ? "Missing artifacts" : "Verified artifacts"}
          value={String(
            analysis.missingArtifactCount > 0
              ? analysis.missingArtifactCount
              : analysis.verifiedArtifacts.length,
          )}
          variant={analysis.missingArtifactCount > 0 ? "muted" : "success"}
        />
      </div>

      <EvidenceCueList cues={analysis.evidenceCues} />

      {analysis.artifactSummaries.length === 0 ? (
        <div className="rounded-md border bg-card p-3 text-sm text-muted-foreground">
          No replay, eval, provider, or release artifacts are retained in this snapshot. Use CLI
          replay/eval commands for authoritative reproduction when artifact evidence is missing.
        </div>
      ) : (
        <div className="space-y-4">
          <ArtifactGroup
            artifacts={analysis.blockingArtifacts}
            empty="No blocking replay or eval evidence."
            title="Blocking evidence"
          />
          <ArtifactGroup
            artifacts={analysis.advisoryArtifacts}
            empty="No advisory drift or provider artifacts."
            title="Advisory evidence"
          />
          <ArtifactGroup
            artifacts={analysis.verifiedArtifacts}
            empty="No verified artifact summaries."
            title="Verified state"
          />
        </div>
      )}

      <WorkingSetProvenance
        inheritedWorkingSetCount={analysis.inheritedWorkingSetCount}
        items={analysis.workingSetItems}
      />
    </section>
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
