import type {
  BranchSearchDetailResponse,
  ChangesetDetailResponse,
  GlassboxApiClient,
} from "@/api/client";
import type { ChangesetStoreState } from "@/stores/changeset-store";
import {
  createFailedChangesetDetailState,
  createLoadingChangesetDetailState,
} from "@/stores/changeset-store-selectors";
import { errorMessage, type createRequestTracker } from "@/stores/store-actions";

export type ChangesetStoreSet = {
  (
    partial:
      | ChangesetStoreState
      | Partial<ChangesetStoreState>
      | ((state: ChangesetStoreState) => ChangesetStoreState | Partial<ChangesetStoreState>),
    replace?: false,
  ): void;
};

export type ChangesetStoreGet = () => ChangesetStoreState;
export type RequestTracker = ReturnType<typeof createRequestTracker>;

export const CHANGESET_PAGE_SIZE = 100;

export type ReloadSelectedChangesetOptions = {
  lastActionMessage: string | null;
};

export async function loadChangesetPage(input: {
  apiClient: GlassboxApiClient;
  listRequests: RequestTracker;
  query?: { sessionId?: string | null };
  set: ChangesetStoreSet;
}): Promise<void> {
  const currentRequestId = input.listRequests.next();
  input.set((state) => ({
    page: { ...state.page, error: null, loadState: "loading" },
  }));
  try {
    const page = await input.apiClient.getChangesetPage({
      limit: CHANGESET_PAGE_SIZE,
      session_id: input.query?.sessionId ?? undefined,
    });
    if (!input.listRequests.isCurrent(currentRequestId)) {
      return;
    }
    input.set({ page: { error: null, items: page.items, loadState: "loaded" } });
  } catch (error) {
    if (!input.listRequests.isCurrent(currentRequestId)) {
      return;
    }
    input.set((state) => ({
      page: { ...state.page, error: errorMessage(error), loadState: "failed" },
    }));
  }
}

export async function selectChangeset(input: {
  apiClient: GlassboxApiClient;
  changesetId: string;
  detailRequests: RequestTracker;
  set: ChangesetStoreSet;
}): Promise<void> {
  const currentRequestId = input.detailRequests.next();
  input.set({ detail: createLoadingChangesetDetailState(input.changesetId) });
  try {
    const detail = await input.apiClient.getChangesetDetail(input.changesetId);
    const [verificationPlan, commitReadiness, handoffReadiness, commitMessage, branchSearchDetail] =
      await Promise.all([
        input.apiClient.getChangesetVerificationPlan(input.changesetId),
        input.apiClient.getChangesetCommitReadiness(input.changesetId),
        input.apiClient.getChangesetHandoffReadiness(input.changesetId),
        input.apiClient.getChangesetCommitMessage(input.changesetId),
        loadBranchSearchForChangeset(input.apiClient, detail),
      ]);
    if (!input.detailRequests.isCurrent(currentRequestId)) {
      return;
    }
    input.set({
      detail: {
        branchSearchDetail,
        commitMessage,
        commitReadiness,
        detail,
        error: null,
        handoffReadiness,
        lastActionMessage: null,
        loadState: "loaded",
        selectedChangesetId: input.changesetId,
        verificationPlan,
      },
    });
  } catch (error) {
    if (!input.detailRequests.isCurrent(currentRequestId)) {
      return;
    }
    input.set({
      detail: createFailedChangesetDetailState({
        changesetId: input.changesetId,
        error: errorMessage(error),
      }),
    });
  }
}

export async function reloadSelectedChangeset(
  apiClient: GlassboxApiClient,
  changesetId: string,
  set: ChangesetStoreSet,
  options: ReloadSelectedChangesetOptions,
): Promise<void> {
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

export async function loadBranchSearchForChangeset(
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
