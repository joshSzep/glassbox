import type { GlassboxApiClient } from "@/api/client";
import type { ChangesetStoreActions } from "@/stores/changeset-store";
import {
  recordVerificationActionMessage,
  verificationPreviewActionMessage,
} from "@/stores/changeset-store-action-messages";
import {
  loadRepositoryIntelligenceForChangeset,
  reloadSelectedChangeset,
  type ChangesetStoreGet,
  type ChangesetStoreSet,
} from "@/stores/changeset-store-loaders";
import { requireSelectedChangesetId } from "@/stores/changeset-store-selectors";
import {
  createFailedActionStatus,
  createPendingActionStatus,
  createSucceededActionStatus,
} from "@/stores/store-actions";

type VerificationActionContext = {
  apiClient: GlassboxApiClient;
  get: ChangesetStoreGet;
  set: ChangesetStoreSet;
};

export function createChangesetStoreVerificationActions({
  apiClient,
  get,
  set,
}: VerificationActionContext): Pick<
  ChangesetStoreActions,
  "previewVerification" | "recordVerification"
> {
  return {
    previewVerification: async (changesetId) => {
      const selectedChangesetId = changesetId ?? requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("preview-verification") });
      try {
        const verificationPlan = await apiClient.getChangesetVerificationPlan(selectedChangesetId);
        const repositoryIntelligence = await loadRepositoryIntelligenceForChangeset(
          apiClient,
          verificationPlan,
        );
        set((state) => ({
          detail: {
            ...state.detail,
            error: null,
            lastActionMessage: verificationPreviewActionMessage(
              verificationPlan.recommended_commands.length,
            ),
            loadState: "loaded",
            repositoryIntelligence,
            selectedChangesetId,
            verificationPlan,
          },
        }));
        set({ action: createSucceededActionStatus("preview-verification") });
      } catch (error) {
        set({ action: createFailedActionStatus("preview-verification", error) });
      }
    },
    recordVerification: async (input) => {
      const selectedChangesetId = requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("record-verification") });
      try {
        const response = await apiClient.recordChangesetVerification({
          changesetId: selectedChangesetId,
          taskId: input.taskId,
          verificationId: input.verificationId,
        });
        await reloadSelectedChangeset(apiClient, selectedChangesetId, set, {
          lastActionMessage: recordVerificationActionMessage(response),
        });
        set({ action: createSucceededActionStatus("record-verification") });
        await get().loadChangesetPage();
      } catch (error) {
        set({ action: createFailedActionStatus("record-verification", error) });
      }
    },
  };
}
