"use client";

import { RefreshCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  BranchSearchDetail,
  BranchSearchList,
  StateLine,
} from "@/components/console/branch-search-sections";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type {
  BranchSearchActionStatus,
  BranchSearchDetailState,
  BranchSearchPageState,
} from "@/stores/dashboard-stores";

export type BranchSearchConsoleProps = {
  action?: BranchSearchActionStatus;
  detail: BranchSearchDetailState;
  onMarkCandidate?: (input: {
    action: "needs-review" | "reject" | "select";
    candidateId: string;
    searchId: string;
  }) => void;
  onRefresh?: () => void;
  onSelectSearch?: (searchId: string) => void;
  page: BranchSearchPageState;
};

export function BranchSearchConsole({
  action = { error: null, kind: null, state: "idle" },
  detail,
  onMarkCandidate,
  onRefresh,
  onSelectSearch,
  page,
}: BranchSearchConsoleProps) {
  return (
    <main className="min-h-screen bg-surface-subtle px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-5">
        <section
          aria-label="Branch search console status"
          className="grid gap-3 rounded-md border border-border/80 bg-card p-4 shadow-sm lg:grid-cols-[minmax(0,1fr)_auto]"
        >
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Autonomy Console
            </p>
            <h1 className="mt-1 text-lg font-semibold tracking-normal">Branch Search</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {page.items.length} branch-search comparison{page.items.length === 1 ? "" : "s"}{" "}
              available for candidate review.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="info">Metadata only</Badge>
            <Button onClick={onRefresh} size="sm" type="button" variant="outline">
              <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
              Refresh
            </Button>
          </div>
        </section>
        {action.state === "failed" && action.error !== null ? (
          <StateLine tone="destructive" value={action.error} />
        ) : null}
        <section className="grid gap-4 xl:grid-cols-[20rem_1fr]">
          <BranchSearchList detail={detail} onSelectSearch={onSelectSearch} page={page} />
          <BranchSearchDetail action={action} detail={detail} onMarkCandidate={onMarkCandidate} />
        </section>
      </div>
    </main>
  );
}
