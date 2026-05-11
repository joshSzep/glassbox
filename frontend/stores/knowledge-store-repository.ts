import type { GlassboxApiClient } from "@/api/client";
import { createRequestTracker, errorMessage } from "@/stores/store-actions";

import type { KnowledgeStoreState, RepositoryInspectorState } from "./knowledge-store";

const REPOSITORY_INDEX_SEARCH_SIZE = 50;
const REPOSITORY_RECIPE_PAGE_SIZE = 50;

type RepositoryStoreAccess = {
  apiClient: GlassboxApiClient;
  get: () => KnowledgeStoreState;
  repositoryRequests: ReturnType<typeof createRequestTracker>;
  set: (
    partial:
      | Partial<KnowledgeStoreState>
      | ((state: KnowledgeStoreState) => Partial<KnowledgeStoreState>),
  ) => void;
};

export function createIdleRepositoryInspectorState(): RepositoryInspectorState {
  return {
    commandRecipes: [],
    error: null,
    freshness: null,
    items: [],
    memoryCandidates: [],
    overview: null,
    pathInspection: null,
    pathQuery: "",
    query: "",
    rebuild: null,
    searchState: "idle",
    selectedEntry: null,
    selectedEntryId: null,
    status: null,
    statusState: "idle",
    verification: null,
  };
}

export async function inspectRepositoryPath(
  { apiClient, get, set }: RepositoryStoreAccess,
  path = get().repository.pathQuery,
): Promise<void> {
  const normalizedPath = path.trim();
  if (!normalizedPath) {
    return;
  }
  set((state) => ({
    repository: {
      ...state.repository,
      error: null,
      pathQuery: normalizedPath,
    },
  }));
  try {
    const [pathInspection, verification] = await Promise.all([
      apiClient.inspectRepositoryIntelligencePath(normalizedPath),
      apiClient.recommendRepositoryIntelligenceVerification({
        paths: [normalizedPath],
      }),
    ]);
    set((state) => ({
      repository: {
        ...state.repository,
        error: null,
        pathInspection,
        pathQuery: normalizedPath,
        verification,
      },
    }));
  } catch (error) {
    set((state) => ({
      repository: { ...state.repository, error: errorMessage(error) },
    }));
  }
}

export async function loadRepositoryStatus({
  apiClient,
  get,
  repositoryRequests,
  set,
}: RepositoryStoreAccess): Promise<void> {
  const currentRequestId = repositoryRequests.next();
  set((state) => ({
    repository: { ...state.repository, error: null, statusState: "loading" },
  }));
  try {
    const [status, freshness] = await Promise.all([
      apiClient.getRepositoryIndexStatus(),
      apiClient.getRepositoryIntelligenceFreshness(),
    ]);
    const [overviewResult, recipeResult] = await Promise.allSettled([
      apiClient.getRepositoryIntelligenceOverview(),
      apiClient.listRepositoryIntelligenceCommandRecipes({
        limit: REPOSITORY_RECIPE_PAGE_SIZE,
      }),
    ]);
    const overview = overviewResult.status === "fulfilled" ? overviewResult.value : null;
    const recipes = recipeResult.status === "fulfilled" ? recipeResult.value.items : [];
    if (!repositoryRequests.isCurrent(currentRequestId)) {
      return;
    }
    const currentPath = get().repository.pathQuery.trim();
    const defaultPath = currentPath || overview?.source_roots[0]?.path || "";
    set((state) => ({
      repository: {
        ...state.repository,
        commandRecipes: recipes,
        error: null,
        freshness,
        overview,
        pathQuery: defaultPath,
        status,
        statusState: "loaded",
      },
    }));
    if (defaultPath) {
      await get().inspectRepositoryPath(defaultPath);
    }
  } catch (error) {
    if (!repositoryRequests.isCurrent(currentRequestId)) {
      return;
    }
    set((state) => ({
      repository: { ...state.repository, error: errorMessage(error), statusState: "failed" },
    }));
  }
}

export async function searchRepositoryIndex(
  { apiClient, get, set }: RepositoryStoreAccess,
  query = get().repository.query,
): Promise<void> {
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
}

export async function selectRepositoryEntry(
  { apiClient, set }: RepositoryStoreAccess,
  entryId: string,
): Promise<void> {
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
}
