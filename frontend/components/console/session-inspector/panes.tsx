import type { ReactNode } from "react";
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
  onOpenForkTurn,
  onOpenSession,
}: {
  data: DashboardState;
  onClearCompare?: () => void;
  onCompareSession?: (sessionId: string) => void;
  onOpenForkTurn?: (turnId: string | null) => void;
  onOpenSession?: (sessionId: string) => void;
}) {
  const hasLineage =
    data.parentSessionId !== null ||
    data.childSessions.length > 0 ||
    data.branchableTurns.length > 0 ||
    data.currentTurn !== null;

  return (
    <Pane icon={GitBranch} title="Lineage and turns">
      {!hasLineage ? (
        <EmptyLine value="No turn or lineage entries are available." />
      ) : (
        <div className="space-y-4">
          <section className="rounded-md border bg-card p-3" aria-label="Current lineage anchor">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
                  Current session
                </p>
                <h4 className="mt-1 break-all text-sm font-semibold tracking-normal">
                  {data.sessionId}
                </h4>
                <p className="mt-1 text-xs text-muted-foreground">
                  {data.branchLabel ?? "root branch"} · {data.status}
                  {data.forkedFromTurnId !== null ? ` · forked from ${data.forkedFromTurnId}` : ""}
                </p>
              </div>
              <Badge variant={data.parentSessionId === null ? "outline" : "info"}>
                {data.parentSessionId === null ? "root" : "parented"}
              </Badge>
            </div>
          </section>

          <LineageSection title="Parent session">
            {data.parentSessionId === null ? (
              <EmptyLine value="This session has no persisted parent." />
            ) : (
              <LineageTargetRow
                compareSessionId={data.compareSessionId}
                description="Persisted parent relationship"
                label={`Parent ${data.parentSessionId}`}
                onClearCompare={onClearCompare}
                onCompareSession={onCompareSession}
                onOpenSession={onOpenSession}
                sessionId={data.parentSessionId}
              />
            )}
          </LineageSection>

          <LineageSection title="Child sessions">
            {data.childSessions.length === 0 ? (
              <EmptyLine value="No child sessions are attached to this snapshot." />
            ) : (
              <DataList density="compact">
                {data.childSessions.map((child) => (
                  <LineageTargetRow
                    compareSessionId={data.compareSessionId}
                    description={child.latest_message_summary ?? child.status}
                    key={child.session_id}
                    label={child.branch_label ?? child.session_id}
                    metadata={`${child.status} · updated ${formatTime(child.updated_at)}`}
                    onClearCompare={onClearCompare}
                    onCompareSession={onCompareSession}
                    onOpenSession={onOpenSession}
                    sessionId={child.session_id}
                  />
                ))}
              </DataList>
            )}
          </LineageSection>

          <LineageSection title="Forkable turns">
            {data.branchableTurns.length === 0 ? (
              <EmptyLine value="No completed fork points are available." />
            ) : (
              <DataList density="compact">
                {data.branchableTurns.map((turn) => (
                  <DataListItem key={turn.turn_id}>
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <DataListLabel>{turn.label}</DataListLabel>
                        <DataListMeta>
                          turn {turn.turn_id} · sequence {turn.sequence} ·{" "}
                          {formatTime(turn.created_at)}
                        </DataListMeta>
                      </div>
                      <Button
                        onClick={() => onOpenForkTurn?.(turn.turn_id)}
                        size="xs"
                        type="button"
                        variant="outline"
                      >
                        Open fork flow for {turn.label}
                      </Button>
                    </div>
                  </DataListItem>
                ))}
              </DataList>
            )}
          </LineageSection>
        </div>
      )}
    </Pane>
  );
}

function LineageSection({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section>
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        {title}
      </p>
      {children}
    </section>
  );
}

