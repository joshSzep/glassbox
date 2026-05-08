import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import type { ChangesetActionStatus, ChangesetDetailState } from "@/stores/dashboard-stores";

import { readinessBadgeVariant } from "./format";
import { formatReviewPostureState, responseBadgeVariant } from "./review-posture";
import { Section } from "./shared";
import type { ChangesetConsoleProps } from "./types";

type ChangesetDetailRecord = NonNullable<ChangesetDetailState["detail"]>;

export function ReviewPanel({
  briefCount,
  latestBriefId,
  readiness,
}: {
  briefCount: number;
  latestBriefId: string | null;
  readiness: ChangesetDetailRecord["readiness"][number] | undefined;
}) {
  const state = readiness?.state ?? "needs_review";
  const blockers = readiness?.blockers ?? [];
  return (
    <Section title="Review Readiness">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={readinessBadgeVariant(state)}>{formatReviewPostureState(state)}</Badge>
          <Badge variant={briefCount > 0 ? "success" : "warning"}>{briefCount} brief</Badge>
          {latestBriefId ? <Badge variant="outline">Latest brief attached</Badge> : null}
        </div>
        <p className="text-sm text-muted-foreground">
          {readiness?.reason ??
            "Generate a brief after inventory and verification evidence settle."}
        </p>
        {latestBriefId ? (
          <p className="break-all text-console text-muted-foreground">{latestBriefId}</p>
        ) : null}
        {blockers.length > 0 ? (
          <DataList density="compact">
            {blockers.map((blocker) => (
              <DataListItem key={blocker}>
                <DataListLabel>Blocker</DataListLabel>
                <DataListMeta>{blocker}</DataListMeta>
              </DataListItem>
            ))}
          </DataList>
        ) : null}
      </div>
    </Section>
  );
}

