import type { StoreApi } from "zustand/vanilla";

import type { GlassboxApiClient } from "@/api/client";
import type { HandoffStoreState } from "@/stores/handoff-store";
import { optionalText } from "@/stores/handoff-store-drafts";
import { runHandoffAction } from "@/stores/handoff-store-package-actions";
import { requireSelectedRecord, setDecisionResponse } from "@/stores/handoff-store-selectors";

export function createHandoffDecisionActions({
  apiClient,
  get,
  set,
}: {
  apiClient: GlassboxApiClient;
  get: StoreApi<HandoffStoreState>["getState"];
  set: StoreApi<HandoffStoreState>["setState"];
}) {
  return {
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
  } satisfies Pick<HandoffStoreState, "acceptSelected" | "archiveSelected" | "rejectSelected">;
}
