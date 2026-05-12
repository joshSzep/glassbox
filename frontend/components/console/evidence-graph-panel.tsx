import type { ReactNode } from "react";
import { GitBranch, Link2 } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { EvidenceGraph } from "@/state/session-state";

type EvidenceGraphPanelProps = {
  emptyTarget: string;
  graph: EvidenceGraph | null | undefined;
  title?: string;
};

type GraphFilter = {
  count: number;
  description: string;
  label: string;
  variant: NonNullable<BadgeProps["variant"]>;
};

export function EvidenceGraphPanel({
  emptyTarget,
  graph,
  title = "Evidence Graph",
}: EvidenceGraphPanelProps) {
  if (graph === null || graph === undefined) {
    return (
      <EvidenceGraphFrame title={title}>
        <p className="text-sm text-muted-foreground">
          No derived evidence graph is loaded for {emptyTarget}. Older sessions may only have event
          and artifact summaries.
        </p>
      </EvidenceGraphFrame>
    );
  }

  const nodes = graph.nodes ?? [];
  const edges = graph.edges ?? [];
  const claims = graph.claims ?? [];
  const filters = buildGraphFilters(graph);

  return (
    <EvidenceGraphFrame title={title}>
      <div className="grid gap-3">
        <div className="flex flex-wrap gap-2" aria-label="Evidence graph summary">
          <Badge variant="info">{graph.target.kind}</Badge>
          <Badge variant="outline">{nodes.length} nodes</Badge>
          <Badge variant="outline">{edges.length} edges</Badge>
          <Badge variant="outline">{claims.length} claims</Badge>
          <Badge variant={(graph.limitations ?? []).length > 0 ? "warning" : "muted"}>
            {(graph.limitations ?? []).length} limitations
          </Badge>
          <Badge variant="muted">{graph.graph_id}</Badge>
        </div>

        <DataList density="compact" aria-label="Evidence graph filters">
          {filters.map((filter) => (
            <DataListItem id={filterId(filter.label)} key={filter.label}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <DataListLabel>{filter.label}</DataListLabel>
                  <DataListMeta>{filter.description}</DataListMeta>
                </div>
                <Badge variant={filter.count > 0 ? filter.variant : "muted"}>{filter.count}</Badge>
              </div>
            </DataListItem>
          ))}
        </DataList>

        <GraphClaims claims={claims} />
        <GraphNodes nodes={nodes} />
        <GraphRelationships edges={edges} />
        <GraphLimitations limitations={graph.limitations ?? []} />
      </div>
    </EvidenceGraphFrame>
  );
}

