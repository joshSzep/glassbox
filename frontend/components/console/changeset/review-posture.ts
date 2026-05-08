import type { ChangesetDetailState } from "@/stores/dashboard-stores";

import type { ChangesetBadgeVariant } from "./types";

type ChangesetDetailRecord = NonNullable<ChangesetDetailState["detail"]>;
export type ManualEvidenceItem = ChangesetDetailRecord["manual_evidence"][number];

export type SkippedEvidencePosture = {
  reason: string | null;
  state: "not_run" | "not_applicable";
  stateLabel: string;
};

export type ResponseBadgeVariant = ChangesetBadgeVariant | "default";

export function formatReviewPostureState(state: string): string {
  return state.replaceAll("_", " ");
}

export function skippedEvidencePosture(item: ManualEvidenceItem): SkippedEvidencePosture | null {
  const captureState = limitationValue(item.limitations, "capture state");
  if (captureState !== "not_run" && captureState !== "not_applicable") {
    return null;
  }
  return {
    reason: limitationValue(item.limitations, "skip reason"),
    state: captureState,
    stateLabel: formatReviewPostureState(captureState),
  };
}

export function isSkippedEvidence(item: ManualEvidenceItem): boolean {
  return skippedEvidencePosture(item) !== null;
}

export function responseBadgeVariant(state: string): ResponseBadgeVariant {
  if (state === "ready_for_handoff" || state === "resolved") {
    return "success";
  }
  if (state === "blocked" || state === "reopened") {
    return "warning";
  }
  if (state === "accepted_with_risk") {
    return "outline";
  }
  return "default";
}

export function handoffPostureLabel(state: string): string {
  return formatReviewPostureState(state);
}

function limitationValue(limitations: string[], label: string): string | null {
  const prefix = `${label}: `;
  return (
    limitations
      .find((limitation) => limitation.toLowerCase().startsWith(prefix))
      ?.split(": ", 2)[1] ?? null
  );
}
