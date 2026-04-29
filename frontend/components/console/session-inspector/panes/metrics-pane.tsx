import { Activity } from "lucide-react";

import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import { formatDuration } from "@/components/console/session-inspector/format";
import { LoadMoreDetail } from "@/components/console/session-inspector/panes/diagnostics-shared";
import { MetricSummary, summarizeTurnMetrics } from "./shared";
import type { DashboardState } from "@/state/session-state";
import type { DetailPageStatus } from "@/stores/dashboard-stores";

const DETAIL_RENDER_WINDOW = 80;

export function MetricsPane({
  data,
  onLoadMore,
  page,
}: {
  data: DashboardState;
  onLoadMore?: () => void;
  page?: DetailPageStatus;
}) {
  const totals = summarizeTurnMetrics(data.turnMetrics);
  const visibleMetrics = data.turnMetrics.slice(0, DETAIL_RENDER_WINDOW);
  const insights = buildMetricInsights(data);

  return (
    <Pane icon={Activity} title="Metrics">
      {data.turnMetrics.length === 0 ? (
        <EmptyLine value="No turn metrics are available." />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4" aria-label="Metrics summary">
            <MetricSummary label="Turn duration" value={formatDuration(totals.turnDurationMs)} />
            <MetricSummary label="Model duration" value={formatDuration(totals.modelDurationMs)} />
            <MetricSummary label="Tool duration" value={formatDuration(totals.toolDurationMs)} />
            <MetricSummary
              label="Tokens"
              value={`${totals.inputTokens + totals.outputTokens} total`}
            />
          </div>
          <section aria-label="Latency analysis">
            <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
              Latency analysis
            </p>
            <DataList density="compact">
              {insights.map((insight) => (
                <DataListItem key={insight.label}>
                  <DataListLabel>{insight.label}</DataListLabel>
                  <DataListMeta>{insight.value}</DataListMeta>
                </DataListItem>
              ))}
            </DataList>
          </section>
          <section aria-label="Cost and failure patterns">
            <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
              Cost and failure patterns
            </p>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              <MetricSummary label="Model calls" value={`${totals.modelCalls}`} />
              <MetricSummary label="Tool calls" value={`${totals.toolCalls}`} />
              <MetricSummary label="Failed tools" value={`${totals.failedToolCalls}`} />
              <MetricSummary
                label="Average turn"
                value={formatDuration(averageKnownTurnDuration(data.turnMetrics))}
              />
            </div>
          </section>
          <details className="rounded-md border bg-card p-3" open>
            <summary className="cursor-pointer text-sm font-medium">Raw turn metrics</summary>
            <DataList className="mt-3" density="compact">
              {visibleMetrics.map((metric) => (
                <DataListItem key={metric.turn_id}>
                  <DataListLabel>{metric.turn_id}</DataListLabel>
                  <DataListMeta>
                    {metric.model_call_count} model · {metric.tool_call_count} tools ·{" "}
                    {formatDuration(metric.turn_duration_ms)}
                  </DataListMeta>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {metric.model_input_tokens_total} input tokens ·{" "}
                    {metric.model_output_tokens_total} output tokens ·{" "}
                    {metric.failed_tool_call_count} failed tools
                  </p>
                </DataListItem>
              ))}
            </DataList>
            <LoadMoreDetail label="turn metrics" onLoadMore={onLoadMore} page={page} />
          </details>
        </div>
      )}
    </Pane>
  );
}