function EvidenceGraphFrame({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-md border border-border/80 bg-card p-3 text-card-foreground">
      <h3 className="flex items-center gap-2 text-sm font-semibold tracking-normal">
        <GitBranch className={operatorIconSizeClass} aria-hidden="true" />
        {title}
      </h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function GraphClaims({ claims }: { claims: NonNullable<EvidenceGraph["claims"]> }) {
  return (
    <EvidenceGraphDetails empty="No claims are represented in this graph." title="Claim Support">
      {claims.slice(0, 10).map((claim) => (
        <DataListItem id={claimAnchor(claim.claim_id)} key={claim.claim_id}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <DataListLabel>{claim.title}</DataListLabel>
              <DataListMeta>{claim.summary}</DataListMeta>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant={claimStateVariant(claim.state)}>{claim.state}</Badge>
              <Badge variant="outline">{claim.confidence}</Badge>
              <Badge variant={visibilityVariant(claim.visibility)}>{claim.visibility}</Badge>
            </div>
          </div>
          <DataListMeta>
            {claim.supporting_edge_ids?.length ?? 0} supporting edges;{" "}
            {claim.stale_node_ids?.length ?? 0} stale nodes; {claim.missing_evidence?.length ?? 0}{" "}
            missing evidence; {claim.accepted_risk_node_ids?.length ?? 0} accepted risks
          </DataListMeta>
          {(claim.missing_evidence ?? []).slice(0, 2).map((missing) => (
            <DataListMeta key={missing.missing_id}>
              Missing {missing.kind}: {missing.summary}
            </DataListMeta>
          ))}
          {(claim.limitations ?? []).slice(0, 2).map((limitation) => (
            <DataListMeta key={limitation}>Limitation: {limitation}</DataListMeta>
          ))}
        </DataListItem>
      ))}
    </EvidenceGraphDetails>
  );
}

function GraphNodes({ nodes }: { nodes: NonNullable<EvidenceGraph["nodes"]> }) {
  return (
    <EvidenceGraphDetails empty="No node summaries are available." title="Node Summaries">
      {nodes.slice(0, 12).map((node) => (
        <DataListItem id={nodeAnchor(node.node_id)} key={node.node_id}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <DataListLabel>{node.title}</DataListLabel>
              <DataListMeta>{node.summary}</DataListMeta>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{node.kind}</Badge>
              <Badge variant={freshnessVariant(node.freshness)}>{node.freshness}</Badge>
              <Badge variant={visibilityVariant(node.visibility)}>{node.visibility}</Badge>
            </div>
          </div>
          <DataListMeta>
            confidence {node.confidence}; redaction {node.redaction_status}
          </DataListMeta>
          {(node.provenance ?? []).slice(0, 2).map((source) => (
            <DataListMeta className="break-words" key={`${node.node_id}:${source.summary}`}>
              {source.source_kind} {source.source_id ?? ""} {source.source_path ?? ""}:{" "}
              {source.summary}
            </DataListMeta>
          ))}
          {(node.limitations ?? []).slice(0, 2).map((limitation) => (
            <DataListMeta key={limitation}>Limitation: {limitation}</DataListMeta>
          ))}
        </DataListItem>
      ))}
    </EvidenceGraphDetails>
  );
}

function GraphRelationships({ edges }: { edges: NonNullable<EvidenceGraph["edges"]> }) {
  return (
    <EvidenceGraphDetails empty="No graph relationships are available." title="Relationships">
      {edges.slice(0, 12).map((edge) => (
        <DataListItem key={edge.edge_id}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <DataListLabel>{edge.kind}</DataListLabel>
              <DataListMeta>{edge.summary}</DataListMeta>
            </div>
            <Badge variant={edgeKindVariant(edge.kind)}>{edge.confidence}</Badge>
          </div>
          <DataListMeta className="flex min-w-0 flex-wrap items-center gap-1">
            <NodeAnchorLink nodeId={edge.from_node_id} /> to{" "}
            <NodeAnchorLink nodeId={edge.to_node_id} />
          </DataListMeta>
          {(edge.limitations ?? []).slice(0, 2).map((limitation) => (
            <DataListMeta key={limitation}>Limitation: {limitation}</DataListMeta>
          ))}
        </DataListItem>
      ))}
    </EvidenceGraphDetails>
  );
}

function EvidenceGraphDetails({
  children,
  empty,
  title,
}: {
  children: ReactNode;
  empty: string;
  title: string;
}) {
  const childArray = Array.isArray(children) ? children : [children];
  return (
    <details className="rounded-md border border-border/70 bg-surface p-3" open>
      <summary className="cursor-pointer text-sm font-medium">{title}</summary>
      <div className="mt-3">
        {childArray.length === 0 ? (
          <p className="text-sm text-muted-foreground">{empty}</p>
        ) : (
          <DataList density="compact">{children}</DataList>
        )}
      </div>
    </details>
  );
}

function GraphLimitations({ limitations }: { limitations: string[] }) {
  if (limitations.length === 0) {
    return null;
  }
  return (
    <DataList density="compact" aria-label="Evidence graph limitations">
      {limitations.slice(0, 4).map((limitation) => (
        <DataListItem key={limitation}>
          <DataListLabel>Limitation</DataListLabel>
          <DataListMeta>{limitation}</DataListMeta>
        </DataListItem>
      ))}
    </DataList>
  );
}

function NodeAnchorLink({ nodeId }: { nodeId: string }) {
  return (
    <a
      className="inline-flex min-w-0 items-center gap-1 rounded-md border border-border/70 bg-card px-2 py-1 font-mono text-[0.75rem] text-foreground hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      href={`#${nodeAnchor(nodeId)}`}
    >
      <Link2 className="h-3 w-3 shrink-0" aria-hidden="true" />
      <span className="truncate">{nodeId}</span>
    </a>
  );
}

function buildGraphFilters(graph: EvidenceGraph): GraphFilter[] {
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

function filterId(label: string) {
  return `evidence-filter-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

function nodeAnchor(nodeId: string) {
  return `evidence-node-${nodeId}`;
}

function claimAnchor(claimId: string) {
  return `evidence-claim-${claimId}`;
}

function claimStateVariant(
  state: NonNullable<EvidenceGraph["claims"]>[number]["state"],
): NonNullable<BadgeProps["variant"]> {
  return state === "supported"
    ? "success"
    : state === "contradicted" || state === "missing"
      ? "destructive"
      : state === "stale" || state === "accepted_with_risk"
        ? "warning"
        : "info";
}

function freshnessVariant(
  freshness: NonNullable<EvidenceGraph["nodes"]>[number]["freshness"],
): NonNullable<BadgeProps["variant"]> {
  return freshness === "fresh"
    ? "success"
    : freshness === "missing"
      ? "destructive"
      : freshness === "stale" || freshness === "superseded"
        ? "warning"
        : "info";
}

function edgeKindVariant(
  kind: NonNullable<EvidenceGraph["edges"]>[number]["kind"],
): NonNullable<BadgeProps["variant"]> {
  return kind === "contradicts"
    ? "destructive"
    : kind === "accepted-risk-for" || kind === "skipped-by" || kind === "makes-stale"
      ? "warning"
      : "info";
}

function visibilityVariant(
  visibility: NonNullable<EvidenceGraph["nodes"]>[number]["visibility"],
): NonNullable<BadgeProps["variant"]> {
  return visibility === "operator_only"
    ? "muted"
    : visibility === "reviewer_safe"
      ? "success"
      : "info";
}
