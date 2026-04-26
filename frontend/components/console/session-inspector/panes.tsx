import {
  Activity,
  GitBranch,
  History,
  ListChecks,
  MessageSquareText,
  ScrollText,
  TerminalSquare,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import {
  formatDuration,
  formatMessage,
  formatTime,
} from "@/components/console/session-inspector/format";
import type { SessionStreamState } from "@/api/sse";
import {
  buildSessionNarrative,
  type DashboardState,
  type SessionNarrativeItem,
  type SessionNarrativeTurn,
} from "@/state/session-state";

export function TranscriptPane({ data }: { data: DashboardState }) {
  const narrative = buildSessionNarrative(data);
  const latestTurn = narrative.turns.at(-1) ?? null;
  const pendingTurn = narrative.turns.find((turn) =>
    turn.items.some((item) => item.kind === "approval" || item.kind === "question"),
  );
  const failedTurn = narrative.turns.find((turn) => turn.status === "failed");

  return (
    <Pane icon={MessageSquareText} title="Transcript">
      {narrative.turns.length === 0 ? (
        <EmptyLine value="No transcript narrative is available." />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2" aria-label="Transcript jumps">
            {latestTurn !== null ? <JumpLink label="Latest activity" turn={latestTurn} /> : null}
            {pendingTurn !== undefined ? (
              <JumpLink label="Pending action" turn={pendingTurn} />
            ) : null}
            {failedTurn !== undefined ? <JumpLink label="Failed turn" turn={failedTurn} /> : null}
          </div>
          <div className="space-y-4" aria-label="Session narrative turns">
            {narrative.turns.map((turn) => (
              <NarrativeTurnCard key={turn.id} turn={turn} />
            ))}
          </div>
        </div>
      )}
    </Pane>
  );
}

function JumpLink({ label, turn }: { label: string; turn: SessionNarrativeTurn }) {
  return (
    <Button asChild size="xs" type="button" variant="outline">
      <a href={`#${narrativeTurnDomId(turn)}`}>{label}</a>
    </Button>
  );
}

function NarrativeTurnCard({ turn }: { turn: SessionNarrativeTurn }) {
  return (
    <article
      aria-labelledby={`${narrativeTurnDomId(turn)}-title`}
      className="rounded-md border bg-background p-3"
      id={narrativeTurnDomId(turn)}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h4
            className="break-words text-sm font-semibold tracking-normal"
            id={`${narrativeTurnDomId(turn)}-title`}
          >
            {turn.title}
          </h4>
          <p className="mt-1 text-xs text-muted-foreground">
            {turn.turnId ?? "partial history"}
            {turn.sequence !== null ? ` · sequence ${turn.sequence}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={badgeForNarrativeStatus(turn.status)}>{turn.status}</Badge>
          {turn.isFallback ? <Badge variant="outline">partial metadata</Badge> : null}
        </div>
      </div>
      <div className="mt-3 space-y-2">
        {turn.items.map((item, index) => (
          <NarrativeItemRow item={item} key={`${item.kind}:${index}`} />
        ))}
      </div>
    </article>
  );
}

function NarrativeItemRow({ item }: { item: SessionNarrativeItem }) {
  switch (item.kind) {
    case "message":
      return (
        <div className="rounded-md border bg-card p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Badge variant={item.message.role === "user" ? "info" : "outline"}>
              {item.message.role}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {formatTime(item.message.created_at)}
            </span>
          </div>
          <p className="mt-2 whitespace-pre-wrap break-words text-sm">
            {formatMessage(item.message)}
          </p>
        </div>
      );
    case "tool-call":
      return (
        <NarrativeLine
          label={item.toolCall.tool_name}
          meta={item.toolCall.summary ?? item.toolCall.status}
        />
      );
    case "approval":
      return (
        <NarrativeLine label={`Approval: ${item.approval.subject}`} meta={item.approval.reason} />
      );
    case "question":
      return <NarrativeLine label="Question" meta={item.text ?? "Awaiting operator answer"} />;
    case "live-output":
      return <NarrativeLine label={`Live ${item.output.stream}`} meta={item.output.chunk} />;
    case "failure":
      return (
        <NarrativeLine
          label={item.retryable ? "Retryable failure" : "Failure"}
          meta={item.message}
          variant="destructive"
        />
      );
    case "metric":
      return (
        <NarrativeLine
          label="Turn metrics"
          meta={`${item.metric.model_call_count} model · ${item.metric.tool_call_count} tools · ${formatDuration(
            item.metric.turn_duration_ms,
          )}`}
        />
      );
    case "fork-boundary":
      return (
        <NarrativeLine
          label="Fork boundary"
          meta={`${item.turn.label} · sequence ${item.turn.sequence}`}
        />
      );
    case "event-evidence":
      return (
        <NarrativeLine label={item.event.event_type} meta={`sequence ${item.event.sequence}`} />
      );
  }
}

function NarrativeLine({
  label,
  meta,
  variant = "outline",
}: {
  label: string;
  meta: string;
  variant?: "destructive" | "info" | "outline" | "warning";
}) {
  return (
    <div className="rounded-md border bg-card p-3">
      <Badge className="justify-start" variant={variant}>
        {label}
      </Badge>
      <p className="mt-2 whitespace-pre-wrap break-words text-sm text-muted-foreground">{meta}</p>
    </div>
  );
}

function badgeForNarrativeStatus(status: SessionNarrativeTurn["status"]) {
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

function narrativeTurnDomId(turn: SessionNarrativeTurn): string {
  return `narrative-${turn.id.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

export function LineagePane({
  data,
  onClearCompare,
  onCompareSession,
  onOpenSession,
}: {
  data: DashboardState;
  onClearCompare?: () => void;
  onCompareSession?: (sessionId: string) => void;
  onOpenSession?: (sessionId: string) => void;
}) {
  return (
    <Pane icon={GitBranch} title="Lineage and turns">
      <DataList density="compact">
        {data.parentSessionId !== null ? (
          <DataListItem>
            <DataListLabel>Parent {data.parentSessionId}</DataListLabel>
            <DataListMeta>Persisted parent relationship</DataListMeta>
            <LineageActions
              onClearCompare={onClearCompare}
              onCompareSession={onCompareSession}
              onOpenSession={onOpenSession}
              sessionId={data.parentSessionId}
            />
          </DataListItem>
        ) : null}
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
            <LineageActions
              onClearCompare={onClearCompare}
              onCompareSession={onCompareSession}
              onOpenSession={onOpenSession}
              sessionId={child.session_id}
            />
          </DataListItem>
        ))}
        {data.currentTurn === null &&
        data.parentSessionId === null &&
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

function LineageActions({
  onClearCompare,
  onCompareSession,
  onOpenSession,
  sessionId,
}: {
  onClearCompare?: () => void;
  onCompareSession?: (sessionId: string) => void;
  onOpenSession?: (sessionId: string) => void;
  sessionId: string;
}) {
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      <Button
        onClick={() => onCompareSession?.(sessionId)}
        size="xs"
        type="button"
        variant="outline"
      >
        Compare
      </Button>
      <Button onClick={() => onOpenSession?.(sessionId)} size="xs" type="button" variant="ghost">
        Open
      </Button>
      <Button onClick={() => onClearCompare?.()} size="xs" type="button" variant="ghost">
        Clear compare
      </Button>
    </div>
  );
}

export function ComparePane({
  data,
  onClearCompare,
  onOpenSession,
}: {
  data: DashboardState;
  onClearCompare?: () => void;
  onOpenSession?: (sessionId: string) => void;
}) {
  const compare = data.compareSession;
  return (
    <Pane icon={GitBranch} title="Compare">
      {compare === null ? (
        <EmptyLine value="Select a parent or child session to compare persisted snapshots." />
      ) : (
        <div className="space-y-3">
          <div className="rounded-md border bg-card p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="break-all text-sm font-medium">{compare.sessionId}</p>
                <p className="text-xs text-muted-foreground">
                  {compare.branchLabel ?? "unlabeled branch"} · {compare.status}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => onOpenSession?.(compare.sessionId ?? "")}
                  size="xs"
                  type="button"
                  variant="outline"
                >
                  Open compared
                </Button>
                <Button onClick={() => onClearCompare?.()} size="xs" type="button" variant="ghost">
                  Clear
                </Button>
              </div>
            </div>
          </div>
          <DataList density="compact">
            <DataListItem>
              <DataListLabel>Transcript</DataListLabel>
              <DataListMeta>
                {data.transcript.length} current · {compare.transcript.length} compared ·{" "}
                {compare.transcript.length - data.transcript.length} delta
              </DataListMeta>
            </DataListItem>
            <DataListItem>
              <DataListLabel>Runtime context</DataListLabel>
              <DataListMeta>
                {(data.runtimeContext?.working_set?.items ?? []).length} current working-set ·{" "}
                {compare.runtimeContext?.working_set?.items?.length ?? 0} compared
              </DataListMeta>
            </DataListItem>
            <DataListItem>
              <DataListLabel>Turn summaries</DataListLabel>
              <DataListMeta>
                {data.turnMetrics.length} current metrics · {compare.turnMetrics.length} compared
                metrics
              </DataListMeta>
            </DataListItem>
            <DataListItem>
              <DataListLabel>Branch metadata</DataListLabel>
              <DataListMeta>
                parent {compare.parentSessionId ?? "none"} · forked sequence{" "}
                {compare.forkedFromSequence ?? "unknown"}
              </DataListMeta>
            </DataListItem>
          </DataList>
        </div>
      )}
    </Pane>
  );
}

export function ActionSummaryPane({ data }: { data: DashboardState }) {
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

export function TimelinePane({
  data,
  onOpenForkTurn,
}: {
  data: DashboardState;
  onOpenForkTurn?: (turnId: string | null) => void;
}) {
  const narrative = buildSessionNarrative(data);
  const activeTurn =
    narrative.turns.find((turn) => turn.turnId === data.currentTurn?.turn_id) ??
    narrative.turns.find((turn) => ["active", "running"].includes(turn.status));
  const pendingTurn = narrative.turns.find((turn) =>
    turn.items.some((item) => item.kind === "approval" || item.kind === "question"),
  );
  const failedTurn = narrative.turns.find((turn) => turn.status === "failed");
  const forkableTurn = narrative.turns.find((turn) =>
    turn.items.some((item) => item.kind === "fork-boundary"),
  );

  return (
    <Pane icon={History} title="Timeline">
      {narrative.turns.length === 0 ? (
        <EmptyLine value="No timeline events are available." />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2" aria-label="Timeline jumps">
            {activeTurn !== undefined ? <JumpLink label="Active turn" turn={activeTurn} /> : null}
            {pendingTurn !== undefined ? (
              <JumpLink label="Pending action" turn={pendingTurn} />
            ) : null}
            {failedTurn !== undefined ? <JumpLink label="Failed turn" turn={failedTurn} /> : null}
            {forkableTurn !== undefined ? (
              <JumpLink label="Fork boundary" turn={forkableTurn} />
            ) : null}
          </div>
          <div className="divide-y rounded-lg border bg-card" aria-label="Timeline turns">
            {narrative.turns.map((turn) => (
              <TimelineTurnRow key={turn.id} onOpenForkTurn={onOpenForkTurn} turn={turn} />
            ))}
          </div>
        </div>
      )}
    </Pane>
  );
}

function TimelineTurnRow({
  onOpenForkTurn,
  turn,
}: {
  onOpenForkTurn?: (turnId: string | null) => void;
  turn: SessionNarrativeTurn;
}) {
  const metric = turn.items.find((item) => item.kind === "metric");
  const forkBoundary = turn.items.find((item) => item.kind === "fork-boundary");
  const pendingCount = turn.items.filter(
    (item) => item.kind === "approval" || item.kind === "question",
  ).length;
  const toolCount = turn.items.filter((item) => item.kind === "tool-call").length;
  const liveOutputCount = turn.items.filter((item) => item.kind === "live-output").length;
  const failure = turn.items.find((item) => item.kind === "failure");

  return (
    <article
      className="grid gap-3 p-3 sm:grid-cols-[minmax(0,1fr)_auto]"
      id={narrativeTurnDomId(turn)}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h4 className="break-words text-sm font-semibold tracking-normal">{turn.title}</h4>
          <Badge variant={badgeForNarrativeStatus(turn.status)}>{turn.status}</Badge>
          {turn.isFallback ? <Badge variant="outline">partial</Badge> : null}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {turn.turnId ?? "unassigned evidence"}
          {turn.sequence !== null ? ` · sequence ${turn.sequence}` : ""}
        </p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
          {metric?.kind === "metric" ? (
            <span>
              {metric.metric.model_call_count} model · {metric.metric.tool_call_count} tools ·{" "}
              {formatDuration(metric.metric.turn_duration_ms)}
            </span>
          ) : null}
          {pendingCount > 0 ? <span>{pendingCount} pending intervention</span> : null}
          {toolCount > 0 ? <span>{toolCount} active tool</span> : null}
          {liveOutputCount > 0 ? <span>{liveOutputCount} live output</span> : null}
          {failure?.kind === "failure" ? <span>{failure.message}</span> : null}
        </div>
      </div>
      {forkBoundary?.kind === "fork-boundary" ? (
        <div className="flex items-start sm:justify-end">
          <Button
            onClick={() => onOpenForkTurn?.(forkBoundary.turn.turn_id)}
            size="xs"
            type="button"
            variant="outline"
          >
            Open fork flow for {forkBoundary.turn.label}
          </Button>
        </div>
      ) : null}
    </article>
  );
}

export function RuntimePane({ data }: { data: DashboardState }) {
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

export function MetricsPane({ data }: { data: DashboardState }) {
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

export function EvidencePane({
  data,
  stream,
}: {
  data: DashboardState;
  stream: SessionStreamState;
}) {
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
