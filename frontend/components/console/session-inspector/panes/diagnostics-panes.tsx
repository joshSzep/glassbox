import type { ReactNode } from "react";
import { ChevronDown, Activity, ScrollText, TerminalSquare } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import { formatDuration } from "@/components/console/session-inspector/format";
import { MetricSummary, summarizeTurnMetrics } from "./shared";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState } from "@/state/session-state";
import type { DetailPageStatus } from "@/stores/dashboard-stores";

const DETAIL_RENDER_WINDOW = 80;

export function RuntimePane({ data }: { data: DashboardState }) {
  const context = data.runtimeContext;
  const workingSet = context?.working_set?.items ?? [];
  const notes = context?.runtime_notes ?? [];
  const artifacts = context?.artifact_context?.summaries ?? [];
  const memory = context?.workspace_memory ?? [];
  const repositoryIndex = context?.repository_index ?? null;
  const repositoryIndexItems = repositoryIndex?.items ?? [];

  if (context === null) {
    return (
      <Pane icon={TerminalSquare} title="Runtime context">
        <EmptyLine value="Runtime context is unavailable for this snapshot." />
      </Pane>
    );
  }

  return (
    <Pane icon={TerminalSquare} title="Runtime context">
      <div className="space-y-4">
        <section className="rounded-md border bg-card p-3">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-semibold tracking-normal">
              {context.repository_context.workspace_name}
            </h4>
            <Badge variant="outline">Repository</Badge>
          </div>
          <RuntimeTextList
            empty="No high-signal paths"
            label="High-signal paths"
            values={context.repository_context.high_signal_paths ?? []}
          />
          <RuntimeTextList
            empty="No project markers"
            label="Project markers"
            values={context.repository_context.project_markers ?? []}
          />
          <RuntimeTextList
            empty="No top-level entries"
            label="Top-level entries"
            values={[
              ...(context.repository_context.top_level_directories ?? []),
              ...(context.repository_context.top_level_files ?? []),
            ]}
          />
        </section>
        <section>
          <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Workspace memory influence
          </p>
          {memory.length === 0 ? (
            <EmptyLine value="No workspace memory items influenced this runtime context." />
          ) : (
            <DataList density="compact">
              {memory.map((item) => (
                <DataListItem key={item.memory_id}>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <DataListLabel>{item.summary}</DataListLabel>
                      <DataListMeta>{item.content}</DataListMeta>
                    </div>
                    <Badge variant={item.redacted ? "warning" : "success"}>{item.kind}</Badge>
                  </div>
                  <p className="mt-2 break-all text-xs text-muted-foreground">
                    {item.provenance.source_type}
                    {item.provenance.session_id
                      ? ` ${item.provenance.session_id}#${item.provenance.source_sequence ?? 0}`
                      : ""}
                    {" · "}
                    {item.use_count} use{item.use_count === 1 ? "" : "s"}
                  </p>
                </DataListItem>
              ))}
            </DataList>
          )}
        </section>
        <section>
          <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Repository index influence
          </p>
          {repositoryIndex === null ? (
            <EmptyLine value="Repository index context was not available for this snapshot." />
          ) : repositoryIndexItems.length === 0 ? (
            <EmptyLine
              value={
                repositoryIndex.detail ??
                "No repository index items were selected for this runtime context."
              }
            />
          ) : (
            <DataList density="compact">
              {repositoryIndexItems.map((item) => (
                <DataListItem key={item.entry_id}>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <DataListLabel>{item.name}</DataListLabel>
                      <DataListMeta>{item.summary ?? item.path ?? item.symbol}</DataListMeta>
                    </div>
                    <Badge variant="outline">{item.kind}</Badge>
                  </div>
                  <p className="mt-2 break-all text-xs text-muted-foreground">
                    {item.source_type ?? "source"} · {item.path ?? item.symbol ?? item.entry_id}
                  </p>
                </DataListItem>
              ))}
            </DataList>
          )}
          {repositoryIndex !== null ? (
            <p className="mt-2 text-xs text-muted-foreground">
              {repositoryIndex.status} · {repositoryIndex.entry_count} indexed entries ·{" "}
              {repositoryIndex.context_bytes} context bytes
            </p>
          ) : null}
        </section>
        <section>
          <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Working set
          </p>
          {workingSet.length === 0 ? (
            <EmptyLine value="No working-set items are retained in this snapshot." />
          ) : (
            <DataList density="compact">
              {workingSet.map((item) => (
                <DataListItem key={`${item.subject_kind}:${item.subject}`}>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <DataListLabel>{item.subject}</DataListLabel>
                      <DataListMeta>{item.summary}</DataListMeta>
                    </div>
                    <Badge variant={item.inherited ? "info" : "success"}>
                      {item.inherited ? "inherited" : "current"}
                    </Badge>
                  </div>
                  <p className="mt-2 break-all text-xs text-muted-foreground">
                    {item.signal_types?.join(", ") || "unknown signal"} ·{" "}
                    {item.reasons?.join(", ") || "no recorded reason"}
                  </p>
                </DataListItem>
              ))}
            </DataList>
          )}
        </section>
        <RuntimeNotes notes={notes} />
        <ArtifactProvenance artifacts={artifacts} />
      </div>
    </Pane>
  );
}

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

