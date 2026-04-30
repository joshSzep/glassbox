import { GitBranch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import {
  formatDuration,
  formatMessage,
  formatTime,
} from "@/components/console/session-inspector/format";
import { MetricSummary, summarizeTurnMetrics } from "./shared";
import {
  buildCompareAnalysis,
  type ComparableSnapshot,
  type CompareAnalysis,
  type CompareFact,
} from "./compare-analysis";
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
  const analysis = compare === null ? null : buildCompareAnalysis(data, compare);

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
              {analysis?.summary.map((difference) => (
                <DataListItem key={difference.label}>
                  <DataListLabel>{difference.label}</DataListLabel>
                  <DataListMeta>{difference.value}</DataListMeta>
                </DataListItem>
              ))}
            </DataList>
          </section>
          {analysis !== null ? <BranchMetadataSection analysis={analysis} /> : null}
          {analysis !== null ? <TranscriptDivergenceSection analysis={analysis} /> : null}
          {analysis !== null ? <ToolActivitySection analysis={analysis} /> : null}
          {analysis !== null ? <PolicyOutcomeSection analysis={analysis} /> : null}
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
          {analysis !== null ? <RuntimeProjectionSection analysis={analysis} /> : null}
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

function CompareSessionCard({ label, session }: { label: string; session: ComparableSnapshot }) {
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

function BranchMetadataSection({ analysis }: { analysis: CompareAnalysis }) {
  return (
    <AlignedCompareSection
      current={analysis.branch.current}
      compared={analysis.branch.compared}
      title="Branch metadata"
    />
  );
}

function TranscriptDivergenceSection({ analysis }: { analysis: CompareAnalysis }) {
  return (
    <section>
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        Transcript divergence
      </p>
      <div className="grid gap-3 md:grid-cols-3">
        <DivergenceCard
          empty="No shared message ids were retained between these snapshots."
          label="Shared transcript"
          messages={analysis.transcript.shared}
        />
        <DivergenceCard
          empty="No current-only post-fork messages."
          label="Current-only messages"
          messages={analysis.transcript.currentOnly}
        />
        <DivergenceCard
          empty="No compared-only messages."
          label="Compared-only messages"
          messages={analysis.transcript.comparedOnly}
        />
      </div>
    </section>
  );
}

function ToolActivitySection({ analysis }: { analysis: CompareAnalysis }) {
  return (
    <AlignedCompareSection
      current={analysis.tools.current}
      compared={analysis.tools.compared}
      title="Tool activity"
    />
  );
}

function PolicyOutcomeSection({ analysis }: { analysis: CompareAnalysis }) {
  return (
    <AlignedCompareSection
      current={analysis.policy.current}
      compared={analysis.policy.compared}
      title="Policy outcomes"
    />
  );
}

function RuntimeProjectionSection({ analysis }: { analysis: CompareAnalysis }) {
  return (
    <AlignedCompareSection
      current={analysis.runtime.current}
      compared={analysis.runtime.compared}
      title="Runtime and projection"
    />
  );
}

function AlignedCompareSection({
  compared,
  current,
  title,
}: {
  compared: CompareFact[];
  current: CompareFact[];
  title: string;
}) {
  return (
    <section>
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        {title}
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        <CompareFactCard facts={current} label="Current" />
        <CompareFactCard facts={compared} label="Compared" />
      </div>
    </section>
  );
}

function CompareFactCard({ facts, label }: { facts: CompareFact[]; label: string }) {
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        {label}
      </p>
      <DataList density="compact">
        {facts.map((fact) => (
          <DataListItem key={fact.label}>
            <DataListLabel>{fact.label}</DataListLabel>
            <DataListMeta>{fact.value}</DataListMeta>
          </DataListItem>
        ))}
      </DataList>
    </div>
  );
}

function DivergenceCard({
  empty,
  label,
  messages,
}: {
  empty: string;
  label: string;
  messages: DashboardState["transcript"];
}) {
  const visibleMessages = messages.slice(-3);
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        {label}
      </p>
      {visibleMessages.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <DataList className="mt-2" density="compact">
          {visibleMessages.map((message) => (
            <DataListItem key={message.message_id}>
              <DataListLabel>{message.role}</DataListLabel>
              <DataListMeta>{formatMessage(message)}</DataListMeta>
              <p className="mt-2 break-all text-xs text-muted-foreground">
                {message.message_id} · {formatTime(message.created_at)}
              </p>
            </DataListItem>
          ))}
        </DataList>
      )}
    </div>
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
