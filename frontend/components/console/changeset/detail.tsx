import { Badge } from "@/components/ui/badge";
import type { ChangesetActionStatus, ChangesetDetailState } from "@/stores/dashboard-stores";

import { formatVerificationState, verificationBadgeVariant } from "./format";
import { ChangesetDetailActions } from "./actions";

type ChangesetDetailRecord = NonNullable<ChangesetDetailState["detail"]>;

export function ChangesetDetailHeader({
  action,
  briefCount,
  changeset,
  inventoryStatus,
  onGenerateReviewBrief,
  onRefreshChangeset,
  onShowList,
  verificationState,
}: {
  action: ChangesetActionStatus;
  briefCount: number;
  changeset: ChangesetDetailRecord["changeset"];
  inventoryStatus: ChangesetDetailRecord["inventory_status"];
  onGenerateReviewBrief?: () => void;
  onRefreshChangeset?: () => void;
  onShowList?: () => void;
  verificationState: string;
}) {
  const highRisk = changeset.risk_level === "high";
  const staleInventory = inventoryStatus.stale || inventoryStatus.freshness === "stale";

  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
          {changeset.status}
        </p>
        <h2 className="mt-1 text-base font-semibold tracking-normal">{changeset.objective}</h2>
        <p className="mt-1 break-all text-console text-muted-foreground">
          {changeset.changeset_id}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge variant={highRisk ? "warning" : "muted"}>Risk {changeset.risk_level}</Badge>
          <Badge variant={staleInventory ? "warning" : "muted"}>
            Inventory {inventoryStatus.freshness}
          </Badge>
          <Badge variant={verificationBadgeVariant(verificationState)}>
            Verification {formatVerificationState(verificationState)}
          </Badge>
          {changeset.unresolved_risk_count > 0 ? (
            <Badge variant="outline">{changeset.unresolved_risk_count} unresolved</Badge>
          ) : null}
        </div>
      </div>
      <ChangesetDetailActions
        action={action}
        briefCount={briefCount}
        onGenerateReviewBrief={onGenerateReviewBrief}
        onRefreshChangeset={onRefreshChangeset}
        onShowList={onShowList}
      />
    </div>
  );
}
