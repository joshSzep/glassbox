"use client";

import { ChevronLeft, RefreshCcw } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type {
  ChangesetActionStatus,
  ChangesetDetailState,
  ChangesetPageState,
} from "@/stores/dashboard-stores";

export type ChangesetConsoleProps = {
  action?: ChangesetActionStatus;
  detail: ChangesetDetailState;
  onRefresh?: () => void;
  onRefreshChangeset?: () => void;
  onSelectChangeset?: (changesetId: string) => void;
  onShowList?: () => void;
  page: ChangesetPageState;
};

export function ChangesetConsole({
  action = { error: null, kind: null, state: "idle" },
  detail,
  onRefresh,
  onRefreshChangeset,
  onSelectChangeset,
  onShowList,
  page,
}: ChangesetConsoleProps) {
  return (
    <main className="min-h-screen bg-surface-subtle px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-5">
        <section
          aria-label="Changeset console status"
          className="grid gap-3 rounded-md border border-border/80 bg-card p-4 shadow-sm lg:grid-cols-[minmax(0,1fr)_auto]"
        >
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Review Console
            </p>
            <h1 className="mt-1 text-lg font-semibold tracking-normal">Changesets</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {page.items.length} local changeset{page.items.length === 1 ? "" : "s"} available for
              basic inspection.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="info">Evidence object</Badge>
            <Button onClick={onRefresh} size="sm" type="button" variant="outline">
              <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
              Refresh
            </Button>
          </div>
        </section>
        {action.state === "failed" && action.error !== null ? (
          <StateLine tone="destructive" value={action.error} />
        ) : null}
        <section className="grid gap-4 xl:grid-cols-[22rem_1fr]">
          <ChangesetList detail={detail} onSelectChangeset={onSelectChangeset} page={page} />
          <ChangesetDetail
            action={action}
            detail={detail}
            onRefreshChangeset={onRefreshChangeset}
            onShowList={onShowList}
          />
        </section>
      </div>
    </main>
  );
}

function ChangesetList({
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

function ChangesetDetail({
  action,
  detail,
  onRefreshChangeset,
  onShowList,
}: {
  action: ChangesetActionStatus;
  detail: ChangesetDetailState;
  onRefreshChangeset?: () => void;
  onShowList?: () => void;
}) {
  if (detail.loadState === "idle") {
    return <StateLine value="Select a changeset to inspect its source evidence." />;
  }
  if (detail.loadState === "failed") {
    return <StateLine tone="destructive" value={detail.error ?? "Unable to load changeset."} />;
  }
  if (detail.detail === null) {
    return <StateLine value="Loading changeset evidence." />;
  }
  const { changeset } = detail.detail;
  const highRisk = changeset.risk_level === "high";
  const inventoryStatus = detail.detail.inventory_status;
  const staleInventory = inventoryStatus.stale || inventoryStatus.freshness === "stale";
  return (
    <article className="rounded-md border border-border/80 bg-card p-4 shadow-sm">
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
            {changeset.unresolved_risk_count > 0 ? (
              <Badge variant="outline">{changeset.unresolved_risk_count} unresolved</Badge>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={onShowList} size="sm" type="button" variant="ghost">
            <ChevronLeft className={operatorIconSizeClass} aria-hidden="true" />
            List
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
      </div>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <Fact label="Session" value={changeset.session_id} />
        <Fact label="Task" value={changeset.task_id ?? "None"} />
        <Fact label="Branch search" value={changeset.branch_search_id ?? "None"} />
        <Fact label="Inventory" value={inventoryStatus.freshness} />
        <Fact label="Risk" value={changeset.risk_summary ?? changeset.risk_level} />
      </dl>
      {inventoryStatus.reason ? (
        <StateLine tone={staleInventory ? "destructive" : "muted"} value={inventoryStatus.reason} />
      ) : null}
      <Section title="Sources">
        {detail.detail.sources.length === 0 ? (
          <p className="text-sm text-muted-foreground">No source records attached.</p>
        ) : (
          <DataList density="compact">
            {detail.detail.sources.map((source) => (
              <DataListItem key={`${source.source_kind}-${source.last_sequence}`}>
                <DataListLabel>{source.source_kind}</DataListLabel>
                <DataListMeta>{source.reason}</DataListMeta>
                {source.limitation ? <DataListMeta>{source.limitation}</DataListMeta> : null}
              </DataListItem>
            ))}
          </DataList>
        )}
      </Section>
      <Section title="Safe Next Actions">
        <ul className="grid gap-2 text-console text-muted-foreground">
          {detail.detail.safe_next_actions.map((item) => (
            <li className="break-all" key={item}>
              {item}
            </li>
          ))}
        </ul>
      </Section>
      {detail.detail.limitations.length > 0 ? (
        <Section title="Limitations">
          <ul className="grid gap-2 text-sm text-muted-foreground">
            {detail.detail.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Section>
      ) : null}
    </article>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-border/70 bg-surface px-3 py-2">
      <dt className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 truncate text-console">{value}</dd>
    </div>
  );
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="mt-4">
      <h3 className="text-sm font-semibold tracking-normal">{title}</h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function StateLine({ tone = "muted", value }: { tone?: "destructive" | "muted"; value: string }) {
  return (
    <div
      className={
        tone === "destructive"
          ? "rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          : "rounded-md border border-border/80 bg-card px-3 py-2 text-sm text-muted-foreground"
      }
    >
      {value}
    </div>
  );
}
