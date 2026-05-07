import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import type { ChangesetDetailState } from "@/stores/dashboard-stores";

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
  posture,
  verificationPlan,
}: {
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
  const visibleRequirements = readiness.requirements.slice(0, 6);
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
        </div>
        <p className="text-sm text-muted-foreground">{readiness.summary}</p>
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
