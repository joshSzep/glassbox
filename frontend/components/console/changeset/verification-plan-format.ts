import type { ChangesetDetailState } from "@/stores/dashboard-stores";

export type VerificationPlan = NonNullable<ChangesetDetailState["verificationPlan"]>;
export type VerificationPlanEntry = VerificationPlan["plan_entries"][number];
export type VerificationRequirement = VerificationPlan["readiness"]["requirements"][number];
export type VerificationReviewLoopSummary = VerificationPlan["review_loop_summary"];
export type VerificationSkippedCheck = VerificationPlan["skipped_checks"][number];
export type VerificationSummaryEntry = VerificationPlan["plan_summary"]["entries"][number];

export type VerificationPlanEntryGroup = {
  entries: VerificationPlanEntry[];
  label: string;
};

export function groupPlanEntries(entries: VerificationPlanEntry[]): VerificationPlanEntryGroup[] {
  return [
    {
      entries: entries.filter(
        (entry) => entry.command.length > 0 && !entry.manual_evidence_required,
      ),
      label: "Deterministic checks",
    },
    {
      entries: entries.filter(
        (entry) => entry.command.length === 0 && !entry.manual_evidence_required && !entry.blocking,
      ),
      label: "Advisory checks",
    },
    {
      entries: entries.filter((entry) => entry.manual_evidence_required),
      label: "Manual checks",
    },
  ];
}

export function verificationEntryId(verificationId: string) {
  return `verification-plan-entry-${verificationId}`;
}
