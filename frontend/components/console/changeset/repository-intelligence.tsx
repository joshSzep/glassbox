import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { ChangesetDetailState } from "@/stores/dashboard-stores";

import { verificationBadgeVariant } from "./format";
import { Section, StateLine } from "./shared";

type RepositoryIntelligenceState = NonNullable<ChangesetDetailState["repositoryIntelligence"]>;

export function ChangesetRepositoryIntelligencePanel({
  repositoryIntelligence,
  verificationPlan,
}: {
  repositoryIntelligence?: RepositoryIntelligenceState;
  verificationPlan: ChangesetDetailState["verificationPlan"];
}) {
  const changedPaths = verificationPlan?.changed_paths ?? [];
  const intelligence = repositoryIntelligence ?? null;
  const freshness = intelligence?.freshness;
  const verification = intelligence?.verification;
  const inspections = intelligence?.pathInspections ?? [];
  const commandRecipes = intelligence?.commandRecipes ?? [];
  const subsystems = uniqueStrings(
    inspections.flatMap((inspection) => inspection.subsystems.map((item) => item.name)),
  );
  const packages = uniqueStrings(
    inspections.flatMap((inspection) => inspection.packages.map((item) => item.name)),
  );
  const owners = uniqueStrings(
    inspections.flatMap((inspection) => inspection.ownership_hints.map((item) => item.owner_label)),
  );
  const releaseSurfaces = uniqueStrings(
    inspections.flatMap((inspection) => inspection.release_surfaces.map((item) => item.name)),
  );
  const freshnessCues = freshness?.cues ?? [];

  if (changedPaths.length === 0 && intelligence?.loadState !== "failed") {
    return null;
  }

  return (
    <Section title="Repository Intelligence">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={freshness?.index.status === "fresh" ? "success" : "warning"}>
            Index {freshness?.index.status ?? intelligence?.loadState ?? "loading"}
          </Badge>
          <Badge variant={verificationBadgeVariant(verification?.status ?? "missing")}>
            Recommendations {verification?.status ?? "missing"}
          </Badge>
          {freshnessCues.length > 0 ? (
            <Badge variant="warning">{freshnessCues.length} stale cues</Badge>
          ) : null}
          {owners.length > 0 ? <Badge variant="outline">{owners.length} owner hints</Badge> : null}
        </div>
        {intelligence?.error ? (
          <StateLine
            tone={intelligence.loadState === "failed" ? "destructive" : "muted"}
            value={`Repository intelligence loaded partially: ${intelligence.error}`}
          />
        ) : null}
        {verification?.next_actions?.length ? (
          <ul className="grid gap-2 text-console text-muted-foreground">
            {verification.next_actions.slice(0, 3).map((action) => (
              <li className="break-all" key={action}>
                {action}
              </li>
            ))}
          </ul>
        ) : null}
        <DataList density="compact">
          <DataListItem>
            <DataListLabel>Affected repository areas</DataListLabel>
            <DataListMeta>
              {joinOrNone(subsystems, "subsystems")} - {joinOrNone(packages, "packages")}
            </DataListMeta>
            {releaseSurfaces.length > 0 ? (
              <DataListMeta>Release surfaces: {releaseSurfaces.join(", ")}</DataListMeta>
            ) : null}
            {owners.length > 0 ? (
              <DataListMeta>
                Owner hints: {owners.join(", ")}; advisory only, not reviewer assignment.
              </DataListMeta>
            ) : null}
          </DataListItem>
          {commandRecipes.slice(0, 4).map((recipe) => (
            <DataListItem key={recipe.recipe_id}>
              <DataListLabel>{recipe.name}</DataListLabel>
              <DataListMeta>
                {recipe.purpose} - {recipe.risk} - {recipe.confidence}
              </DataListMeta>
              <DataListMeta className="break-all">{recipe.command}</DataListMeta>
            </DataListItem>
          ))}
        </DataList>
        {freshnessCues.length > 0 ? (
          <DataList density="compact">
            {freshnessCues.slice(0, 3).map((cue) => (
              <DataListItem key={`${cue.source}:${cue.reason}`}>
                <DataListLabel>{cue.source}</DataListLabel>
                <DataListMeta>
                  {cue.state} - {cue.reason} - {cue.detail}
                </DataListMeta>
              </DataListItem>
            ))}
          </DataList>
        ) : null}
        {changedPaths.length > 0 ? (
          <div>
            <h4 className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Inspect changed paths
            </h4>
            <ul className="mt-2 grid gap-2 text-console text-muted-foreground">
              {changedPaths.slice(0, 6).map((path) => (
                <li className="break-all" key={path}>
                  <a
                    className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    href={`/app/repository-index?path=${encodeURIComponent(path)}`}
                  >
                    {path}
                    <ExternalLink className={operatorIconSizeClass} aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </Section>
  );
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function joinOrNone(values: string[], label: string): string {
  return values.length === 0 ? `no ${label}` : values.join(", ");
}
