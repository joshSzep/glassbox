import { Badge } from "@/components/ui/badge";
import { DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import {
  claimAnchor,
  claimStateVariant,
  visibilityVariant,
  type EvidenceGraphClaim,
} from "@/components/console/evidence-graph/format";
import { EvidenceGraphDetails } from "@/components/console/evidence-graph/summary";

export function GraphClaims({ claims }: { claims: EvidenceGraphClaim[] }) {
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
