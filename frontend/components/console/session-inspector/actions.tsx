"use client";

import { useState, type ReactNode } from "react";
import {
  GitBranch,
  ListChecks,
  MessageSquareText,
  SendHorizontal,
  ShieldCheck,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Pane } from "@/components/console/session-inspector/frame";
import type { DashboardState, PendingApproval } from "@/state/session-state";
import type { ActionStatus, DraftState } from "@/stores/dashboard-stores";

export function OperatorActionPane({
  action,
  data,
  drafts,
  onAnswerTextChange,
  onFork,
  onForkLabelChange,
  onPromptChange,
  onResolveApproval,
  onSubmitAnswer,
  onSubmitPrompt,
}: {
  action: ActionStatus;
  data: DashboardState;
  drafts: DraftState;
  onAnswerTextChange?: (questionId: string, text: string) => void;
  onFork?: (input?: { branchLabel?: string | null; turnId?: string | null }) => void;
  onForkLabelChange?: (text: string) => void;
  onPromptChange?: (text: string) => void;
  onResolveApproval?: (input: { approvalId: string; decision: "approved" | "denied" }) => void;
  onSubmitAnswer?: (questionId: string) => void;
  onSubmitPrompt?: () => void;
}) {
  const pending = action.state === "pending";
  const questionId = data.pendingQuestionId;
  const answerText = questionId === null ? "" : (drafts.answerTextByQuestionId[questionId] ?? "");
  const canPrompt = data.status === "running" && data.sessionFailureMessage === null;

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
                approval={approval}
                key={approval.approval_id}
                onResolveApproval={onResolveApproval}
                pending={pending}
              />
            ))}
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
            <Button
              disabled={pending || answerText.trim().length === 0}
              type="submit"
              variant="secondary"
            >
              Submit answer
            </Button>
          </form>
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
          <Button
            disabled={pending || !canPrompt || drafts.composerText.trim().length === 0}
            type="submit"
          >
            Send prompt
          </Button>
        </form>

        <ForkDialog
          data={data}
          drafts={drafts}
          onFork={onFork}
          onForkLabelChange={onForkLabelChange}
          pending={pending}
        />
      </div>
    </Pane>
  );
}

function SectionHeader({
  detail,
  icon,
  title,
}: {
  detail: string;
  icon: ReactNode;
  title: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{detail}</p>
    </div>
  );
}

function ApprovalCard({
  approval,
  onResolveApproval,
  pending,
}: {
  approval: PendingApproval;
  onResolveApproval?: (input: { approvalId: string; decision: "approved" | "denied" }) => void;
  pending: boolean;
}) {
  return (
    <article className="grid gap-3 border-t pt-3 first:border-t-0 first:pt-0">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="break-words text-sm font-medium">{approval.subject}</p>
          <Badge variant={approval.policy_risk_level === "high" ? "destructive" : "warning"}>
            {approval.policy_risk_level} risk
          </Badge>
          <Badge variant="outline">{approval.policy_source_label}</Badge>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{approval.reason}</p>
        <p className="mt-1 text-xs text-muted-foreground">Requested {approval.requested_at}</p>
        {approval.resolution_error ? (
          <Badge className="mt-2 justify-start" variant="destructive">
            {approval.resolution_error}
          </Badge>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          disabled={pending || approval.resolution_state === "pending"}
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
          disabled={pending || approval.resolution_state === "pending"}
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

function ForkDialog({
  data,
  drafts,
  onFork,
  onForkLabelChange,
  pending,
}: {
  data: DashboardState;
  drafts: DraftState;
  onFork?: (input?: { branchLabel?: string | null; turnId?: string | null }) => void;
  onForkLabelChange?: (text: string) => void;
  pending: boolean;
}) {
  const [open, setOpen] = useState(false);
  const blocked = pending || !data.canFork;

  function forkFrom(turnId?: string | null) {
    onFork?.({ branchLabel: drafts.forkLabel || null, turnId: turnId ?? null });
    setOpen(false);
  }

  return (
    <Dialog onOpenChange={setOpen} open={open}>
      <div className="space-y-3 rounded-md border bg-card p-3">
        <SectionHeader
          detail={
            data.forkBlockedReason ??
            "Choose a fork point and optional branch label in a focused flow."
          }
          icon={<GitBranch className="h-4 w-4" aria-hidden="true" />}
          title="Create fork"
        />
        <DialogTrigger asChild>
          <Button disabled={blocked} type="button" variant="outline">
            Create fork
          </Button>
        </DialogTrigger>
      </div>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create fork</DialogTitle>
          <DialogDescription>
            Name the branch and choose the persisted turn where the new session should start.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="fork-label">
              Fork label
            </label>
            <Input
              id="fork-label"
              onChange={(event) => onForkLabelChange?.(event.currentTarget.value)}
              placeholder="Optional branch label"
              value={drafts.forkLabel}
            />
          </div>
          <div className="grid gap-2">
            {data.branchableTurns.length > 0 ? (
              data.branchableTurns.map((turn) => (
                <Button
                  disabled={pending}
                  key={turn.turn_id}
                  onClick={() => forkFrom(turn.turn_id)}
                  type="button"
                  variant="outline"
                >
                  Fork {turn.label}
                </Button>
              ))
            ) : (
              <Button
                disabled={blocked}
                onClick={() => forkFrom(null)}
                type="button"
                variant="outline"
              >
                Fork latest point
              </Button>
            )}
          </div>
          {data.forkBlockedReason !== null ? (
            <p className="text-xs text-muted-foreground">{data.forkBlockedReason}</p>
          ) : null}
        </div>
        <DialogFooter>
          <Button onClick={() => setOpen(false)} type="button" variant="ghost">
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ActionStatusLine({ action }: { action: ActionStatus }) {
  if (action.state === "idle") {
    return <p className="text-sm text-muted-foreground">Actions wait for backend confirmation.</p>;
  }
  if (action.state === "failed") {
    return (
      <Badge className="justify-start" variant="destructive">
        {action.kind ?? "action"} failed: {action.error}
      </Badge>
    );
  }
  return (
    <Badge className="justify-start" variant={action.state === "succeeded" ? "success" : "info"}>
      {action.kind ?? "action"} {action.state}
    </Badge>
  );
}
