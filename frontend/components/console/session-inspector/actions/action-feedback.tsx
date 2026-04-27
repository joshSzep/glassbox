import { Badge } from "@/components/ui/badge";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState } from "@/state/session-state";
import type { ActionKind, ActionStatus } from "@/stores/dashboard-stores";

export function InlineActionFeedback({
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

export function isBlockedByNonRetryableFailure(action: ActionStatus, kind: ActionKind): boolean {
  if (action.kind !== kind || action.state !== "failed") {
    return false;
  }
  const feedback = classifyFailure(action.error ?? "");
  return !feedback.retryable;
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
