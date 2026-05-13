import { GraphClaims } from "@/components/console/evidence-graph/claims";
import { buildGraphFilters } from "@/components/console/evidence-graph/format";
import { GraphNodes } from "@/components/console/evidence-graph/nodes";
import { GraphRelationships } from "@/components/console/evidence-graph/relationships";
import {
  EvidenceGraphFrame,
  EvidenceGraphSummary,
  GraphLimitations,
} from "@/components/console/evidence-graph/summary";
import type { EvidenceGraph } from "@/state/session-state";

type EvidenceGraphPanelProps = {
  emptyTarget: string;
  graph: EvidenceGraph | null | undefined;
  title?: string;
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
        <EvidenceGraphSummary
          claims={claims}
          edges={edges}
          filters={filters}
          graph={graph}
          nodes={nodes}
        />
        <GraphClaims claims={claims} />
        <GraphNodes nodes={nodes} />
        <GraphRelationships edges={edges} />
        <GraphLimitations limitations={graph.limitations ?? []} />
      </div>
    </EvidenceGraphFrame>
  );
}
