import { ChevronLeft, FileText, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { ChangesetActionStatus } from "@/stores/dashboard-stores";

export function ChangesetDetailActions({
  action,
  briefCount,
  onGenerateReviewBrief,
  onRefreshChangeset,
  onShowList,
}: {
  action: ChangesetActionStatus;
  briefCount: number;
  onGenerateReviewBrief?: () => void;
  onRefreshChangeset?: () => void;
  onShowList?: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button onClick={onShowList} size="sm" type="button" variant="ghost">
        <ChevronLeft className={operatorIconSizeClass} aria-hidden="true" />
        List
      </Button>
      <Button
        disabled={action.state === "pending"}
        onClick={onGenerateReviewBrief}
        size="sm"
        type="button"
        variant={briefCount > 0 ? "outline" : "default"}
      >
        <FileText className={operatorIconSizeClass} aria-hidden="true" />
        Brief
      </Button>
      <Button
        disabled={action.state === "pending"}
        onClick={onRefreshChangeset}
        size="sm"
        type="button"
        variant="outline"
      >
        <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
        Refresh
      </Button>
    </div>
  );
}
