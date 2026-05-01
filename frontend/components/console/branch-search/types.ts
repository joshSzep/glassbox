import type { BranchSearchDetailState } from "@/stores/dashboard-stores";

export type Candidate = NonNullable<BranchSearchDetailState["detail"]>["candidates"][number];
export type CandidateDecisionSupport = NonNullable<
  BranchSearchDetailState["detail"]
>["decision_support"]["candidates"][number];

export type MarkCandidateInput = {
  action: "needs-review" | "reject" | "select";
  candidateId: string;
  searchId: string;
};
