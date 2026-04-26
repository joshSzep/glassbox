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
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState, PendingApproval } from "@/state/session-state";
import type { ActionKind, ActionStatus, DraftState } from "@/stores/dashboard-stores";

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
  stream,
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
  stream: SessionStreamState;
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
          onFork={onFork}
          onForkLabelChange={onForkLabelChange}
          pending={pending}
          stream={stream}
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

function ForkDialog({
  action,
  data,
  drafts,
  onFork,
  onForkLabelChange,
  pending,
  stream,
}: {
  action: ActionStatus;
  data: DashboardState;
  drafts: DraftState;
  onFork?: (input?: { branchLabel?: string | null; turnId?: string | null }) => void;
  onForkLabelChange?: (text: string) => void;
  pending: boolean;
  stream: SessionStreamState;
}) {
  const [open, setOpen] = useState(false);
  const blocked = pending || !data.canFork || isBlockedByNonRetryableFailure(action, "fork");

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
        <InlineActionFeedback action={action} data={data} kind="fork" stream={stream} />
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
          <InlineActionFeedback action={action} data={data} kind="fork" stream={stream} />
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

function InlineActionFeedback({
  action,
  data,
  kind,
  stream,
}: {
  action: ActionStatus;
  data: DashboardState;
  kind: ActionKind;
  stream: SessionStreamState;
}) {
  const feedback = feedbackForAction(action, kind) ?? availabilityFeedback(data, kind, stream);
  if (feedback === null) {
    return null;
  }

  return (
    <div className="rounded-md border bg-background p-3 text-sm" role="status">
      <Badge className="justify-start" variant={feedback.variant}>
        {feedback.label}
      </Badge>
      <p className="mt-2 text-muted-foreground">{feedback.message}</p>
    </div>
  );
}

function feedbackForAction(action: ActionStatus, kind: ActionKind): ActionFeedback | null {
  if (action.kind !== kind) {
    return null;
  }
  if (action.state === "pending") {
    return {
      label: pendingLabel(kind),
      message: "Waiting for backend confirmation. Local draft text is preserved while this runs.",
      retryable: false,
      variant: "info",
    };
  }
  if (action.state === "succeeded") {
    return {
      label: successLabel(kind),
      message:
        "The backend accepted this action. The selected session snapshot will stay canonical.",
      retryable: false,
      variant: "success",
    };
  }
  if (action.state !== "failed") {
    return null;
  }

  return classifyFailure(action.error ?? "Glassbox API request failed.");
}

function availabilityFeedback(
  data: DashboardState,
  kind: ActionKind,
  stream: SessionStreamState,
): ActionFeedback | null {
  if ((kind === "prompt" || kind === "fork") && data.status !== "running") {
    return {
      label: "historical-only",
      message:
        "This is a historical snapshot. Review transcript, lineage, and evidence instead of sending new live actions.",
      retryable: false,
      variant: "muted",
    };
  }
  if (stream.status === "live_unavailable" && (kind === "prompt" || kind === "answer")) {
    return {
      label: "live unavailable",
      message:
        stream.error ??
        "The persisted snapshot is visible, but live action confirmation is unavailable right now.",
      retryable: true,
      variant: "warning",
    };
  }
  if (data.runtimeContext === null && (kind === "prompt" || kind === "fork")) {
    return {
      label: "runtime offline",
      message:
        "Runtime context is unavailable. Keep drafts intact and retry after the workspace runtime recovers.",
      retryable: true,
      variant: "warning",
    };
  }
  if (data.projectionHealth?.degraded && (kind === "approval" || kind === "answer")) {
    return {
      label: "projection degraded",
      message:
        "Projection lag may hide the latest evidence. Verify the evidence tab before resolving this action.",
      retryable: false,
      variant: "warning",
    };
  }
  return null;
}

type ActionFeedback = {
  label: string;
  message: string;
  retryable: boolean;
  variant: "destructive" | "info" | "muted" | "success" | "warning";
};

function classifyFailure(error: string): ActionFeedback {
  const normalized = error.toLowerCase();
  if (
    normalized.includes("conflict") ||
    normalized.includes("already") ||
    normalized.includes("no longer")
  ) {
    return {
      label: "conflict",
      message: `${error} Refresh the snapshot before acting again; this action may already be resolved.`,
      retryable: false,
      variant: "warning",
    };
  }
  if (
    normalized.includes("validation") ||
    normalized.includes("invalid") ||
    normalized.includes("empty")
  ) {
    return {
      label: "validation error",
      message: `${error} Fix the input and submit again. Your draft is still here.`,
      retryable: true,
      variant: "destructive",
    };
  }
  if (
    normalized.includes("network") ||
    normalized.includes("fetch") ||
    normalized.includes("timeout")
  ) {
    return {
      label: "network error",
      message: `${error} Your draft is preserved; retry when the connection recovers.`,
      retryable: true,
      variant: "destructive",
    };
  }
  if (normalized.includes("unavailable") || normalized.includes("offline")) {
    return {
      label: "unavailable runtime",
      message: `${error} Keep the current draft and retry after the runtime is healthy.`,
      retryable: true,
      variant: "warning",
    };
  }
  return {
    label: "request failed",
    message: `${error} Your draft is preserved so you can retry safely after checking the snapshot.`,
    retryable: true,
    variant: "destructive",
  };
}

function isBlockedByNonRetryableFailure(action: ActionStatus, kind: ActionKind): boolean {
  if (action.kind !== kind || action.state !== "failed") {
    return false;
  }
  const feedback = classifyFailure(action.error ?? "");
  return !feedback.retryable;
}

function pendingLabel(kind: ActionKind): string {
  if (kind === "approval") {
    return "resolving approval";
  }
  if (kind === "answer") {
    return "submitting answer";
  }
  if (kind === "fork") {
    return "creating fork";
  }
  return "sending prompt";
}

function successLabel(kind: ActionKind): string {
  if (kind === "approval") {
    return "approval resolved";
  }
  if (kind === "answer") {
    return "answer submitted";
  }
  if (kind === "fork") {
    return "fork created";
  }
  return "prompt sent";
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
