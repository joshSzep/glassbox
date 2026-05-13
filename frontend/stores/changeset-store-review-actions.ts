import type { GlassboxApiClient } from "@/api/client";
import type { ChangesetStoreActions } from "@/stores/changeset-store";
import {
  feedbackStatusActionMessage,
  fixupInventoryActionMessage,
  fixupInventoryFailedActionMessage,
  handoffActionMessage,
  inspectFirstActionMessage,
  manualEvidenceActionMessage,
  refreshChangesetActionMessage,
  reviewBriefActionMessage,
} from "@/stores/changeset-store-action-messages";
import { createChangesetStoreVerificationActions } from "@/stores/changeset-store-verification-actions";
import {
  loadBranchSearchForChangeset,
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

type ReviewActionContext = {
  apiClient: GlassboxApiClient;
  get: ChangesetStoreGet;
  set: ChangesetStoreSet;
};

export function createChangesetStoreReviewActions({
  apiClient,
  get,
  set,
}: ReviewActionContext): Pick<
  ChangesetStoreActions,
  | "attachManualEvidence"
  | "generateReviewBrief"
  | "inspectFeedbackStatus"
  | "inspectHandoff"
  | "previewVerification"
  | "recordFeedbackFixupInventory"
  | "recordVerification"
  | "refreshChangeset"
> {
  const verificationActions = createChangesetStoreVerificationActions({ apiClient, get, set });
  return {
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
    generateReviewBrief: async (changesetId) => {
      const selectedChangesetId = changesetId ?? requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("generate-brief") });
      try {
        const response = await apiClient.generateChangesetReviewBrief({
          changesetId: selectedChangesetId,
        });
        const branchSearchDetail = await loadBranchSearchForChangeset(apiClient, response.detail);
        const verificationPlan = await apiClient.getChangesetVerificationPlan(selectedChangesetId);
        const repositoryIntelligence = await loadRepositoryIntelligenceForChangeset(
          apiClient,
          verificationPlan,
        );
        const [commitReadiness, handoffReadiness, commitMessage, evidenceGraph] = await Promise.all(
          [
            apiClient.getChangesetCommitReadiness(selectedChangesetId),
            apiClient.getChangesetHandoffReadiness(selectedChangesetId),
            apiClient.getChangesetCommitMessage(selectedChangesetId),
            apiClient.getChangesetEvidenceGraph(selectedChangesetId).catch(() => null),
          ],
        );
        set({
          action: createSucceededActionStatus("generate-brief"),
          detail: {
            branchSearchDetail,
            commitMessage,
            commitReadiness,
            detail: response.detail,
            evidenceGraph,
            error: null,
            handoffReadiness,
            lastActionMessage: reviewBriefActionMessage(response),
            loadState: "loaded",
            repositoryIntelligence,
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
            lastActionMessage: feedbackStatusActionMessage(),
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
              lastActionMessage: feedbackStatusActionMessage(),
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
            lastActionMessage: handoffActionMessage(handoffReadiness.state),
            loadState: "loaded",
            selectedChangesetId,
          },
        }));
        set({ action: createSucceededActionStatus("inspect-handoff") });
      } catch (error) {
        set({ action: createFailedActionStatus("inspect-handoff", error) });
      }
    },
    previewVerification: verificationActions.previewVerification,
    recordFeedbackFixupInventory: async (feedbackId) => {
      const currentDetail = get().detail.detail;
      const selectedChangesetId = requireSelectedChangesetId(get().detail);
      const response = currentDetail?.review_response_summary.items.find(
        (item) => item.feedback_id === feedbackId,
      );
      set({ action: createPendingActionStatus("record-feedback-fixup") });
      try {
        if (response?.safe_next_actions[0]) {
          set((state) => ({
            detail: {
              ...state.detail,
              lastActionMessage: inspectFirstActionMessage(response.safe_next_actions[0]),
            },
          }));
        }
        const fixup = await apiClient.recordReviewFeedbackFixupInventory({
          feedbackId,
          fromWorkspace: true,
        });
        await reloadSelectedChangeset(apiClient, fixup.changeset_id, set, {
          lastActionMessage: fixupInventoryActionMessage({
            artifactId: fixup.artifact_id,
            feedbackId,
          }),
        });
        set({ action: createSucceededActionStatus("record-feedback-fixup") });
        await get().loadChangesetPage();
      } catch (error) {
        set({ action: createFailedActionStatus("record-feedback-fixup", error) });
        if (currentDetail !== null) {
          await reloadSelectedChangeset(apiClient, selectedChangesetId, set, {
            lastActionMessage: fixupInventoryFailedActionMessage(),
          });
        }
      }
    },
    recordVerification: verificationActions.recordVerification,
    refreshChangeset: async (changesetId) => {
      const selectedChangesetId = changesetId ?? requireSelectedChangesetId(get().detail);
      set({ action: createPendingActionStatus("refresh-changeset") });
      try {
        const response = await apiClient.refreshChangeset({ changesetId: selectedChangesetId });
        const branchSearchDetail = await loadBranchSearchForChangeset(apiClient, response.detail);
        const verificationPlan = await apiClient.getChangesetVerificationPlan(selectedChangesetId);
        const repositoryIntelligence = await loadRepositoryIntelligenceForChangeset(
          apiClient,
          verificationPlan,
        );
        const [commitReadiness, handoffReadiness, commitMessage, evidenceGraph] = await Promise.all(
          [
            apiClient.getChangesetCommitReadiness(selectedChangesetId),
            apiClient.getChangesetHandoffReadiness(selectedChangesetId),
            apiClient.getChangesetCommitMessage(selectedChangesetId),
            apiClient.getChangesetEvidenceGraph(selectedChangesetId).catch(() => null),
          ],
        );
        set({
          action: createSucceededActionStatus("refresh-changeset"),
          detail: {
            branchSearchDetail,
            commitMessage,
            commitReadiness,
            detail: response.detail,
            evidenceGraph,
            error: null,
            handoffReadiness,
            lastActionMessage: refreshChangesetActionMessage(response.event_sequence),
            loadState: "loaded",
            repositoryIntelligence,
            selectedChangesetId,
            verificationPlan,
          },
        });
        await get().loadChangesetPage();
      } catch (error) {
        set({ action: createFailedActionStatus("refresh-changeset", error) });
      }
    },
  };
}
