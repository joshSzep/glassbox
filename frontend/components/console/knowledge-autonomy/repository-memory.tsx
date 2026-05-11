import { Brain } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { operatorIconSizeClass } from "@/design-system/operator-status";

import { shortId } from "./format";
import { repositoryMemoryCandidateEmptyText } from "./repository-format";
import { StateLine } from "./shared";
import type { RepositoryInspectorState } from "./types";

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
            {repositoryMemoryCandidateEmptyText(anchorSessionId)}
          </p>
        )}
      </div>
    </section>
  );
}
