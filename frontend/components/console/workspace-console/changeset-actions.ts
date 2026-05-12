import {
  selectChangesetRoute,
  selectChangesetSurfaceRoute,
  type AppRouteState,
} from "@/routing/app-route";

import { confirmAction } from "./action-confirm";
import type { WorkspaceConsoleStores } from "./types";

type Navigate = (route: AppRouteState) => void;

export function changesetConsoleActions({
  changesetStore,
  navigate,
  route,
}: Pick<WorkspaceConsoleStores, "changesetStore"> & {
  navigate: Navigate;
  route: AppRouteState;
}) {
  return {
    onRefresh: () => {
      void changesetStore.getState().loadChangesetPage();
      const selected = changesetStore.getState().detail.selectedChangesetId;
      if (selected !== null) {
        void changesetStore.getState().selectChangeset(selected);
      }
    },
    onRefreshChangeset: () => {
      if (!confirmAction("Refresh basic source evidence for this changeset?")) {
        return;
      }
      void changesetStore.getState().refreshChangeset();
    },
    onGenerateReviewBrief: () => {
      if (!confirmAction("Generate a reviewer-safe brief for this changeset?")) {
        return;
      }
      void changesetStore.getState().generateReviewBrief();
    },
    onInspectFeedbackStatus: () => {
      void changesetStore.getState().inspectFeedbackStatus();
    },
    onInspectHandoff: () => {
      void changesetStore.getState().inspectHandoff();
    },
    onPreviewVerification: () => {
      void changesetStore.getState().previewVerification();
    },
    onAttachManualEvidence: (
      input: Parameters<ReturnType<typeof changesetStore.getState>["attachManualEvidence"]>[0],
    ) => {
      if (!confirmAction("Attach this manual evidence record?")) {
        return;
      }
      void changesetStore.getState().attachManualEvidence(input);
    },
    onRecordFeedbackFixup: (feedbackId: string) => {
      if (
        !confirmAction(
          "Record response-linked fixup inventory from the current workspace diff? Inspect feedback detail first if scope is unclear.",
        )
      ) {
        return;
      }
      void changesetStore.getState().recordFeedbackFixupInventory(feedbackId);
    },
    onRecordVerification: (
      input: Parameters<ReturnType<typeof changesetStore.getState>["recordVerification"]>[0],
    ) => {
      if (
        !confirmAction(
          "Record retained verification evidence for this plan entry? This does not run commands.",
        )
      ) {
        return;
      }
      void changesetStore.getState().recordVerification(input);
    },
    onSelectChangeset: (changesetId: string) => {
      navigate(selectChangesetRoute(route, changesetId));
      void changesetStore.getState().selectChangeset(changesetId);
    },
    onShowList: () => {
      navigate(selectChangesetSurfaceRoute(route));
      changesetStore.getState().reset();
      void changesetStore.getState().loadChangesetPage();
    },
  };
}
