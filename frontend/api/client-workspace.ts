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
export type WorkspaceMemoryKind = components["schemas"]["WorkspaceMemoryKind"];
export type WorkspaceMemoryState = components["schemas"]["WorkspaceMemoryState"];

export type WorkspaceMemoryListPageQuery = NonNullable<
  paths["/memory"]["get"]["parameters"]["query"]
>;
export type RepositoryIndexSearchQuery = NonNullable<
  paths["/repo/index/search"]["get"]["parameters"]["query"]
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
  };
}
