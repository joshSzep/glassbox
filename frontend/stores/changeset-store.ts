import { createStore, type StoreApi } from "zustand/vanilla";

import type {
  BranchSearchDetailResponse,
  ChangesetDetailResponse,
  ChangesetListPageResponse,
  ChangesetVerificationPlanPreviewResponse,
  CommitMessageSuggestionResponse,
  CommitReadinessResponse,
  GlassboxApiClient,
} from "@/api/client";
import {
  createFailedActionStatus,
  createIdleActionStatus,
  createPendingActionStatus,
  createRequestTracker,
  createSucceededActionStatus,
  errorMessage,
  type LoadState,
  type StoreActionStatus,
} from "@/stores/store-actions";

export type ChangesetActionKind = "generate-brief" | "refresh-changeset";

export type ChangesetActionStatus = StoreActionStatus<ChangesetActionKind>;

export type ChangesetPageState = {
  error: string | null;
  items: ChangesetListPageResponse["items"];
  loadState: LoadState;
};

export type ChangesetDetailState = {
  branchSearchDetail: BranchSearchDetailResponse | null;
  detail: ChangesetDetailResponse | null;
  error: string | null;
  commitMessage: CommitMessageSuggestionResponse | null;
  commitReadiness: CommitReadinessResponse | null;
  loadState: LoadState;
  selectedChangesetId: string | null;
  verificationPlan: ChangesetVerificationPlanPreviewResponse | null;
};

export type ChangesetStoreState = {
  action: ChangesetActionStatus;
  detail: ChangesetDetailState;
  generateReviewBrief: (changesetId?: string) => Promise<void>;
  loadChangesetPage: (query?: { sessionId?: string | null }) => Promise<void>;
  page: ChangesetPageState;
  refreshChangeset: (changesetId?: string) => Promise<void>;
  reset: () => void;
  selectChangeset: (changesetId: string) => Promise<void>;
};

const CHANGESET_PAGE_SIZE = 100;

