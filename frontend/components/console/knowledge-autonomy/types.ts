import type {
  KnowledgeActionStatus,
  MemoryFilter,
  MemoryInspectorState,
  RepositoryInspectorState,
} from "@/stores/dashboard-stores";

export type { KnowledgeActionStatus, MemoryFilter, MemoryInspectorState, RepositoryInspectorState };

export type MemoryEntry = MemoryInspectorState["items"][number];
export type RepositoryEntry = RepositoryInspectorState["items"][number];
