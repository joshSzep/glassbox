import { Badge } from "@/components/ui/badge";
import { DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import {
  freshnessVariant,
  nodeAnchor,
  visibilityVariant,
  type EvidenceGraphNode,
} from "@/components/console/evidence-graph/format";
import { EvidenceGraphDetails } from "@/components/console/evidence-graph/summary";

export function GraphNodes({ nodes }: { nodes: EvidenceGraphNode[] }) {
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
