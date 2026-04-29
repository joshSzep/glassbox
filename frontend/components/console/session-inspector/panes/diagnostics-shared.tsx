import { ChevronDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { DetailPageStatus } from "@/stores/dashboard-stores";

export function LoadMoreDetail({
  label,
  onLoadMore,
  page,
}: {
  label: string;
  onLoadMore?: () => void;
  page?: DetailPageStatus;
}) {
  if (page === undefined || !page.hasMore) {
    return null;
  }
  return (
    <div className="mt-3 flex flex-wrap items-center gap-3">
      <Button
        disabled={page.state === "loading"}
        onClick={onLoadMore}
        size="sm"
        type="button"
        variant="outline"
      >
        <ChevronDown className="h-4 w-4" aria-hidden="true" />
        {page.state === "loading" ? "Loading" : `Load more ${label}`}
      </Button>
      {page.error !== null ? (
        <p className="text-xs text-destructive">{page.error}</p>
      ) : (
        <p className="text-xs text-muted-foreground">Next cursor {page.nextCursor}</p>
      )}
    </div>
  );
}
