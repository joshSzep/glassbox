import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { DashboardState, SessionNarrativeTurn } from "@/state/session-state";

export function JumpLink({ label, turn }: { label: string; turn: SessionNarrativeTurn }) {
  return (
    <Button asChild size="xs" type="button" variant="outline">
      <a href={`#${narrativeTurnDomId(turn)}`}>{label}</a>
    </Button>
  );
}

export function badgeForNarrativeStatus(status: SessionNarrativeTurn["status"]) {
  if (status === "failed") {
    return "destructive";
  }
  if (status === "awaiting-approval" || status === "awaiting-answer") {
    return "warning";
  }
  if (status === "active" || status === "running") {
    return "info";
  }
  if (status === "completed") {
    return "success";
  }
  return "outline";
}

export function narrativeTurnDomId(turn: SessionNarrativeTurn): string {
  return `narrative-${turn.id.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

export function MetricSummary({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold">{value}</p>
    </div>
  );
}

export function summarizeTurnMetrics(metrics: DashboardState["turnMetrics"]) {
  return metrics.reduce(
    (totals, metric) => ({
      failedToolCalls: totals.failedToolCalls + metric.failed_tool_call_count,
      inputTokens: totals.inputTokens + metric.model_input_tokens_total,
      modelCalls: totals.modelCalls + metric.model_call_count,
      modelDurationMs: totals.modelDurationMs + metric.model_duration_ms_total,
      outputTokens: totals.outputTokens + metric.model_output_tokens_total,
      toolCalls: totals.toolCalls + metric.tool_call_count,
      toolDurationMs: totals.toolDurationMs + metric.tool_duration_ms_total,
      turnDurationMs: totals.turnDurationMs + (metric.turn_duration_ms ?? 0),
    }),
    {
      failedToolCalls: 0,
      inputTokens: 0,
      modelCalls: 0,
      modelDurationMs: 0,
      outputTokens: 0,
      toolCalls: 0,
      toolDurationMs: 0,
      turnDurationMs: 0,
    },
  );
}

export function StatusBadge({ status }: { status: SessionNarrativeTurn["status"] }) {
  return <Badge variant={badgeForNarrativeStatus(status)}>{status}</Badge>;
}
