import type { BadgeProps } from "@/components/ui/badge";
import type { EvidenceGraph } from "@/state/session-state";

export type EvidenceGraphClaim = NonNullable<EvidenceGraph["claims"]>[number];
export type EvidenceGraphEdge = NonNullable<EvidenceGraph["edges"]>[number];
export type EvidenceGraphNode = NonNullable<EvidenceGraph["nodes"]>[number];

export type GraphFilter = {
  count: number;
  description: string;
  label: string;
  variant: NonNullable<BadgeProps["variant"]>;
};

export function buildGraphFilters(graph: EvidenceGraph): GraphFilter[] {
  const claims = graph.claims ?? [];
  const nodes = graph.nodes ?? [];
  const edges = graph.edges ?? [];
  return [
    {
      count:
        nodes.filter((node) => node.freshness === "stale").length +
        claims.filter((claim) => claim.state === "stale").length,
      description: "Evidence that may need refresh before it supports a claim.",
      label: "Stale",
      variant: "warning",
    },
    {
      count:
        nodes.filter((node) => node.freshness === "missing").length +
        claims.filter((claim) => claim.state === "missing").length +
        claims.reduce((total, claim) => total + (claim.missing_evidence?.length ?? 0), 0),
      description: "Claims or expected evidence with no local support node.",
      label: "Missing",
      variant: "destructive",
    },
    {
      count:
        nodes.filter((node) => node.freshness === "manual-only").length +
        claims.filter((claim) => claim.state === "manual-only").length,
      description: "Manual-only support that should not be treated as retained command proof.",
      label: "Manual-only",
      variant: "info",
    },
    {
      count: claims.filter((claim) => claim.state === "accepted_with_risk").length,
      description: "Claims supported only after an explicit accepted-risk decision.",
      label: "Accepted-risk",
      variant: "warning",
    },
    {
      count:
        edges.filter((edge) => edge.kind === "contradicts").length +
        claims.filter((claim) => claim.state === "contradicted").length,
      description: "Claims or relationships that contradict the current story.",
      label: "Contradictory",
      variant: "destructive",
    },
    {
      count: nodes.filter((node) => node.visibility !== "operator_only").length,
      description: "Evidence summaries safe for reviewer or release contexts.",
      label: "Reviewer-safe",
      variant: "success",
    },
  ];
}

export function filterId(label: string) {
  return `evidence-filter-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

export function nodeAnchor(nodeId: string) {
  return `evidence-node-${nodeId}`;
}

export function claimAnchor(claimId: string) {
  return `evidence-claim-${claimId}`;
}

export function claimStateVariant(
  state: EvidenceGraphClaim["state"],
): NonNullable<BadgeProps["variant"]> {
  return state === "supported"
    ? "success"
    : state === "contradicted" || state === "missing"
      ? "destructive"
      : state === "stale" || state === "accepted_with_risk"
        ? "warning"
        : "info";
}

export function freshnessVariant(
  freshness: EvidenceGraphNode["freshness"],
): NonNullable<BadgeProps["variant"]> {
  return freshness === "fresh"
    ? "success"
    : freshness === "missing"
      ? "destructive"
      : freshness === "stale" || freshness === "superseded"
        ? "warning"
        : "info";
}

export function edgeKindVariant(
  kind: EvidenceGraphEdge["kind"],
): NonNullable<BadgeProps["variant"]> {
  return kind === "contradicts"
    ? "destructive"
    : kind === "accepted-risk-for" || kind === "skipped-by" || kind === "makes-stale"
      ? "warning"
      : "info";
}

export function visibilityVariant(
  visibility: EvidenceGraphNode["visibility"],
): NonNullable<BadgeProps["variant"]> {
  return visibility === "operator_only"
    ? "muted"
    : visibility === "reviewer_safe"
      ? "success"
      : "info";
}
