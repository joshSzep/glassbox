import type { ReactNode } from "react";
import { Activity, ScrollText, TerminalSquare } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import { formatDuration } from "@/components/console/session-inspector/format";
import { MetricSummary, summarizeTurnMetrics } from "./shared";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState } from "@/state/session-state";

export function RuntimePane({ data }: { data: DashboardState }) {
  const context = data.runtimeContext;
  const workingSet = context?.working_set?.items ?? [];
  const notes = context?.runtime_notes ?? [];
  const artifacts = context?.artifact_context?.summaries ?? [];

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

export function MetricsPane({ data }: { data: DashboardState }) {
  const totals = summarizeTurnMetrics(data.turnMetrics);

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
          <details className="rounded-md border bg-card p-3" open>
            <summary className="cursor-pointer text-sm font-medium">Raw turn metrics</summary>
            <DataList className="mt-3" density="compact">
              {data.turnMetrics.map((metric) => (
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
          </details>
        </div>
      )}
    </Pane>
  );
}

export function EvidencePane({
  data,
  stream,
}: {
  data: DashboardState;
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
        <EvidenceList title="Event log" empty="No event log entries are attached to this snapshot.">
          {recentEvents.map((event) => (
            <DataListItem key={`${event.event_type}:${event.sequence}`}>
              <DataListLabel>{event.event_type}</DataListLabel>
              <DataListMeta>sequence {event.sequence}</DataListMeta>
            </DataListItem>
          ))}
        </EvidenceList>
        <EvidenceList
          title="Raw metric details"
          empty="No raw metric rows are attached to this snapshot."
        >
          {data.turnMetrics.map((metric) => (
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
