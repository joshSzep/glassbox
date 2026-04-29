import { FileSearch, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import {
  EvidenceCueList,
  VerificationSummary,
  WorkingSetProvenance,
  type EvidenceCue,
  type WorkingSetItem,
} from "@/components/console/verification-cues-sections";
import { policySourceLabel } from "@/components/console/session-inspector/policy-evidence";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { DashboardState } from "@/state/session-state";

export function VerificationCues({ data }: { data: DashboardState }) {
  const artifactSummaries = data.runtimeContext?.artifact_context?.summaries ?? [];
  const workingSetItems = data.runtimeContext?.working_set?.items ?? [];
  const blockingArtifacts = artifactSummaries.filter(isBlockingCue);
  const advisoryArtifacts = artifactSummaries.filter(
    (artifact) => !isBlockingCue(artifact) && isAdvisoryCue(artifact),
  );
  const verifiedArtifacts = artifactSummaries.filter(
    (artifact) => !isBlockingCue(artifact) && !isAdvisoryCue(artifact),
  );
  const inheritedWorkingSetCount = workingSetItems.filter((item) => item.inherited).length;
  const missingArtifactCount = artifactSummaries.length === 0 ? 1 : 0;
  const evidenceCues = buildEvidenceCues(data, artifactSummaries, workingSetItems);
  const policyCueCount = countPolicyCues(data);

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
          detail="Stale, inherited, timed-out, or provider-canary evidence that needs judgment."
          label="Advisory evidence"
          value={String(advisoryArtifacts.length)}
          variant={advisoryArtifacts.length > 0 ? "warning" : "muted"}
        />
        <VerificationSummary
          detail="Policy decisions with retained source or risk evidence."
          label="Policy cues"
          value={String(policyCueCount)}
          variant={policyCueCount > 0 ? "info" : "muted"}
        />
        <VerificationSummary
          detail="Snapshots without retained replay, eval, provider, or release artifacts."
          label={missingArtifactCount > 0 ? "Missing artifacts" : "Verified artifacts"}
          value={String(missingArtifactCount > 0 ? missingArtifactCount : verifiedArtifacts.length)}
          variant={missingArtifactCount > 0 ? "muted" : "success"}
        />
      </div>

      <EvidenceCueList cues={evidenceCues} />

      {artifactSummaries.length === 0 ? (
        <div className="rounded-md border bg-card p-3 text-sm text-muted-foreground">
          No replay, eval, provider, or release artifacts are retained in this snapshot. Use CLI
          replay/eval commands for authoritative reproduction when artifact evidence is missing.
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
            empty="No advisory drift or provider artifacts."
            title="Advisory evidence"
          />
          <ArtifactGroup
            artifacts={verifiedArtifacts}
            empty="No verified artifact summaries."
            title="Verified state"
          />
        </div>
      )}

      <WorkingSetProvenance
        inheritedWorkingSetCount={inheritedWorkingSetCount}
        items={workingSetItems}
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

type ArtifactSummary = NonNullable<
  NonNullable<NonNullable<DashboardState["runtimeContext"]>["artifact_context"]>["summaries"]
>[number];

function buildEvidenceCues(
  data: DashboardState,
  artifacts: ArtifactSummary[],
  workingSetItems: WorkingSetItem[],
): EvidenceCue[] {
  return [
    buildPolicyCue(data),
    buildEvalCoverageCue(artifacts, workingSetItems),
    buildReplayDriftCue(artifacts),
    buildProviderCue(artifacts),
    buildReleaseCue(artifacts),
  ];
}

function buildPolicyCue(data: DashboardState): EvidenceCue {
  const policySummary = data.currentTurnPolicySummary ?? data.sessionPolicySummary;
  const sourceLabels = collectPolicySources(data);
  const blockedCount = (policySummary?.blocked_count ?? 0) + (policySummary?.deny_count ?? 0);
  const approvalCount = Math.max(
    policySummary?.approve_count ?? 0,
    data.pendingApprovals.filter((approval) => approval.policy_outcome === "approve").length,
  );
  const totalDecisions = countPolicyCues(data);
  const sourceText =
    sourceLabels.length > 0
      ? `Sources: ${sourceLabels.join(", ")}`
      : "Sources: no active policy source label is retained in this snapshot.";

  if (blockedCount > 0) {
    return {
      badge: "blocking policy",
      detail: `${blockedCount} denied or blocked policy decision${blockedCount === 1 ? "" : "s"}; inspect Actions, Timeline, or Event evidence before continuing.`,
      label: "Policy decision source",
      source: sourceText,
      variant: "destructive",
    };
  }

  if (approvalCount > 0) {
    return {
      badge: "approval policy",
      detail: `${approvalCount} approval policy decision${approvalCount === 1 ? "" : "s"} retained with risk/source context.`,
      label: "Policy decision source",
      source: sourceText,
      variant: "warning",
    };
  }

  if (totalDecisions > 0) {
    return {
      badge: "policy retained",
      detail: `${totalDecisions} policy decision${totalDecisions === 1 ? "" : "s"} retained; no blocking or approval decision is visible.`,
      label: "Policy decision source",
      source: sourceText,
      variant: "info",
    };
  }

  return {
    badge: "no policy cue",
    detail: "No policy decision source is retained for this snapshot.",
    label: "Policy decision source",
    source: sourceText,
    variant: "muted",
  };
}

function buildEvalCoverageCue(
  artifacts: ArtifactSummary[],
  workingSetItems: WorkingSetItem[],
): EvidenceCue {
  const evalArtifacts = artifacts.filter(isEvalEvidence);
  if (evalArtifacts.length === 0) {
    return {
      badge: "missing evidence",
      detail:
        "No retained eval coverage, impact, or recommendation artifact is available for this snapshot.",
      label: "Eval coverage relevance",
      source:
        "Run glassbox eval audit or glassbox eval recommend when changed paths need deterministic coverage guidance.",
      variant: "muted",
    };
  }

  const blockingCount = evalArtifacts.filter(isBlockingCue).length;
  const advisoryCount = evalArtifacts.filter(
    (artifact) => !isBlockingCue(artifact) && isDriftCue(artifact),
  ).length;
  const relevantTargets = matchingTargetPaths(evalArtifacts, workingSetItems);
  const targetDetail =
    relevantTargets.length > 0
      ? `${relevantTargets.length} target path${relevantTargets.length === 1 ? "" : "s"} overlap the working set.`
      : "No retained target path overlaps the current working set.";

  if (blockingCount > 0) {
    return {
      badge: "blocking eval",
      detail: `${blockingCount} eval artifact${blockingCount === 1 ? "" : "s"} report failures or errors. ${targetDetail}`,
      label: "Eval coverage relevance",
      source: artifactPathSummary(evalArtifacts),
      variant: "destructive",
    };
  }

  if (advisoryCount > 0) {
    return {
      badge: "advisory eval",
      detail: `${advisoryCount} eval artifact${advisoryCount === 1 ? "" : "s"} are stale, inherited, or timed out. ${targetDetail}`,
      label: "Eval coverage relevance",
      source: artifactPathSummary(evalArtifacts),
      variant: "warning",
    };
  }

  return {
    badge: "eval retained",
    detail: `${evalArtifacts.length} eval coverage or recommendation artifact${evalArtifacts.length === 1 ? "" : "s"} retained. ${targetDetail}`,
    label: "Eval coverage relevance",
    source: artifactPathSummary(evalArtifacts),
    variant: "success",
  };
}

function buildReplayDriftCue(artifacts: ArtifactSummary[]): EvidenceCue {
  const replayArtifacts = artifacts.filter(isReplayEvidence);
  if (replayArtifacts.length === 0) {
    return {
      badge: "missing replay",
      detail: "No retained replay artifact is available for drift comparison.",
      label: "Replay drift",
      source: "Use glassbox replay run when reproduction proof is needed.",
      variant: "muted",
    };
  }

  const blockingCount = replayArtifacts.filter(isBlockingCue).length;
  const driftCount = replayArtifacts.filter(
    (artifact) => !isBlockingCue(artifact) && isDriftCue(artifact),
  ).length;

  if (blockingCount > 0) {
    return {
      badge: "blocking replay",
      detail: `${blockingCount} replay artifact${blockingCount === 1 ? "" : "s"} report failures, errors, or failing tests.`,
      label: "Replay drift",
      source: artifactPathSummary(replayArtifacts),
      variant: "destructive",
    };
  }

  if (driftCount > 0) {
    return {
      badge: "advisory drift",
      detail: `${driftCount} replay artifact${driftCount === 1 ? "" : "s"} are stale, inherited, or timed out.`,
      label: "Replay drift",
      source: artifactPathSummary(replayArtifacts),
      variant: "warning",
    };
  }

  return {
    badge: "replay retained",
    detail: `${replayArtifacts.length} replay artifact${replayArtifacts.length === 1 ? "" : "s"} retained without blocking or drift cues.`,
    label: "Replay drift",
    source: artifactPathSummary(replayArtifacts),
    variant: "success",
  };
}

function buildProviderCue(artifacts: ArtifactSummary[]): EvidenceCue {
  const providerArtifacts = artifacts.filter(isProviderEvidence);
  if (providerArtifacts.length === 0) {
    return {
      badge: "missing advisory",
      detail: "No retained provider canary or capability evidence is available for this snapshot.",
      label: "Provider canary status",
      source:
        "Provider compatibility remains unknown here; canary evidence is advisory when present.",
      variant: "muted",
    };
  }

  const advisoryIssueCount = providerArtifacts.filter(
    (artifact) => hasFailureSignal(artifact) || isDriftCue(artifact),
  ).length;

  return {
    badge: "advisory provider",
    detail:
      advisoryIssueCount > 0
        ? `${advisoryIssueCount} provider canary artifact${advisoryIssueCount === 1 ? "" : "s"} report failure, stale, inherited, or timed-out evidence; this is not deterministic release signoff.`
        : `${providerArtifacts.length} provider canary artifact${providerArtifacts.length === 1 ? "" : "s"} retained as advisory compatibility evidence, not deterministic release signoff.`,
    label: "Provider canary status",
    source: artifactPathSummary(providerArtifacts),
    variant: advisoryIssueCount > 0 ? "warning" : "info",
  };
}

function buildReleaseCue(artifacts: ArtifactSummary[]): EvidenceCue {
  const releaseArtifacts = artifacts.filter(isReleaseEvidence);
  if (releaseArtifacts.length === 0) {
    return {
      badge: "missing release",
      detail: "No retained release evidence pointer is available in this session snapshot.",
      label: "Release evidence freshness",
      source:
        "Release evidence usually lives under .glassbox/releases or an explicit gate/signoff artifact.",
      variant: "muted",
    };
  }

  const deterministicReleaseArtifacts = releaseArtifacts.filter(
    (artifact) => !isProviderEvidence(artifact),
  );
  const blockingCount = deterministicReleaseArtifacts.filter(isBlockingCue).length;
  const staleCount = releaseArtifacts.filter(isDriftCue).length;

  if (blockingCount > 0) {
    return {
      badge: "blocking release",
      detail: `${blockingCount} deterministic release evidence artifact${blockingCount === 1 ? "" : "s"} report failures or errors.`,
      label: "Release evidence freshness",
      source: artifactPathSummary(releaseArtifacts),
      variant: "destructive",
    };
  }

  if (staleCount > 0) {
    return {
      badge: "stale release",
      detail: `${staleCount} release evidence artifact${staleCount === 1 ? "" : "s"} are stale, inherited, or timed out.`,
      label: "Release evidence freshness",
      source: artifactPathSummary(releaseArtifacts),
      variant: "warning",
    };
  }

  if (deterministicReleaseArtifacts.length === 0) {
    return {
      badge: "advisory release",
      detail:
        "Only advisory provider evidence is retained under release evidence; deterministic release signoff is not present in this snapshot.",
      label: "Release evidence freshness",
      source: artifactPathSummary(releaseArtifacts),
      variant: "info",
    };
  }

  return {
    badge: "release retained",
    detail: `${deterministicReleaseArtifacts.length} deterministic release evidence artifact${deterministicReleaseArtifacts.length === 1 ? "" : "s"} are retained and fresh.`,
    label: "Release evidence freshness",
    source: artifactPathSummary(releaseArtifacts),
    variant: "success",
  };
}

function countPolicyCues(data: DashboardState): number {
  return Math.max(
    data.currentTurnPolicySummary?.total_decisions ?? 0,
    data.sessionPolicySummary?.total_decisions ?? 0,
    data.pendingApprovals.filter((approval) => approval.policy_outcome !== null).length,
    data.activeToolCalls.filter((toolCall) => toolCall.policy_outcome !== null).length,
  );
}

function isBlockingCue(artifact: ArtifactSummary): boolean {
  if (isProviderEvidence(artifact)) {
    return false;
  }
  return hasFailureSignal(artifact);
}

function hasFailureSignal(artifact: ArtifactSummary): boolean {
  return (
    artifact.error_count > 0 ||
    artifact.failure_count > 0 ||
    (artifact.failing_tests ?? []).length > 0
  );
}

function isDriftCue(artifact: ArtifactSummary): boolean {
  return artifact.freshness === "stale" || artifact.inherited || artifact.timed_out;
}

function isAdvisoryCue(artifact: ArtifactSummary): boolean {
  return isProviderEvidence(artifact) || isDriftCue(artifact);
}

function artifactBadgeVariant(artifact: ArtifactSummary) {
  if (isBlockingCue(artifact)) {
    return "destructive" as const;
  }
  if (isDriftCue(artifact)) {
    return "warning" as const;
  }
  if (isProviderEvidence(artifact)) {
    return "info" as const;
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
  if (isProviderEvidence(artifact)) {
    return "advisory provider";
  }
  return "verified";
}

function collectPolicySources(data: DashboardState): string[] {
  const sources = new Set<string>();
  for (const approval of data.pendingApprovals) {
    const source = policySourceLabel(approval.policy_source_kind, approval.policy_source_label);
    if (source) {
      sources.add(source);
    }
  }
  for (const toolCall of data.activeToolCalls) {
    const source = policySourceLabel(toolCall.policy_source_kind, toolCall.policy_source_label);
    if (source) {
      sources.add(source);
    }
  }
  return [...sources].sort();
}

function isEvalEvidence(artifact: ArtifactSummary): boolean {
  if (isProviderEvidence(artifact) || isReplayEvidence(artifact)) {
    return false;
  }
  return evidenceText(artifact).includes("eval");
}

function isReplayEvidence(artifact: ArtifactSummary): boolean {
  return evidenceText(artifact).includes("replay");
}

function isProviderEvidence(artifact: ArtifactSummary): boolean {
  const text = evidenceText(artifact);
  return (
    text.includes("provider-canary") ||
    text.includes("provider canary") ||
    text.includes("provider capability") ||
    text.includes("capability matrix") ||
    text.includes("live-provider") ||
    text.includes("provider diagnostics")
  );
}

function isReleaseEvidence(artifact: ArtifactSummary): boolean {
  const text = evidenceText(artifact);
  return (
    artifact.artifact_path.includes(".glassbox/releases/") ||
    text.includes("release") ||
    text.includes("signoff") ||
    text.includes("sign-off") ||
    text.includes("gate")
  );
}

function evidenceText(artifact: ArtifactSummary): string {
  return [
    artifact.artifact_kind,
    artifact.artifact_path,
    artifact.summary_kind,
    artifact.source_tool_name,
    artifact.summary,
  ]
    .join(" ")
    .toLowerCase();
}

function matchingTargetPaths(
  artifacts: ArtifactSummary[],
  workingSetItems: WorkingSetItem[],
): string[] {
  const workingSetSubjects = workingSetItems.map((item) => item.subject);
  const targetPaths = new Set<string>();
  for (const artifact of artifacts) {
    for (const targetPath of artifact.target_paths ?? []) {
      if (workingSetSubjects.some((subject) => pathsOverlap(subject, targetPath))) {
        targetPaths.add(targetPath);
      }
    }
  }
  return [...targetPaths].sort();
}

function pathsOverlap(leftPath: string, rightPath: string): boolean {
  return (
    leftPath === rightPath ||
    leftPath.startsWith(`${rightPath}/`) ||
    rightPath.startsWith(`${leftPath}/`)
  );
}

function artifactPathSummary(artifacts: ArtifactSummary[]): string {
  const paths = artifacts.map((artifact) => artifact.artifact_path);
  const visiblePaths = paths.slice(0, 3).join(", ");
  const additionalCount = Math.max(paths.length - 3, 0);
  return additionalCount > 0
    ? `Artifacts: ${visiblePaths}, and ${additionalCount} more.`
    : `Artifacts: ${visiblePaths}.`;
}
