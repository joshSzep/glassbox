"use client";

import type { ReactNode } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Database,
  FileSearch,
  Loader2,
  RefreshCcw,
  Search,
  ShieldCheck,
  Trash2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import { buildAppRoute } from "@/routing/app-route";
import type {
  KnowledgeActionStatus,
  MemoryFilter,
  MemoryInspectorState,
  RepositoryInspectorState,
} from "@/stores/dashboard-stores";

export type KnowledgeAutonomyConsoleProps = {
  action?: KnowledgeActionStatus;
  anchorSessionId?: string | null;
  memory: MemoryInspectorState;
  onConfirmMemory?: (memoryId: string) => void;
  onInvalidateMemory?: (memoryId: string) => void;
  onMemoryFilter?: (filter: MemoryFilter) => void;
  onMemoryQuery?: (query: string) => void;
  onPreviewPruneMemory?: (memoryId: string) => void;
  onPruneMemory?: (memoryId: string) => void;
  onRebuildRepositoryIndex?: (input?: { background?: boolean; sessionId?: string | null }) => void;
  onRefresh?: () => void;
  onRepositoryQuery?: (query: string) => void;
  onSelectMemory?: (memoryId: string) => void;
  onSelectRepositoryEntry?: (entryId: string) => void;
  repository: RepositoryInspectorState;
  surface: "memory" | "repository";
};

const memoryFilters: Array<{ filter: MemoryFilter; label: string }> = [
  { filter: "active", label: "Active" },
  { filter: "stale", label: "Stale" },
  { filter: "invalidated", label: "Invalidated" },
  { filter: "all", label: "All" },
];

