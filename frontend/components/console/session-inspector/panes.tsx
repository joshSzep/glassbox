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
import type { DashboardState, TranscriptMessage } from "@/state/session-state";

export function TranscriptPane({ messages }: { messages: TranscriptMessage[] }) {
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

export function TimelinePane({ data }: { data: DashboardState }) {
  return (
    <Pane icon={History} title="Timeline">
      <DataList density="compact">
        {data.currentTurn !== null ? (
          <DataListItem>
            <DataListLabel>Current turn {data.currentTurn.turn_id}</DataListLabel>
            <DataListMeta>{data.currentTurn.status}</DataListMeta>
          </DataListItem>
        ) : null}
        {data.activeToolCalls.map((tool) => (
          <DataListItem key={tool.tool_call_id}>
            <DataListLabel>{tool.tool_name}</DataListLabel>
            <DataListMeta>{tool.summary ?? tool.status}</DataListMeta>
          </DataListItem>
        ))}
        {data.branchableTurns.map((turn) => (
          <DataListItem key={turn.turn_id}>
            <DataListLabel>{turn.label}</DataListLabel>
            <DataListMeta>
              sequence {turn.sequence} · {formatTime(turn.created_at)}
            </DataListMeta>
          </DataListItem>
        ))}
        {data.eventLog.slice(-5).map((event) => (
          <DataListItem key={`${event.event_type}:${event.sequence}`}>
            <DataListLabel>{event.event_type}</DataListLabel>
            <DataListMeta>sequence {event.sequence}</DataListMeta>
          </DataListItem>
        ))}
        {data.currentTurn === null &&
        data.activeToolCalls.length === 0 &&
        data.branchableTurns.length === 0 &&
        data.eventLog.length === 0 ? (
          <DataListItem>
            <DataListMeta>No timeline events are available.</DataListMeta>
          </DataListItem>
        ) : null}
      </DataList>
    </Pane>
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