function LineageTargetRow({
  compareSessionId,
  description,
  label,
  metadata,
  onClearCompare,
  onCompareSession,
  onOpenSession,
  sessionId,
}: {
  compareSessionId: string | null;
  description: string;
  label: string;
  metadata?: string;
  onClearCompare?: () => void;
  onCompareSession?: (sessionId: string) => void;
  onOpenSession?: (sessionId: string) => void;
  sessionId: string;
}) {
  return (
    <DataList density="compact">
      <DataListItem>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <DataListLabel>{label}</DataListLabel>
              {compareSessionId === sessionId ? <Badge variant="info">comparing</Badge> : null}
            </div>
            <DataListMeta>{description}</DataListMeta>
            {metadata !== undefined ? (
              <p className="mt-1 text-xs text-muted-foreground">{metadata}</p>
            ) : null}
          </div>
          <LineageActions
            isComparing={compareSessionId === sessionId}
            label={sessionId}
            onClearCompare={onClearCompare}
            onCompareSession={onCompareSession}
            onOpenSession={onOpenSession}
            sessionId={sessionId}
          />
        </div>
      </DataListItem>
    </DataList>
  );
}

function LineageActions({
  isComparing,
  label,
  onClearCompare,
  onCompareSession,
  onOpenSession,
  sessionId,
}: {
  isComparing: boolean;
  label: string;
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
        Compare {label}
      </Button>
      <Button onClick={() => onOpenSession?.(sessionId)} size="xs" type="button" variant="ghost">
        Open {label}
      </Button>
      {isComparing ? (
        <Button onClick={() => onClearCompare?.()} size="xs" type="button" variant="ghost">
          Clear compare
        </Button>
      ) : null}
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
                    {artifact.source_tool_name} · {artifact.provenance_class} · {artifact.freshness}{" "}
                    · {artifact.artifact_path}
                  </p>
                </DataListItem>
              ))}
            </DataList>
          )}
        </section>
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

        <EvidenceDetails title="Live output tail">
          {recentLiveOutput.length === 0 ? (
            <EmptyLine value="No live output chunks are attached to this snapshot." />
          ) : (
            <DataList density="compact">
              {recentLiveOutput.map((entry, index) => (
                <DataListItem key={`${entry.tool_call_id}:${index}`}>
                  <DataListLabel>
                    {entry.stream} · {entry.tool_call_id}
                  </DataListLabel>
                  <DataListMeta>{entry.chunk}</DataListMeta>
                  <p className="mt-2 break-all text-xs text-muted-foreground">
                    turn {entry.turn_id}
                  </p>
                </DataListItem>
              ))}
            </DataList>
          )}
        </EvidenceDetails>

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

        <EvidenceDetails title="Event log">
          {recentEvents.length === 0 ? (
            <EmptyLine value="No event log entries are attached to this snapshot." />
          ) : (
            <DataList density="compact">
              {recentEvents.map((event) => (
                <DataListItem key={`${event.event_type}:${event.sequence}`}>
                  <DataListLabel>{event.event_type}</DataListLabel>
                  <DataListMeta>sequence {event.sequence}</DataListMeta>
                </DataListItem>
              ))}
            </DataList>
          )}
        </EvidenceDetails>

        <EvidenceDetails title="Raw metric details">
          {data.turnMetrics.length === 0 ? (
            <EmptyLine value="No raw metric rows are attached to this snapshot." />
          ) : (
            <DataList density="compact">
              {data.turnMetrics.map((metric) => (
                <DataListItem key={metric.turn_id}>
                  <DataListLabel>{metric.turn_id}</DataListLabel>
                  <DataListMeta>
                    model {formatDuration(metric.model_duration_ms_total)} · tool{" "}
                    {formatDuration(metric.tool_duration_ms_total)}
                  </DataListMeta>
                </DataListItem>
              ))}
            </DataList>
          )}
        </EvidenceDetails>
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

function MetricSummary({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold">{value}</p>
    </div>
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

function summarizeTurnMetrics(metrics: DashboardState["turnMetrics"]) {
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
