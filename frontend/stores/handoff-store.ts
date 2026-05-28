import { createStore, type StoreApi } from "zustand/vanilla";

import type {
  GlassboxApiClient,
  HandoffExportResponse,
  HandoffGuidanceResponse,
  HandoffImportResponse,
  HandoffImportTriageResponse,
  HandoffIntent,
  HandoffListResponse,
  HandoffPackageInspectResponse,
  HandoffPreparePreviewResponse,
  HandoffReadinessUnifiedResponse,
  HandoffRecordResponse,
} from "@/api/client";
import { createHandoffDecisionActions } from "@/stores/handoff-store-decision-actions";
import { createDefaultHandoffDrafts, sourceKindDraft } from "@/stores/handoff-store-drafts";
import { createHandoffLoaders } from "@/stores/handoff-store-loaders";
import { createHandoffPackageActions } from "@/stores/handoff-store-package-actions";
import {
  createIdleHandoffDetailState,
  createIdleHandoffPageState,
} from "@/stores/handoff-store-selectors";
import {
  createIdleActionStatus,
  createRequestTracker,
  type LoadState,
  type StoreActionStatus,
} from "@/stores/store-actions";

export type HandoffActionKind =
  | "accept"
  | "archive"
  | "export"
  | "guidance"
  | "import"
  | "inspect"
  | "preview"
  | "readiness"
  | "reject"
  | "triage";

export type HandoffActionStatus = StoreActionStatus<HandoffActionKind>;

export type HandoffDraftState = {
  decisionActor: string;
  decisionReason: string;
  expectedCustodian: string;
  exportedBy: string;
  followUpIntent: HandoffIntent;
  intent: HandoffIntent;
  markdownOutputPath: string;
  note: string;
  outputFormat: string;
  outputPath: string;
  packagePath: string;
  recipient: string;
  sourceId: string;
  sourceKind: "changeset" | "release" | "session" | "task" | "workspace";
};

export type HandoffPageState = {
  error: string | null;
  items: NonNullable<HandoffListResponse["items"]>;
  loadState: LoadState;
};

export type HandoffDetailState = {
  exported: HandoffExportResponse | null;
  guidance: HandoffGuidanceResponse | null;
  importResult: HandoffImportResponse | null;
  inspect: HandoffPackageInspectResponse | null;
  preview: HandoffPreparePreviewResponse | null;
  readiness: HandoffReadinessUnifiedResponse | null;
  selected: HandoffRecordResponse | null;
  triage: HandoffImportTriageResponse | null;
};

export type HandoffStoreState = {
  action: HandoffActionStatus;
  acceptSelected: () => Promise<void>;
  archiveSelected: () => Promise<void>;
  detail: HandoffDetailState;
  drafts: HandoffDraftState;
  exportPackage: () => Promise<void>;
  importPackage: () => Promise<void>;
  inspectPackage: () => Promise<void>;
  list: HandoffPageState;
  loadGuidance: () => Promise<void>;
  loadHandoffs: (query?: { includeArchived?: boolean; sessionId?: string | null }) => Promise<void>;
  loadReadiness: () => Promise<void>;
  previewExport: () => Promise<void>;
  rejectSelected: () => Promise<void>;
  reset: () => void;
  selectHandoff: (record: HandoffRecordResponse | null) => void;
  setDraft: <K extends keyof HandoffDraftState>(key: K, value: HandoffDraftState[K]) => void;
  triagePackage: () => Promise<void>;
};

export function createHandoffStore(apiClient: GlassboxApiClient): StoreApi<HandoffStoreState> {
  const listRequests = createRequestTracker();

  return createStore<HandoffStoreState>((set, get) => ({
    action: createIdleActionStatus(),
    detail: createIdleHandoffDetailState(),
    drafts: createDefaultHandoffDrafts(),
    list: createIdleHandoffPageState(),
    reset: () => {
      listRequests.invalidate();
      set({
        action: createIdleActionStatus(),
        detail: createIdleHandoffDetailState(),
        drafts: createDefaultHandoffDrafts(),
        list: createIdleHandoffPageState(),
      });
    },
    selectHandoff: (record) => {
      set((state) => ({
        detail: {
          ...state.detail,
          guidance: null,
          selected: record,
        },
        drafts:
          record === null
            ? state.drafts
            : {
                ...state.drafts,
                expectedCustodian:
                  record.record.expected_custodian ?? state.drafts.expectedCustodian,
                followUpIntent: record.record.follow_up_intent ?? state.drafts.followUpIntent,
                intent: record.record.intent ?? state.drafts.intent,
                sourceId: record.record.source_id ?? state.drafts.sourceId,
                sourceKind: sourceKindDraft(record.record.source_kind, state.drafts.sourceKind),
              },
      }));
    },
    setDraft: (key, value) => {
      set((state) => ({ drafts: { ...state.drafts, [key]: value } }));
    },
    ...createHandoffDecisionActions({ apiClient, get, set }),
    ...createHandoffLoaders({ apiClient, get, listRequests, set }),
    ...createHandoffPackageActions({ apiClient, get, set }),
  }));
}
