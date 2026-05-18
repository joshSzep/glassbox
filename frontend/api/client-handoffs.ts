import type { components, paths } from "@/generated/api-types";

import type { RequestJson, RequestOptions } from "./client-core";

export type HandoffListResponse = components["schemas"]["HandoffListResponse"];
export type HandoffRecordResponse = components["schemas"]["HandoffRecordResponse"];
export type HandoffPreparePreviewRequest = components["schemas"]["HandoffPreparePreviewRequest"];
export type HandoffPreparePreviewResponse = components["schemas"]["HandoffPreparePreviewResponse"];
export type HandoffExportRequest = components["schemas"]["HandoffExportRequest"];
export type HandoffExportResponse = components["schemas"]["HandoffExportResponse"];
export type HandoffPackagePathRequest = components["schemas"]["HandoffPackagePathRequest"];
export type HandoffPackageInspectResponse = components["schemas"]["HandoffPackageInspectResponse"];
export type HandoffImportTriageResponse = components["schemas"]["HandoffImportTriageResponse"];
export type HandoffImportResponse = components["schemas"]["HandoffImportResponse"];
export type HandoffReadinessUnifiedResponse =
  components["schemas"]["HandoffReadinessUnifiedResponse"];
export type HandoffGuidanceResponse = components["schemas"]["HandoffGuidanceResponse"];
export type HandoffDecisionResponse = components["schemas"]["HandoffDecisionResponse"];
export type HandoffAcceptRequest = components["schemas"]["HandoffAcceptRequest"];
export type HandoffRejectRequest = components["schemas"]["HandoffRejectRequest"];
export type HandoffArchiveRequest = components["schemas"]["HandoffArchiveRequest"];

export type HandoffListQuery = NonNullable<paths["/handoffs"]["get"]["parameters"]["query"]>;
export type HandoffReadinessQuery = NonNullable<
  paths["/handoffs/readiness"]["get"]["parameters"]["query"]
>;

export function createHandoffEndpoints(requestJson: RequestJson) {
  return {
    listHandoffs: (query: HandoffListQuery = {}, requestOptions?: RequestOptions) =>
      requestJson<HandoffListResponse>("GET", "/handoffs", { ...requestOptions, query }),

    getHandoff: (sessionId: string, packageId: string, requestOptions?: RequestOptions) =>
      requestJson<HandoffRecordResponse>(
        "GET",
        `/handoffs/${encodeURIComponent(sessionId)}/${encodeURIComponent(packageId)}`,
        requestOptions,
      ),

    previewHandoff: (body: HandoffPreparePreviewRequest, requestOptions?: RequestOptions) =>
      requestJson<HandoffPreparePreviewResponse>("POST", "/handoffs/prepare-preview", {
        ...requestOptions,
        body,
      }),

    exportHandoff: (body: HandoffExportRequest, requestOptions?: RequestOptions) =>
      requestJson<HandoffExportResponse>("POST", "/handoffs/exports", {
        ...requestOptions,
        body,
      }),

    inspectHandoffPackage: (body: HandoffPackagePathRequest, requestOptions?: RequestOptions) =>
      requestJson<HandoffPackageInspectResponse>("POST", "/handoffs/inspect", {
        ...requestOptions,
        body,
      }),

    triageHandoffImport: (body: HandoffPackagePathRequest, requestOptions?: RequestOptions) =>
      requestJson<HandoffImportTriageResponse>("POST", "/handoffs/import-triage", {
        ...requestOptions,
        body,
      }),

    importHandoff: (body: HandoffPackagePathRequest, requestOptions?: RequestOptions) =>
      requestJson<HandoffImportResponse>("POST", "/handoffs/imports", {
        ...requestOptions,
        body,
      }),

    getHandoffReadiness: (query: HandoffReadinessQuery = {}, requestOptions?: RequestOptions) =>
      requestJson<HandoffReadinessUnifiedResponse>("GET", "/handoffs/readiness", {
        ...requestOptions,
        query,
      }),

    getHandoffGuidance: (sessionId: string, packageId: string, requestOptions?: RequestOptions) =>
      requestJson<HandoffGuidanceResponse>(
        "GET",
        `/handoffs/${encodeURIComponent(sessionId)}/${encodeURIComponent(packageId)}/guidance`,
        requestOptions,
      ),

    acceptHandoff: (
      input: { body: HandoffAcceptRequest; packageId: string; sessionId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<HandoffDecisionResponse>(
        "POST",
        `/handoffs/${encodeURIComponent(input.sessionId)}/${encodeURIComponent(
          input.packageId,
        )}/accept`,
        { ...requestOptions, body: input.body },
      ),

    rejectHandoff: (
      input: { body: HandoffRejectRequest; packageId: string; sessionId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<HandoffDecisionResponse>(
        "POST",
        `/handoffs/${encodeURIComponent(input.sessionId)}/${encodeURIComponent(
          input.packageId,
        )}/reject`,
        { ...requestOptions, body: input.body },
      ),

    archiveHandoff: (
      input: { body: HandoffArchiveRequest; packageId: string; sessionId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<HandoffDecisionResponse>(
        "POST",
        `/handoffs/${encodeURIComponent(input.sessionId)}/${encodeURIComponent(
          input.packageId,
        )}/archive`,
        { ...requestOptions, body: input.body },
      ),
  };
}