export function EvidencePane({
  data,
  eventPage,
  onLoadMoreEvents,
  stream,
}: {
  data: DashboardState;
  eventPage?: DetailPageStatus;
  onLoadMoreEvents?: () => void;
  stream: SessionStreamState;
}) {
  const recentLiveOutput = data.liveOutput.slice(-6);
  const recentEvents = data.eventLog.slice(-8);
  const projection = data.projectionHealth;

  return (
    <Pane icon={ScrollText} title="Event evidence">
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2" aria-label="Evidence overview">
          <Badge variant={stream.status === "live" ? "success" : "warning"}>
            stream {stream.status}
          </Badge>
          <Badge variant="outline">last sequence {stream.lastSequence}</Badge>
          <Badge variant={projection?.degraded ? "warning" : "success"}>
            projection {projection?.state ?? "unknown"}
          </Badge>
          <Badge variant="outline">{recentEvents.length} recent events</Badge>
        </div>
        <WhyThisActionEvidence data={data} />
        <EvidenceDetails title="Stream state">
          <DataList density="compact">
            <DataListItem>
              <DataListLabel>{stream.status}</DataListLabel>
              <DataListMeta>
                last sequence {stream.lastSequence} · retries {stream.retryCount}
              </DataListMeta>
              {stream.error !== null ? (
                <p className="mt-2 break-words text-xs text-muted-foreground">{stream.error}</p>
              ) : null}
            </DataListItem>
          </DataList>
        </EvidenceDetails>
        <EvidenceList
          title="Live output tail"
          empty="No live output chunks are attached to this snapshot."
        >
          {recentLiveOutput.map((entry, index) => (
            <DataListItem key={`${entry.tool_call_id}:${index}`}>
              <DataListLabel>
                {entry.stream} · {entry.tool_call_id}
              </DataListLabel>
              <DataListMeta>{entry.chunk}</DataListMeta>
              <p className="mt-2 break-all text-xs text-muted-foreground">turn {entry.turn_id}</p>
            </DataListItem>
          ))}
        </EvidenceList>
        <ProjectionDetails projection={projection} />
        <AutonomyTimelineMarkers events={recentEvents} />
        <EvidenceList title="Event log" empty="No event log entries are attached to this snapshot.">
          {recentEvents.map((event) => (
            <DataListItem key={`${event.event_type}:${event.sequence}`}>
              <DataListLabel>{event.event_type}</DataListLabel>
              <DataListMeta>sequence {event.sequence}</DataListMeta>
            </DataListItem>
          ))}
          <LoadMoreDetail label="events" onLoadMore={onLoadMoreEvents} page={eventPage} />
        </EvidenceList>
        <EvidenceList
          title="Raw metric details"
          empty="No raw metric rows are attached to this snapshot."
        >
          {data.turnMetrics.slice(0, DETAIL_RENDER_WINDOW).map((metric) => (
            <DataListItem key={metric.turn_id}>
              <DataListLabel>{metric.turn_id}</DataListLabel>
              <DataListMeta>
                model {formatDuration(metric.model_duration_ms_total)} · tool{" "}
                {formatDuration(metric.tool_duration_ms_total)}
              </DataListMeta>
            </DataListItem>
          ))}
        </EvidenceList>
      </div>
    </Pane>
  );
}

function WhyThisActionEvidence({ data }: { data: DashboardState }) {
  const cues = buildWhyThisActionCues(data);
  return (
    <EvidenceDetails title="Why this action">
      <DataList density="compact">
        {cues.map((cue) => (
          <DataListItem key={cue.label}>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <DataListLabel>{cue.label}</DataListLabel>
                <DataListMeta>{cue.value}</DataListMeta>
              </div>
              <Badge variant={cue.variant}>{cue.confidence}</Badge>
            </div>
          </DataListItem>
        ))}
      </DataList>
    </EvidenceDetails>
  );
}

