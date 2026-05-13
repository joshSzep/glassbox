import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";

import { formatVerificationState } from "./format";
import {
  VerificationPlanEntryActions,
  type RecordVerificationInput,
} from "./verification-plan-actions";
import {
  verificationEntryId,
  type VerificationPlanEntry,
  type VerificationPlanEntryGroup,
  type VerificationRequirement,
  type VerificationReviewLoopSummary,
  type VerificationSkippedCheck,
  type VerificationSummaryEntry,
} from "./verification-plan-format";

export function VerificationPlanEntryGroups({
  actionPending,
  groups,
  onRecordVerification,
}: {
  actionPending: boolean;
  groups: VerificationPlanEntryGroup[];
  onRecordVerification?: (input: RecordVerificationInput) => void;
}) {
  return (
    <div className="grid gap-3">
      {groups.map((group) => (
        <section className="rounded-md border border-border/70 bg-surface p-3" key={group.label}>
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              {group.label}
            </h4>
            <Badge variant={group.entries.length > 0 ? "info" : "muted"}>
              {group.entries.length}
            </Badge>
          </div>
          {group.entries.length === 0 ? (
            <p className="text-xs text-muted-foreground">No {group.label.toLowerCase()}.</p>
          ) : (
            <DataList density="compact">
              {group.entries.map((entry) => (
                <VerificationPlanEntryRow
                  actionPending={actionPending}
                  entry={entry}
                  key={entry.verification_id}
                  onRecordVerification={onRecordVerification}
                />
              ))}
            </DataList>
          )}
        </section>
      ))}
    </div>
  );
}

function VerificationPlanEntryRow({
  actionPending,
  entry,
  onRecordVerification,
}: {
  actionPending: boolean;
  entry: VerificationPlanEntry;
  onRecordVerification?: (input: RecordVerificationInput) => void;
}) {
  return (
    <DataListItem id={verificationEntryId(entry.verification_id)}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <DataListLabel>{entry.check_name}</DataListLabel>
          <DataListMeta>
            {entry.kind} - {entry.lifecycle_state} - {entry.source}
          </DataListMeta>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={entry.blocking ? "warning" : "muted"}>
            {entry.blocking ? "blocking" : "advisory"}
          </Badge>
          <Badge variant={entry.manual_evidence_required ? "info" : "outline"}>
            {entry.manual_evidence_required ? "manual" : "command"}
          </Badge>
        </div>
      </div>
      <DataListMeta>{entry.rationale}</DataListMeta>
      {entry.selection_rationale ? <DataListMeta>{entry.selection_rationale}</DataListMeta> : null}
      {entry.command.length > 0 ? (
        <DataListMeta className="break-all">{entry.command.join(" ")}</DataListMeta>
      ) : null}
      {entry.stale_reasons.length > 0 ? (
        <DataListMeta>Stale: {entry.stale_reasons.join("; ")}</DataListMeta>
      ) : null}
      {entry.evidence_references.slice(0, 2).map((ref) => (
        <DataListMeta key={`${entry.verification_id}:${ref.ref_id}`}>
          Evidence {ref.kind}: {ref.summary} ({ref.freshness ?? "unknown"})
        </DataListMeta>
      ))}
      <VerificationPlanEntryActions
        actionPending={actionPending}
        entry={entry}
        onRecordVerification={onRecordVerification}
      />
    </DataListItem>
  );
}

export function VerificationSkippedChecks({ checks }: { checks: VerificationSkippedCheck[] }) {
  return (
    <section className="rounded-md border border-border/70 bg-surface p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
          Skipped checks
        </h4>
        <Badge variant="warning">{checks.length}</Badge>
      </div>
      <DataList density="compact">
        {checks.map((check) => (
          <DataListItem key={`${check.target_kind}:${check.target_id}:${check.reason}`}>
            <DataListLabel>{check.target_id}</DataListLabel>
            <DataListMeta>
              {check.target_kind} - {check.reason}
            </DataListMeta>
            <DataListMeta>{check.explanation}</DataListMeta>
            {check.matched_paths.length > 0 ? (
              <DataListMeta>{check.matched_paths.join(", ")}</DataListMeta>
            ) : null}
          </DataListItem>
        ))}
      </DataList>
    </section>
  );
}

export function VerificationPlanSummaryEntries({
  entries,
}: {
  entries: VerificationSummaryEntry[];
}) {
  if (entries.length === 0) {
    return null;
  }
  return (
    <DataList density="compact">
      {entries.map((entry) => (
        <DataListItem key={entry.verification_id}>
          <DataListLabel>{entry.check_name}</DataListLabel>
          <DataListMeta>
            {formatVerificationState(entry.status)} - {entry.lifecycle_state}
            {entry.reason ? ` - ${entry.reason}` : ""}
          </DataListMeta>
          {entry.command.length > 0 ? <DataListMeta>{entry.command.join(" ")}</DataListMeta> : null}
        </DataListItem>
      ))}
    </DataList>
  );
}

export function VerificationReviewLoopContext({
  reviewLoop,
}: {
  reviewLoop: VerificationReviewLoopSummary;
}) {
  return (
    <DataList density="compact">
      <DataListItem>
        <DataListLabel>Review-loop context</DataListLabel>
        <DataListMeta>
          {reviewLoop.open_feedback_count} open feedback -{" "}
          {reviewLoop.missing_response_verification_count} missing response checks -{" "}
          {reviewLoop.accepted_risk_response_count} accepted with risk
        </DataListMeta>
        <DataListMeta>
          {reviewLoop.browser_evidence_count} browser/dashboard -{" "}
          {reviewLoop.accessibility_evidence_count} accessibility -{" "}
          {reviewLoop.skipped_live_evidence_count} skipped live - {reviewLoop.topology_impact_count}{" "}
          topology impacts
        </DataListMeta>
      </DataListItem>
    </DataList>
  );
}

export function VerificationRequirementsList({
  requirements,
}: {
  requirements: VerificationRequirement[];
}) {
  if (requirements.length === 0) {
    return null;
  }
  return (
    <DataList density="compact">
      {requirements.map((requirement) => (
        <DataListItem key={requirement.requirement_id}>
          <DataListLabel>{requirement.check_name}</DataListLabel>
          <DataListMeta>
            {formatVerificationState(requirement.state)} - {requirement.reason}
          </DataListMeta>
          {requirement.evidence_summary ? (
            <DataListMeta>{requirement.evidence_summary}</DataListMeta>
          ) : null}
        </DataListItem>
      ))}
    </DataList>
  );
}
