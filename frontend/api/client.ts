import { createChangesetEndpoints } from "./client-changesets";
import {
  createCoreEndpoints,
  createRequestJson,
  type GlassboxApiClientOptions,
} from "./client-core";
import { createSessionEndpoints } from "./client-sessions";
import { createTaskEndpoints } from "./client-tasks";
import { createWorkspaceEndpoints } from "./client-workspace";

export type {
  BranchCandidateActionResponse,
  BranchSearchDetailResponse,
  BranchSearchListPageQuery,
  BranchSearchListPageResponse,
  ChangesetActionResponse,
  ChangesetDetailResponse,
  ChangesetListPageQuery,
  ChangesetListPageResponse,
  ChangesetReviewBriefGenerateResponse,
  ChangesetVerificationPlanPreviewResponse,
  CommitMessageSuggestionResponse,
  CommitReadinessResponse,
  HandoffReadinessResponse,
  ManualEvidenceActionResponse,
  ReviewFeedbackActionResponse,
  ReviewFeedbackFixupInventoryActionResponse,
  ReviewFeedbackListPageQuery,
  ReviewFeedbackListPageResponse,
} from "./client-changesets";
export {
  buildApiUrl,
  GlassboxApiError,
  requestJsonWithFetch,
  type ActionAcceptedResponse,
  type ApiErrorKind,
  type ApprovalDecision,
  type FastApiValidationIssue,
  type FetchLike,
  type GlassboxApiClientOptions,
  type HealthResponse,
  type JsonRequestOptions,
  type Query,
  type RequestJson,
  type RequestOptions,
} from "./client-core";
export type {
  ForkSessionResponse,
  SessionAggregateQuery,
  SessionAggregateResponse,
  SessionArtifactPageQuery,
  SessionArtifactPageResponse,
  SessionEventLogPageQuery,
  SessionEventLogPageResponse,
  SessionSnapshotResponse,
  SessionSummaryResponse,
  SessionToolCallPageQuery,
  SessionToolCallPageResponse,
  SessionTranscriptPageQuery,
  SessionTranscriptPageResponse,
  SessionTurnMetricsPageQuery,
  SessionTurnMetricsPageResponse,
  ToolAttemptRecoveryResponse,
} from "./client-sessions";
export type {
  AutonomyBudget,
  AutonomyMode,
  BackgroundJobDetailResponse,
  TaskContinuationWindowActionResponse,
  TaskDetailResponse,
  TaskEventPageQuery,
  TaskEventPageResponse,
  TaskListPageQuery,
  TaskListPageResponse,
  TaskPauseWindowResponse,
  TaskStepPageQuery,
  TaskStepPageResponse,
} from "./client-tasks";
export type {
  RepositoryIndexEntryDetailResponse,
  RepositoryIndexRebuildResponse,
  RepositoryIndexSearchPageResponse,
  RepositoryIndexSearchQuery,
  RepositoryIndexStatusResponse,
  WorkspaceMemoryDetailResponse,
  WorkspaceMemoryKind,
  WorkspaceMemoryListPageQuery,
  WorkspaceMemoryListPageResponse,
  WorkspaceMemoryPrunePreviewResponse,
  WorkspaceMemoryState,
} from "./client-workspace";

export function createGlassboxApiClient(options: GlassboxApiClientOptions = {}) {
  const requestJson = createRequestJson(options);
  return {
    ...createCoreEndpoints(requestJson),
    ...createSessionEndpoints(requestJson),
    ...createTaskEndpoints(requestJson),
    ...createChangesetEndpoints(requestJson),
    ...createWorkspaceEndpoints(requestJson),
  };
}

export type GlassboxApiClient = ReturnType<typeof createGlassboxApiClient>;
