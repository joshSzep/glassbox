import type { ReactNode } from "react";
import { Boxes, ClipboardList, FileSearch, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";

import { repositoryStatusVariant } from "./format";
import { repositoryOverviewSummary } from "./repository-format";
import { StateLine } from "./shared";
import type { RepositoryInspectorState } from "./types";

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
            {repositoryOverviewSummary(overview)}
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