function AutonomyTimelineMarkers({ events }: { events: DashboardState["eventLog"] }) {
  const markers = events
    .map((event) => ({ ...event, marker: autonomyTimelineMarker(event.event_type) }))
    .filter((event) => event.marker !== null);
  return (
    <EvidenceList
      title="Autonomy timeline markers"
      empty="No autonomous decision or human intervention markers are in the loaded event window."
    >
      {markers.map((event) => (
        <DataListItem key={`${event.event_type}:${event.sequence}`}>
          <DataListLabel>{event.marker}</DataListLabel>
          <DataListMeta>
            {event.event_type} at sequence {event.sequence}
          </DataListMeta>
        </DataListItem>
      ))}
    </EvidenceList>
  );
}

function buildWhyThisActionCues(data: DashboardState) {
  const runtimeContext = data.runtimeContext;
  const memoryCount = runtimeContext?.workspace_memory?.length ?? 0;
  const indexCount = runtimeContext?.repository_index?.items?.length ?? 0;
  const verificationFailures = data.turnMetrics.reduce(
    (total, metric) => total + metric.failed_tool_call_count,
    0,
  );
  return [
    {
      confidence: data.currentTurnPolicySummary === null ? "missing" : "direct",
      label: "Policy",
      value:
        data.currentTurnPolicySummary === null
          ? "No current-turn policy summary is retained for this snapshot."
          : `${data.currentTurnPolicySummary.total_decisions} decisions; ${data.currentTurnPolicySummary.approve_count} approvals; ${data.currentTurnPolicySummary.blocked_count} blocked.`,
      variant: data.currentTurnPolicySummary === null ? ("warning" as const) : ("info" as const),
    },
    {
      confidence: data.budgetPosture === null ? "missing" : "direct",
      label: "Budget",
      value:
        data.budgetPosture === null
          ? "No autonomy budget posture is retained for this snapshot."
          : `${data.budgetPosture.last_decision} at sequence ${data.budgetPosture.last_sequence}${data.budgetPosture.last_detail ? `; ${data.budgetPosture.last_detail}` : ""}`,
      variant: data.budgetPosture === null ? ("warning" as const) : ("info" as const),
    },
    {
      confidence: memoryCount === 0 && indexCount === 0 ? "missing" : "direct",
      label: "Memory and index",
      value:
        memoryCount === 0 && indexCount === 0
          ? "No workspace memory or repository index context is retained for this turn."
          : `${memoryCount} memory item${memoryCount === 1 ? "" : "s"} and ${indexCount} index item${indexCount === 1 ? "" : "s"} influenced context.`,
      variant: memoryCount === 0 && indexCount === 0 ? ("warning" as const) : ("success" as const),
    },
    {
      confidence: data.turnMetrics.length === 0 ? "missing" : "direct",
      label: "Verification",
      value:
        data.turnMetrics.length === 0
          ? "No turn metrics are loaded to explain verification or tool failures."
          : `${verificationFailures} failed tool call${verificationFailures === 1 ? "" : "s"} across ${data.turnMetrics.length} loaded turn metric row${data.turnMetrics.length === 1 ? "" : "s"}.`,
      variant: verificationFailures > 0 ? ("warning" as const) : ("success" as const),
    },
    {
      confidence: providerEvidenceCount(data) === 0 ? "missing" : "advisory",
      label: "Provider readiness",
      value:
        providerEvidenceCount(data) === 0
          ? "No provider readiness artifact is retained; treat provider status as unknown."
          : `${providerEvidenceCount(data)} advisory provider artifact${providerEvidenceCount(data) === 1 ? "" : "s"} retained.`,
      variant: providerEvidenceCount(data) === 0 ? ("warning" as const) : ("info" as const),
    },
  ];
}

function providerEvidenceCount(data: DashboardState): number {
  return (data.runtimeContext?.artifact_context?.summaries ?? []).filter((artifact) => {
    const searchable = [
      artifact.artifact_kind,
      artifact.source_tool_name,
      artifact.summary,
      artifact.summary_kind,
    ]
      .join(" ")
      .toLowerCase();
    return searchable.includes("provider");
  }).length;
}

function autonomyTimelineMarker(eventType: string): string | null {
  if (eventType.startsWith("Task") || eventType.startsWith("BranchCandidate")) {
    return "autonomous decision";
  }
  if (
    eventType === "BudgetDecisionRecorded" ||
    eventType === "BudgetExhausted" ||
    eventType === "BackgroundJobCreated"
  ) {
    return "runtime autonomy";
  }
  if (
    eventType.includes("Approval") ||
    eventType.includes("Question") ||
    eventType.includes("Selected") ||
    eventType.includes("Rejected") ||
    eventType.includes("NeedsReview")
  ) {
    return "human intervention";
  }
  return null;
}

