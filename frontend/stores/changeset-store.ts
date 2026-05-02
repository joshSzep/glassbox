import { createStore, type StoreApi } from "zustand/vanilla";

import type {
  ChangesetDetailResponse,
  ChangesetListPageResponse,
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

export type ChangesetActionKind = "refresh-changeset";

export type ChangesetActionStatus = StoreActionStatus<ChangesetActionKind>;

export type ChangesetPageState = {
  error: string | null;
  items: ChangesetListPageResponse["items"];
  loadState: LoadState;
};

export type ChangesetDetailState = {
  detail: ChangesetDetailResponse | null;
  error: string | null;
  loadState: LoadState;
  selectedChangesetId: string | null;
};

export type ChangesetStoreState = {
  action: ChangesetActionStatus;
  detail: ChangesetDetailState;
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
        set({
          action: createSucceededActionStatus("refresh-changeset"),
          detail: {
            detail: response.detail,
            error: null,
            loadState: "loaded",
            selectedChangesetId,
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
          detail: null,
          error: null,
          loadState: "loading",
          selectedChangesetId: changesetId,
        },
      });
      try {
        const detail = await apiClient.getChangesetDetail(changesetId);
        if (!detailRequests.isCurrent(currentRequestId)) {
          return;
        }
        set({
          detail: { detail, error: null, loadState: "loaded", selectedChangesetId: changesetId },
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
            selectedChangesetId: changesetId,
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
  return { detail: null, error: null, loadState: "idle", selectedChangesetId: null };
}

function requireSelectedChangesetId(detail: ChangesetDetailState): string {
  if (detail.selectedChangesetId === null) {
    throw new Error("No changeset is selected.");
  }
  return detail.selectedChangesetId;
}
