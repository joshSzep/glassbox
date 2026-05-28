import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import type { HandoffDetailState } from "@/stores/dashboard-stores";

import { CockpitPanel, CommandList, redactionVariant } from "./shared";

export function PreviewPanel({ preview }: { preview: HandoffDetailState["preview"] }) {
  if (preview === null) {
    return null;
  }
  const model = preview.preview;
  return (
    <CockpitPanel title="Redaction Preview And Local-Only Inventory">
      <div className="grid gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge variant={redactionVariant(model.redaction.posture)}>
            {model.redaction.posture}
          </Badge>
          <Badge variant={model.local_only_evidence_count > 0 ? "warning" : "muted"}>
            {model.local_only_evidence_count} local-only
          </Badge>
          <Badge variant="outline">{model.intent}</Badge>
        </div>
        <DataList density="compact">
          <DataListItem>
            <DataListLabel>Included sections</DataListLabel>
            <DataListMeta>{(model.included_sections ?? []).join(", ") || "none"}</DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Redacted categories</DataListLabel>
            <DataListMeta>
              {(model.redaction.redacted_categories ?? []).join(", ") || "none"}
            </DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Omitted raw categories</DataListLabel>
            <DataListMeta>{(model.omitted_raw_categories ?? []).join(", ") || "none"}</DataListMeta>
          </DataListItem>
          {model.local_only_inventory.items?.slice(0, 5).map((item) => (
            <DataListItem key={`${item.category}-${item.summary}`}>
              <DataListLabel>{item.category}</DataListLabel>
              <DataListMeta>{item.summary}</DataListMeta>
              <DataListMeta>{item.recipient_limitation}</DataListMeta>
            </DataListItem>
          ))}
        </DataList>
        <CommandList commands={model.safe_inspection_commands ?? []} />
      </div>
    </CockpitPanel>
  );
}
