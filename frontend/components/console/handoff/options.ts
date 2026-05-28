import type { HandoffDraftState } from "@/stores/dashboard-stores";

export const handoffIntentOptions: HandoffDraftState["intent"][] = [
  "review-only",
  "continue-work",
  "verification-needed",
  "failure-triage",
  "release-signoff",
  "future-self",
  "fork-recommended",
];

export const handoffSourceKindOptions: HandoffDraftState["sourceKind"][] = [
  "session",
  "task",
  "changeset",
  "workspace",
  "release",
];
