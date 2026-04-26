import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertCircle,
  GitBranch,
  ListChecks,
  MessageSquareText,
  RadioTower,
  ScrollText,
  TerminalSquare,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import { buildAppRoute, type AppQueue, type InspectorTab } from "@/routing/app-route";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState, TranscriptMessage } from "@/state/session-state";
import type { LoadState } from "@/stores/dashboard-stores";

const inspectorTabs: { label: string; value: InspectorTab }[] = [
  { label: "Overview", value: "overview" },
  { label: "Transcript", value: "transcript" },
  { label: "Timeline", value: "timeline" },
  { label: "Actions", value: "actions" },
  { label: "Runtime", value: "runtime" },
  { label: "Metrics", value: "metrics" },
  { label: "Events", value: "events" },
];

export type SessionInspectorProps = {
  activeTab: InspectorTab;
  data: DashboardState;
  error: string | null;
  loadState: LoadState;
  queue: AppQueue;
  stream: SessionStreamState;
};

export function SessionInspector({
  activeTab,
  data,
  error,
  loadState,
  queue,
  stream,
}: SessionInspectorProps) {
  if (data.selectedSessionId !== null && data.sessionId === null) {
    return (
      <InspectorFrame>
        <StateBlock
          icon={loadState === "failed" ? AlertCircle : RadioTower}
          title={loadState === "failed" ? "Session unavailable" : "Loading selected session"}
          value={error ?? data.selectedSessionId}
          variant={loadState === "failed" ? "destructive" : "info"}
        />
      </InspectorFrame>
    );
  }

  if (data.sessionId === null) {
    return (
      <InspectorFrame>
        <StateBlock
          icon={MessageSquareText}
          title="No session selected"
          value="Choose a queue row to inspect transcript, timeline, runtime context, and actions."
          variant="muted"
        />
      </InspectorFrame>
    );
  }

  return (
    <InspectorFrame>
      <SessionHeader data={data} stream={stream} />
      <InspectorTabs activeTab={activeTab} data={data} queue={queue} />
      <div className="grid gap-4 xl:grid-cols-2">
        <TranscriptPane messages={data.transcript} />
        <TimelinePane data={data} />
        <ActionPane data={data} />
        <RuntimePane data={data} />
        <MetricsPane data={data} />
        <EvidencePane data={data} stream={stream} />
      </div>
    </InspectorFrame>
  );
}

function InspectorFrame({ children }: { children: React.ReactNode }) {
  return (
    <aside
      className="min-w-0 rounded-lg border bg-card text-card-foreground shadow-sm"
      aria-label="Selected session inspector"
    >
      {children}
    </aside>
  );
}

function SessionHeader({ data, stream }: { data: DashboardState; stream: SessionStreamState }) {
  return (
    <header className="border-b p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Selected session
          </p>
          <h2 className="mt-1 break-all text-lg font-semibold tracking-normal">{data.sessionId}</h2>
          <p className="mt-1 break-all text-sm text-muted-foreground">
            {data.cwd ?? "workspace unknown"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={data.status === "failed" ? "destructive" : "outline"}>
            {data.status}
          </Badge>
          <Badge variant={stream.status === "live" ? "success" : "muted"}>{stream.status}</Badge>
          <ProjectionBadge
            state={data.projectionHealth?.state ?? "unknown"}
            degraded={Boolean(data.projectionHealth?.degraded)}
          />
        </div>
      </div>
      <Separator className="my-3" />
      <div className="grid gap-2 text-sm sm:grid-cols-2 xl:grid-cols-4">
        <HeaderFact label="Model" value={data.modelName ?? "unknown"} />
        <HeaderFact label="Last sequence" value={String(data.lastSequence)} />
        <HeaderFact label="Lineage" value={lineageLabel(data)} />
        <HeaderFact label="Next action" value={nextActionLabel(data)} />
      </div>
    </header>
  );
}

function HeaderFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 break-words text-sm font-medium">{value}</p>
    </div>
  );
}