function buildMetricInsights(data: DashboardState) {
  const metrics = data.turnMetrics;
  const longestTurn = maxMetric(metrics, (metric) => metric.turn_duration_ms ?? -1);
  const largestModel = maxMetric(metrics, (metric) => metric.model_duration_ms_total);
  const largestTool = maxMetric(metrics, (metric) => metric.tool_duration_ms_total);
  const highestToken = maxMetric(
    metrics,
    (metric) => metric.model_input_tokens_total + metric.model_output_tokens_total,
  );
  const mostFailedTools = maxMetric(metrics, (metric) => metric.failed_tool_call_count);

  return [
    {
      label: "Longest observed turn",
      value:
        longestTurn === null
          ? "No completed turn duration is retained."
          : `${longestTurn.turn_id} · ${formatDuration(longestTurn.turn_duration_ms)} observed duration, no threshold applied`,
    },
    {
      label: "Provider latency",
      value:
        largestModel === null || largestModel.model_duration_ms_total === 0
          ? "No model-call duration is retained."
          : `${largestModel.turn_id} · ${formatDuration(largestModel.model_duration_ms_total)} model time · ${largestModel.model_call_count} call${largestModel.model_call_count === 1 ? "" : "s"}`,
    },
    {
      label: "Tool execution latency",
      value:
        largestTool === null || largestTool.tool_duration_ms_total === 0
          ? "No tool execution duration is retained."
          : `${largestTool.turn_id} · ${formatDuration(largestTool.tool_duration_ms_total)} tool time · ${largestTool.tool_call_count} call${largestTool.tool_call_count === 1 ? "" : "s"}`,
    },
    {
      label: "Token cost",
      value:
        highestToken === null
          ? "No token totals are retained."
          : `${highestToken.turn_id} · ${highestToken.model_input_tokens_total + highestToken.model_output_tokens_total} tokens (${highestToken.model_input_tokens_total} input, ${highestToken.model_output_tokens_total} output)`,
    },
    {
      label: "Failure pattern",
      value:
        mostFailedTools === null || mostFailedTools.failed_tool_call_count === 0
          ? "No failed tool calls are retained in these metric rows."
          : `${mostFailedTools.turn_id} · ${mostFailedTools.failed_tool_call_count} failed tool call${mostFailedTools.failed_tool_call_count === 1 ? "" : "s"}`,
    },
    {
      label: "Approval or answer wait",
      value:
        data.pendingApprovals.length > 0
          ? `${data.pendingApprovals.length} pending approval${data.pendingApprovals.length === 1 ? "" : "s"}; wait duration is event evidence, not turn runtime.`
          : data.pendingQuestionId !== null
            ? "Waiting on ask_user; inspect Actions and Event evidence for timestamps."
            : "No current approval or answer wait is visible for this snapshot.",
    },
    {
      label: "Replay or eval drift",
      value: buildReplayDriftInsight(data),
    },
  ];
}

function buildReplayDriftInsight(data: DashboardState): string {
  const artifacts = data.runtimeContext?.artifact_context?.summaries ?? [];
  if (artifacts.length === 0) {
    return "No retained replay/eval artifacts; this pane shows runtime latency only.";
  }
  const driftCount = artifacts.filter(
    (artifact) => artifact.freshness === "stale" || artifact.inherited || artifact.timed_out,
  ).length;
  return driftCount === 0
    ? "Retained artifacts show no stale, inherited, or timed-out drift cue."
    : `${driftCount} advisory drift artifact${driftCount === 1 ? "" : "s"}; inspect Evidence before treating runtime metrics as reproduction proof.`;
}

function averageKnownTurnDuration(metrics: DashboardState["turnMetrics"]): number | null {
  const knownDurations = metrics
    .map((metric) => metric.turn_duration_ms)
    .filter((duration): duration is number => duration !== null);
  if (knownDurations.length === 0) {
    return null;
  }
  return Math.round(
    knownDurations.reduce((total, duration) => total + duration, 0) / knownDurations.length,
  );
}

function maxMetric(
  metrics: DashboardState["turnMetrics"],
  valueForMetric: (metric: DashboardState["turnMetrics"][number]) => number,
) {
  let result: DashboardState["turnMetrics"][number] | null = null;
  let resultValue = Number.NEGATIVE_INFINITY;
  for (const metric of metrics) {
    const value = valueForMetric(metric);
    if (value > resultValue) {
      result = metric;
      resultValue = value;
    }
  }
  return result;
}
