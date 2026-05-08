import type { ChangesetBadgeVariant } from "./types";
import { formatReviewPostureState } from "./review-posture";

export function verificationBadgeVariant(state: string): ChangesetBadgeVariant {
  if (state === "failed") {
    return "destructive";
  }
  if (state === "passed" || state === "not_applicable") {
    return "success";
  }
  if (state === "stale" || state === "missing") {
    return "warning";
  }
  if (state === "accepted_with_risk" || state === "skipped") {
    return "outline";
  }
  return "muted";
}

export function readinessBadgeVariant(state: string): ChangesetBadgeVariant {
  if (state === "ready") {
    return "success";
  }
  if (state === "failed_checks" || state === "not_ready") {
    return "destructive";
  }
  if (state === "accepted_with_risk") {
    return "outline";
  }
  if (state === "needs_verification" || state === "stale_inventory") {
    return "warning";
  }
  return "muted";
}

export function handoffBadgeVariant(state: string): ChangesetBadgeVariant {
  if (state === "handoff_ready" || state === "commit_prep_ready") {
    return "success";
  }
  if (state === "accepted_with_risk") {
    return "outline";
  }
  if (state === "publication_blocked") {
    return "destructive";
  }
  if (
    state === "needs_review_response" ||
    state === "needs_verification" ||
    state === "stale_inventory" ||
    state === "unresolved_risk"
  ) {
    return "warning";
  }
  return "muted";
}

export function candidateBadgeVariant(state: string | null | undefined): ChangesetBadgeVariant {
  if (state === "selected" || state === "verified" || state === "completed") {
    return "success";
  }
  if (state === "rejected") {
    return "destructive";
  }
  if (state === "needs_review" || state === "planned" || state === "forked") {
    return "warning";
  }
  if (state === null || state === undefined) {
    return "muted";
  }
  return "info";
}

export function formatVerificationState(state: string): string {
  return formatReviewPostureState(state);
}
