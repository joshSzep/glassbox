import type { StoreApi } from "zustand/vanilla";

import type { GlassboxApiClient } from "@/api/client";
import type { HandoffActionKind, HandoffStoreState } from "@/stores/handoff-store";
import {
  optionalText,
  requirePackagePath,
  sourceIdForRequest,
} from "@/stores/handoff-store-drafts";
import {
  createFailedActionStatus,
  createPendingActionStatus,
  createSucceededActionStatus,
} from "@/stores/store-actions";

export function createHandoffPackageActions({
  apiClient,
  get,
  set,
}: {
  apiClient: GlassboxApiClient;
  get: StoreApi<HandoffStoreState>["getState"];
  set: StoreApi<HandoffStoreState>["setState"];
}) {
  return {
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
  } satisfies Pick<
    HandoffStoreState,
    "exportPackage" | "importPackage" | "inspectPackage" | "previewExport" | "triagePackage"
  >;
}

export async function runHandoffAction({
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
