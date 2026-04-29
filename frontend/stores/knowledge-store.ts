import { createStore, type StoreApi } from "zustand/vanilla";

import type {
  GlassboxApiClient,
  RepositoryIndexEntryDetailResponse,
  RepositoryIndexRebuildResponse,
  RepositoryIndexSearchPageResponse,
  RepositoryIndexStatusResponse,
  WorkspaceMemoryDetailResponse,
  WorkspaceMemoryKind,
  WorkspaceMemoryListPageResponse,
  WorkspaceMemoryPrunePreviewResponse,
  WorkspaceMemoryState,
} from "@/api/client";
import {
  createFailedActionStatus,
  createIdleActionStatus,
  createPendingActionStatus,
  createRequestTracker,
  createSucceededActionStatus,
  errorMessage,
  runAsyncStoreAction,
  type LoadState,
  type StoreActionStatus,
} from "@/stores/store-actions";

export type KnowledgeActionKind =
  | "confirm-memory"
  | "invalidate-memory"
  | "preview-prune-memory"
  | "prune-memory"
  | "rebuild-index";

export type KnowledgeActionStatus = StoreActionStatus<KnowledgeActionKind>;
export type MemoryFilter = "active" | "all" | "invalidated" | "stale";

export type MemoryInspectorState = {
  error: string | null;
  filter: MemoryFilter;
  items: WorkspaceMemoryListPageResponse["items"];
  loadState: LoadState;
  page: WorkspaceMemoryListPageResponse["page"] | null;
  preview: WorkspaceMemoryPrunePreviewResponse | null;
  query: string;
  selectedEntry: WorkspaceMemoryDetailResponse["entry"] | null;
  selectedMemoryId: string | null;
};

export type RepositoryInspectorState = {
  error: string | null;
  items: RepositoryIndexSearchPageResponse["items"];
  query: string;
  rebuild: RepositoryIndexRebuildResponse | null;
  searchState: LoadState;
  selectedEntry: RepositoryIndexEntryDetailResponse["entry"] | null;
  selectedEntryId: string | null;
  status: RepositoryIndexStatusResponse | null;
  statusState: LoadState;
};

export type KnowledgeStoreState = {
  action: KnowledgeActionStatus;
  confirmMemory: (input?: { memoryId?: string; reason?: string | null }) => Promise<void>;
  invalidateMemory: (input: { memoryId?: string; reason: string }) => Promise<void>;
  loadMemoryPage: (query?: {
    filter?: MemoryFilter;
    kind?: WorkspaceMemoryKind | null;
    query?: string;
  }) => Promise<void>;
  loadRepositoryStatus: () => Promise<void>;
  memory: MemoryInspectorState;
  previewPruneMemory: (input?: { memoryId?: string; reason?: string | null }) => Promise<void>;
  pruneMemory: (input: { memoryId?: string; reason: string }) => Promise<void>;
  rebuildRepositoryIndex: (input?: {
    background?: boolean;
    sessionId?: string | null;
  }) => Promise<void>;
  repository: RepositoryInspectorState;
  reset: () => void;
  searchRepositoryIndex: (query?: string) => Promise<void>;
  selectMemory: (memoryId: string) => Promise<void>;
  selectRepositoryEntry: (entryId: string) => Promise<void>;
  setMemoryFilter: (filter: MemoryFilter) => Promise<void>;
  setMemoryQuery: (query: string) => Promise<void>;
  setRepositoryQuery: (query: string) => Promise<void>;
};

const MEMORY_PAGE_SIZE = 200;
const REPOSITORY_INDEX_SEARCH_SIZE = 50;

