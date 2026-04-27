import type { ReactNode } from "react";
import { GitBranch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import { formatTime } from "@/components/console/session-inspector/format";
import type { DashboardState } from "@/state/session-state";

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
