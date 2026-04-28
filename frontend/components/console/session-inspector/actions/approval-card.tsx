import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InlineActionFeedback, isBlockedByNonRetryableFailure } from "./action-feedback";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState, PendingApproval } from "@/state/session-state";
import type { ActionStatus } from "@/stores/dashboard-stores";

export function ApprovalCard({
  action,
  approval,
  data,
  onResolveApproval,
  pending,
  stream,
}: {
  action: ActionStatus;
  approval: PendingApproval;
  data: DashboardState;
  onResolveApproval?: (input: { approvalId: string; decision: "approved" | "denied" }) => void;
  pending: boolean;
  stream: SessionStreamState;
}) {
  const blocked = pending || isBlockedByNonRetryableFailure(action, "approval");
  const policySource = [approval.policy_source_kind, approval.policy_source_label]
    .filter(Boolean)
    .join(":");

  return (
    <article className="grid gap-3 border-t pt-3 first:border-t-0 first:pt-0">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="break-words text-sm font-medium">{approval.subject}</p>
          {approval.policy_outcome ? (
            <Badge variant="warning">{approval.policy_outcome}</Badge>
          ) : null}
          {approval.policy_risk_level ? (
            <Badge variant="outline">{approval.policy_risk_level} risk</Badge>
          ) : null}
          {policySource ? <Badge variant="outline">{policySource}</Badge> : null}
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{approval.reason}</p>
        <p className="mt-1 text-xs text-muted-foreground">Requested {approval.requested_at}</p>
        {approval.resolution_error ? (
          <Badge className="mt-2 justify-start" variant="destructive">
            {approval.resolution_error}
          </Badge>
        ) : null}
      </div>
      <InlineActionFeedback action={action} data={data} kind="approval" stream={stream} />
      <div className="flex flex-wrap gap-2">
        <Button
          disabled={blocked || approval.resolution_state === "pending"}
          onClick={() =>
            onResolveApproval?.({
              approvalId: approval.approval_id,
              decision: "approved",
            })
          }
          size="sm"
          type="button"
        >
          Approve
        </Button>
        <Button
          disabled={blocked || approval.resolution_state === "pending"}
          onClick={() =>
            onResolveApproval?.({ approvalId: approval.approval_id, decision: "denied" })
          }
          size="sm"
          type="button"
          variant="destructive"
        >
          Deny
        </Button>
      </div>
    </article>
  );
}
