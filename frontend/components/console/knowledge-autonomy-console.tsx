"use client";

import { RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import {
  MemoryInspector,
  memorySummary,
  RepositoryIndexInspector,
  repositorySummary,
  StateLine,
  SurfaceLink,
} from "@/components/console/knowledge-autonomy-sections";
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
  onRepositoryPathQuery?: (path: string) => void;
  onRepositoryQuery?: (query: string) => void;
  onSelectMemory?: (memoryId: string) => void;
  onSelectRepositoryEntry?: (entryId: string) => void;
  repository: RepositoryInspectorState;
  surface: "memory" | "repository";
};

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
  onRepositoryPathQuery,
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
            onRepositoryPathQuery={onRepositoryPathQuery}
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