export function createKnowledgeStore(apiClient: GlassboxApiClient): StoreApi<KnowledgeStoreState> {
  const memoryRequests = createRequestTracker();
  const memoryDetailRequests = createRequestTracker();
  const repositoryRequests = createRequestTracker();

  return createStore<KnowledgeStoreState>((set, get) => ({
    action: createIdleActionStatus(),
    confirmMemory: async (input = {}) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      await runKnowledgeAction({
        action: () => apiClient.confirmWorkspaceMemory({ memoryId, reason: input.reason }),
        get,
        kind: "confirm-memory",
        memoryId,
        set,
      });
    },
    invalidateMemory: async (input) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      await runKnowledgeAction({
        action: () => apiClient.invalidateWorkspaceMemory({ memoryId, reason: input.reason }),
        get,
        kind: "invalidate-memory",
        memoryId,
        set,
      });
    },
    loadMemoryPage: async (query = {}) => {
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
    },
    loadRepositoryStatus: async () => {
      const currentRequestId = repositoryRequests.next();
      set((state) => ({
        repository: { ...state.repository, error: null, statusState: "loading" },
      }));
      try {
        const status = await apiClient.getRepositoryIndexStatus();
        if (!repositoryRequests.isCurrent(currentRequestId)) {
          return;
        }
        set((state) => ({
          repository: { ...state.repository, error: null, status, statusState: "loaded" },
        }));
      } catch (error) {
        if (!repositoryRequests.isCurrent(currentRequestId)) {
          return;
        }
        set((state) => ({
          repository: { ...state.repository, error: errorMessage(error), statusState: "failed" },
        }));
      }
    },
    memory: createIdleMemoryInspectorState(),
    previewPruneMemory: async (input = {}) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      set({ action: createPendingActionStatus("preview-prune-memory") });
      try {
        const preview = await apiClient.previewWorkspaceMemoryPrune({
          memoryId,
          reason: input.reason,
        });
        set((state) => ({
          action: createSucceededActionStatus("preview-prune-memory"),
          memory: { ...state.memory, preview },
        }));
      } catch (error) {
        set({ action: createFailedActionStatus("preview-prune-memory", error) });
      }
    },
    pruneMemory: async (input) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      await runKnowledgeAction({
        action: () => apiClient.pruneWorkspaceMemory({ memoryId, reason: input.reason }),
        get,
        kind: "prune-memory",
        memoryId,
        set,
      });
    },
    rebuildRepositoryIndex: async (input = {}) => {
      set({ action: createPendingActionStatus("rebuild-index") });
      try {
        const rebuild = await apiClient.rebuildRepositoryIndex({
          background: input.background,
          sessionId: input.sessionId,
        });
        set((state) => ({
          action: createSucceededActionStatus("rebuild-index"),
          repository: { ...state.repository, rebuild },
        }));
        await get().loadRepositoryStatus();
        if (get().repository.query.trim()) {
          await get().searchRepositoryIndex();
        }
      } catch (error) {
        set({ action: createFailedActionStatus("rebuild-index", error) });
      }
    },
    repository: createIdleRepositoryInspectorState(),
    reset: () => {
      memoryRequests.invalidate();
      memoryDetailRequests.invalidate();
      repositoryRequests.invalidate();
      set({
        action: createIdleActionStatus(),
        memory: createIdleMemoryInspectorState(),
        repository: createIdleRepositoryInspectorState(),
      });
    },
    searchRepositoryIndex: async (query = get().repository.query) => {
      set((state) => ({
        repository: {
          ...state.repository,
          error: null,
          query,
          searchState: "loading",
        },
      }));
      try {
        const page = await apiClient.searchRepositoryIndex({
          limit: REPOSITORY_INDEX_SEARCH_SIZE,
          query: query.trim() || "glassbox",
        });
        set((state) => ({
          repository: {
            ...state.repository,
            error: null,
            items: page.items,
            query,
            searchState: "loaded",
          },
        }));
      } catch (error) {
        set((state) => ({
          repository: { ...state.repository, error: errorMessage(error), searchState: "failed" },
        }));
      }
    },
    selectMemory: async (memoryId) => {
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
    },
    selectRepositoryEntry: async (entryId) => {
      set((state) => ({
        repository: {
          ...state.repository,
          error: null,
          selectedEntry: null,
          selectedEntryId: entryId,
        },
      }));
      try {
        const detail = await apiClient.getRepositoryIndexEntryDetail(entryId);
        set((state) => ({
          repository: { ...state.repository, selectedEntry: detail.entry },
        }));
      } catch (error) {
        set((state) => ({
          repository: { ...state.repository, error: errorMessage(error) },
        }));
      }
    },
    setMemoryFilter: async (filter) => {
      await get().loadMemoryPage({ filter });
    },
    setMemoryQuery: async (query) => {
      await get().loadMemoryPage({ query });
    },
    setRepositoryQuery: async (query) => {
      set((state) => ({ repository: { ...state.repository, query } }));
      await get().searchRepositoryIndex(query);
    },
  }));
}

function createIdleMemoryInspectorState(): MemoryInspectorState {
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

function createIdleRepositoryInspectorState(): RepositoryInspectorState {
  return {
    error: null,
    items: [],
    query: "",
    rebuild: null,
    searchState: "idle",
    selectedEntry: null,
    selectedEntryId: null,
    status: null,
    statusState: "idle",
  };
}

async function runKnowledgeAction({
  action,
  get,
  kind,
  memoryId,
  set,
}: {
  action: () => Promise<unknown>;
  get: StoreApi<KnowledgeStoreState>["getState"];
  kind: KnowledgeActionKind;
  memoryId: string | null;
  set: StoreApi<KnowledgeStoreState>["setState"];
}) {
  await runAsyncStoreAction({
    action,
    kind,
    onSuccess: async () => {
      await get().loadMemoryPage();
      if (memoryId !== null) {
        await get().selectMemory(memoryId);
      }
    },
    setAction: (status) => set({ action: status }),
  });
}

function requireSelectedMemoryId(memory: MemoryInspectorState): string {
  if (memory.selectedMemoryId === null) {
    throw new Error("No workspace memory entry is selected.");
  }
  return memory.selectedMemoryId;
}

function memoryStateForFilter(filter: MemoryFilter): WorkspaceMemoryState | undefined {
  return filter === "all" ? undefined : filter;
}
