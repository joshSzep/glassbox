import type { ReactNode } from "react";
import { ScrollText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import { formatDuration } from "@/components/console/session-inspector/format";
import { LoadMoreDetail } from "@/components/console/session-inspector/panes/diagnostics-shared";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState } from "@/state/session-state";
import type { DetailPageStatus } from "@/stores/dashboard-stores";

const DETAIL_RENDER_WINDOW = 80;

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