export function KnowledgeAutonomyConsole({
  action = { error: null, kind: null, state: "idle" },
  anchorSessionId = null,
  memory,
  onConfirmMemory,
  onInvalidateMemory,
  onMemoryFilter,
  onMemoryQuery,
  onPreviewPruneMemory,
  onPruneMemory,
  onRebuildRepositoryIndex,
  onRefresh,
  onRepositoryQuery,
  onSelectMemory,
  onSelectRepositoryEntry,
  repository,
  surface,
}: KnowledgeAutonomyConsoleProps) {
  const title = surface === "memory" ? "Memory Inspector" : "Repository Index";

  return (
    <main className="min-h-screen bg-surface-subtle px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-5">
        <section
          aria-label="Knowledge console status"
          className="grid gap-3 rounded-md border border-border/80 bg-card p-4 shadow-sm lg:grid-cols-[minmax(0,1fr)_auto]"
        >
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Autonomy Console
            </p>
            <h1 className="mt-1 text-lg font-semibold tracking-normal">{title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {surface === "memory"
                ? memorySummary(memory)
                : repositorySummary(repository, anchorSessionId)}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <SurfaceLink current={surface === "memory"} href="/app/memory">
              Memory
            </SurfaceLink>
            <SurfaceLink current={surface === "repository"} href="/app/repository-index">
              Repository
            </SurfaceLink>
            <Button onClick={onRefresh} size="sm" type="button" variant="outline">
              <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
              Refresh
            </Button>
          </div>
        </section>

        {action.state === "failed" && action.error !== null ? (
          <StateLine tone="destructive" value={action.error} />
        ) : null}

        {surface === "memory" ? (
          <MemoryInspector
            action={action}
            memory={memory}
            onConfirmMemory={onConfirmMemory}
            onInvalidateMemory={onInvalidateMemory}
            onMemoryFilter={onMemoryFilter}
            onMemoryQuery={onMemoryQuery}
            onPreviewPruneMemory={onPreviewPruneMemory}
            onPruneMemory={onPruneMemory}
            onSelectMemory={onSelectMemory}
          />
        ) : (
          <RepositoryIndexInspector
            action={action}
            anchorSessionId={anchorSessionId}
            onRebuildRepositoryIndex={onRebuildRepositoryIndex}
            onRepositoryQuery={onRepositoryQuery}
            onSelectRepositoryEntry={onSelectRepositoryEntry}
            repository={repository}
          />
        )}
      </div>
    </main>
  );
}

function SurfaceLink({
  children,
  current,
  href,
}: {
  children: ReactNode;
  current: boolean;
  href: string;
}) {
  return (
    <a
      aria-current={current ? "page" : undefined}
      className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        current
          ? "border-accent bg-accent text-accent-foreground"
          : "border-border bg-surface hover:bg-surface-raised"
      }`}
      href={href}
    >
      {children}
    </a>
  );
}

function MemoryInspector({
  action,
  memory,
  onConfirmMemory,
  onInvalidateMemory,
  onMemoryFilter,
  onMemoryQuery,
  onPreviewPruneMemory,
  onPruneMemory,
  onSelectMemory,
}: {
  action: KnowledgeActionStatus;
  memory: MemoryInspectorState;
  onConfirmMemory?: (memoryId: string) => void;
  onInvalidateMemory?: (memoryId: string) => void;
  onMemoryFilter?: (filter: MemoryFilter) => void;
  onMemoryQuery?: (query: string) => void;
  onPreviewPruneMemory?: (memoryId: string) => void;
  onPruneMemory?: (memoryId: string) => void;
  onSelectMemory?: (memoryId: string) => void;
}) {
  return (
    <section className="grid gap-4 xl:grid-cols-[18rem_1fr]">
      <aside className="rounded-md border border-border/80 bg-card p-3 shadow-sm">
        <div className="mb-3 flex items-center justify-between gap-3 px-1">
          <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
            Memory Filters
          </h2>
          <Badge variant="muted">{memory.items.length}</Badge>
        </div>
        <div className="grid gap-1">
          {memoryFilters.map((item) => (
            <button
              aria-pressed={memory.filter === item.filter}
              className={`grid min-h-density-row rounded-md px-3 py-2 text-left text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                memory.filter === item.filter
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-surface-raised"
              }`}
              key={item.filter}
              onClick={() => onMemoryFilter?.(item.filter)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
        <label className="mt-4 block text-xs font-medium uppercase tracking-normal text-muted-foreground">
          Search
        </label>
        <Input
          className="mt-2"
          defaultValue={memory.query}
          onBlur={(event) => onMemoryQuery?.(event.currentTarget.value)}
          placeholder="source, tag, content"
        />
      </aside>

      <section className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(28rem,0.8fr)]">
        <MemoryRows memory={memory} onSelectMemory={onSelectMemory} />
        <MemoryDetail
          action={action}
          memory={memory}
          onConfirmMemory={onConfirmMemory}
          onInvalidateMemory={onInvalidateMemory}
          onPreviewPruneMemory={onPreviewPruneMemory}
          onPruneMemory={onPruneMemory}
        />
      </section>
    </section>
  );
}

function MemoryRows({
  memory,
  onSelectMemory,
}: {
  memory: MemoryInspectorState;
  onSelectMemory?: (memoryId: string) => void;
}) {
  if (memory.error !== null) {
    return <StateLine tone="destructive" value={memory.error} />;
  }
  if (memory.loadState === "loading" && memory.items.length === 0) {
    return (
      <StateLine
        icon={<Loader2 className={operatorIconSizeClass} aria-hidden="true" />}
        value="Loading workspace memory."
      />
    );
  }
  if (memory.items.length === 0) {
    return (
      <StateLine
        icon={<CheckCircle2 className={operatorIconSizeClass} aria-hidden="true" />}
        value={`No ${memory.filter} memory entries.`}
      />
    );
  }

  return (
    <section aria-label="Workspace memory rows" className="min-w-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Memory</TableHead>
            <TableHead>State</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Use</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {memory.items.map((entry) => (
            <TableRow
              aria-selected={memory.selectedMemoryId === entry.memory_id}
              className="cursor-pointer"
              key={entry.memory_id}
              onClick={() => onSelectMemory?.(entry.memory_id)}
            >
              <TableCell>
                <a
                  className="font-medium text-primary underline-offset-2 hover:underline"
                  href={buildAppRoute({
                    compareSessionId: null,
                    queue: "all",
                    selectedSessionId: null,
                    selectedTaskId: null,
                    surface: "memory",
                    tab: "overview",
                    taskQueue: "active",
                  })}
                  onClick={(event) => {
                    event.preventDefault();
                    onSelectMemory?.(entry.memory_id);
                  }}
                >
                  {entry.summary ?? entry.content}
                </a>
                <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{entry.content}</p>
              </TableCell>
              <TableCell>
                <Badge variant={memoryStateVariant(entry.state)}>{entry.state}</Badge>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {memorySourceLabel(entry)}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {entry.use_count} use{entry.use_count === 1 ? "" : "s"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </section>
  );
}

function MemoryDetail({
  action,
  memory,
  onConfirmMemory,
  onInvalidateMemory,
  onPreviewPruneMemory,
  onPruneMemory,
}: {
  action: KnowledgeActionStatus;
  memory: MemoryInspectorState;
  onConfirmMemory?: (memoryId: string) => void;
  onInvalidateMemory?: (memoryId: string) => void;
  onPreviewPruneMemory?: (memoryId: string) => void;
  onPruneMemory?: (memoryId: string) => void;
}) {
  const entry = memory.selectedEntry;
  if (entry === null) {
    return (
      <StateLine
        icon={<FileSearch className={operatorIconSizeClass} aria-hidden="true" />}
        value="Select memory to inspect provenance, freshness, and usage evidence."
      />
    );
  }

  const actionDisabled = action.state === "pending";
  return (
    <section
      aria-label="Workspace memory detail"
      className="rounded-md border border-border/80 bg-card p-4 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold tracking-normal">Memory Evidence</h2>
          <p className="mt-1 break-words text-sm text-muted-foreground">{entry.summary}</p>
        </div>
        <Badge variant={memoryStateVariant(entry.state)}>{entry.state}</Badge>
      </div>
      <p className="mt-3 whitespace-pre-wrap break-words text-sm">{entry.content}</p>
      <DataList className="mt-4" density="compact">
        <DataListItem>
          <DataListLabel>Source</DataListLabel>
          <DataListMeta>{memorySourceLabel(entry)}</DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Freshness</DataListLabel>
          <DataListMeta>
            confirmed {formatMaybeDate(entry.confirmed_at)} by {entry.confirmed_by ?? "unknown"}
          </DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Usage</DataListLabel>
          <DataListMeta>
            {entry.use_count} prompt use{entry.use_count === 1 ? "" : "s"}; last used{" "}
            {formatMaybeDate(entry.last_used_at)}
          </DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Tags</DataListLabel>
          <DataListMeta>{entry.tags.length > 0 ? entry.tags.join(", ") : "none"}</DataListMeta>
        </DataListItem>
      </DataList>
      {memory.preview !== null && memory.preview.entry.memory_id === entry.memory_id ? (
        <div className="mt-4 rounded-md border border-border/80 bg-surface p-3 text-sm">
          <p className="font-medium">Prune preview</p>
          <p className="mt-1 text-muted-foreground">
            {memory.preview.would_prune
              ? "This entry would be pruned from active retrieval and retained as history."
              : "This entry is already pruned."}
          </p>
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          disabled={actionDisabled}
          onClick={() => onConfirmMemory?.(entry.memory_id)}
          size="sm"
          type="button"
          variant="outline"
        >
          <ShieldCheck className={operatorIconSizeClass} aria-hidden="true" />
          Confirm
        </Button>
        <Button
          disabled={actionDisabled}
          onClick={() => onInvalidateMemory?.(entry.memory_id)}
          size="sm"
          type="button"
          variant="outline"
        >
          <AlertCircle className={operatorIconSizeClass} aria-hidden="true" />
          Invalidate
        </Button>
        <Button
          disabled={actionDisabled}
          onClick={() => onPreviewPruneMemory?.(entry.memory_id)}
          size="sm"
          type="button"
          variant="outline"
        >
          <FileSearch className={operatorIconSizeClass} aria-hidden="true" />
          Preview Prune
        </Button>
        <Button
          disabled={actionDisabled}
          onClick={() => onPruneMemory?.(entry.memory_id)}
          size="sm"
          type="button"
          variant="destructive"
        >
          <Trash2 className={operatorIconSizeClass} aria-hidden="true" />
          Prune
        </Button>
      </div>
    </section>
  );
}

function RepositoryIndexInspector({
  action,
  anchorSessionId,
  onRebuildRepositoryIndex,
  onRepositoryQuery,
  onSelectRepositoryEntry,
  repository,
}: {
  action: KnowledgeActionStatus;
  anchorSessionId: string | null;
  onRebuildRepositoryIndex?: (input?: { background?: boolean; sessionId?: string | null }) => void;
  onRepositoryQuery?: (query: string) => void;
  onSelectRepositoryEntry?: (entryId: string) => void;
  repository: RepositoryInspectorState;
}) {
  return (
    <section className="grid gap-4 xl:grid-cols-[18rem_1fr]">
      <aside className="rounded-md border border-border/80 bg-card p-3 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
            Index Status
          </h2>
          <Badge variant={repositoryStatusVariant(repository.status?.status)}>
            {repository.status?.status ?? repository.statusState}
          </Badge>
        </div>
        <DataList className="mt-3" density="compact">
          <DataListItem>
            <DataListLabel>Entries</DataListLabel>
            <DataListMeta>{repository.status?.entry_count ?? 0}</DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Built</DataListLabel>
            <DataListMeta>{formatMaybeDate(repository.status?.built_at ?? null)}</DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Digest</DataListLabel>
            <DataListMeta>{repository.status?.source_digest ?? "not available"}</DataListMeta>
          </DataListItem>
        </DataList>
        {repository.status?.status !== "fresh" ? (
          <StateLine
            className="mt-3"
            icon={<AlertCircle className={operatorIconSizeClass} aria-hidden="true" />}
            tone="warning"
            value={repository.status?.detail ?? "Repository index needs a rebuild."}
          />
        ) : null}
        <Button
          className="mt-3 w-full"
          disabled={action.state === "pending"}
          onClick={() =>
            onRebuildRepositoryIndex?.({ background: true, sessionId: anchorSessionId })
          }
          size="sm"
          type="button"
          variant="outline"
        >
          <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
          Rebuild Index
        </Button>
        {repository.rebuild !== null ? (
          <p className="mt-2 text-xs text-muted-foreground">
            Last rebuild: {repository.rebuild.mode} {repository.rebuild.status}
          </p>
        ) : null}
      </aside>

      <section className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(28rem,0.8fr)]">
        <section aria-label="Repository index search" className="min-w-0">
          <div className="mb-3 flex gap-2">
            <Input
              defaultValue={repository.query}
              onBlur={(event) => onRepositoryQuery?.(event.currentTarget.value)}
              placeholder="symbol, path, command, test"
            />
            <Button
              onClick={() => onRepositoryQuery?.(repository.query)}
              size="sm"
              type="button"
              variant="outline"
            >
              <Search className={operatorIconSizeClass} aria-hidden="true" />
              Search
            </Button>
          </div>
          <RepositoryRows
            repository={repository}
            onSelectRepositoryEntry={onSelectRepositoryEntry}
          />
        </section>
        <RepositoryDetail repository={repository} />
      </section>
    </section>
  );
}

function RepositoryRows({
  onSelectRepositoryEntry,
  repository,
}: {
  onSelectRepositoryEntry?: (entryId: string) => void;
  repository: RepositoryInspectorState;
}) {
  if (repository.error !== null && repository.searchState === "failed") {
    return <StateLine tone="destructive" value={repository.error} />;
  }
  if (repository.searchState === "loading" && repository.items.length === 0) {
    return (
      <StateLine
        icon={<Loader2 className={operatorIconSizeClass} aria-hidden="true" />}
        value="Searching repository index."
      />
    );
  }
  if (repository.items.length === 0) {
    return (
      <StateLine
        icon={<Database className={operatorIconSizeClass} aria-hidden="true" />}
        value="No repository index entries match the current search."
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Entity</TableHead>
          <TableHead>Kind</TableHead>
          <TableHead>Path</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {repository.items.map((entry) => (
          <TableRow
            aria-selected={repository.selectedEntryId === entry.entry_id}
            className="cursor-pointer"
            key={entry.entry_id}
            onClick={() => onSelectRepositoryEntry?.(entry.entry_id)}
          >
            <TableCell>
              <span className="font-medium">{entry.name}</span>
              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{entry.summary}</p>
            </TableCell>
            <TableCell>
              <Badge variant="outline">{entry.kind}</Badge>
            </TableCell>
            <TableCell className="break-all text-xs text-muted-foreground">
              {entry.path ?? entry.symbol ?? "workspace"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function RepositoryDetail({ repository }: { repository: RepositoryInspectorState }) {
  const entry = repository.selectedEntry;
  if (entry === null) {
    return (
      <StateLine
        icon={<FileSearch className={operatorIconSizeClass} aria-hidden="true" />}
        value="Select an index entry to inspect provenance and freshness."
      />
    );
  }

  return (
    <section
      aria-label="Repository index detail"
      className="rounded-md border border-border/80 bg-card p-4 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold tracking-normal">{entry.name}</h2>
          <p className="mt-1 break-all text-sm text-muted-foreground">
            {entry.path ?? entry.symbol ?? entry.entry_id}
          </p>
        </div>
        <Badge variant="outline">{entry.kind}</Badge>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">
        {entry.summary ?? "No summary retained for this index entry."}
      </p>
      <DataList className="mt-4" density="compact">
        {entry.provenance.map((source, index) => (
          <DataListItem key={`${source.source_type}:${source.path ?? index}`}>
            <DataListLabel>{source.source_type}</DataListLabel>
            <DataListMeta>
              {source.path ?? source.source_label ?? "operator hint"}
              {source.line_start !== null ? `:${source.line_start}` : ""}
            </DataListMeta>
          </DataListItem>
        ))}
      </DataList>
    </section>
  );
}

function StateLine({
  className = "",
  icon,
  tone = "muted",
  value,
}: {
  className?: string;
  icon?: ReactNode;
  tone?: "destructive" | "muted" | "warning";
  value: string;
}) {
  const toneClass =
    tone === "destructive"
      ? "border-destructive/40 text-destructive"
      : tone === "warning"
        ? "border-warning/50 text-warning-foreground"
        : "border-border/80 text-muted-foreground";
  return (
    <div className={`rounded-md border bg-card p-4 text-sm shadow-sm ${toneClass} ${className}`}>
      <span className="flex items-center gap-2">
        {icon}
        {value}
      </span>
    </div>
  );
}

function memorySummary(memory: MemoryInspectorState): string {
  return `${memory.items.length} ${memory.filter} workspace memory entries with provenance, freshness, and usage evidence.`;
}

function repositorySummary(repository: RepositoryInspectorState, anchorSessionId: string | null) {
  const anchor =
    anchorSessionId === null ? "no session anchor" : `session ${shortId(anchorSessionId)}`;
  return `${repository.status?.entry_count ?? 0} indexed entities; ${anchor} for background rebuilds.`;
}

function memorySourceLabel(entry: MemoryInspectorState["items"][number]): string {
  const source = entry.provenance;
  const sourceType = source.source_type ?? "source";
  if (source.source_label != null) {
    return source.source_label;
  }
  if (source.session_id != null) {
    return `${sourceType} ${shortId(source.session_id)}#${source.source_sequence ?? 0}`;
  }
  if (source.artifact_id != null) {
    return `${sourceType} ${shortId(source.artifact_id)}`;
  }
  return sourceType;
}

function memoryStateVariant(state: string) {
  if (state === "active") {
    return "success" as const;
  }
  if (state === "stale" || state === "imported") {
    return "warning" as const;
  }
  if (state === "invalidated" || state === "pruned") {
    return "destructive" as const;
  }
  return "muted" as const;
}

function repositoryStatusVariant(status: string | undefined) {
  if (status === "fresh") {
    return "success" as const;
  }
  if (status === "missing" || status === "stale" || status === "building") {
    return "warning" as const;
  }
  if (status === "failed") {
    return "destructive" as const;
  }
  return "muted" as const;
}

function formatMaybeDate(value: string | null | undefined): string {
  if (value === null || value === undefined) {
    return "not recorded";
  }
  return new Date(value).toLocaleString();
}

function shortId(value: string): string {
  return value.length <= 10 ? value : `${value.slice(0, 8)}...`;
}
