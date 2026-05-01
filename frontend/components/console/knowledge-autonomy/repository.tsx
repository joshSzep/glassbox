"use client";

import { AlertCircle, Database, FileSearch, Loader2, RefreshCcw, Search } from "lucide-react";

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

import { formatMaybeDate, repositoryStatusVariant } from "./format";
import { StateLine } from "./shared";
import type { KnowledgeActionStatus, RepositoryInspectorState } from "./types";

export function RepositoryIndexInspector({
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
              aria-label="Search repository index"
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
            key={entry.entry_id}
          >
            <TableCell>
              <button
                className="rounded-sm text-left font-medium text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => onSelectRepositoryEntry?.(entry.entry_id)}
                type="button"
              >
                {entry.name}
              </button>
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
