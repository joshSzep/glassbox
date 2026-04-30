import { AlertTriangle, CheckCircle2, ClipboardCheck, HelpCircle, ServerCog } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { buildAppRoute, type AppQueue } from "@/routing/app-route";
import type { WorkspaceAttentionSummary as WorkspaceAttentionSummaryModel } from "@/state/session-state";

export function WorkspaceAttentionSummary({
  summary,
}: {
  summary: WorkspaceAttentionSummaryModel;
}) {
  const target = attentionTarget(summary);

  return (
    <section
      aria-label="Workspace attention summary"
      className="rounded-md border border-border/80 bg-card p-4 text-card-foreground shadow-sm"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-border/70 bg-surface">
            <WorkspaceAttentionIcon kind={summary.kind} />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
                Workspace Attention
              </h2>
              <Badge variant={attentionVariant(summary.level)}>{summary.kind}</Badge>
            </div>
            <p className="mt-1 text-lg font-semibold tracking-normal">{summary.title}</p>
            <p className="mt-1 text-sm text-muted-foreground">{summary.detail}</p>
          </div>
        </div>
        {target.kind === "link" ? (
          <Button asChild className="shrink-0" size="sm" variant="outline">
            <a href={target.href}>{summary.actionLabel}</a>
          </Button>
        ) : target.kind === "command" ? (
          <code className="block max-w-full overflow-x-auto rounded-md border border-border/70 bg-surface px-3 py-2 text-xs text-muted-foreground">
            {target.command}
          </code>
        ) : null}
      </div>
    </section>
  );
}

function WorkspaceAttentionIcon({ kind }: { kind: WorkspaceAttentionSummaryModel["kind"] }) {
  const iconClassName = "h-5 w-5 text-muted-foreground";
  if (kind === "healthy") {
    return <CheckCircle2 className={iconClassName} aria-hidden="true" />;
  }
  if (kind === "approval") {
    return <ClipboardCheck className={iconClassName} aria-hidden="true" />;
  }
  if (kind === "question") {
    return <HelpCircle className={iconClassName} aria-hidden="true" />;
  }
  if (kind === "runtime" || kind === "job") {
    return <ServerCog className={iconClassName} aria-hidden="true" />;
  }
  return <AlertTriangle className={iconClassName} aria-hidden="true" />;
}

function attentionVariant(level: WorkspaceAttentionSummaryModel["level"]) {
  if (level === "healthy") {
    return "success" as const;
  }
  if (level === "action" || level === "warning") {
    return "warning" as const;
  }
  return "info" as const;
}

function attentionTarget(
  summary: WorkspaceAttentionSummaryModel,
): { href: string; kind: "link" } | { command: string; kind: "command" } | { kind: "none" } {
  if (summary.target.kind === "session") {
    return {
      href: buildAppRoute({
        compareSessionId: null,
        queue: summary.target.queue as AppQueue,
        selectedSessionId: summary.target.sessionId,
        tab: "overview",
      }),
      kind: "link",
    };
  }
  if (summary.target.kind === "queue") {
    return {
      href: buildAppRoute({
        compareSessionId: null,
        queue: summary.target.queue as AppQueue,
        selectedSessionId: null,
        tab: "overview",
      }),
      kind: "link",
    };
  }
  if (summary.target.kind === "command") {
    return { command: summary.target.command, kind: "command" };
  }
  return { kind: "none" };
}