function InspectorTabs({
  activeTab,
  data,
  queue,
}: {
  activeTab: InspectorTab;
  data: DashboardState;
  queue: AppQueue;
}) {
  return (
    <div className="overflow-x-auto border-b p-3">
      <Tabs value={activeTab}>
        <TabsList aria-label="Inspector tabs">
          {inspectorTabs.map((tab) => (
            <TabsTrigger asChild key={tab.value} value={tab.value}>
              <a
                href={buildAppRoute({
                  compareSessionId: data.compareSessionId,
                  queue,
                  selectedSessionId: data.sessionId,
                  tab: tab.value,
                })}
              >
                {tab.label}
              </a>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
    </div>
  );
}

function TranscriptPane({ messages }: { messages: TranscriptMessage[] }) {
  return (
    <Pane icon={MessageSquareText} title="Transcript">
      {messages.length === 0 ? (
        <EmptyLine value="No transcript messages are available." />
      ) : (
        <div className="space-y-3">
          {messages.map((message) => (
            <article className="rounded-md border bg-background p-3" key={message.message_id}>
              <div className="flex items-center justify-between gap-3">
                <Badge variant={message.role === "user" ? "info" : "outline"}>{message.role}</Badge>
                <span className="text-xs text-muted-foreground">
                  {formatTime(message.created_at)}
                </span>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm">{formatMessage(message)}</p>
            </article>
          ))}
        </div>
      )}
    </Pane>
  );
}

function TimelinePane({ data }: { data: DashboardState }) {
  return (
    <Pane icon={GitBranch} title="Turn timeline">
      <DataList density="compact">
        {data.currentTurn !== null ? (
          <DataListItem>
            <DataListLabel>Current turn {data.currentTurn.turn_id}</DataListLabel>
            <DataListMeta>{data.currentTurn.status}</DataListMeta>
          </DataListItem>
        ) : null}
        {data.branchableTurns.map((turn) => (
          <DataListItem key={turn.turn_id}>
            <DataListLabel>{turn.label}</DataListLabel>
            <DataListMeta>
              sequence {turn.sequence} · {formatTime(turn.created_at)}
            </DataListMeta>
          </DataListItem>
        ))}
        {data.childSessions.map((child) => (
          <DataListItem key={child.session_id}>
            <DataListLabel>{child.branch_label ?? child.session_id}</DataListLabel>
            <DataListMeta>{child.latest_message_summary ?? child.status}</DataListMeta>
          </DataListItem>
        ))}
        {data.currentTurn === null &&
        data.branchableTurns.length === 0 &&
        data.childSessions.length === 0 ? (
          <DataListItem>
            <DataListMeta>No turn or lineage entries are available.</DataListMeta>
          </DataListItem>
        ) : null}
      </DataList>
    </Pane>
  );
}

function ActionPane({ data }: { data: DashboardState }) {
  return (
    <Pane icon={ListChecks} title="Actions">
      <DataList density="compact">
        {data.pendingApprovals.map((approval) => (
          <DataListItem key={approval.approval_id}>
            <DataListLabel>{approval.subject}</DataListLabel>
            <DataListMeta>{approval.reason}</DataListMeta>
          </DataListItem>
        ))}
        {data.pendingQuestionId !== null ? (
          <DataListItem>
            <DataListLabel>Question {data.pendingQuestionId}</DataListLabel>
            <DataListMeta>{data.pendingQuestionText ?? "Awaiting operator answer"}</DataListMeta>
          </DataListItem>
        ) : null}
        {data.activeToolCalls.map((tool) => (
          <DataListItem key={tool.tool_call_id}>
            <DataListLabel>{tool.tool_name}</DataListLabel>
            <DataListMeta>{tool.summary ?? tool.status}</DataListMeta>
          </DataListItem>
        ))}
        {data.pendingApprovals.length === 0 &&
        data.pendingQuestionId === null &&
        data.activeToolCalls.length === 0 ? (
          <DataListItem>
            <DataListMeta>No active approvals, questions, or tool calls.</DataListMeta>
          </DataListItem>
        ) : null}
      </DataList>
    </Pane>
  );
}

function RuntimePane({ data }: { data: DashboardState }) {
  const context = data.runtimeContext;
  const workingSet = context?.working_set?.items ?? [];
  const notes = context?.runtime_notes ?? [];
  return (
    <Pane icon={TerminalSquare} title="Runtime context">
      <DataList density="compact">
        <DataListItem>
          <DataListLabel>
            {context?.repository_context.workspace_name ?? "Repository"}
          </DataListLabel>
          <DataListMeta>
            {(context?.repository_context.high_signal_paths ?? []).join(", ") ||
              "No high-signal paths"}
          </DataListMeta>
        </DataListItem>
        {workingSet.map((item) => (
          <DataListItem key={`${item.subject_kind}:${item.subject}`}>
            <DataListLabel>{item.subject}</DataListLabel>
            <DataListMeta>{item.summary}</DataListMeta>
          </DataListItem>
        ))}
        {notes.map((note, index) => (
          <DataListItem key={`${note.category}:${index}`}>
            <DataListLabel>{note.category}</DataListLabel>
            <DataListMeta>{note.message}</DataListMeta>
          </DataListItem>
        ))}
      </DataList>
    </Pane>
  );
}

function MetricsPane({ data }: { data: DashboardState }) {
  return (
    <Pane icon={Activity} title="Metrics">
      {data.turnMetrics.length === 0 ? (
        <EmptyLine value="No turn metrics are available." />
      ) : (
        <DataList density="compact">
          {data.turnMetrics.map((metric) => (
            <DataListItem key={metric.turn_id}>
              <DataListLabel>{metric.turn_id}</DataListLabel>
              <DataListMeta>
                {metric.model_call_count} model · {metric.tool_call_count} tools ·{" "}
                {formatDuration(metric.turn_duration_ms)}
              </DataListMeta>
            </DataListItem>
          ))}
        </DataList>
      )}
    </Pane>
  );
}

function EvidencePane({ data, stream }: { data: DashboardState; stream: SessionStreamState }) {
  return (
    <Pane icon={ScrollText} title="Event evidence">
      <DataList density="compact">
        <DataListItem>
          <DataListLabel>Stream</DataListLabel>
          <DataListMeta>
            {stream.status} · last sequence {stream.lastSequence}
          </DataListMeta>
        </DataListItem>
        {data.liveOutput.map((entry, index) => (
          <DataListItem key={`${entry.tool_call_id}:${index}`}>
            <DataListLabel>{entry.stream}</DataListLabel>
            <DataListMeta>{entry.chunk}</DataListMeta>
          </DataListItem>
        ))}
        {data.eventLog.slice(-6).map((event) => (
          <DataListItem key={`${event.event_type}:${event.sequence}`}>
            <DataListLabel>{event.event_type}</DataListLabel>
            <DataListMeta>sequence {event.sequence}</DataListMeta>
          </DataListItem>
        ))}
      </DataList>
    </Pane>
  );
}

function Pane({
  children,
  icon: Icon,
  title,
}: {
  children: ReactNode;
  icon: LucideIcon;
  title: string;
}) {
  return (
    <section className="rounded-lg border bg-background p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-muted-foreground">
        <Icon className={operatorIconSizeClass} aria-hidden="true" />
        {title}
      </h3>
      {children}
    </section>
  );
}

function StateBlock({
  icon: Icon,
  title,
  value,
  variant,
}: {
  icon: LucideIcon;
  title: string;
  value: string;
  variant: "destructive" | "info" | "muted";
}) {
  return (
    <div className="grid min-h-80 place-items-center p-8 text-center">
      <div className="max-w-sm">
        <Badge variant={variant}>
          <Icon className={operatorIconSizeClass} aria-hidden="true" />
          {title}
        </Badge>
        <p className="mt-4 text-sm text-muted-foreground">{value}</p>
      </div>
    </div>
  );
}

function EmptyLine({ value }: { value: string }) {
  return <p className="text-sm text-muted-foreground">{value}</p>;
}

function ProjectionBadge({ degraded, state }: { degraded: boolean; state: string }) {
  return (
    <Badge variant={degraded || state !== "ok" ? "warning" : "success"}>projection {state}</Badge>
  );
}

function lineageLabel(data: DashboardState): string {
  if (data.parentSessionId !== null) {
    return `parent ${data.parentSessionId}`;
  }
  if (data.childSessions.length > 0) {
    return `${data.childSessions.length} child sessions`;
  }
  return data.branchLabel ?? "root session";
}

function nextActionLabel(data: DashboardState): string {
  if (data.pendingApprovalId !== null) {
    return `approval ${data.pendingApprovalId}`;
  }
  if (data.pendingQuestionId !== null) {
    return `question ${data.pendingQuestionId}`;
  }
  if (data.currentTurn !== null) {
    return data.currentTurn.status;
  }
  return data.canFork ? "fork available" : "inspect";
}

function formatMessage(message: TranscriptMessage): string {
  return message.parts.map((part) => part.text).join("\n");
}

function formatDuration(value: number | null): string {
  if (value === null) {
    return "duration unknown";
  }
  if (value < 1000) {
    return `${value}ms`;
  }
  return `${(value / 1000).toFixed(1)}s`;
}

function formatTime(value: string | null): string {
  if (value === null) {
    return "time unknown";
  }
  return value.replace("T", " ").replace("Z", " UTC");
}
