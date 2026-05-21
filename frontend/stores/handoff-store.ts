import { createStore, type StoreApi } from "zustand/vanilla";

import type {
  GlassboxApiClient,
  HandoffDecisionResponse,
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

const HANDOFF_PAGE_SIZE = 100;

export function createHandoffStore(apiClient: GlassboxApiClient): StoreApi<HandoffStoreState> {
  const listRequests = createRequestTracker();

  return createStore<HandoffStoreState>((set, get) => ({
    acceptSelected: async () => {
      const record = requireSelectedRecord(get().detail);
      await runHandoffAction({
        action: async () => {
          const response = await apiClient.acceptHandoff({
            body: {
              accepted_by: get().drafts.decisionActor || "operator",
              follow_up_intent: get().drafts.followUpIntent,
              reason: optionalText(get().drafts.decisionReason),
            },
            packageId: record.record.package_id,
            sessionId: record.record.session_id,
          });
          setDecisionResponse(set, response);
        },
        kind: "accept",
        set,
      });
    },
    action: createIdleActionStatus(),
    archiveSelected: async () => {
      const record = requireSelectedRecord(get().detail);
      await runHandoffAction({
        action: async () => {
          const response = await apiClient.archiveHandoff({
            body: {
              archived_by: get().drafts.decisionActor || "operator",
              reason: get().drafts.decisionReason || "dashboard archive",
            },
            packageId: record.record.package_id,
            sessionId: record.record.session_id,
          });
          setDecisionResponse(set, response);
        },
        kind: "archive",
        set,
      });
    },
    detail: createIdleHandoffDetailState(),
    drafts: createDefaultHandoffDrafts(),
    exportPackage: async () => {
      await runHandoffAction({
        action: async () => {
          const drafts = get().drafts;
          const response = await apiClient.exportHandoff({
            expected_custodian: optionalText(drafts.expectedCustodian),
            exported_by: optionalText(drafts.exportedBy),
            intent: drafts.intent,
            markdown_output_path: optionalText(drafts.markdownOutputPath),
            note: optionalText(drafts.note),
            output_format: drafts.outputFormat,
            output_path: optionalText(drafts.outputPath),
            recipient: optionalText(drafts.recipient),
            source_id: sourceIdForRequest(drafts),
            source_kind: drafts.sourceKind,
          });
          set((state) => ({
            detail: { ...state.detail, exported: response },
            drafts: {
              ...state.drafts,
              outputPath: response.output_path,
              packagePath: response.output_path,
            },
          }));
        },
        kind: "export",
        set,
      });
    },
    importPackage: async () => {
      await runHandoffAction({
        action: async () => {
          const response = await apiClient.importHandoff({ package_path: requirePackagePath(get) });
          set((state) => ({ detail: { ...state.detail, importResult: response } }));
          await get().loadHandoffs();
        },
        kind: "import",
        set,
      });
    },
    inspectPackage: async () => {
      await runHandoffAction({
        action: async () => {
          const response = await apiClient.inspectHandoffPackage({
            package_path: requirePackagePath(get),
          });
          set((state) => ({
            detail: {
              ...state.detail,
              inspect: response,
              triage:
                response.triage === null || response.triage === undefined
                  ? state.detail.triage
                  : { triage: response.triage },
            },
          }));
        },
        kind: "inspect",
        set,
      });
    },
    list: createIdleHandoffPageState(),
    loadGuidance: async () => {
      const record = requireSelectedRecord(get().detail);
      await runHandoffAction({
        action: async () => {
          const response = await apiClient.getHandoffGuidance(
            record.record.session_id,
            record.record.package_id,
          );
          set((state) => ({ detail: { ...state.detail, guidance: response } }));
        },
        kind: "guidance",
        set,
      });
    },
    loadHandoffs: async (query = {}) => {
      const currentRequestId = listRequests.next();
      set((state) => ({
        list: { ...state.list, error: null, loadState: "loading" },
      }));
      try {
        const page = await apiClient.listHandoffs({
          include_archived: query.includeArchived ?? false,
          limit: HANDOFF_PAGE_SIZE,
          session_id: query.sessionId ?? undefined,
        });
        if (!listRequests.isCurrent(currentRequestId)) {
          return;
        }
        set({
          list: {
            error: null,
            items: page.items ?? [],
            loadState: "loaded",
          },
        });
      } catch (error) {
        if (!listRequests.isCurrent(currentRequestId)) {
          return;
        }
        set((state) => ({
          list: { ...state.list, error: errorMessage(error), loadState: "failed" },
        }));
      }
    },
    loadReadiness: async () => {
      await runHandoffAction({
        action: async () => {
          const drafts = get().drafts;
          const response = await apiClient.getHandoffReadiness({
            intent: drafts.intent,
            source_id: needsSourceId(drafts.sourceKind) ? sourceIdForRequest(drafts) : undefined,
            source_kind: drafts.sourceKind,
          });
          set((state) => ({ detail: { ...state.detail, readiness: response } }));
        },
        kind: "readiness",
        set,
      });
    },
    previewExport: async () => {
      await runHandoffAction({
        action: async () => {
          const drafts = get().drafts;
          const response = await apiClient.previewHandoff({
            expected_custodian: optionalText(drafts.expectedCustodian),
            exported_by: optionalText(drafts.exportedBy),
            intent: drafts.intent,
            note: optionalText(drafts.note),
            output_format: drafts.outputFormat,
            recipient: optionalText(drafts.recipient),
            source_id: sourceIdForRequest(drafts),
            source_kind: drafts.sourceKind,
          });
          set((state) => ({ detail: { ...state.detail, preview: response } }));
        },
        kind: "preview",
        set,
      });
    },
    rejectSelected: async () => {
      const record = requireSelectedRecord(get().detail);
      await runHandoffAction({
        action: async () => {
          const response = await apiClient.rejectHandoff({
            body: {
              reason: get().drafts.decisionReason || "dashboard rejection",
              rejected_by: get().drafts.decisionActor || "operator",
            },
            packageId: record.record.package_id,
            sessionId: record.record.session_id,
          });
          setDecisionResponse(set, response);
        },
        kind: "reject",
        set,
      });
    },
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
    triagePackage: async () => {
      await runHandoffAction({
        action: async () => {
          const response = await apiClient.triageHandoffImport({
            package_path: requirePackagePath(get),
          });
          set((state) => ({ detail: { ...state.detail, triage: response } }));
        },
        kind: "triage",
        set,
      });
    },
  }));
}

function createDefaultHandoffDrafts(): HandoffDraftState {
  return {
    decisionActor: "operator",
    decisionReason: "",
    expectedCustodian: "",
    exportedBy: "operator",
    followUpIntent: "verification-needed",
    intent: "review-only",
    markdownOutputPath: "",
    note: "",
    outputFormat: "json",
    outputPath: "",
    packagePath: "",
    recipient: "",
    sourceId: "",
    sourceKind: "session",
  };
}

function createIdleHandoffPageState(): HandoffPageState {
  return { error: null, items: [], loadState: "idle" };
}

function createIdleHandoffDetailState(): HandoffDetailState {
  return {
    exported: null,
    guidance: null,
    importResult: null,
    inspect: null,
    preview: null,
    readiness: null,
    selected: null,
    triage: null,
  };
}

async function runHandoffAction({
  action,
  kind,
  set,
}: {
  action: () => Promise<void>;
  kind: HandoffActionKind;
  set: StoreApi<HandoffStoreState>["setState"];
}) {
  set({ action: createPendingActionStatus(kind) });
  try {
    await action();
    set({ action: createSucceededActionStatus(kind) });
  } catch (error) {
    set({ action: createFailedActionStatus(kind, error) });
  }
}

function setDecisionResponse(
  set: StoreApi<HandoffStoreState>["setState"],
  response: HandoffDecisionResponse,
) {
  set((state) => ({
    detail: { ...state.detail, selected: response.handoff },
    list: {
      ...state.list,
      items: state.list.items.map((item) =>
        sameRecord(item, response.handoff) ? response.handoff : item,
      ),
    },
  }));
}

function sameRecord(left: HandoffRecordResponse, right: HandoffRecordResponse): boolean {
  return (
    left.record.session_id === right.record.session_id &&
    left.record.package_id === right.record.package_id
  );
}

function optionalText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length === 0 ? null : trimmed;
}

