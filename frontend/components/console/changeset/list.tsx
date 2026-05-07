import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import type { ChangesetDetailState, ChangesetPageState } from "@/stores/dashboard-stores";

import { StateLine } from "./shared";

export function ChangesetList({
  detail,
  onSelectChangeset,
  page,
}: {
  detail: ChangesetDetailState;
  onSelectChangeset?: (changesetId: string) => void;
  page: ChangesetPageState;
}) {
  if (page.loadState === "failed") {
    return <StateLine tone="destructive" value={page.error ?? "Unable to load changesets."} />;
  }
  if (page.items.length === 0) {
    return <StateLine value="No changesets found." />;
  }
  return (
    <DataList density="compact">
      {page.items.map((changeset) => (
        <DataListItem
          className={
            changeset.changeset_id === detail.selectedChangesetId ? "bg-surface-raised" : ""
          }
          key={changeset.changeset_id}
        >
          <button
            className="grid min-w-0 gap-1 text-left"
            onClick={() => onSelectChangeset?.(changeset.changeset_id)}
            type="button"
          >
            <DataListLabel className="truncate">{changeset.objective}</DataListLabel>
            <DataListMeta className="truncate">
              {changeset.status} - risk {changeset.risk_level} - {changeset.changeset_id}
            </DataListMeta>
          </button>
        </DataListItem>
      ))}
    </DataList>
  );
}
