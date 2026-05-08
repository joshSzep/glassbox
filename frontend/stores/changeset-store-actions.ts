import type { GlassboxApiClient } from "@/api/client";
import type { ChangesetStoreActions } from "@/stores/changeset-store";
import {
  loadChangesetPage,
  selectChangeset,
  type ChangesetStoreGet,
  type ChangesetStoreSet,
  type RequestTracker,
} from "@/stores/changeset-store-loaders";
import { createChangesetStoreReviewActions } from "@/stores/changeset-store-review-actions";
import {
  createIdleChangesetDetailState,
  createIdleChangesetPageState,
} from "@/stores/changeset-store-selectors";

type ChangesetActionContext = {
  apiClient: GlassboxApiClient;
  detailRequests: RequestTracker;
  get: ChangesetStoreGet;
  listRequests: RequestTracker;
  set: ChangesetStoreSet;
};

export function createChangesetStoreActions({
  apiClient,
  detailRequests,
  get,
  listRequests,
  set,
}: ChangesetActionContext): ChangesetStoreActions {
  return {
    ...createChangesetStoreReviewActions({ apiClient, get, set }),
    loadChangesetPage: async (query = {}) => {
      await loadChangesetPage({ apiClient, listRequests, query, set });
    },
    reset: () => {
      listRequests.invalidate();
      detailRequests.invalidate();
      set({
        action: { error: null, kind: null, state: "idle" },
        detail: createIdleChangesetDetailState(),
        page: createIdleChangesetPageState(),
      });
    },
    selectChangeset: async (changesetId) => {
      await selectChangeset({ apiClient, changesetId, detailRequests, set });
    },
  };
}
