import type { StoreApi } from "zustand/vanilla";

import type { HandoffDecisionResponse, HandoffRecordResponse } from "@/api/client";
import type {
  HandoffDetailState,
  HandoffPageState,
  HandoffStoreState,
} from "@/stores/handoff-store";

export function createIdleHandoffPageState(): HandoffPageState {
  return { error: null, items: [], loadState: "idle" };
}

export function createIdleHandoffDetailState(): HandoffDetailState {
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

export function requireSelectedRecord(detail: HandoffDetailState): HandoffRecordResponse {
  if (detail.selected === null) {
    throw new Error("Select a handoff record before recording a custody decision.");
  }
  return detail.selected;
}

export function setDecisionResponse(
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
