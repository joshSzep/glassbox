import type { ReactNode } from "react";
import {
  AlertCircle,
  Boxes,
  Brain,
  ClipboardList,
  Database,
  FileSearch,
  Loader2,
  RefreshCcw,
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

import { formatMaybeDate, repositoryStatusVariant, shortId } from "./format";
import { StateLine } from "./shared";
import type { KnowledgeActionStatus, RepositoryInspectorState } from "./types";

export function RepositoryStatusPanel({
  action,
  anchorSessionId,
  onRebuildRepositoryIndex,
  repository,
}: {
  action: KnowledgeActionStatus;
  anchorSessionId: string | null;
  onRebuildRepositoryIndex?: (input?: { background?: boolean; sessionId?: string | null }) => void;
  repository: RepositoryInspectorState;
}) {
  const status = repository.status?.status ?? repository.statusState;
  const cues = repository.freshness?.cues ?? repository.status?.freshness_cues ?? [];

  return (
    <aside className="rounded-md border border-border/80 bg-card p-3 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          Intelligence Status
        </h2>
        <Badge variant={repositoryStatusVariant(repository.status?.status)}>{status}</Badge>
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
          <DataListLabel>Recipes</DataListLabel>
          <DataListMeta>{repository.status?.command_recipe_count ?? 0}</DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Subsystems</DataListLabel>
          <DataListMeta>{repository.status?.subsystem_count ?? 0}</DataListMeta>
        </DataListItem>
      </DataList>
      {repository.status?.status !== "fresh" ? (
        <StateLine
          className="mt-3"
          icon={<AlertCircle className={operatorIconSizeClass} aria-hidden="true" />}
          tone="warning"
          value={repository.status?.detail ?? "Repository intelligence needs a refresh."}
        />
      ) : null}
      {cues.length > 0 ? (
        <div className="mt-3 space-y-2">
          {cues.slice(0, 3).map((cue) => (
            <StateLine
              icon={<AlertCircle className={operatorIconSizeClass} aria-hidden="true" />}
              key={`${cue.source}:${cue.reason}`}
              tone={cue.severity === "warning" ? "warning" : "muted"}
              value={`${cue.source}: ${cue.state} - ${cue.detail}`}
            />
          ))}
        </div>
      ) : null}
      <Button
        className="mt-3 w-full"
        disabled={action.state === "pending"}
        onClick={() => onRebuildRepositoryIndex?.({ background: true, sessionId: anchorSessionId })}
        size="sm"
        type="button"
        variant="outline"
      >
        <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
        Refresh Intelligence
      </Button>
      {repository.rebuild !== null ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Last rebuild: {repository.rebuild.mode} {repository.rebuild.status}
        </p>
      ) : null}
    </aside>
  );
}

export function RepositoryMap({ repository }: { repository: RepositoryInspectorState }) {
  const overview = repository.overview;
  if (repository.statusState === "loading" && overview === null) {
    return (
      <StateLine
        icon={<Loader2 className={operatorIconSizeClass} aria-hidden="true" />}
        value="Loading repository intelligence."
      />
    );
  }
  if (overview === null) {
    return (
      <StateLine
        icon={<Boxes className={operatorIconSizeClass} aria-hidden="true" />}
        value="Repository map is unavailable until the intelligence snapshot is built."
      />
    );
  }

  return (
    <section
      aria-label="Repository intelligence map"
      className="rounded-md border border-border/80 bg-card p-4 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold tracking-normal">Repository Map</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {overview.package_boundaries.length} packages, {overview.subsystems.length} subsystems,{" "}
            {overview.release_surfaces.length} release-sensitive surfaces.
          </p>
        </div>
        <Badge variant={repositoryStatusVariant(overview.index.status)}>
          {overview.index.status}
        </Badge>
      </div>
      <DataList className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4" density="compact">
        <DataListItem>
          <DataListLabel>Source Roots</DataListLabel>
          <DataListMeta>{overview.source_roots.length}</DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Test Roots</DataListLabel>
          <DataListMeta>{overview.test_roots.length}</DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Docs Roots</DataListLabel>
          <DataListMeta>{overview.doc_roots.length}</DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Generated Paths</DataListLabel>
          <DataListMeta>{overview.generated_paths.length}</DataListMeta>
        </DataListItem>
      </DataList>
      <div className="mt-4 grid min-w-0 gap-3 xl:grid-cols-3">
        <InlineList
          icon={<Boxes className={operatorIconSizeClass} aria-hidden="true" />}
          items={overview.source_roots.map((root) => root.path)}
          title="Source"
        />
        <InlineList
          icon={<FileSearch className={operatorIconSizeClass} aria-hidden="true" />}
          items={overview.test_roots.map((root) => root.path)}
          title="Tests"
        />
        <InlineList
          icon={<ClipboardList className={operatorIconSizeClass} aria-hidden="true" />}
          items={overview.release_surfaces.map((surface) => surface.name)}
          title="Release"
        />
      </div>
    </section>
  );
}

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
                  {inspection.packages.map((item) => item.package_id).join(", ") || "none"}
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Subsystems</DataListLabel>
                <DataListMeta>
                  {inspection.subsystems.map((item) => item.name).join(", ") || "none"}
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Owner Hints</DataListLabel>
                <DataListMeta>
                  {inspection.ownership_hints.map((item) => item.owner_label).join(", ") || "none"}
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Release Surfaces</DataListLabel>
                <DataListMeta>
                  {inspection.release_surfaces.map((item) => item.name).join(", ") || "none"}
                </DataListMeta>
              </DataListItem>
            </DataList>
          </div>
          <div className="min-w-0 rounded-md border border-border/70 p-3">
            <h3 className="text-sm font-semibold tracking-normal">Verification</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {verification?.status === "ok"
                ? (verification.report?.cheapest_next_command ??
                  verification.next_actions?.[0] ??
                  "Recommendation report loaded.")
                : (verification?.detail ??
                  "Verification recommendations load after a path is inspected.")}
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
              {entry.path ?? entry.symbol ?? "workspace"}
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

