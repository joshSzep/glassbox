import { AlertCircle, RefreshCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";

import { formatMaybeDate, repositoryStatusVariant } from "./format";
import { repositoryFreshnessCueLabel } from "./repository-format";
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
              value={repositoryFreshnessCueLabel(cue)}
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