function LoadMoreDetail({
  label,
  onLoadMore,
  page,
}: {
  label: string;
  onLoadMore?: () => void;
  page?: DetailPageStatus;
}) {
  if (page === undefined || !page.hasMore) {
    return null;
  }
  return (
    <div className="mt-3 flex flex-wrap items-center gap-3">
      <Button
        disabled={page.state === "loading"}
        onClick={onLoadMore}
        size="sm"
        type="button"
        variant="outline"
      >
        <ChevronDown className="h-4 w-4" aria-hidden="true" />
        {page.state === "loading" ? "Loading" : `Load more ${label}`}
      </Button>
      {page.error !== null ? (
        <p className="text-xs text-destructive">{page.error}</p>
      ) : (
        <p className="text-xs text-muted-foreground">Next cursor {page.nextCursor}</p>
      )}
    </div>
  );
}

function RuntimeTextList({
  empty,
  label,
  values,
}: {
  empty: string;
  label: string;
  values: string[];
}) {
  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 break-all text-sm text-muted-foreground">
        {values.length > 0 ? values.join(", ") : empty}
      </p>
    </div>
  );
}

function RuntimeNotes({
  notes,
}: {
  notes: NonNullable<NonNullable<DashboardState["runtimeContext"]>["runtime_notes"]>;
}) {
  return (
    <section>
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        Runtime notes
      </p>
      {notes.length === 0 ? (
        <EmptyLine value="No runtime notes are retained in this snapshot." />
      ) : (
        <DataList density="compact">
          {notes.map((note, index) => (
            <DataListItem key={`${note.category}:${index}`}>
              <div className="flex flex-wrap items-center gap-2">
                <DataListLabel>{note.category}</DataListLabel>
                <Badge variant={note.inherited ? "info" : "outline"}>
                  {note.inherited ? "inherited" : "current"}
                </Badge>
              </div>
              <DataListMeta>{note.message}</DataListMeta>
              {note.source_session_id !== undefined && note.source_session_id !== null ? (
                <p className="mt-2 break-all text-xs text-muted-foreground">
                  source {note.source_session_id}
                </p>
              ) : null}
            </DataListItem>
          ))}
        </DataList>
      )}
    </section>
  );
}

function ArtifactProvenance({
  artifacts,
}: {
  artifacts: NonNullable<
    NonNullable<NonNullable<DashboardState["runtimeContext"]>["artifact_context"]>["summaries"]
  >;
}) {
  return (
    <section>
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        Artifact provenance
      </p>
      {artifacts.length === 0 ? (
        <EmptyLine value="No artifact provenance is attached to this runtime context." />
      ) : (
        <DataList density="compact">
          {artifacts.map((artifact) => (
            <DataListItem key={`${artifact.artifact_kind}:${artifact.artifact_path}`}>
              <DataListLabel>{artifact.summary_kind}</DataListLabel>
              <DataListMeta>{artifact.summary}</DataListMeta>
              <p className="mt-2 break-all text-xs text-muted-foreground">
                {artifact.source_tool_name} · {artifact.provenance_class} · {artifact.freshness} ·{" "}
                {artifact.artifact_path}
              </p>
            </DataListItem>
          ))}
        </DataList>
      )}
    </section>
  );
}

function ProjectionDetails({ projection }: { projection: DashboardState["projectionHealth"] }) {
  return (
    <EvidenceDetails title="Projection details">
      {projection === null ? (
        <EmptyLine value="No projection health details are available." />
      ) : (
        <DataList density="compact">
          <DataListItem>
            <DataListLabel>{projection.state}</DataListLabel>
            <DataListMeta>{projection.detail ?? "Projection is current."}</DataListMeta>
            <p className="mt-2 text-xs text-muted-foreground">
              canonical {projection.canonical_last_sequence} · projected{" "}
              {projection.projected_last_sequence} · lag {projection.lag}
              {projection.estimated_rebuild_event_count > 0
                ? ` · rebuild scope ${projection.estimated_rebuild_event_count} events`
                : ""}
              {projection.projected_progress_ratio !== null
                ? ` · progress ${Math.round(projection.projected_progress_ratio * 100)}%`
                : ""}
            </p>
          </DataListItem>
        </DataList>
      )}
    </EvidenceDetails>
  );
}

function EvidenceList({
  children,
  empty,
  title,
}: {
  children: ReactNode;
  empty: string;
  title: string;
}) {
  const childrenArray = Array.isArray(children) ? children : [children];
  return (
    <EvidenceDetails title={title}>
      {childrenArray.length === 0 ? (
        <EmptyLine value={empty} />
      ) : (
        <DataList density="compact">{children}</DataList>
      )}
    </EvidenceDetails>
  );
}

function EvidenceDetails({ children, title }: { children: ReactNode; title: string }) {
  return (
    <details className="rounded-md border bg-card p-3" open>
      <summary className="cursor-pointer text-sm font-medium">{title}</summary>
      <div className="mt-3">{children}</div>
    </details>
  );
}
