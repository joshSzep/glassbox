import type {
  ChangesetRecordVerificationResponse,
  ChangesetReviewBriefGenerateResponse,
  ManualEvidenceActionResponse,
} from "@/api/client";

export function manualEvidenceActionMessage(response: ManualEvidenceActionResponse): string {
  return `Manual evidence ${response.evidence.evidence_id} attached.`;
}

export function reviewBriefActionMessage(response: ChangesetReviewBriefGenerateResponse): string {
  const summary = response.limitation_summary;
  if (summary?.summarized === true && typeof summary.overflow_count === "number") {
    return (
      `Lifecycle brief ${response.artifact_id} generated with ` +
      `${summary.overflow_count} summarized limitation${summary.overflow_count === 1 ? "" : "s"}.`
    );
  }
  return `Lifecycle brief ${response.artifact_id} generated.`;
}

export function feedbackStatusActionMessage(): string {
  return "Feedback status refreshed.";
}

export function handoffActionMessage(state: string): string {
  return `Handoff posture ${state} refreshed.`;
}

export function verificationPreviewActionMessage(commandCount: number): string {
  return (
    `${commandCount} verification command${commandCount === 1 ? "" : "s"} ` +
    "previewed; none were run."
  );
}

export function recordVerificationActionMessage(
  response: ChangesetRecordVerificationResponse,
): string {
  const count = response.selected_verification_ids.length;
  return `${count} retained verification entr${count === 1 ? "y" : "ies"} recorded.`;
}

export function inspectFirstActionMessage(nextAction: string): string {
  return `Inspect first: ${nextAction}`;
}

export function fixupInventoryActionMessage(input: {
  artifactId: string;
  feedbackId: string;
}): string {
  return (
    `Fixup inventory ${input.artifactId} recorded for feedback ${input.feedbackId}; ` +
    "reviewer approval is not implied."
  );
}

export function fixupInventoryFailedActionMessage(): string {
  return "Fixup inventory was not recorded.";
}

export function refreshChangesetActionMessage(eventSequence: number): string {
  return `Inventory refreshed at sequence ${eventSequence}.`;
}