export function createChangesetStore(apiClient: GlassboxApiClient): StoreApi<ChangesetStoreState> {
  const listRequests = createRequestTracker();
  const detailRequests = createRequestTracker();

  return createStore<ChangesetStoreState>((set, get) => ({
    action: createIdleActionStatus(),
    detail: createIdleChangesetDetailState(),
    generateReviewBrief: async (changesetId) => {
      const selectedChangesetId = changesetId ?? requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("generate-brief") });
      try {
        const response = await apiClient.generateChangesetReviewBrief({
          changesetId: selectedChangesetId,
        });
        const branchSearchDetail = await loadBranchSearchForChangeset(apiClient, response.detail);
        const verificationPlan = await apiClient.getChangesetVerificationPlan(selectedChangesetId);
        const [commitReadiness, commitMessage] = await Promise.all([
          apiClient.getChangesetCommitReadiness(selectedChangesetId),
          apiClient.getChangesetCommitMessage(selectedChangesetId),
        ]);
        set({
          action: createSucceededActionStatus("generate-brief"),
          detail: {
            branchSearchDetail,
            commitMessage,
            commitReadiness,
            detail: response.detail,
            error: null,
            loadState: "loaded",
            selectedChangesetId,
            verificationPlan,
          },
        });
        await get().loadChangesetPage();
      } catch (error) {
        set({ action: createFailedActionStatus("generate-brief", error) });
      }
    },
    loadChangesetPage: async (query = {}) => {
      const currentRequestId = listRequests.next();
      set((state) => ({
        page: { ...state.page, error: null, loadState: "loading" },
      }));
      try {
        const page = await apiClient.getChangesetPage({
          limit: CHANGESET_PAGE_SIZE,
          session_id: query.sessionId ?? undefined,
        });
        if (!listRequests.isCurrent(currentRequestId)) {
          return;
        }
        set({ page: { error: null, items: page.items, loadState: "loaded" } });
      } catch (error) {
        if (!listRequests.isCurrent(currentRequestId)) {
          return;
        }
        set((state) => ({
          page: { ...state.page, error: errorMessage(error), loadState: "failed" },
        }));
      }
    },
    page: createIdleChangesetPageState(),
    refreshChangeset: async (changesetId) => {
      const selectedChangesetId = changesetId ?? requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("refresh-changeset") });
      try {
        const response = await apiClient.refreshChangeset({ changesetId: selectedChangesetId });
        const branchSearchDetail = await loadBranchSearchForChangeset(apiClient, response.detail);
        const verificationPlan = await apiClient.getChangesetVerificationPlan(selectedChangesetId);
        const [commitReadiness, commitMessage] = await Promise.all([
          apiClient.getChangesetCommitReadiness(selectedChangesetId),
          apiClient.getChangesetCommitMessage(selectedChangesetId),
        ]);
        set({
          action: createSucceededActionStatus("refresh-changeset"),
          detail: {
            branchSearchDetail,
            commitMessage,
            commitReadiness,
            detail: response.detail,
            error: null,
            loadState: "loaded",
            selectedChangesetId,
            verificationPlan,
          },
        });
        await get().loadChangesetPage();
      } catch (error) {
        set({ action: createFailedActionStatus("refresh-changeset", error) });
      }
    },
    reset: () => {
      listRequests.invalidate();
      detailRequests.invalidate();
      set({
        action: createIdleActionStatus(),
        detail: createIdleChangesetDetailState(),
        page: createIdleChangesetPageState(),
      });
    },
    selectChangeset: async (changesetId) => {
      const currentRequestId = detailRequests.next();
      set({
        detail: {
          branchSearchDetail: null,
          commitMessage: null,
          commitReadiness: null,
          detail: null,
          error: null,
          loadState: "loading",
          selectedChangesetId: changesetId,
          verificationPlan: null,
        },
      });
      try {
        const detail = await apiClient.getChangesetDetail(changesetId);
        const [verificationPlan, commitReadiness, commitMessage, branchSearchDetail] =
          await Promise.all([
            apiClient.getChangesetVerificationPlan(changesetId),
            apiClient.getChangesetCommitReadiness(changesetId),
            apiClient.getChangesetCommitMessage(changesetId),
            loadBranchSearchForChangeset(apiClient, detail),
          ]);
        if (!detailRequests.isCurrent(currentRequestId)) {
          return;
        }
        set({
          detail: {
            branchSearchDetail,
            commitMessage,
            commitReadiness,
            detail,
            error: null,
            loadState: "loaded",
            selectedChangesetId: changesetId,
            verificationPlan,
          },
        });
      } catch (error) {
        if (!detailRequests.isCurrent(currentRequestId)) {
          return;
        }
        set({
          detail: {
            branchSearchDetail: null,
            commitMessage: null,
            commitReadiness: null,
            detail: null,
            error: errorMessage(error),
            loadState: "failed",
            selectedChangesetId: changesetId,
            verificationPlan: null,
          },
        });
      }
    },
  }));
}

function createIdleChangesetPageState(): ChangesetPageState {
  return { error: null, items: [], loadState: "idle" };
}

function createIdleChangesetDetailState(): ChangesetDetailState {
  return {
    branchSearchDetail: null,
    commitMessage: null,
    commitReadiness: null,
    detail: null,
    error: null,
    loadState: "idle",
    selectedChangesetId: null,
    verificationPlan: null,
  };
}

async function loadBranchSearchForChangeset(
  apiClient: GlassboxApiClient,
  detail: ChangesetDetailResponse,
): Promise<BranchSearchDetailResponse | null> {
  const searchId = detail.changeset.branch_search_id;
  if (searchId === null || searchId === undefined) {
    return null;
  }
  try {
    return await apiClient.getBranchSearchDetail(searchId);
  } catch {
    return null;
  }
}

function requireSelectedChangesetId(detail: ChangesetDetailState): string {
  if (detail.selectedChangesetId === null) {
    throw new Error("No changeset is selected.");
  }
  return detail.selectedChangesetId;
}
