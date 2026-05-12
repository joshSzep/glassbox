import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import type { ChangesetActionStatus, ChangesetDetailState } from "@/stores/dashboard-stores";

import { formatVerificationState, verificationBadgeVariant } from "./format";
import { Section } from "./shared";

type ChangesetDetailRecord = NonNullable<ChangesetDetailState["detail"]>;

export function InventoryPanel({ detail }: { detail: ChangesetDetailRecord }) {
  const inventory = detail.inventory;
  if (inventory == null) {
    return (
      <Section title="Changed Files">
        <p className="text-sm text-muted-foreground">No structured inventory is attached yet.</p>
      </Section>
    );
  }
  return (
    <Section title="Changed Files">
      <DataList density="compact">
        <DataListItem>
          <DataListLabel>{inventory.changed_path_count} changed paths</DataListLabel>
          <DataListMeta>
            Risk {inventory.risk_level} - {inventory.unresolved_risk_count} unresolved -{" "}
            {inventory.accepted_risk_count} accepted
          </DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>{inventory.artifact_id}</DataListLabel>
          <DataListMeta>
            Inventory artifact - freshness {detail.inventory_status.freshness} - sequence{" "}
            {inventory.last_sequence}
          </DataListMeta>
        </DataListItem>
      </DataList>
    </Section>
  );
}

export function TopologyPanel({
  verificationPlan,
}: {
  verificationPlan: ChangesetDetailState["verificationPlan"];
}) {
  const impacts = verificationPlan?.topology_impacts ?? [];
  if (impacts.length === 0) {
    return null;
  }
  return (
    <Section title="Affected Subsystems">
      <DataList density="compact">
        {impacts.slice(0, 6).map((impact) => (
          <DataListItem key={impact.component_id}>
            <DataListLabel>
              {impact.name} - {impact.kind}
            </DataListLabel>
            <DataListMeta>
              {impact.root_path} - topology {impact.topology_freshness} -{" "}
              {impact.recommendation_posture}
            </DataListMeta>
            {impact.test_roots.length > 0 ? (
              <DataListMeta>Tests: {impact.test_roots.join(", ")}</DataListMeta>
            ) : null}
            {impact.ownership_hints.length > 0 ? (
              <DataListMeta>Owners: {impact.ownership_hints.join(", ")}</DataListMeta>
            ) : null}
            {impact.dependency_hints.length > 0 ? (
              <DataListMeta>
                Dependencies: {impact.dependency_hints.slice(0, 4).join("; ")}
              </DataListMeta>
            ) : null}
            {impact.limitations.length > 0 ? (
              <DataListMeta>{impact.limitations.join("; ")}</DataListMeta>
            ) : null}
          </DataListItem>
        ))}
      </DataList>
    </Section>
  );
}

