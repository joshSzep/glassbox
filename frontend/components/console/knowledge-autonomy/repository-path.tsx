import { Database, FileSearch, Loader2 } from "lucide-react";

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

import { repositoryStatusVariant } from "./format";
import {
  repositoryDetailLocation,
  repositoryEntryLocation,
  repositoryJoinedLabels,
  repositoryVerificationSummary,
} from "./repository-format";
import { StateLine } from "./shared";
import type { RepositoryInspectorState } from "./types";

export function PathInspector({
  onRepositoryPathQuery,
  repository,
}: {
  onRepositoryPathQuery?: (path: string) => void;
  repository: RepositoryInspectorState;
}) {
  const inspection = repository.pathInspection;
  const verification = repository.verification;

  return (
    <section
      aria-label="Repository path inspector"
      className="rounded-md border border-border/80 bg-card p-4 shadow-sm"
    >
      <form
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const path = String(form.get("path") ?? "");
          onRepositoryPathQuery?.(path);
        }}
      >
        <Input
          aria-label="Inspect repository path"
          defaultValue={repository.pathQuery}
          key={repository.pathQuery}
          name="path"
          placeholder="src/glassbox/runtime/repository_index.py"
        />
        <Button size="sm" type="submit" variant="outline">
          <FileSearch className={operatorIconSizeClass} aria-hidden="true" />
          Inspect Path
        </Button>
      </form>
      {inspection === null ? (
        <StateLine
          className="mt-3"
          icon={<FileSearch className={operatorIconSizeClass} aria-hidden="true" />}
          value="Choose a path to inspect affected packages, subsystems, recipes, and limits."
        />
      ) : (
        <div className="mt-4 grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(20rem,0.7fr)]">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold tracking-normal break-all">
                {inspection.path}
              </h2>
              <Badge variant={repositoryStatusVariant(inspection.snapshot_status)}>
                {inspection.snapshot_status}
              </Badge>
            </div>
            <DataList className="mt-3" density="compact">
              <DataListItem>
                <DataListLabel>Packages</DataListLabel>
                <DataListMeta>
                  {repositoryJoinedLabels(inspection.packages.map((item) => item.package_id))}
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Subsystems</DataListLabel>
                <DataListMeta>
                  {repositoryJoinedLabels(inspection.subsystems.map((item) => item.name))}
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Owner Hints</DataListLabel>
                <DataListMeta>
                  {repositoryJoinedLabels(
                    inspection.ownership_hints.map((item) => item.owner_label),
                  )}
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Release Surfaces</DataListLabel>
                <DataListMeta>
                  {repositoryJoinedLabels(inspection.release_surfaces.map((item) => item.name))}
                </DataListMeta>
              </DataListItem>
            </DataList>
          </div>
          <div className="min-w-0 rounded-md border border-border/70 p-3">
            <h3 className="text-sm font-semibold tracking-normal">Verification</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {repositoryVerificationSummary(verification)}
            </p>
            {(verification?.next_actions ?? []).length ? (
              <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                {(verification?.next_actions ?? []).slice(0, 3).map((action) => (
                  <li className="break-all" key={action}>
                    {action}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      )}
    </section>
  );
}

export function RepositoryRows({
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
        value="Searching repository intelligence."
      />
    );
  }
  if (repository.items.length === 0) {
    return (
      <StateLine
        icon={<Database className={operatorIconSizeClass} aria-hidden="true" />}
        value="No repository intelligence entries match the current search."
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
              {repositoryEntryLocation(entry)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function RepositoryDetail({ repository }: { repository: RepositoryInspectorState }) {
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
            {repositoryDetailLocation(entry)}
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