export function ReviewFeedbackPanel({
  action,
  detail,
  onRecordFeedbackFixup,
}: {
  action: ChangesetActionStatus;
  detail: ChangesetDetailRecord;
  onRecordFeedbackFixup?: ChangesetConsoleProps["onRecordFeedbackFixup"];
}) {
  const feedback = detail.review_feedback;
  const responseSummary = detail.review_response_summary;
  const responseByFeedbackId = new Map(
    responseSummary.items.map((item) => [item.feedback_id, item]),
  );
  const openItems = feedback.filter(
    (item) => item.disposition === "open" || item.disposition === "in_progress",
  );
  const questions = feedback.filter((item) => item.feedback_kind === "reviewer_question");
  const requestedChanges = feedback.filter((item) => item.feedback_kind === "requested_change");
  const acceptedRisks = feedback.filter((item) => item.disposition === "accepted_with_risk");
  const resolved = feedback.filter((item) => item.disposition === "resolved_locally");
  return (
    <Section title="Review Feedback">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={openItems.length > 0 ? "warning" : "muted"}>
            {openItems.length} open
          </Badge>
          <Badge variant={requestedChanges.length > 0 ? "warning" : "muted"}>
            {requestedChanges.length} requested
          </Badge>
          <Badge variant={questions.length > 0 ? "info" : "muted"}>
            {questions.length} questions
          </Badge>
          <Badge variant={resolved.length > 0 ? "success" : "muted"}>
            {resolved.length} resolved locally
          </Badge>
          <Badge variant={acceptedRisks.length > 0 ? "outline" : "muted"}>
            {acceptedRisks.length} accepted risks
          </Badge>
          <Badge variant={responseSummary.responded_count > 0 ? "success" : "muted"}>
            {responseSummary.responded_count} responded
          </Badge>
          <Badge variant={responseSummary.stale_response_count > 0 ? "warning" : "muted"}>
            {responseSummary.stale_response_count} stale responses
          </Badge>
        </div>
        {feedback.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No local review feedback is attached to this changeset.
          </p>
        ) : (
          <DataList density="compact">
            {feedback.slice(0, 8).map((item) => {
              const response = responseByFeedbackId.get(item.feedback_id);
              const fixupPending =
                action.state === "pending" && action.kind === "record-feedback-fixup";
              const fixupFailed =
                action.state === "failed" && action.kind === "record-feedback-fixup";
              const fixupAttached = response !== undefined && response.fixup_inventory_count > 0;
              return (
                <DataListItem id={feedbackRowId(item.feedback_id)} key={item.feedback_id}>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <DataListLabel>{item.summary}</DataListLabel>
                    <div className="flex flex-wrap items-center gap-2">
                      {response ? (
                        <Badge variant={responseBadgeVariant(response.response_state)}>
                          {formatReviewPostureState(response.response_state)}
                        </Badge>
                      ) : null}
                      <Button asChild size="sm" variant="ghost">
                        <a href={`#${feedbackRowId(item.feedback_id)}`}>Link</a>
                      </Button>
                      <Button
                        aria-label={`Record fixup inventory for feedback ${item.feedback_id}`}
                        disabled={action.state === "pending" || onRecordFeedbackFixup === undefined}
                        onClick={() => onRecordFeedbackFixup?.(item.feedback_id)}
                        size="sm"
                        type="button"
                        variant={fixupAttached ? "outline" : "default"}
                      >
                        {fixupPending
                          ? "Recording"
                          : fixupAttached
                            ? "Refresh fixup"
                            : "Record fixup"}
                      </Button>
                    </div>
                  </div>
                  <DataListMeta>
                    {item.feedback_kind} - {item.disposition} - {item.provenance}
                    {item.reviewer_label ? ` - ${item.reviewer_label}` : ""}
                  </DataListMeta>
                  {response ? (
                    <>
                      <DataListMeta>
                        Response {response.response_state} - {response.fixup_inventory_count}{" "}
                        inventories - {response.changed_path_count} paths -{" "}
                        {response.matched_scope_path_count} scoped matches
                      </DataListMeta>
                      <DataListMeta>
                        Freshness {response.inventory_freshness}
                        {response.stale_reason ? ` - ${response.stale_reason}` : ""}
                      </DataListMeta>
                      {response.fixup_inventory_count === 0 ? (
                        <DataListMeta>
                          Missing fixup inventory; inspect feedback status before recording.
                        </DataListMeta>
                      ) : null}
                      <DataListMeta>
                        Verification {response.verification_state}
                        {response.verification_reason ? ` - ${response.verification_reason}` : ""}
                      </DataListMeta>
                      {response.verification_safe_next_actions.slice(0, 1).map((action) => (
                        <DataListMeta className="break-all" key={action}>
                          Inspect first: {action}
                        </DataListMeta>
                      ))}
                      <DataListMeta className="break-all">
                        glassbox changeset feedback fixup {item.feedback_id} --from-workspace --cwd
                        .
                      </DataListMeta>
                      {response.path_summaries.slice(0, 2).map((summary) => (
                        <DataListMeta key={summary}>{summary}</DataListMeta>
                      ))}
                      {response.blockers.slice(0, 2).map((blocker) => (
                        <DataListMeta key={blocker}>Blocker: {blocker}</DataListMeta>
                      ))}
                      {fixupFailed ? (
                        <DataListMeta>
                          Fixup action failed; reviewer approval was not recorded.
                        </DataListMeta>
                      ) : null}
                    </>
                  ) : null}
                  {item.resolution_summary ? (
                    <DataListMeta>Resolution: {item.resolution_summary}</DataListMeta>
                  ) : null}
                  {item.risk_summary ? (
                    <DataListMeta>Accepted risk: {item.risk_summary}</DataListMeta>
                  ) : null}
                  {item.residual_risk ? (
                    <DataListMeta>Residual risk: {item.residual_risk}</DataListMeta>
                  ) : null}
                </DataListItem>
              );
            })}
          </DataList>
        )}
        <ul className="grid gap-2 text-console text-muted-foreground">
          {responseSummary.safe_next_actions.map((action) => (
            <li className="break-all" key={action}>
              {action}
            </li>
          ))}
          <li className="break-all">
            glassbox changeset feedback list --changeset {detail.changeset.changeset_id} --cwd .
          </li>
          {responseSummary.non_claims.slice(0, 1).map((claim) => (
            <li key={claim}>{claim}</li>
          ))}
        </ul>
      </div>
    </Section>
  );
}

function feedbackRowId(feedbackId: string) {
  return `feedback-${feedbackId}`;
}
