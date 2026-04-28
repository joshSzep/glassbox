"use client";

import {
  ListChecks,
  MessageSquareText,
  SendHorizontal,
  ShieldCheck,
  Square,
  Wrench,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApprovalCard } from "@/components/console/session-inspector/actions/approval-card";
import {
  InlineActionFeedback,
  isBlockedByNonRetryableFailure,
} from "@/components/console/session-inspector/actions/action-feedback";
import { ForkDialog } from "@/components/console/session-inspector/actions/fork-dialog";
import { SectionHeader } from "@/components/console/session-inspector/actions/section-header";
import { Pane } from "@/components/console/session-inspector/frame";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState } from "@/state/session-state";
import type { ActionStatus, DraftState } from "@/stores/dashboard-stores";

export function OperatorActionPane({
  action,
  data,
  drafts,
  forkDialogRequest,
  onAnswerTextChange,
  onClearForkDialogRequest,
  onFork,
  onForkLabelChange,
  onPromptChange,
  onRequestCancellation,
  onResolveApproval,
  onSubmitAnswer,
  onSubmitPrompt,
  stream,
}: {
  action: ActionStatus;
  data: DashboardState;
  drafts: DraftState;
  forkDialogRequest?: { requestId: number; turnId: string | null } | null;
  onAnswerTextChange?: (questionId: string, text: string) => void;
  onClearForkDialogRequest?: () => void;
  onFork?: (input?: { branchLabel?: string | null; turnId?: string | null }) => void;
  onForkLabelChange?: (text: string) => void;
  onPromptChange?: (text: string) => void;
  onRequestCancellation?: () => void;
  onResolveApproval?: (input: { approvalId: string; decision: "approved" | "denied" }) => void;
  onSubmitAnswer?: (questionId: string) => void;
  onSubmitPrompt?: () => void;
  stream: SessionStreamState;
}) {
  const pending = action.state === "pending";
  const questionId = data.pendingQuestionId;
  const answerText = questionId === null ? "" : (drafts.answerTextByQuestionId[questionId] ?? "");
  const canPrompt = data.status === "running" && data.sessionFailureMessage === null;
  const canCancel = data.currentTurn?.status === "running";

  return (
    <Pane icon={ListChecks} title="Operator actions">
      <div className="space-y-4">
        <ActionStatusLine action={action} />

        {data.pendingApprovals.length > 0 ? (
          <section className="space-y-3 rounded-md border border-warning bg-card p-3">
            <SectionHeader
              detail="Resolve policy decisions before lower-priority session actions."
              icon={<ShieldCheck className="h-4 w-4" aria-hidden="true" />}
              title="Pending approvals"
            />
            {data.pendingApprovals.map((approval) => (
              <ApprovalCard
                action={action}
                approval={approval}
                data={data}
                key={approval.approval_id}
                onResolveApproval={onResolveApproval}
                pending={pending}
                stream={stream}
              />
            ))}
          </section>
        ) : null}

        {data.activeToolCalls.length > 0 ? (
          <section className="space-y-3 rounded-md border bg-card p-3">
            <SectionHeader
              detail="Running tool calls with their policy decision evidence."
              icon={<Wrench className="h-4 w-4" aria-hidden="true" />}
              title="Active tools"
            />
            {data.activeToolCalls.map((tool) => {
              const policySource = [tool.policy_source_kind, tool.policy_source_label]
                .filter(Boolean)
                .join(":");

              return (
                <article
                  className="grid gap-2 border-t pt-3 first:border-t-0 first:pt-0"
                  key={tool.tool_call_id}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="break-words text-sm font-medium">{tool.tool_name}</p>
                    <Badge variant="outline">{tool.status}</Badge>
                    {tool.policy_outcome ? (
                      <Badge variant="info">{tool.policy_outcome}</Badge>
                    ) : null}
                    {tool.policy_risk_level ? (
                      <Badge variant="outline">{tool.policy_risk_level} risk</Badge>
                    ) : null}
                    {policySource ? <Badge variant="outline">{policySource}</Badge> : null}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {tool.policy_reason ?? tool.summary ?? "Tool is running."}
                  </p>
                </article>
              );
            })}
          </section>
        ) : null}

        {questionId !== null ? (
          <form
            className="space-y-3 rounded-md border border-info bg-card p-3"
            onSubmit={(event) => {
              event.preventDefault();
              onSubmitAnswer?.(questionId);
            }}
          >
            <SectionHeader
              detail={data.pendingQuestionText ?? "The session is waiting for an answer."}
              icon={<MessageSquareText className="h-4 w-4" aria-hidden="true" />}
              title="Answer pending question"
            />
            <Textarea
              aria-label="Answer pending question"
              id="session-answer"
              onChange={(event) => onAnswerTextChange?.(questionId, event.currentTarget.value)}
              placeholder="Answer for ask_user"
              value={answerText}
            />
            <InlineActionFeedback action={action} data={data} kind="answer" stream={stream} />
            <Button
              disabled={
                pending ||
                answerText.trim().length === 0 ||
                isBlockedByNonRetryableFailure(action, "answer")
              }
              type="submit"
              variant="secondary"
            >
              Submit answer
            </Button>
          </form>
        ) : null}

        {canCancel ? (
          <section className="space-y-3 rounded-md border border-warning bg-card p-3">
            <SectionHeader
              detail="Request cancellation from the live runtime owner. Partial output remains in the session evidence."
              icon={<Square className="h-4 w-4" aria-hidden="true" />}
              title="Cancel active turn"
            />
            <InlineActionFeedback action={action} data={data} kind="cancel" stream={stream} />
            <Button
              disabled={pending || isBlockedByNonRetryableFailure(action, "cancel")}
              onClick={() => onRequestCancellation?.()}
              type="button"
              variant="secondary"
            >
              Cancel turn
            </Button>
          </section>
        ) : null}

        <form
          className="space-y-3 rounded-md border bg-card p-3"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmitPrompt?.();
          }}
        >
          <SectionHeader
            detail={
              canPrompt
                ? "Send the next prompt once urgent approvals and questions are settled."
                : (data.sessionFailureMessage ??
                  data.forkBlockedReason ??
                  "This session cannot accept a prompt right now.")
            }
            icon={<SendHorizontal className="h-4 w-4" aria-hidden="true" />}
            title="Continue session"
          />
          <Textarea
            aria-label="Continue session"
            id="session-prompt"
            onChange={(event) => onPromptChange?.(event.currentTarget.value)}
            placeholder="Send the next prompt"
            value={drafts.composerText}
          />
          <InlineActionFeedback action={action} data={data} kind="prompt" stream={stream} />
          <Button
            disabled={
              pending ||
              !canPrompt ||
              drafts.composerText.trim().length === 0 ||
              isBlockedByNonRetryableFailure(action, "prompt")
            }
            type="submit"
          >
            Send prompt
          </Button>
        </form>

        <ForkDialog
          data={data}
          drafts={drafts}
          action={action}
          forkDialogRequest={forkDialogRequest ?? null}
          onClearForkDialogRequest={onClearForkDialogRequest}
          onFork={onFork}
          onForkLabelChange={onForkLabelChange}
          pending={pending}
          stream={stream}
        />
      </div>
    </Pane>
  );
}

function ActionStatusLine({ action }: { action: ActionStatus }) {
  if (action.state === "idle") {
    return <p className="text-sm text-muted-foreground">Actions wait for backend confirmation.</p>;
  }
  if (action.state === "failed") {
    return (
      <Badge className="justify-start" variant="warning">
        Review inline recovery guidance for {action.kind ?? "the action"}.
      </Badge>
    );
  }
  return (
    <Badge className="justify-start" variant={action.state === "succeeded" ? "success" : "info"}>
      {action.kind ?? "action"} {action.state}
    </Badge>
  );
}
