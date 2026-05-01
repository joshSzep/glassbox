import type { Candidate, CandidateDecisionSupport } from "./types";

export function selectedCandidateFor(candidates: Candidate[]): Candidate | null {
  return candidates.find((candidate) => candidate.selection_state === "selected") ?? null;
}

export function decisionSupportFor(
  candidate: Candidate,
  supportCandidates: CandidateDecisionSupport[],
): CandidateDecisionSupport | null {
  return (
    supportCandidates.find((support) => support.candidate_id === candidate.candidate_id) ?? null
  );
}

export function verificationRecommendationSummary(
  support: CandidateDecisionSupport | null,
): string {
  const recommendation = support?.verification_recommendations?.[0];
  if (recommendation == null) {
    return "Inspect candidate evidence before choosing verification.";
  }
  if ((recommendation.commands ?? []).length > 0) {
    return (recommendation.commands ?? []).join("; ");
  }
  return recommendation.rationale;
}

export function candidateStatusVariant(status: string) {
  if (status === "selected" || status === "verified") {
    return "success" as const;
  }
  if (status === "rejected") {
    return "destructive" as const;
  }
  if (status === "needs_review" || status === "planned" || status === "forked") {
    return "warning" as const;
  }
  return "info" as const;
}

export function verificationVariant(status: string) {
  if (status === "passed" || status === "strong") {
    return "success" as const;
  }
  if (status === "failed" || status === "timed_out" || status === "risky") {
    return "destructive" as const;
  }
  if (
    status === "blocked" ||
    status === "inconclusive" ||
    status === "not_run" ||
    status === "review"
  ) {
    return "warning" as const;
  }
  return "muted" as const;
}

export function shortId(value: string): string {
  return value.length <= 10 ? value : `${value.slice(0, 8)}...`;
}
