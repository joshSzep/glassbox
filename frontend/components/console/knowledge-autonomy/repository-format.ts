import type { RepositoryEntry, RepositoryInspectorState } from "./types";

type RepositoryOverview = NonNullable<RepositoryInspectorState["overview"]>;
type RepositoryFreshnessCue = NonNullable<
  NonNullable<RepositoryInspectorState["freshness"]>["cues"]
>[number];
type RepositoryVerification = RepositoryInspectorState["verification"];

export function repositoryOverviewSummary(overview: RepositoryOverview): string {
  return `${overview.package_boundaries.length} packages, ${overview.subsystems.length} subsystems, ${overview.release_surfaces.length} release-sensitive surfaces.`;
}

export function repositoryFreshnessCueLabel(cue: RepositoryFreshnessCue): string {
  return `${cue.source}: ${cue.state} - ${cue.detail}`;
}

export function repositoryJoinedLabels(items: string[]): string {
  return items.join(", ") || "none";
}

export function repositoryEntryLocation(entry: RepositoryEntry): string {
  return entry.path ?? entry.symbol ?? "workspace";
}

export function repositoryDetailLocation(entry: RepositoryEntry): string {
  return entry.path ?? entry.symbol ?? entry.entry_id;
}

export function repositoryVerificationSummary(verification: RepositoryVerification): string {
  if (verification?.status === "ok") {
    return (
      verification.report?.cheapest_next_command ??
      verification.next_actions?.[0] ??
      "Recommendation report loaded."
    );
  }
  return verification?.detail ?? "Verification recommendations load after a path is inspected.";
}

export function repositoryMemoryCandidateEmptyText(anchorSessionId: string | null): string {
  return anchorSessionId === null
    ? "Memory candidates need a session anchor."
    : "Refresh this console to load repository memory candidates.";
}
