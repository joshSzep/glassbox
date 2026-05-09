import type { components, paths } from "@/generated/api-types";

import type { RequestJson, RequestOptions } from "./client-core";

export type WorkspaceMemoryListPageResponse =
  components["schemas"]["WorkspaceMemoryListPageResponse"];
export type WorkspaceMemoryDetailResponse = components["schemas"]["WorkspaceMemoryDetailResponse"];
export type WorkspaceMemoryPrunePreviewResponse =
  components["schemas"]["WorkspaceMemoryPrunePreviewResponse"];
export type RepositoryIndexStatusResponse = components["schemas"]["RepositoryIndexStatusResponse"];
export type RepositoryIndexSearchPageResponse =
  components["schemas"]["RepositoryIndexSearchPageResponse"];
export type RepositoryIndexEntryDetailResponse =
  components["schemas"]["RepositoryIndexEntryDetailResponse"];
export type RepositoryIndexRebuildResponse =
  components["schemas"]["RepositoryIndexRebuildResponse"];
export type RepositoryIntelligenceOverviewResponse =
  components["schemas"]["RepositoryIntelligenceOverviewResponse"];
export type RepositoryIntelligenceFreshnessResponse =
  components["schemas"]["RepositoryIntelligenceFreshnessResponse"];
export type RepositoryIntelligencePathInspectionResponse =
  components["schemas"]["RepositoryIntelligencePathInspectionResponse"];
export type RepositoryIntelligenceCommandRecipeListPageResponse =
  components["schemas"]["RepositoryIntelligenceCommandRecipeListPageResponse"];
export type RepositoryIntelligenceVerificationRecommendationResponse =
  components["schemas"]["RepositoryIntelligenceVerificationRecommendationResponse"];
export type RepositoryIntelligenceMemoryCandidateListPageResponse =
  components["schemas"]["RepositoryIntelligenceMemoryCandidateListPageResponse"];
export type WorkspaceMemoryKind = components["schemas"]["WorkspaceMemoryKind"];
export type WorkspaceMemoryState = components["schemas"]["WorkspaceMemoryState"];

export type WorkspaceMemoryListPageQuery = NonNullable<
  paths["/memory"]["get"]["parameters"]["query"]
>;
export type RepositoryIndexSearchQuery = NonNullable<
  paths["/repo/index/search"]["get"]["parameters"]["query"]
>;
export type RepositoryIntelligenceCommandRecipeListQuery = NonNullable<
  paths["/repo/intelligence/command-recipes"]["get"]["parameters"]["query"]
>;
export type RepositoryIntelligenceVerificationQuery = NonNullable<
  paths["/repo/intelligence/verification"]["get"]["parameters"]["query"]
>;
export type RepositoryIntelligenceMemoryCandidateListQuery = NonNullable<
  paths["/repo/intelligence/memory-candidates"]["get"]["parameters"]["query"]
>;

export function createWorkspaceEndpoints(requestJson: RequestJson) {
  return {
    listWorkspaceMemory: (
      query: WorkspaceMemoryListPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<WorkspaceMemoryListPageResponse>("GET", "/memory", { ...requestOptions, query }),

    getWorkspaceMemoryDetail: (memoryId: string, requestOptions?: RequestOptions) =>
      requestJson<WorkspaceMemoryDetailResponse>(
        "GET",
        `/memory/${encodeURIComponent(memoryId)}`,
        requestOptions,
      ),

    confirmWorkspaceMemory: (
      input: { actor?: string; memoryId: string; reason?: string | null },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<WorkspaceMemoryDetailResponse>(
        "POST",
        `/memory/${encodeURIComponent(input.memoryId)}/confirm`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    invalidateWorkspaceMemory: (
      input: { actor?: string; memoryId: string; reason: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<WorkspaceMemoryDetailResponse>(
        "POST",
        `/memory/${encodeURIComponent(input.memoryId)}/invalidate`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason },
        },
      ),

    previewWorkspaceMemoryPrune: (
      input: { actor?: string; memoryId: string; reason?: string | null },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<WorkspaceMemoryPrunePreviewResponse>(
        "POST",
        `/memory/${encodeURIComponent(input.memoryId)}/prune-preview`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    pruneWorkspaceMemory: (
      input: { actor?: string; memoryId: string; reason: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<WorkspaceMemoryDetailResponse>(
        "POST",
        `/memory/${encodeURIComponent(input.memoryId)}/prune`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason },
        },
      ),

    getRepositoryIndexStatus: (requestOptions?: RequestOptions) =>
      requestJson<RepositoryIndexStatusResponse>("GET", "/repo/index/status", requestOptions),

    searchRepositoryIndex: (query: RepositoryIndexSearchQuery, requestOptions?: RequestOptions) =>
      requestJson<RepositoryIndexSearchPageResponse>("GET", "/repo/index/search", {
        ...requestOptions,
        query,
      }),

    getRepositoryIndexEntryDetail: (entryId: string, requestOptions?: RequestOptions) =>
      requestJson<RepositoryIndexEntryDetailResponse>(
        "GET",
        `/repo/index/entries/${encodeURIComponent(entryId)}`,
        requestOptions,
      ),

    rebuildRepositoryIndex: (
      input: {
        background?: boolean;
        requestedBy?: string;
        sessionId?: string | null;
      } = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<RepositoryIndexRebuildResponse>("POST", "/repo/index/rebuild", {
        ...requestOptions,
        body: {
          background: input.background ?? true,
          requested_by: input.requestedBy ?? "operator",
          session_id: input.sessionId ?? null,
        },
      }),

    getRepositoryIntelligenceOverview: (requestOptions?: RequestOptions) =>
      requestJson<RepositoryIntelligenceOverviewResponse>(
        "GET",
        "/repo/intelligence",
        requestOptions,
      ),

    getRepositoryIntelligenceFreshness: (requestOptions?: RequestOptions) =>
      requestJson<RepositoryIntelligenceFreshnessResponse>(
        "GET",
        "/repo/intelligence/freshness",
        requestOptions,
      ),

    inspectRepositoryIntelligencePath: (path: string, requestOptions?: RequestOptions) =>
      requestJson<RepositoryIntelligencePathInspectionResponse>(
        "GET",
        `/repo/intelligence/paths/${encodeRepositoryPath(path)}`,
        requestOptions,
      ),

    listRepositoryIntelligenceCommandRecipes: (
      query: RepositoryIntelligenceCommandRecipeListQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<RepositoryIntelligenceCommandRecipeListPageResponse>(
        "GET",
        "/repo/intelligence/command-recipes",
        {
          ...requestOptions,
          query,
        },
      ),

    recommendRepositoryIntelligenceVerification: (
      query: RepositoryIntelligenceVerificationQuery,
      requestOptions?: RequestOptions,
    ) =>
      requestJson<RepositoryIntelligenceVerificationRecommendationResponse>(
        "GET",
        "/repo/intelligence/verification",
        {
          ...requestOptions,
          query,
        },
      ),

    listRepositoryIntelligenceMemoryCandidates: (
      query: RepositoryIntelligenceMemoryCandidateListQuery,
      requestOptions?: RequestOptions,
    ) =>
      requestJson<RepositoryIntelligenceMemoryCandidateListPageResponse>(
        "GET",
        "/repo/intelligence/memory-candidates",
        {
          ...requestOptions,
          query,
        },
      ),
  };
}

function encodeRepositoryPath(path: string): string {
  return path
    .split("/")
    .filter((part) => part.length > 0)
    .map((part) => encodeURIComponent(part))
    .join("/");
}
