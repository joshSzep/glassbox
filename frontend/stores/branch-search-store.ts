import { createStore, type StoreApi } from "zustand/vanilla";

import type {
  BranchSearchDetailResponse,
  BranchSearchListPageResponse,
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

export type BranchSearchActionKind =
  | "needs-review-candidate"
  | "reject-candidate"
  | "select-candidate";

export type BranchSearchActionStatus = StoreActionStatus<BranchSearchActionKind>;

export type BranchSearchPageState = {
  error: string | null;
  items: BranchSearchListPageResponse["items"];
  loadState: LoadState;
};

export type BranchSearchDetailState = {
  detail: BranchSearchDetailResponse | null;
  error: string | null;
  loadState: LoadState;
  selectedSearchId: string | null;
};

export type BranchSearchStoreState = {
  action: BranchSearchActionStatus;
  detail: BranchSearchDetailState;
  loadBranchSearchPage: (query?: { sessionId?: string | null }) => Promise<void>;
  markCandidate: (input: {
    action: "needs-review" | "reject" | "select";
    candidateId: string;
    reason: string;
    searchId?: string;
  }) => Promise<void>;
  page: BranchSearchPageState;
  reset: () => void;
  selectBranchSearch: (searchId: string) => Promise<void>;
};

const BRANCH_SEARCH_PAGE_SIZE = 100;

export function createBranchSearchStore(
  apiClient: GlassboxApiClient,
): StoreApi<BranchSearchStoreState> {
  const listRequests = createRequestTracker();
  const detailRequests = createRequestTracker();

  return createStore<BranchSearchStoreState>((set, get) => ({
    action: createIdleActionStatus(),
    detail: createIdleBranchSearchDetailState(),
    loadBranchSearchPage: async (query = {}) => {
      const currentRequestId = listRequests.next();
      set((state) => ({
        page: { ...state.page, error: null, loadState: "loading" },
      }));
      try {
        const page = await apiClient.getBranchSearchPage({
          limit: BRANCH_SEARCH_PAGE_SIZE,
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
    markCandidate: async (input) => {
      const searchId = input.searchId ?? requireSelectedBranchSearchId(get().detail);
      const kind = branchActionKind(input.action);
      set({ action: createPendingActionStatus(kind) });
      try {
        await apiClient.markBranchCandidate({
          action: input.action,
          candidateId: input.candidateId,
          reason: input.reason,
          searchId,
        });
        set({ action: createSucceededActionStatus(kind) });
        await get().selectBranchSearch(searchId);
        await get().loadBranchSearchPage();
      } catch (error) {
        set({ action: createFailedActionStatus(kind, error) });
      }
    },
    page: createIdleBranchSearchPageState(),
    reset: () => {
      listRequests.invalidate();
      detailRequests.invalidate();
      set({
        action: createIdleActionStatus(),
        detail: createIdleBranchSearchDetailState(),
        page: createIdleBranchSearchPageState(),
      });
    },
    selectBranchSearch: async (searchId) => {
      const currentRequestId = detailRequests.next();
      set({
        detail: {
          detail: null,
          error: null,
          loadState: "loading",
          selectedSearchId: searchId,
        },
      });
      try {
        const detail = await apiClient.getBranchSearchDetail(searchId);
        if (!detailRequests.isCurrent(currentRequestId)) {
          return;
        }
        set({
          detail: { detail, error: null, loadState: "loaded", selectedSearchId: searchId },
        });
      } catch (error) {
        if (!detailRequests.isCurrent(currentRequestId)) {
          return;
        }
        set({
          detail: {
            detail: null,
            error: errorMessage(error),
            loadState: "failed",
            selectedSearchId: searchId,
          },
        });
      }
    },
  }));
}

function createIdleBranchSearchPageState(): BranchSearchPageState {
  return { error: null, items: [], loadState: "idle" };
}

function createIdleBranchSearchDetailState(): BranchSearchDetailState {
  return { detail: null, error: null, loadState: "idle", selectedSearchId: null };
}

function requireSelectedBranchSearchId(detail: BranchSearchDetailState): string {
  if (detail.selectedSearchId === null) {
    throw new Error("No branch search is selected.");
  }
  return detail.selectedSearchId;
}

function branchActionKind(action: "needs-review" | "reject" | "select"): BranchSearchActionKind {
  if (action === "select") {
    return "select-candidate";
  }
  if (action === "reject") {
    return "reject-candidate";
  }
  return "needs-review-candidate";
}
