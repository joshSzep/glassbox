import { GitBranch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import { formatDuration, formatMessage } from "@/components/console/session-inspector/format";
import { MetricSummary, summarizeTurnMetrics } from "./shared";
import type { DashboardState } from "@/state/session-state";

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
  const currentTotals = summarizeTurnMetrics(data.turnMetrics);
  const compareTotals = summarizeTurnMetrics(compare?.turnMetrics ?? []);
  const differences = compare === null ? [] : buildCompareDifferences(data, compare);

  return (
    <Pane icon={GitBranch} title="Compare">
      {compare === null ? (
        <EmptyLine
          value={
            data.compareSessionId === null
              ? "Select a parent or child session to compare persisted snapshots."
              : `Compare target ${data.compareSessionId} is loading or unavailable.`
          }
        />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2" aria-label="Compare session anchors">
            <CompareSessionCard label="Current" session={data} />
            <CompareSessionCard label="Compared" session={compare} />
          </div>
          <section>
            <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
              Difference summary
            </p>
            <DataList density="compact">
              {differences.map((difference) => (
                <DataListItem key={difference.label}>
                  <DataListLabel>{difference.label}</DataListLabel>
                  <DataListMeta>{difference.value}</DataListMeta>
                </DataListItem>
              ))}
            </DataList>
          </section>
          <section>
            <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
              Latest messages
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              <CompareMessageCard label="Current latest" message={data.transcript.at(-1) ?? null} />
              <CompareMessageCard
                label="Compared latest"
                message={compare.transcript.at(-1) ?? null}
              />
            </div>
          </section>
          <section>
            <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
              Turn metrics
            </p>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4" aria-label="Compare metrics">
              <MetricSummary
                label="Current duration"
                value={formatDuration(currentTotals.turnDurationMs)}
              />
              <MetricSummary
                label="Compared duration"
                value={formatDuration(compareTotals.turnDurationMs)}
              />
              <MetricSummary
                label="Current tokens"
                value={`${currentTotals.inputTokens + currentTotals.outputTokens}`}
              />
              <MetricSummary
                label="Compared tokens"
                value={`${compareTotals.inputTokens + compareTotals.outputTokens}`}
              />
            </div>
          </section>
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={compare.sessionId === null}
              onClick={() => compare.sessionId !== null && onOpenSession?.(compare.sessionId)}
              size="xs"
              type="button"
              variant="outline"
            >
              Open compared {compare.sessionId}
            </Button>
            <Button onClick={() => onClearCompare?.()} size="xs" type="button" variant="ghost">
              Clear compare
            </Button>
          </div>
        </div>
      )}
    </Pane>
  );
}

function CompareSessionCard({
  label,
  session,
}: {
  label: string;
  session: DashboardState | NonNullable<DashboardState["compareSession"]>;
}) {
  return (
    <section className="rounded-md border bg-card p-3">
      <p className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        {label}
      </p>
      <h4 className="mt-1 break-all text-sm font-semibold tracking-normal">
        {session.sessionId ?? "unknown session"}
      </h4>
      <div className="mt-2 flex flex-wrap gap-2">
        <Badge variant={session.status === "failed" ? "destructive" : "outline"}>
          {session.status}
        </Badge>
        <Badge variant={session.parentSessionId === null ? "outline" : "info"}>
          {session.parentSessionId === null ? "root" : `parent ${session.parentSessionId}`}
        </Badge>
      </div>
      <p className="mt-2 break-words text-xs text-muted-foreground">
        {session.branchLabel ?? "unlabeled branch"}
        {session.forkedFromSequence !== null
          ? ` · forked sequence ${session.forkedFromSequence}`
          : ""}
        {session.forkedFromTurnId !== null ? ` · source ${session.forkedFromTurnId}` : ""}
      </p>
    </section>
  );
}

function CompareMessageCard({
  label,
  message,
}: {
  label: string;
  message: DashboardState["transcript"][number] | null;
}) {
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      {message === null ? (
        <p className="mt-2 text-sm text-muted-foreground">No transcript message is available.</p>
      ) : (
        <>
          <Badge className="mt-2" variant={message.role === "user" ? "info" : "outline"}>
            {message.role}
          </Badge>
          <p className="mt-2 whitespace-pre-wrap break-words text-sm text-muted-foreground">
            {formatMessage(message)}
          </p>
        </>
      )}
    </div>
  );
}

function buildCompareDifferences(
  current: DashboardState,
  compare: NonNullable<DashboardState["compareSession"]>,
) {
  const workingSetDelta = compareStringSets(
    current.runtimeContext?.working_set?.items?.map((item) => item.subject) ?? [],
    compare.runtimeContext?.working_set?.items?.map((item) => item.subject) ?? [],
  );
  const runtimePathDelta = compareStringSets(
    current.runtimeContext?.repository_context.high_signal_paths ?? [],
    compare.runtimeContext?.repository_context.high_signal_paths ?? [],
  );
  const currentLatest = current.transcript.at(-1);
  const compareLatest = compare.transcript.at(-1);
  return [
    {
      label: "Status change",
      value:
        current.status === compare.status
          ? `both ${current.status}`
          : `${compare.status} compared -> ${current.status} current`,
    },
    {
      label: "Transcript length",
      value: `${current.transcript.length} current · ${compare.transcript.length} compared · delta ${current.transcript.length - compare.transcript.length}`,
    },
    {
      label: "Latest message",
      value:
        currentLatest === undefined || compareLatest === undefined
          ? "latest message unavailable in one snapshot"
          : currentLatest.message_id === compareLatest.message_id
            ? "same latest message id"
            : `${compareLatest.role} compared -> ${currentLatest.role} current`,
    },
    {
      label: "Runtime context",
      value: `${runtimePathDelta.currentOnly.length} current-only paths · ${runtimePathDelta.comparedOnly.length} compared-only paths`,
    },
    {
      label: "Working set",
      value: `${workingSetDelta.currentOnly.length} current-only items · ${workingSetDelta.comparedOnly.length} compared-only items`,
    },
    {
      label: "Turn summaries",
      value: `${current.turnMetrics.length} current metrics · ${compare.turnMetrics.length} compared metrics`,
    },
    {
      label: "Fork source",
      value: `current ${current.forkedFromTurnId ?? "none"} · compared ${compare.forkedFromTurnId ?? "none"}`,
    },
  ];
}

function compareStringSets(current: string[], compared: string[]) {
  const currentSet = new Set(current);
  const comparedSet = new Set(compared);
  return {
    comparedOnly: compared.filter((value) => !currentSet.has(value)),
    currentOnly: current.filter((value) => !comparedSet.has(value)),
  };
}
