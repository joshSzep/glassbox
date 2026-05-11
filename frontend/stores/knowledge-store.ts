import { createStore, type StoreApi } from "zustand/vanilla";

import type {
  GlassboxApiClient,
  RepositoryIndexEntryDetailResponse,
  RepositoryIndexRebuildResponse,
  RepositoryIndexSearchPageResponse,
  RepositoryIndexStatusResponse,
  RepositoryIntelligenceCommandRecipeListPageResponse,
  RepositoryIntelligenceFreshnessResponse,
  RepositoryIntelligenceMemoryCandidateListPageResponse,
  RepositoryIntelligenceOverviewResponse,
  RepositoryIntelligencePathInspectionResponse,
  RepositoryIntelligenceVerificationRecommendationResponse,
  WorkspaceMemoryDetailResponse,
  WorkspaceMemoryKind,
  WorkspaceMemoryListPageResponse,
  WorkspaceMemoryPrunePreviewResponse,
} from "@/api/client";
import {
  createIdleActionStatus,
  createRequestTracker,
  type LoadState,
  type StoreActionStatus,
} from "@/stores/store-actions";

import {
  previewPruneMemoryAction,
  rebuildRepositoryIndexAction,
  runKnowledgeMemoryAction,
} from "./knowledge-store-actions";
import {
  createIdleMemoryInspectorState,
  loadMemoryPage,
  loadRepositoryMemoryCandidates,
  requireSelectedMemoryId,
  selectMemory,
} from "./knowledge-store-memory";
import {
  createIdleRepositoryInspectorState,
  inspectRepositoryPath,
  loadRepositoryStatus,
  searchRepositoryIndex,
  selectRepositoryEntry,
} from "./knowledge-store-repository";

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
  commandRecipes: RepositoryIntelligenceCommandRecipeListPageResponse["items"];
  error: string | null;
  freshness: RepositoryIntelligenceFreshnessResponse | null;
  items: RepositoryIndexSearchPageResponse["items"];
  memoryCandidates: RepositoryIntelligenceMemoryCandidateListPageResponse["items"];
  overview: RepositoryIntelligenceOverviewResponse | null;
  pathInspection: RepositoryIntelligencePathInspectionResponse | null;
  pathQuery: string;
  query: string;
  rebuild: RepositoryIndexRebuildResponse | null;
  searchState: LoadState;
  selectedEntry: RepositoryIndexEntryDetailResponse["entry"] | null;
  selectedEntryId: string | null;
  status: RepositoryIndexStatusResponse | null;
  statusState: LoadState;
  verification: RepositoryIntelligenceVerificationRecommendationResponse | null;
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
  inspectRepositoryPath: (path?: string) => Promise<void>;
  loadRepositoryMemoryCandidates: (sessionId: string) => Promise<void>;
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

export function createKnowledgeStore(apiClient: GlassboxApiClient): StoreApi<KnowledgeStoreState> {
  const memoryRequests = createRequestTracker();
  const memoryDetailRequests = createRequestTracker();
  const repositoryRequests = createRequestTracker();

  return createStore<KnowledgeStoreState>((set, get) => ({
    action: createIdleActionStatus(),
    confirmMemory: async (input = {}) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      await runKnowledgeMemoryAction({
        action: () => apiClient.confirmWorkspaceMemory({ memoryId, reason: input.reason }),
        get,
        kind: "confirm-memory",
        memoryId,
        set,
      });
    },
    invalidateMemory: async (input) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      await runKnowledgeMemoryAction({
        action: () => apiClient.invalidateWorkspaceMemory({ memoryId, reason: input.reason }),
        get,
        kind: "invalidate-memory",
        memoryId,
        set,
      });
    },
    loadMemoryPage: async (query = {}) => {
      await loadMemoryPage({ apiClient, get, memoryDetailRequests, memoryRequests, set }, query);
    },
    inspectRepositoryPath: async (path = get().repository.pathQuery) => {
      await inspectRepositoryPath({ apiClient, get, repositoryRequests, set }, path);
    },
    loadRepositoryMemoryCandidates: async (sessionId) => {
      await loadRepositoryMemoryCandidates(
        { apiClient, get, memoryDetailRequests, memoryRequests, set },
        sessionId,
      );
    },
    loadRepositoryStatus: async () => {
      await loadRepositoryStatus({ apiClient, get, repositoryRequests, set });
    },
    memory: createIdleMemoryInspectorState(),
    previewPruneMemory: async (input = {}) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      await previewPruneMemoryAction({ apiClient, get, set }, { memoryId, reason: input.reason });
    },
    pruneMemory: async (input) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      await runKnowledgeMemoryAction({
        action: () => apiClient.pruneWorkspaceMemory({ memoryId, reason: input.reason }),
        get,
        kind: "prune-memory",
        memoryId,
        set,
      });
    },
    rebuildRepositoryIndex: async (input = {}) => {
      await rebuildRepositoryIndexAction({ apiClient, get, set }, input);
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
      await searchRepositoryIndex({ apiClient, get, repositoryRequests, set }, query);
    },
    selectMemory: async (memoryId) => {
      await selectMemory({ apiClient, get, memoryDetailRequests, memoryRequests, set }, memoryId);
    },
    selectRepositoryEntry: async (entryId) => {
      await selectRepositoryEntry({ apiClient, get, repositoryRequests, set }, entryId);
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
