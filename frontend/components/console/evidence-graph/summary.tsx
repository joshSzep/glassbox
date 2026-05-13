import type { ReactNode } from "react";
import { GitBranch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { filterId, type GraphFilter } from "@/components/console/evidence-graph/format";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { EvidenceGraph } from "@/state/session-state";

export function EvidenceGraphFrame({ children, title }: { children: ReactNode; title: string }) {
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

export function EvidenceGraphSummary({
  claims,
  edges,
  filters,
  graph,
  nodes,
}: {
  claims: NonNullable<EvidenceGraph["claims"]>;
  edges: NonNullable<EvidenceGraph["edges"]>;
  filters: GraphFilter[];
  graph: EvidenceGraph;
  nodes: NonNullable<EvidenceGraph["nodes"]>;
}) {
  return (
    <>
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
    </>
  );
}

export function EvidenceGraphDetails({
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

export function GraphLimitations({ limitations }: { limitations: string[] }) {
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
