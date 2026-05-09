"use client";

import { Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { operatorIconSizeClass } from "@/design-system/operator-status";

import {
  CommandRecipeBrowser,
  MemoryKnowledgePanel,
  PathInspector,
  RepositoryDetail,
  RepositoryMap,
  RepositoryRows,
  RepositoryStatusPanel,
} from "./repository-panels";
import type { KnowledgeActionStatus, RepositoryInspectorState } from "./types";

export function RepositoryIndexInspector({
  action,
  anchorSessionId,
  onRebuildRepositoryIndex,
  onRepositoryPathQuery,
  onRepositoryQuery,
  onSelectRepositoryEntry,
  repository,
}: {
  action: KnowledgeActionStatus;
  anchorSessionId: string | null;
  onRebuildRepositoryIndex?: (input?: { background?: boolean; sessionId?: string | null }) => void;
  onRepositoryPathQuery?: (path: string) => void;
  onRepositoryQuery?: (query: string) => void;
  onSelectRepositoryEntry?: (entryId: string) => void;
  repository: RepositoryInspectorState;
}) {
  return (
    <section className="grid gap-4 xl:grid-cols-[18rem_1fr]">
      <RepositoryStatusPanel
        action={action}
        anchorSessionId={anchorSessionId}
        onRebuildRepositoryIndex={onRebuildRepositoryIndex}
        repository={repository}
      />

      <section className="grid min-w-0 gap-4">
        <RepositoryMap repository={repository} />
        <PathInspector onRepositoryPathQuery={onRepositoryPathQuery} repository={repository} />
        <section className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(28rem,0.8fr)]">
          <section aria-label="Repository intelligence search" className="min-w-0">
            <div className="mb-3 flex gap-2">
              <Input
                aria-label="Search repository intelligence"
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
        <section className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(28rem,0.8fr)]">
          <CommandRecipeBrowser repository={repository} />
          <MemoryKnowledgePanel repository={repository} anchorSessionId={anchorSessionId} />
        </section>
      </section>
    </section>
  );
}
