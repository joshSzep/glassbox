import { RefreshCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { HandoffDetailState, HandoffPageState } from "@/stores/dashboard-stores";

import { custodyVariant } from "./format";
import { CockpitPanel, StateLine } from "./shared";

export function HandoffRecordsPanel({
  list,
  onLoadList,
  onSelectHandoff,
  selected,
}: {
  list: HandoffPageState;
  onLoadList?: () => void;
  onSelectHandoff?: (record: HandoffPageState["items"][number]) => void;
  selected: HandoffDetailState["selected"];
}) {
  const selectedRecord = selected?.record ?? null;

  return (
    <CockpitPanel title="Handoff Records">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Projected handoff rows remain local workflow evidence.
        </p>
        <Button onClick={onLoadList} size="sm" type="button" variant="outline">
          <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
          Refresh
        </Button>
      </div>
      {list.error !== null ? (
        <StateLine tone="destructive">{list.error}</StateLine>
      ) : list.loadState === "loading" ? (
        <StateLine>Loading handoff records.</StateLine>
      ) : list.items.length === 0 ? (
        <StateLine>No handoff records are projected yet.</StateLine>
      ) : (
        <DataList density="compact">
          {list.items.map((item) => (
            <button
              className={`grid min-h-density-row gap-1 px-3 py-2 text-left transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                selectedRecord?.package_id === item.record.package_id
                  ? "bg-accent text-accent-foreground"
                  : ""
              }`}
              key={`${item.record.session_id}-${item.record.package_id}`}
              onClick={() => onSelectHandoff?.(item)}
              type="button"
            >
              <span className="flex flex-wrap items-center gap-2 text-sm font-medium">
                {item.record.package_id}
                <Badge variant={custodyVariant(item.record.custody_state)}>
                  {item.record.custody_state}
                </Badge>
              </span>
              <span className="text-xs text-muted-foreground">
                {item.record.source_kind} {item.record.source_id ?? item.record.session_id}
              </span>
              <span className="text-xs text-muted-foreground">
                {item.record.intent ?? "intent unknown"} - {item.action_state}
              </span>
            </button>
          ))}
        </DataList>
      )}
    </CockpitPanel>
  );
}
