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
  ManualEvidenceActionResponse,
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

export type ChangesetActionKind =
  | "attach-manual-evidence"
  | "generate-brief"
  | "inspect-feedback"
  | "inspect-handoff"
  | "preview-verification"
  | "refresh-changeset";

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
  handoffReadiness: HandoffReadinessResponse | null;
  lastActionMessage: string | null;
  loadState: LoadState;
  selectedChangesetId: string | null;
  verificationPlan: ChangesetVerificationPlanPreviewResponse | null;
};

export type ChangesetStoreState = {
  action: ChangesetActionStatus;
  attachManualEvidence: (input: {
    commandText?: string | null;
    evidenceKind?: Parameters<GlassboxApiClient["attachManualEvidence"]>[0]["evidenceKind"];
    freshness?: Parameters<GlassboxApiClient["attachManualEvidence"]>[0]["freshness"];
    note?: string | null;
    sourceLabel: string;
    summary: string;
  }) => Promise<void>;
  detail: ChangesetDetailState;
  generateReviewBrief: (changesetId?: string) => Promise<void>;
  inspectFeedbackStatus: (changesetId?: string) => Promise<void>;
  inspectHandoff: (changesetId?: string) => Promise<void>;
  loadChangesetPage: (query?: { sessionId?: string | null }) => Promise<void>;
  page: ChangesetPageState;
  previewVerification: (changesetId?: string) => Promise<void>;
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
    attachManualEvidence: async (input) => {
      const selectedChangesetId = requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("attach-manual-evidence") });
      try {
        const response = await apiClient.attachManualEvidence({
          changesetId: selectedChangesetId,
          commandText: input.commandText,
          evidenceKind: input.evidenceKind,
          freshness: input.freshness,
          note: input.note,
          sourceLabel: input.sourceLabel,
          summary: input.summary,
        });
        await reloadSelectedChangeset(apiClient, selectedChangesetId, set, {
          lastActionMessage: manualEvidenceActionMessage(response),
        });
        set({ action: createSucceededActionStatus("attach-manual-evidence") });
        await get().loadChangesetPage();
      } catch (error) {
        set({ action: createFailedActionStatus("attach-manual-evidence", error) });
      }
    },
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
        const [commitReadiness, handoffReadiness, commitMessage] = await Promise.all([
          apiClient.getChangesetCommitReadiness(selectedChangesetId),
          apiClient.getChangesetHandoffReadiness(selectedChangesetId),
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
            handoffReadiness,
            lastActionMessage: `Lifecycle brief ${response.artifact_id} generated.`,
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
    inspectFeedbackStatus: async (changesetId) => {
      const selectedChangesetId = changesetId ?? requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("inspect-feedback") });
      try {
        const response = await apiClient.getReviewFeedbackPage({
          changeset_id: selectedChangesetId,
        });
        const currentDetail = get().detail.detail;
        if (
          currentDetail === null ||
          currentDetail.changeset.changeset_id !== selectedChangesetId
        ) {
          await reloadSelectedChangeset(apiClient, selectedChangesetId, set, {
            lastActionMessage: "Feedback status refreshed.",
          });
        } else {
          set((state) => ({
            detail: {
              ...state.detail,
              detail: {
                ...currentDetail,
                review_feedback: response.items,
                review_response_summary:
                  response.response_summary ?? currentDetail.review_response_summary,
              },
              error: null,
              lastActionMessage: "Feedback status refreshed.",
              loadState: "loaded",
              selectedChangesetId,
            },
          }));
        }
        set({ action: createSucceededActionStatus("inspect-feedback") });
      } catch (error) {
        set({ action: createFailedActionStatus("inspect-feedback", error) });
      }
    },
    inspectHandoff: async (changesetId) => {
      const selectedChangesetId = changesetId ?? requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("inspect-handoff") });
      try {
        const [handoffReadiness, commitReadiness] = await Promise.all([
          apiClient.getChangesetHandoffReadiness(selectedChangesetId),
          apiClient.getChangesetCommitReadiness(selectedChangesetId),
        ]);
        set((state) => ({
          detail: {
            ...state.detail,
            commitReadiness,
            error: null,
            handoffReadiness,
            lastActionMessage: `Handoff posture ${handoffReadiness.state} refreshed.`,
            loadState: "loaded",
            selectedChangesetId,
          },
        }));
        set({ action: createSucceededActionStatus("inspect-handoff") });
      } catch (error) {
        set({ action: createFailedActionStatus("inspect-handoff", error) });
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
    previewVerification: async (changesetId) => {
      const selectedChangesetId = changesetId ?? requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("preview-verification") });
      try {
        const verificationPlan = await apiClient.getChangesetVerificationPlan(selectedChangesetId);
        const commandCount = verificationPlan.recommended_commands.length;
        set((state) => ({
          detail: {
            ...state.detail,
            error: null,
            lastActionMessage:
              `${commandCount} verification command${commandCount === 1 ? "" : "s"} ` +
              "previewed; none were run.",
            loadState: "loaded",
            selectedChangesetId,
            verificationPlan,
          },
        }));
        set({ action: createSucceededActionStatus("preview-verification") });
      } catch (error) {
        set({ action: createFailedActionStatus("preview-verification", error) });
      }
    },
    refreshChangeset: async (changesetId) => {
      const selectedChangesetId = changesetId ?? requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("refresh-changeset") });
      try {
        const response = await apiClient.refreshChangeset({ changesetId: selectedChangesetId });
        const branchSearchDetail = await loadBranchSearchForChangeset(apiClient, response.detail);
        const verificationPlan = await apiClient.getChangesetVerificationPlan(selectedChangesetId);
        const [commitReadiness, handoffReadiness, commitMessage] = await Promise.all([
          apiClient.getChangesetCommitReadiness(selectedChangesetId),
          apiClient.getChangesetHandoffReadiness(selectedChangesetId),
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
            handoffReadiness,
            lastActionMessage: `Inventory refreshed at sequence ${response.event_sequence}.`,
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
          handoffReadiness: null,
          lastActionMessage: null,
          loadState: "loading",
          selectedChangesetId: changesetId,
          verificationPlan: null,
        },
      });
      try {
        const detail = await apiClient.getChangesetDetail(changesetId);
        const [
          verificationPlan,
          commitReadiness,
          handoffReadiness,
          commitMessage,
          branchSearchDetail,
        ] = await Promise.all([
          apiClient.getChangesetVerificationPlan(changesetId),
          apiClient.getChangesetCommitReadiness(changesetId),
          apiClient.getChangesetHandoffReadiness(changesetId),
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
            handoffReadiness,
            lastActionMessage: null,
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
            handoffReadiness: null,
            lastActionMessage: null,
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
    handoffReadiness: null,
    lastActionMessage: null,
    loadState: "idle",
    selectedChangesetId: null,
    verificationPlan: null,
  };
}

async function reloadSelectedChangeset(
  apiClient: GlassboxApiClient,
  changesetId: string,
  set: StoreApi<ChangesetStoreState>["setState"],
  options: { lastActionMessage: string | null },
) {
  const detail = await apiClient.getChangesetDetail(changesetId);
  const [verificationPlan, commitReadiness, handoffReadiness, commitMessage, branchSearchDetail] =
    await Promise.all([
      apiClient.getChangesetVerificationPlan(changesetId),
      apiClient.getChangesetCommitReadiness(changesetId),
      apiClient.getChangesetHandoffReadiness(changesetId),
      apiClient.getChangesetCommitMessage(changesetId),
      loadBranchSearchForChangeset(apiClient, detail),
    ]);
  set({
    detail: {
      branchSearchDetail,
      commitMessage,
      commitReadiness,
      detail,
      error: null,
      handoffReadiness,
      lastActionMessage: options.lastActionMessage,
      loadState: "loaded",
      selectedChangesetId: changesetId,
      verificationPlan,
    },
  });
}

function manualEvidenceActionMessage(response: ManualEvidenceActionResponse): string {
  return `Manual evidence ${response.evidence.evidence_id} attached.`;
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
