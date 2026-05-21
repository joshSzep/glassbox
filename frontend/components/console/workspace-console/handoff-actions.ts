import type { HandoffDraftState, HandoffPageState } from "@/stores/handoff-store";

import { confirmAction } from "./action-confirm";
import type { WorkspaceConsoleStores } from "./types";

export function handoffConsoleActions({
  handoffStore,
}: Pick<WorkspaceConsoleStores, "handoffStore">) {
  return {
    onAccept: () => {
      void handoffStore.getState().acceptSelected();
    },
    onArchive: () => {
      if (!confirmAction("Archive this handoff record as historical local evidence?")) {
        return;
      }
      void handoffStore.getState().archiveSelected();
    },
    onExport: () => {
      if (!confirmAction("Write this redacted handoff package to the local filesystem?")) {
        return;
      }
      void handoffStore.getState().exportPackage();
    },
    onImport: () => {
      if (!confirmAction("Import this package for inspection-only local state?")) {
        return;
      }
      void handoffStore.getState().importPackage();
    },
    onInspect: () => {
      void handoffStore.getState().inspectPackage();
    },
    onLoadGuidance: () => {
      void handoffStore.getState().loadGuidance();
    },
    onLoadList: () => {
      void handoffStore.getState().loadHandoffs();
    },
    onPreview: () => {
      void handoffStore.getState().previewExport();
    },
    onReadiness: () => {
      void handoffStore.getState().loadReadiness();
    },
    onReject: () => {
      if (!confirmAction("Reject this handoff custody record with the current reason?")) {
        return;
      }
      void handoffStore.getState().rejectSelected();
    },
    onSelectHandoff: (record: HandoffPageState["items"][number]) => {
      handoffStore.getState().selectHandoff(record);
    },
    onSetDraft: <K extends keyof HandoffDraftState>(key: K, value: HandoffDraftState[K]) => {
      handoffStore.getState().setDraft(key, value);
    },
    onTriage: () => {
      void handoffStore.getState().triagePackage();
    },
  };
}
