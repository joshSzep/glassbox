import type { components, paths } from "@/generated/api-types";

import type { RequestJson, RequestOptions } from "./client-core";

export type BranchCandidateActionResponse = components["schemas"]["BranchCandidateActionResponse"];
export type BranchSearchDetailResponse = components["schemas"]["BranchSearchDetailResponse"];
export type BranchSearchListPageResponse = components["schemas"]["BranchSearchListPageResponse"];
export type ChangesetDetailResponse = components["schemas"]["ChangesetDetailResponse"];
export type ChangesetListPageResponse = components["schemas"]["ChangesetListPageResponse"];
export type ChangesetActionResponse = components["schemas"]["ChangesetActionResponse"];
export type ReviewFeedbackActionResponse = components["schemas"]["ReviewFeedbackActionResponse"];
export type ReviewFeedbackFixupInventoryActionResponse =
  components["schemas"]["ReviewFeedbackFixupInventoryActionResponse"];
export type ManualEvidenceActionResponse = components["schemas"]["ManualEvidenceActionResponse"];
export type CommitReadinessResponse = components["schemas"]["CommitReadinessResponse"];
export type HandoffReadinessResponse = components["schemas"]["HandoffReadinessResponse"];
export type CommitMessageSuggestionResponse =
  components["schemas"]["CommitMessageSuggestionResponse"];
export type ChangesetReviewBriefGenerateResponse =
  components["schemas"]["ChangesetReviewBriefGenerateResponse"];
export type ChangesetVerificationPlanPreviewResponse =
  components["schemas"]["ChangesetVerificationPlanPreviewResponse"];
export type ChangesetRecordVerificationResponse =
  components["schemas"]["ChangesetRecordVerificationResponse"];
export type EvidenceGraphResponse = components["schemas"]["EvidenceGraph"];
export type ReviewFeedbackListPageResponse =
  components["schemas"]["ReviewFeedbackListPageResponse"];

export type BranchSearchListPageQuery = NonNullable<
  paths["/branch-searches"]["get"]["parameters"]["query"]
>;
export type ChangesetListPageQuery = NonNullable<
  paths["/changesets"]["get"]["parameters"]["query"]
>;
export type ReviewFeedbackListPageQuery = NonNullable<
  paths["/changesets/feedback"]["get"]["parameters"]["query"]
>;

