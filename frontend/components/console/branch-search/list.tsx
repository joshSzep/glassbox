"use client";

import { CheckCircle2, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { BranchSearchDetailState, BranchSearchPageState } from "@/stores/dashboard-stores";

import { StateLine } from "./shared";

export function BranchSearchList({
  detail,
  onSelectSearch,
  page,
}: {
  detail: BranchSearchDetailState;
  onSelectSearch?: (searchId: string) => void;
  page: BranchSearchPageState;
}) {
  if (page.error !== null) {
    return <StateLine tone="destructive" value={page.error} />;
  }
  if (page.loadState === "loading" && page.items.length === 0) {
    return (
      <StateLine
        icon={<Loader2 className={operatorIconSizeClass} aria-hidden="true" />}
        value="Loading branch searches."
      />
    );
  }
  if (page.items.length === 0) {
    return (
      <StateLine
        icon={<CheckCircle2 className={operatorIconSizeClass} aria-hidden="true" />}
        value="No branch searches are available."
      />
    );
  }

  return (
    <aside
      aria-label="Branch search list"
      className="rounded-md border border-border/80 bg-card p-3 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between gap-3 px-1">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          Searches
        </h2>
        <Badge variant="muted">{page.items.length}</Badge>
      </div>
      <div className="grid gap-2">
        {page.items.map((search) => (
          <button
            aria-pressed={detail.selectedSearchId === search.search_id}
            className={`grid rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
              detail.selectedSearchId === search.search_id
                ? "border-accent bg-accent text-accent-foreground"
                : "border-border/70 hover:bg-surface-raised"
            }`}
            key={search.search_id}
            onClick={() => onSelectSearch?.(search.search_id)}
            type="button"
          >
            <span className="text-sm font-medium">{search.objective}</span>
            <span className="mt-1 text-xs text-muted-foreground">
              {search.candidate_count} candidates · {search.status}
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}