export function VerificationPanel({
  action,
  onRecordVerification,
  posture,
  verificationPlan,
}: {
  action: ChangesetActionStatus;
  onRecordVerification?: (input: {
    taskId?: string | null;
    verificationId?: string | null;
  }) => void;
  posture: ChangesetDetailRecord["verification_posture"];
  verificationPlan: ChangesetDetailState["verificationPlan"];
}) {
  if (verificationPlan === null) {
    return (
      <Section title="Verification">
        <p className="text-sm text-muted-foreground">
          {posture == null
            ? "No verification posture is attached yet."
            : `${posture.state} - ${posture.summary}`}
        </p>
      </Section>
    );
  }
  const readiness = verificationPlan.readiness;
  const reviewLoop = verificationPlan.review_loop_summary;
  const planSummary = verificationPlan.plan_summary;
  const visibleRequirements = readiness.requirements.slice(0, 6);
  const visiblePlanEntries = planSummary.entries.slice(0, 4);
  const groupedPlanEntries = groupPlanEntries(verificationPlan.plan_entries);
  const actionPending = action.state === "pending";
  return (
    <Section title="Verification">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={verificationBadgeVariant(readiness.state)}>
            {formatVerificationState(readiness.state)}
          </Badge>
          {readiness.failed_count > 0 ? (
            <Badge variant="destructive">{readiness.failed_count} failed</Badge>
          ) : null}
          {readiness.stale_count > 0 ? (
            <Badge variant="warning">{readiness.stale_count} stale</Badge>
          ) : null}
          {readiness.missing_count > 0 ? (
            <Badge variant="warning">{readiness.missing_count} missing</Badge>
          ) : null}
          {readiness.accepted_risk_count > 0 ? (
            <Badge variant="outline">{readiness.accepted_risk_count} accepted risk</Badge>
          ) : null}
          <Badge variant={reviewLoop.feedback_count > 0 ? "info" : "muted"}>
            {reviewLoop.feedback_count} feedback
          </Badge>
          <Badge variant={reviewLoop.manual_evidence_count > 0 ? "outline" : "muted"}>
            {reviewLoop.manual_evidence_count} manual evidence
          </Badge>
          <Badge variant={reviewLoop.stale_response_count > 0 ? "warning" : "muted"}>
            {reviewLoop.stale_response_count} stale responses
          </Badge>
          <Badge variant={reviewLoop.skipped_live_evidence_count > 0 ? "warning" : "muted"}>
            {reviewLoop.skipped_live_evidence_count} skipped live
          </Badge>
          <Badge variant={planSummary.selected_count > 0 ? "info" : "muted"}>
            {planSummary.selected_count} selected
          </Badge>
          <Badge variant={planSummary.skipped_count > 0 ? "warning" : "muted"}>
            {planSummary.skipped_count} skipped checks
          </Badge>
          <Badge variant={planSummary.passed_count > 0 ? "success" : "muted"}>
            {planSummary.passed_count} plan passed
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{readiness.summary}</p>
        <VerificationPlanEntryGroups
          actionPending={actionPending}
          groups={groupedPlanEntries}
          onRecordVerification={onRecordVerification}
        />
        {verificationPlan.skipped_checks.length > 0 ? (
          <VerificationSkippedChecks checks={verificationPlan.skipped_checks} />
        ) : null}
        {visiblePlanEntries.length > 0 ? (
          <DataList density="compact">
            {visiblePlanEntries.map((entry) => (
              <DataListItem key={entry.verification_id}>
                <DataListLabel>{entry.check_name}</DataListLabel>
                <DataListMeta>
                  {formatVerificationState(entry.status)} - {entry.lifecycle_state}
                  {entry.reason ? ` - ${entry.reason}` : ""}
                </DataListMeta>
                {entry.command.length > 0 ? (
                  <DataListMeta>{entry.command.join(" ")}</DataListMeta>
                ) : null}
              </DataListItem>
            ))}
          </DataList>
        ) : null}
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
              {reviewLoop.skipped_live_evidence_count} skipped live -{" "}
              {reviewLoop.topology_impact_count} topology impacts
            </DataListMeta>
          </DataListItem>
        </DataList>
        {visibleRequirements.length > 0 ? (
          <DataList density="compact">
            {visibleRequirements.map((requirement) => (
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
        ) : null}
        {verificationPlan.safe_next_actions.length > 0 ? (
          <div>
            <h4 className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Safe next actions
            </h4>
            <ul className="mt-2 grid gap-2 text-console text-muted-foreground">
              {verificationPlan.safe_next_actions.map((action) => (
                <li className="break-all" key={action}>
                  {action}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {verificationPlan.retained_artifact_ids.length > 0 ? (
          <p className="break-all text-console text-muted-foreground">
            Artifacts: {verificationPlan.retained_artifact_ids.join(", ")}
          </p>
        ) : null}
      </div>
    </Section>
  );
}

type VerificationPlan = NonNullable<ChangesetDetailState["verificationPlan"]>;
type VerificationPlanEntry = VerificationPlan["plan_entries"][number];
type VerificationSkippedCheck = VerificationPlan["skipped_checks"][number];

type VerificationPlanEntryGroup = {
  entries: VerificationPlanEntry[];
  label: string;
};

function groupPlanEntries(entries: VerificationPlanEntry[]): VerificationPlanEntryGroup[] {
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

function VerificationPlanEntryGroups({
  actionPending,
  groups,
  onRecordVerification,
}: {
  actionPending: boolean;
  groups: VerificationPlanEntryGroup[];
  onRecordVerification?: (input: { verificationId?: string | null }) => void;
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
  onRecordVerification?: (input: { verificationId?: string | null }) => void;
}) {
  const artifactRef = entry.evidence_references.find((ref) => ref.kind === "artifact");
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
      <div className="mt-2 flex flex-wrap gap-2">
        <Button
          disabled={actionPending || onRecordVerification === undefined}
          onClick={() => onRecordVerification?.({ verificationId: entry.verification_id })}
          size="sm"
          type="button"
          variant="secondary"
        >
          Select
        </Button>
        <Button
          disabled
          size="sm"
          title="Command execution must use a backend endpoint."
          type="button"
          variant="outline"
        >
          Run
        </Button>
        <Button
          disabled
          size="sm"
          title="Retry requires retained failed command output."
          type="button"
          variant="outline"
        >
          Retry
        </Button>
        <Button
          disabled
          size="sm"
          title="Accepted risk requires an explicit backend risk endpoint."
          type="button"
          variant="outline"
        >
          Accept risk
        </Button>
        {artifactRef === undefined ? (
          <Button disabled size="sm" type="button" variant="ghost">
            Inspect artifact
          </Button>
        ) : (
          <Button asChild size="sm" variant="ghost">
            <a href={`#artifact-${artifactRef.ref_id}`}>Inspect artifact</a>
          </Button>
        )}
        <Button asChild size="sm" variant="ghost">
          <a href={`#evidence-claim-${entry.verification_id}`}>Evidence graph</a>
        </Button>
      </div>
    </DataListItem>
  );
}

function VerificationSkippedChecks({ checks }: { checks: VerificationSkippedCheck[] }) {
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

function verificationEntryId(verificationId: string) {
  return `verification-plan-entry-${verificationId}`;
}

export function CommandEvidencePanel({ detail }: { detail: ChangesetDetailRecord }) {
  const evidence = detail.command_evidence;
  return (
    <Section title="Command Evidence">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={evidence.verification_count > 0 ? "success" : "muted"}>
            {evidence.verification_count} verification
          </Badge>
          <Badge variant={evidence.failed_count > 0 ? "warning" : "muted"}>
            {evidence.failed_count} failed
          </Badge>
          <Badge variant={evidence.risky_count > 0 ? "warning" : "muted"}>
            {evidence.risky_count} risky
          </Badge>
          <Badge variant="outline">{evidence.environment_captured_count} environment</Badge>
        </div>
        {evidence.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No retained command attempts are linked to this changeset.
          </p>
        ) : (
          <DataList density="compact">
            {evidence.items.slice(0, 6).map((item) => (
              <DataListItem key={item.tool_attempt_id}>
                <DataListLabel>
                  {item.purpose} - {item.status}
                </DataListLabel>
                <DataListMeta>{item.summary}</DataListMeta>
                <DataListMeta>
                  {item.tool_name} attempt {item.tool_attempt_id} - {item.review_relevance}
                  {item.output_artifact_id ? ` - artifact ${item.output_artifact_id}` : ""}
                </DataListMeta>
                {item.environment_captured ? (
                  <DataListMeta>
                    Environment captured with {item.toolchain_count} toolchain
                    {item.toolchain_count === 1 ? "" : "s"}
                  </DataListMeta>
                ) : null}
                {item.policy_summary ? <DataListMeta>{item.policy_summary}</DataListMeta> : null}
              </DataListItem>
            ))}
          </DataList>
        )}
        {evidence.safe_next_actions.length > 0 ? (
          <ul className="grid gap-2 text-console text-muted-foreground">
            {evidence.safe_next_actions.map((action) => (
              <li className="break-all" key={action}>
                {action}
              </li>
            ))}
          </ul>
        ) : null}
        {evidence.limitations.length > 0 ? (
          <p className="text-xs text-muted-foreground">{evidence.limitations.join("; ")}</p>
        ) : null}
      </div>
    </Section>
  );
}
