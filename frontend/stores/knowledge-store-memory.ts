import type { GlassboxApiClient, WorkspaceMemoryKind, WorkspaceMemoryState } from "@/api/client";
import { createRequestTracker, errorMessage } from "@/stores/store-actions";

import type { KnowledgeStoreState, MemoryFilter, MemoryInspectorState } from "./knowledge-store";

const MEMORY_PAGE_SIZE = 200;
const REPOSITORY_MEMORY_CANDIDATE_PAGE_SIZE = 25;

type MemoryStoreAccess = {
  apiClient: GlassboxApiClient;
  get: () => KnowledgeStoreState;
  memoryDetailRequests: ReturnType<typeof createRequestTracker>;
  memoryRequests: ReturnType<typeof createRequestTracker>;
  set: (
    partial:
      | Partial<KnowledgeStoreState>
      | ((state: KnowledgeStoreState) => Partial<KnowledgeStoreState>),
  ) => void;
};

export function createIdleMemoryInspectorState(): MemoryInspectorState {
  return {
    error: null,
    filter: "active",
    items: [],
    loadState: "idle",
    page: null,
    preview: null,
    query: "",
    selectedEntry: null,
    selectedMemoryId: null,
  };
}

export async function loadMemoryPage(
  { apiClient, get, memoryRequests, set }: MemoryStoreAccess,
  query: {
    filter?: MemoryFilter;
    kind?: WorkspaceMemoryKind | null;
    query?: string;
  } = {},
): Promise<void> {
  const currentRequestId = memoryRequests.next();
  const filter = query.filter ?? get().memory.filter;
  const textQuery = query.query ?? get().memory.query;
  set((state) => ({
    memory: {
      ...state.memory,
      error: null,
      filter,
      loadState: "loading",
      query: textQuery,
    },
  }));

  try {
    const page = await apiClient.listWorkspaceMemory({
      include_pruned: true,
      kind: query.kind ?? undefined,
      limit: MEMORY_PAGE_SIZE,
      query: textQuery.trim() || undefined,
      state: memoryStateForFilter(filter),
    });
    if (!memoryRequests.isCurrent(currentRequestId)) {
      return;
    }
    set((state) => ({
      memory: {
        ...state.memory,
        error: null,
        items: page.items,
        loadState: "loaded",
        page: page.page,
      },
    }));
  } catch (error) {
    if (!memoryRequests.isCurrent(currentRequestId)) {
      return;
    }
    set((state) => ({
      memory: { ...state.memory, error: errorMessage(error), loadState: "failed" },
    }));
  }
}

export async function loadRepositoryMemoryCandidates(
  { apiClient, set }: MemoryStoreAccess,
  sessionId: string,
): Promise<void> {
  try {
    const page = await apiClient.listRepositoryIntelligenceMemoryCandidates({
      limit: REPOSITORY_MEMORY_CANDIDATE_PAGE_SIZE,
      session_id: sessionId,
    });
    set((state) => ({
      repository: {
        ...state.repository,
        error: null,
        memoryCandidates: page.items,
      },
    }));
  } catch (error) {
    set((state) => ({
      repository: { ...state.repository, error: errorMessage(error) },
    }));
  }
}

export async function selectMemory(
  { apiClient, memoryDetailRequests, set }: MemoryStoreAccess,
  memoryId: string,
): Promise<void> {
  const currentRequestId = memoryDetailRequests.next();
  set((state) => ({
    memory: {
      ...state.memory,
      error: null,
      preview: null,
      selectedEntry: null,
      selectedMemoryId: memoryId,
    },
  }));
  try {
    const detail = await apiClient.getWorkspaceMemoryDetail(memoryId);
    if (!memoryDetailRequests.isCurrent(currentRequestId)) {
      return;
    }
    set((state) => ({
      memory: { ...state.memory, selectedEntry: detail.entry },
    }));
  } catch (error) {
    if (!memoryDetailRequests.isCurrent(currentRequestId)) {
      return;
    }
    set((state) => ({
      memory: { ...state.memory, error: errorMessage(error) },
    }));
  }
}

export function requireSelectedMemoryId(memory: MemoryInspectorState): string {
  if (memory.selectedMemoryId === null) {
    throw new Error("No workspace memory entry is selected.");
  }
  return memory.selectedMemoryId;
}

function memoryStateForFilter(filter: MemoryFilter): WorkspaceMemoryState | undefined {
  return filter === "all" ? undefined : filter;
}
