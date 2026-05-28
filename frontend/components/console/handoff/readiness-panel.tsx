import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import type { HandoffDetailState } from "@/stores/dashboard-stores";

import { CommandList } from "./command-list";
import { readinessVariant } from "./format";
import { NonClaims } from "./non-claims";
import { CockpitPanel } from "./shared";

export function ReadinessPanel({ readiness }: { readiness: HandoffDetailState["readiness"] }) {
  if (readiness === null) {
    return null;
  }
  const model = readiness.readiness;
  return (
    <CockpitPanel title="Readiness Summary">
      <div className="grid gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge variant={readinessVariant(model.state)}>{model.state}</Badge>
          <Badge variant="outline">{model.intent}</Badge>
          <Badge variant="muted">{model.freshness}</Badge>
          <Badge variant="muted">{model.confidence}</Badge>
        </div>
        <DataList density="compact">
          <DataListItem>
            <DataListLabel>{model.source.label ?? model.source.kind}</DataListLabel>
            <DataListMeta>
              {model.source.kind} {model.source.primary_id ?? "workspace"}
            </DataListMeta>
          </DataListItem>
          {model.reasons?.slice(0, 5).map((reason) => (
            <DataListItem key={`${reason.kind}-${reason.summary}`}>
              <DataListLabel>{reason.kind}</DataListLabel>
              <DataListMeta>{reason.summary}</DataListMeta>
              {reason.limitation ? <DataListMeta>{reason.limitation}</DataListMeta> : null}
            </DataListItem>
          ))}
        </DataList>
        <CommandList commands={model.safe_first_commands ?? []} />
        <NonClaims claims={model.non_claims ?? []} />
      </div>
    </CockpitPanel>
  );
}
