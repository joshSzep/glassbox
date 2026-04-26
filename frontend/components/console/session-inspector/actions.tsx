import { ListChecks } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Pane } from "@/components/console/session-inspector/frame";
import type { DashboardState } from "@/state/session-state";
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

  return (
    <Pane icon={ListChecks} title="Operator actions">
      <div className="space-y-4">
        <ActionStatusLine action={action} />

        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmitPrompt?.();
          }}
        >
          <label className="text-sm font-medium" htmlFor="session-prompt">
            Continue session
          </label>
          <Textarea
            id="session-prompt"
            onChange={(event) => onPromptChange?.(event.currentTarget.value)}
            placeholder="Send the next prompt"
            value={drafts.composerText}
          />
          <Button disabled={pending || drafts.composerText.trim().length === 0} type="submit">
            Send prompt
          </Button>
        </form>

        {questionId !== null ? (
          <form
            className="space-y-2 rounded-md border bg-card p-3"
            onSubmit={(event) => {
              event.preventDefault();
              onSubmitAnswer?.(questionId);
            }}
          >
            <label className="text-sm font-medium" htmlFor="session-answer">
              Answer pending question
            </label>
            <p className="text-sm text-muted-foreground">{data.pendingQuestionText}</p>
            <Textarea
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

        {data.pendingApprovals.length > 0 ? (
          <div className="space-y-2 rounded-md border bg-card p-3">
            <p className="text-sm font-medium">Pending approvals</p>
            {data.pendingApprovals.map((approval) => (
              <div
                className="grid gap-2 border-t pt-2 first:border-t-0 first:pt-0"
                key={approval.approval_id}
              >
                <div>
                  <p className="text-sm font-medium">{approval.subject}</p>
                  <p className="text-sm text-muted-foreground">{approval.reason}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    disabled={pending}
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
                    disabled={pending}
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
              </div>
            ))}
          </div>
        ) : null}

        <div className="space-y-2 rounded-md border bg-card p-3">
          <label className="text-sm font-medium" htmlFor="fork-label">
            Create fork
          </label>
          <Input
            id="fork-label"
            onChange={(event) => onForkLabelChange?.(event.currentTarget.value)}
            placeholder="Optional branch label"
            value={drafts.forkLabel}
          />
          <div className="flex flex-wrap gap-2">
            {data.branchableTurns.length > 0 ? (
              data.branchableTurns.map((turn) => (
                <Button
                  disabled={pending}
                  key={turn.turn_id}
                  onClick={() =>
                    onFork?.({ branchLabel: drafts.forkLabel || null, turnId: turn.turn_id })
                  }
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  Fork {turn.label}
                </Button>
              ))
            ) : (
              <Button
                disabled={pending || !data.canFork}
                onClick={() => onFork?.()}
                size="sm"
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
