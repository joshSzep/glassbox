"use client";

import {
  ListChecks,
  MessageSquareText,
  RotateCcw,
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
import {
  policyDecisionLabel,
  policyDecisionVariant,
  policyRiskLabel,
  policySourceLabel,
} from "@/components/console/session-inspector/policy-evidence";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState } from "@/state/session-state";
import type { ActionStatus, DraftState } from "@/stores/dashboard-stores";

export function OperatorActionPane({
  action,
  data,
  drafts,
  forkDialogRequest,
  onAnswerTextChange,
  onAbandonToolAttempt,
  onClearForkDialogRequest,
  onFork,
  onForkLabelChange,
  onPromptChange,
  onRequestCancellation,
  onResolveApproval,
  onSubmitAnswer,
  onSubmitPrompt,
  onRetryToolAttempt,
  stream,
}: {
  action: ActionStatus;
  data: DashboardState;
  drafts: DraftState;
  onAbandonToolAttempt?: (toolAttemptId: string) => void;
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
  onRetryToolAttempt?: (toolAttemptId: string) => void;
  stream: SessionStreamState;
}) {
  const pending = action.state === "pending";
  const questionId = data.pendingQuestionId;
  const answerText = questionId === null ? "" : (drafts.answerTextByQuestionId[questionId] ?? "");
  const canPrompt = data.status === "running" && data.sessionFailureMessage === null;
  const canCancel = data.currentTurn?.status === "running";
  const retryAttempts = data.recentToolAttempts
    .filter((attempt) => attempt.retry_classification !== null)
    .slice(0, 3);

  return (
    <Pane icon={ListChecks} title="Operator actions">
      <div className="space-y-4">
        <ActionStatusLine action={action} />
        <RecoveryGuidance data={data} stream={stream} />

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
              const policyDecision = policyDecisionLabel(
                tool.policy_outcome,
                tool.policy_source_kind,
              );
              const policyRisk = policyRiskLabel(tool.policy_risk_level);
              const policySource = policySourceLabel(
                tool.policy_source_kind,
                tool.policy_source_label,
              );

              return (
                <article
                  className="grid gap-2 border-t pt-3 first:border-t-0 first:pt-0"
                  key={tool.tool_call_id}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="break-words text-sm font-medium">{tool.tool_name}</p>
                    <Badge variant="outline">{tool.status}</Badge>
                    {policyDecision ? (
                      <Badge
                        variant={policyDecisionVariant(
                          tool.policy_outcome,
                          tool.policy_source_kind,
                        )}
                      >
                        {policyDecision}
                      </Badge>
                    ) : null}
                    {policyRisk ? <Badge variant="outline">{policyRisk}</Badge> : null}
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

        {retryAttempts.length > 0 ? (
          <section className="space-y-3 rounded-md border bg-card p-3">
            <SectionHeader
              detail="Recent tool attempts with retained retry classification."
              icon={<RotateCcw className="h-4 w-4" aria-hidden="true" />}
              title="Tool retry posture"
            />
            {retryAttempts.map((attempt) => (
              <article
                className="grid gap-2 border-t pt-3 first:border-t-0 first:pt-0"
                key={attempt.tool_attempt_id}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <p className="break-words text-sm font-medium">{attempt.tool_name} attempt</p>
                  <Badge variant="outline">{attempt.status}</Badge>
                  <Badge variant="outline">{attempt.retry_classification}</Badge>
                  {attempt.retry_requires_approval ? (
                    <Badge variant="warning">approval required</Badge>
                  ) : (
                    <Badge variant="outline">no approval</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  {attempt.retry_reason ?? attempt.message ?? "Retry posture is retained."}
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    disabled={
                      pending ||
                      attempt.retry_classification === "unsafe_to_retry" ||
                      attempt.status === "retried" ||
                      attempt.status === "abandoned"
                    }
                    onClick={() => onRetryToolAttempt?.(attempt.tool_attempt_id)}
                    size="sm"
                    type="button"
                    variant="secondary"
                  >
                    <RotateCcw className="h-4 w-4" aria-hidden="true" />
                    Retry
                  </Button>
                  <Button
                    disabled={
                      pending ||
                      attempt.status === "retried" ||
                      attempt.status === "abandoned" ||
                      attempt.status === "succeeded"
                    }
                    onClick={() => onAbandonToolAttempt?.(attempt.tool_attempt_id)}
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    Abandon
                  </Button>
                </div>
              </article>
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

type RecoveryGuidanceCue = {
  commands: string[];
  detail: string;
  label: string;
  tone: "info" | "warning";
};

function RecoveryGuidance({ data, stream }: { data: DashboardState; stream: SessionStreamState }) {
  const cues = buildRecoveryGuidance(data, stream);
  if (cues.length === 0) {
    return null;
  }
  return (
    <section className="space-y-3 rounded-md border bg-card p-3">
      <SectionHeader
        detail="Inspect retained evidence before running mutating recovery commands."
        icon={<ListChecks className="h-4 w-4" aria-hidden="true" />}
        title="Recovery guidance"
      />
      {cues.map((cue) => (
        <article className="grid gap-2 border-t pt-3 first:border-t-0 first:pt-0" key={cue.label}>
          <div className="flex flex-wrap items-center gap-2">
            <p className="break-words text-sm font-medium">{cue.label}</p>
            <Badge variant={cue.tone}>{cue.tone === "warning" ? "attention" : "inspect"}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">{cue.detail}</p>
          {cue.commands.map((command) => (
            <code
              className="block overflow-x-auto rounded-md border border-border/70 bg-surface-raised px-2 py-1 text-xs text-muted-foreground"
              key={command}
            >
              {command}
            </code>
          ))}
        </article>
      ))}
    </section>
  );
}

function buildRecoveryGuidance(
  data: DashboardState,
  stream: SessionStreamState,
): RecoveryGuidanceCue[] {
  const cues: RecoveryGuidanceCue[] = [];
  const sessionId = data.sessionId ?? "SESSION_ID";
  const attempts = data.recentToolAttempts.filter((attempt) =>
    ["failed", "stale", "cancelled"].includes(attempt.status),
  );
  for (const attempt of attempts.slice(0, 2)) {
    cues.push({
      commands: [
        `uv run glassbox session tool-attempt inspect ${sessionId} ${attempt.tool_attempt_id} --cwd .`,
        `uv run glassbox session tool-attempt output ${sessionId} ${attempt.tool_attempt_id} --cwd .`,
      ],
      detail: `Review ${attempt.tool_name} ${attempt.status} output before retry or abandon. Retry and abandon controls require explicit confirmation.`,
      label: "Tool attempt recovery",
      tone: "warning",
    });
  }

  const staleCompactions = data.runtimeContext?.context_compactions?.stale_items ?? [];
  if (staleCompactions.length > 0) {
    const compaction = staleCompactions[0];
    cues.push({
      commands: [
        `uv run glassbox session compactions ${sessionId} --cwd .`,
        `uv run glassbox session compaction-refresh ${sessionId} ${compaction.compaction_id} --yes --cwd .`,
      ],
      detail:
        "Inspect compaction freshness before refresh or invalidation; mutating CLI commands require an explicit confirmation flag.",
      label: "Compaction recovery",
      tone: "warning",
    });
  }

  if (
    data.turnRecoveryPosture != null &&
    ["incomplete", "recoverable", "abandoned", "non_resumable"].includes(
      data.turnRecoveryPosture.state,
    )
  ) {
    cues.push({
      commands: [
        `uv run glassbox session status ${sessionId} --cwd .`,
        `uv run glassbox session resume ${sessionId} --cwd .`,
      ],
      detail: data.turnRecoveryPosture.next_action,
      label: "Turn recovery",
      tone: "warning",
    });
  }

  const failedVerificationCount = data.turnMetrics.reduce(
    (total, metric) => total + metric.failed_tool_call_count,
    0,
  );
  if (failedVerificationCount > 0) {
    cues.push({
      commands: [
        `uv run glassbox replay run ${sessionId} --json --cwd .`,
        "uv run glassbox eval recommend --cwd .",
      ],
      detail:
        "Failed verification evidence is loaded; inspect replay/eval or retained artifacts before marking work repaired.",
      label: "Verification recovery",
      tone: "warning",
    });
  }

  if (data.providerEvidence.freshness_status !== "fresh") {
    cues.push({
      commands: [
        "uv run glassbox provider diagnostics --cwd .",
        "uv run glassbox provider canary evidence --cwd .",
      ],
      detail: `Provider evidence is ${data.providerEvidence.freshness_status}; inspect advisory posture before switching models.`,
      label: "Provider recovery",
      tone: "info",
    });
  }

  if (stream.status !== "live") {
    cues.push({
      commands: ["uv run glassbox daemon status --cwd ."],
      detail: `Browser stream is ${stream.status}; inspect daemon ownership before trusting live-state controls.`,
      label: "Daemon recovery",
      tone: "warning",
    });
  }

  return cues;
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