export function CommandRecipeBrowser({ repository }: { repository: RepositoryInspectorState }) {
  return (
    <section
      aria-label="Repository command recipes"
      className="min-w-0 rounded-md border border-border/80 bg-card p-4 shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-normal">Command Recipes</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Advisory commands with source, confidence, and policy risk.
          </p>
        </div>
        <Badge variant="outline">{repository.commandRecipes.length}</Badge>
      </div>
      {repository.commandRecipes.length === 0 ? (
        <StateLine
          className="mt-3"
          icon={<ClipboardList className={operatorIconSizeClass} aria-hidden="true" />}
          value="No command recipes are available."
        />
      ) : (
        <Table className="mt-3">
          <TableHeader>
            <TableRow>
              <TableHead>Recipe</TableHead>
              <TableHead>Risk</TableHead>
              <TableHead>Command</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {repository.commandRecipes.slice(0, 8).map((recipe) => (
              <TableRow key={recipe.recipe_id}>
                <TableCell>
                  <p className="font-medium">{recipe.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {recipe.purpose} · {recipe.confidence}
                  </p>
                </TableCell>
                <TableCell>
                  <Badge variant={recipe.risk === "read_only" ? "outline" : "warning"}>
                    {recipe.risk}
                  </Badge>
                </TableCell>
                <TableCell className="break-all text-xs text-muted-foreground">
                  {recipe.command}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}

export function MemoryKnowledgePanel({
  anchorSessionId,
  repository,
}: {
  anchorSessionId: string | null;
  repository: RepositoryInspectorState;
}) {
  const references = repository.overview?.memory_references ?? [];

  return (
    <section
      aria-label="Repository memory knowledge"
      className="min-w-0 rounded-md border border-border/80 bg-card p-4 shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-normal">Memory Facts</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Confirmed memory can enrich repository intelligence; candidates stay review-only.
          </p>
        </div>
        <Badge variant="outline">
          {references.length} confirmed
          {repository.memoryCandidates.length
            ? ` · ${repository.memoryCandidates.length} candidates`
            : ""}
        </Badge>
      </div>
      <div className="mt-3 space-y-3">
        {references.length === 0 ? (
          <StateLine
            icon={<Brain className={operatorIconSizeClass} aria-hidden="true" />}
            value="No confirmed memory references are retained in this snapshot."
          />
        ) : (
          references.slice(0, 4).map((reference) => (
            <div className="rounded-md border border-border/70 p-3" key={reference.reference_id}>
              <p className="text-sm font-medium">{reference.summary}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {reference.kind} · {reference.confidence} · {shortId(reference.memory_id)}
              </p>
            </div>
          ))
        )}
        {repository.memoryCandidates.length > 0 ? (
          repository.memoryCandidates.slice(0, 3).map((candidate) => (
            <div
              className="rounded-md border border-dashed border-border p-3"
              key={candidate.candidate_id}
            >
              <p className="text-sm font-medium">{candidate.summary ?? candidate.kind}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Review candidate · {candidate.source_label}
              </p>
            </div>
          ))
        ) : (
          <p className="text-xs text-muted-foreground">
            {anchorSessionId === null
              ? "Memory candidates need a session anchor."
              : "Refresh this console to load repository memory candidates."}
          </p>
        )}
      </div>
    </section>
  );
}

function InlineList({ icon, items, title }: { icon: ReactNode; items: string[]; title: string }) {
  return (
    <div className="min-w-0 rounded-md border border-border/70 p-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {items.length === 0 ? (
          <span className="text-xs text-muted-foreground">none</span>
        ) : (
          items.slice(0, 8).map((item) => (
            <Badge className="max-w-full break-all" key={item} variant="muted">
              {item}
            </Badge>
          ))
        )}
      </div>
    </div>
  );
}