export function createChangesetEndpoints(requestJson: RequestJson) {
  return {
    getBranchSearchPage: (query: BranchSearchListPageQuery = {}, requestOptions?: RequestOptions) =>
      requestJson<BranchSearchListPageResponse>("GET", "/branch-searches", {
        ...requestOptions,
        query,
      }),

    getBranchSearchDetail: (searchId: string, requestOptions?: RequestOptions) =>
      requestJson<BranchSearchDetailResponse>(
        "GET",
        `/branch-searches/${encodeURIComponent(searchId)}`,
        requestOptions,
      ),

    markBranchCandidate: (
      input: {
        action: "needs-review" | "reject" | "select";
        actor?: string;
        candidateId: string;
        reason: string;
        searchId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<BranchCandidateActionResponse>(
        "POST",
        `/branch-searches/${encodeURIComponent(input.searchId)}/candidates/${encodeURIComponent(
          input.candidateId,
        )}/${input.action}`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason },
        },
      ),

    getChangesetPage: (query: ChangesetListPageQuery = {}, requestOptions?: RequestOptions) =>
      requestJson<ChangesetListPageResponse>("GET", "/changesets", {
        ...requestOptions,
        query,
      }),

    getChangesetDetail: (changesetId: string, requestOptions?: RequestOptions) =>
      requestJson<ChangesetDetailResponse>(
        "GET",
        `/changesets/${encodeURIComponent(changesetId)}`,
        requestOptions,
      ),

    getChangesetVerificationPlan: (changesetId: string, requestOptions?: RequestOptions) =>
      requestJson<ChangesetVerificationPlanPreviewResponse>(
        "GET",
        `/changesets/${encodeURIComponent(changesetId)}/verification-plan`,
        requestOptions,
      ),

    getChangesetEvidenceGraph: (changesetId: string, requestOptions?: RequestOptions) =>
      requestJson<EvidenceGraphResponse>(
        "GET",
        `/changesets/${encodeURIComponent(changesetId)}/evidence-graph`,
        requestOptions,
      ),

    recordChangesetVerification: (
      input: {
        changesetId: string;
        taskId?: string | null;
        verificationId?: string | null;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ChangesetRecordVerificationResponse>(
        "POST",
        `/changesets/${encodeURIComponent(input.changesetId)}/record-verification`,
        {
          ...requestOptions,
          body: {
            task_id: input.taskId ?? null,
            verification_id: input.verificationId ?? null,
          },
        },
      ),

    getReviewFeedbackPage: (
      query: ReviewFeedbackListPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ReviewFeedbackListPageResponse>("GET", "/changesets/feedback", {
        ...requestOptions,
        query,
      }),

    getChangesetCommitReadiness: (changesetId: string, requestOptions?: RequestOptions) =>
      requestJson<CommitReadinessResponse>(
        "GET",
        `/changesets/${encodeURIComponent(changesetId)}/commit-readiness`,
        requestOptions,
      ),

    getChangesetHandoffReadiness: (changesetId: string, requestOptions?: RequestOptions) =>
      requestJson<HandoffReadinessResponse>(
        "GET",
        `/changesets/${encodeURIComponent(changesetId)}/handoff-readiness`,
        requestOptions,
      ),

    getChangesetCommitMessage: (changesetId: string, requestOptions?: RequestOptions) =>
      requestJson<CommitMessageSuggestionResponse>(
        "GET",
        `/changesets/${encodeURIComponent(changesetId)}/commit-message`,
        requestOptions,
      ),

    generateChangesetReviewBrief: (
      input: { actor?: string; changesetId: string; includeMarkdown?: boolean },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ChangesetReviewBriefGenerateResponse>(
        "POST",
        `/changesets/${encodeURIComponent(input.changesetId)}/brief`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            include_markdown: input.includeMarkdown ?? false,
          },
        },
      ),

    refreshChangeset: (
      input: { actor?: string; changesetId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ChangesetActionResponse>(
        "POST",
        `/changesets/${encodeURIComponent(input.changesetId)}/refresh`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator" },
        },
      ),

    addReviewFeedback: (
      input: {
        actor?: string;
        body?: string | null;
        changesetId: string;
        feedbackKind: components["schemas"]["ReviewFeedbackCreateRequest"]["feedback_kind"];
        filePath?: string | null;
        lineEnd?: number | null;
        lineStart?: number | null;
        provenance?: components["schemas"]["ReviewFeedbackCreateRequest"]["provenance"];
        reviewerLabel?: string | null;
        scopeKind?: components["schemas"]["ReviewFeedbackCreateRequest"]["scope_kind"];
        scopeReason?: string | null;
        sourceLabel?: string | null;
        summary: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ReviewFeedbackActionResponse>(
        "POST",
        `/changesets/${encodeURIComponent(input.changesetId)}/feedback`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            body: input.body ?? null,
            feedback_kind: input.feedbackKind,
            file_path: input.filePath ?? null,
            line_end: input.lineEnd ?? null,
            line_start: input.lineStart ?? null,
            provenance: input.provenance ?? "manual",
            reviewer_label: input.reviewerLabel ?? null,
            scope_kind: input.scopeKind ?? "changeset",
            scope_reason: input.scopeReason ?? null,
            source_label: input.sourceLabel ?? null,
            summary: input.summary,
          },
        },
      ),

    recordReviewFeedbackFixupInventory: (
      input: {
        actor?: string;
        feedbackId: string;
        fromWorkspace?: boolean;
        paths?: string[];
        sourceSummary?: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ReviewFeedbackFixupInventoryActionResponse>(
        "POST",
        `/changesets/feedback/${encodeURIComponent(input.feedbackId)}/fixup`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            from_workspace: input.fromWorkspace ?? true,
            paths: input.paths ?? [],
            source_summary:
              input.sourceSummary ?? "dashboard recorded response-linked workspace inventory",
          },
        },
      ),

    attachManualEvidence: (
      input: {
        actor?: string;
        changesetId: string;
        commandText?: string | null;
        evidenceKind?: components["schemas"]["ManualEvidenceAttachRequest"]["evidence_kind"];
        freshness?: components["schemas"]["ManualEvidenceAttachRequest"]["freshness"];
        note?: string | null;
        sourceLabel: string;
        summary: string;
        targetId?: string | null;
        targetKind?: components["schemas"]["ManualEvidenceAttachRequest"]["target_kind"];
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ManualEvidenceActionResponse>(
        "POST",
        `/changesets/${encodeURIComponent(input.changesetId)}/manual-evidence`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            command_text: input.commandText ?? null,
            evidence_kind: input.evidenceKind ?? "operator_assertion",
            freshness: input.freshness ?? "needs_inspection",
            note: input.note ?? null,
            source_label: input.sourceLabel,
            summary: input.summary,
            target_id: input.targetId ?? input.changesetId,
            target_kind: input.targetKind ?? "changeset",
          },
        },
      ),
  };
}
