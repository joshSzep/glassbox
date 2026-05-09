import { createStore, type StoreApi } from "zustand/vanilla";

import type {
  BranchSearchDetailResponse,
  ChangesetDetailResponse,
  ChangesetListPageResponse,
  ChangesetVerificationPlanPreviewResponse,
  CommitMessageSuggestionResponse,
  CommitReadinessResponse,
  GlassboxApiClient,
  HandoffReadinessResponse,
  RepositoryIntelligenceCommandRecipeListPageResponse,
  RepositoryIntelligenceFreshnessResponse,
  RepositoryIntelligencePathInspectionResponse,
  RepositoryIntelligenceVerificationRecommendationResponse,
} from "@/api/client";
import { createChangesetStoreActions } from "@/stores/changeset-store-actions";
import {
  createIdleChangesetDetailState,
  createIdleChangesetPageState,
} from "@/stores/changeset-store-selectors";
import {
  createIdleActionStatus,
  createRequestTracker,
  type LoadState,
  type StoreActionStatus,
} from "@/stores/store-actions";

export type ChangesetActionKind =
  | "attach-manual-evidence"
  | "generate-brief"
  | "inspect-feedback"
  | "inspect-handoff"
  | "preview-verification"
  | "record-feedback-fixup"
  | "refresh-changeset";

export type ChangesetActionStatus = StoreActionStatus<ChangesetActionKind>;

export type ChangesetPageState = {
  error: string | null;
  items: ChangesetListPageResponse["items"];
  loadState: LoadState;
};

export type ChangesetRepositoryIntelligenceState = {
  commandRecipes: RepositoryIntelligenceCommandRecipeListPageResponse["items"];
  error: string | null;
  freshness: RepositoryIntelligenceFreshnessResponse | null;
  loadState: LoadState;
  pathInspections: RepositoryIntelligencePathInspectionResponse[];
  verification: RepositoryIntelligenceVerificationRecommendationResponse | null;
};

export type ChangesetDetailState = {
  branchSearchDetail: BranchSearchDetailResponse | null;
  detail: ChangesetDetailResponse | null;
  error: string | null;
  commitMessage: CommitMessageSuggestionResponse | null;
  commitReadiness: CommitReadinessResponse | null;
  handoffReadiness: HandoffReadinessResponse | null;
  lastActionMessage: string | null;
  loadState: LoadState;
  repositoryIntelligence?: ChangesetRepositoryIntelligenceState;
  selectedChangesetId: string | null;
  verificationPlan: ChangesetVerificationPlanPreviewResponse | null;
};

type ChangesetStoreData = {
  action: ChangesetActionStatus;
  detail: ChangesetDetailState;
  page: ChangesetPageState;
};

export type ChangesetStoreActions = {
  attachManualEvidence: (input: {
    commandText?: string | null;
    evidenceKind?: Parameters<GlassboxApiClient["attachManualEvidence"]>[0]["evidenceKind"];
    freshness?: Parameters<GlassboxApiClient["attachManualEvidence"]>[0]["freshness"];
    note?: string | null;
    sourceLabel: string;
    summary: string;
  }) => Promise<void>;
  generateReviewBrief: (changesetId?: string) => Promise<void>;
  inspectFeedbackStatus: (changesetId?: string) => Promise<void>;
  inspectHandoff: (changesetId?: string) => Promise<void>;
  loadChangesetPage: (query?: { sessionId?: string | null }) => Promise<void>;
  previewVerification: (changesetId?: string) => Promise<void>;
  recordFeedbackFixupInventory: (feedbackId: string) => Promise<void>;
  refreshChangeset: (changesetId?: string) => Promise<void>;
  reset: () => void;
  selectChangeset: (changesetId: string) => Promise<void>;
};

export type ChangesetStoreState = ChangesetStoreData & ChangesetStoreActions;

export function createChangesetStore(apiClient: GlassboxApiClient): StoreApi<ChangesetStoreState> {
  const listRequests = createRequestTracker();
  const detailRequests = createRequestTracker();

  return createStore<ChangesetStoreState>((set, get) => ({
    action: createIdleActionStatus(),
    detail: createIdleChangesetDetailState(),
    page: createIdleChangesetPageState(),
    ...createChangesetStoreActions({
      apiClient,
      detailRequests,
      get,
      listRequests,
      set,
    }),
  }));
}