function needsSourceId(sourceKind: HandoffDraftState["sourceKind"]): boolean {
  return sourceKind !== "workspace" && sourceKind !== "release";
}

function sourceIdForRequest(drafts: HandoffDraftState): string {
  if (!needsSourceId(drafts.sourceKind)) {
    return drafts.sourceKind;
  }
  const sourceId = drafts.sourceId.trim();
  if (sourceId.length === 0) {
    throw new Error("Choose a session, task, or changeset id before requesting handoff details.");
  }
  return sourceId;
}

function requirePackagePath(get: () => HandoffStoreState): string {
  const packagePath = get().drafts.packagePath.trim();
  if (packagePath.length === 0) {
    throw new Error("Enter a local handoff package path before package inspection.");
  }
  return packagePath;
}

function requireSelectedRecord(detail: HandoffDetailState): HandoffRecordResponse {
  if (detail.selected === null) {
    throw new Error("Select a handoff record before recording a custody decision.");
  }
  return detail.selected;
}

function sourceKindDraft(
  sourceKind: string,
  fallback: HandoffDraftState["sourceKind"],
): HandoffDraftState["sourceKind"] {
  return sourceKind === "changeset" ||
    sourceKind === "release" ||
    sourceKind === "session" ||
    sourceKind === "task" ||
    sourceKind === "workspace"
    ? sourceKind
    : fallback;
}
