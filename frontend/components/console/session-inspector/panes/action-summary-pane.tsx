import { ListChecks } from "lucide-react";

import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { Pane } from "@/components/console/session-inspector/frame";
import {
  policyDecisionLabel,
  policySourceLabel,
} from "@/components/console/session-inspector/policy-evidence";
import type { DashboardState } from "@/state/session-state";

export function ActionSummaryPane({ data }: { data: DashboardState }) {
  return (
    <Pane icon={ListChecks} title="Actions">
      <DataList density="compact">
        {data.pendingApprovals.map((approval) => (
          <DataListItem key={approval.approval_id}>
            <DataListLabel>{approval.subject}</DataListLabel>
            <DataListMeta>{formatApprovalEvidence(approval)}</DataListMeta>
          </DataListItem>
        ))}
        {data.pendingQuestionId !== null ? (
          <DataListItem>
            <DataListLabel>Question {data.pendingQuestionId}</DataListLabel>
            <DataListMeta>{data.pendingQuestionText ?? "Awaiting operator answer"}</DataListMeta>
          </DataListItem>
        ) : null}
        {data.activeToolCalls.map((tool) => (
          <DataListItem key={tool.tool_call_id}>
            <DataListLabel>{tool.tool_name}</DataListLabel>
            <DataListMeta>{formatToolEvidence(tool)}</DataListMeta>
          </DataListItem>
        ))}
        {data.pendingApprovals.length === 0 &&
        data.pendingQuestionId === null &&
        data.activeToolCalls.length === 0 ? (
          <DataListItem>
            <DataListMeta>No active approvals, questions, or tool calls.</DataListMeta>
          </DataListItem>
        ) : null}
      </DataList>
    </Pane>
  );
}

function formatApprovalEvidence(approval: DashboardState["pendingApprovals"][number]): string {
  return compactPolicyEvidence({
    fallback: approval.reason,
    outcome: approval.policy_outcome,
    reason: approval.reason,
    riskLevel: approval.policy_risk_level,
    sourceKind: approval.policy_source_kind,
    sourceLabel: approval.policy_source_label,
  });
}

function formatToolEvidence(tool: DashboardState["activeToolCalls"][number]): string {
  return compactPolicyEvidence({
    fallback: tool.summary ?? tool.status,
    outcome: tool.policy_outcome,
    reason: tool.policy_reason,
    riskLevel: tool.policy_risk_level,
    sourceKind: tool.policy_source_kind,
    sourceLabel: tool.policy_source_label,
  });
}

function compactPolicyEvidence({
  fallback,
  outcome,
  reason,
  riskLevel,
  sourceKind,
  sourceLabel,
}: {
  fallback: string;
  outcome?: string | null;
  reason?: string | null;
  riskLevel?: string | null;
  sourceKind?: string | null;
  sourceLabel?: string | null;
}): string {
  const source = [sourceKind, sourceLabel].filter(Boolean).join(":");
  const summary = [
    policyDecisionLabel(outcome, sourceKind),
    riskLevel,
    policySourceLabel(sourceKind, sourceLabel) ?? source,
  ]
    .filter(Boolean)
    .join(" / ");
  if (!summary) {
    return fallback;
  }
  return reason ? `${summary}: ${reason}` : summary;
}
