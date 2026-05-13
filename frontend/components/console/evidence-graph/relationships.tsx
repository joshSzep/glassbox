import { Link2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import {
  edgeKindVariant,
  nodeAnchor,
  type EvidenceGraphEdge,
} from "@/components/console/evidence-graph/format";
import { EvidenceGraphDetails } from "@/components/console/evidence-graph/summary";

export function GraphRelationships({ edges }: { edges: EvidenceGraphEdge[] }) {
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
