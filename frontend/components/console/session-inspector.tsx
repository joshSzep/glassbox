"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { AlertCircle, MessageSquareText, RadioTower } from "lucide-react";

import { VerificationCues } from "@/components/console/verification-cues";
import { OperatorActionPane } from "@/components/console/session-inspector/actions";
import { InspectorFrame, StateBlock } from "@/components/console/session-inspector/frame";
import { SessionHeader } from "@/components/console/session-inspector/header";
import { SessionOverviewTab } from "@/components/console/session-inspector/overview";
import {
  ComparePane,
  EvidencePane,
  LineagePane,
  MetricsPane,
  RuntimePane,
  TimelinePane,
  TranscriptPane,
} from "@/components/console/session-inspector/panes";
import { InspectorTabs } from "@/components/console/session-inspector/tabs";
import type { SessionStreamState } from "@/api/sse";
import type { AppQueue, InspectorTab } from "@/routing/app-route";
import type { DashboardState } from "@/state/session-state";
import type { ActionStatus, DraftState, LoadState } from "@/stores/dashboard-stores";
import type { DetailPageState } from "@/stores/dashboard-stores";

type ForkDialogRequest = { requestId: number; turnId: string | null };

const idleAction: ActionStatus = { error: null, kind: null, state: "idle" };
const emptyDrafts: DraftState = {
  answerTextByQuestionId: {},
  composerText: "",
  forkLabel: "",
  selectedCompareTargetId: null,
};
const idleDetailPages: DetailPageState = {
  events: { error: null, hasMore: false, nextCursor: null, state: "idle" },
  metrics: { error: null, hasMore: false, nextCursor: null, state: "idle" },
  transcript: { error: null, hasMore: false, nextCursor: null, state: "idle" },
};

export type SessionInspectorProps = {
  action?: ActionStatus;
  activeTab: InspectorTab;
  data: DashboardState;
  detailPages?: DetailPageState;
  drafts?: DraftState;
  error: string | null;
  loadState: LoadState;
  onAnswerTextChange?: (questionId: string, text: string) => void;
  onAbandonToolAttempt?: (toolAttemptId: string) => void;
  onClearCompare?: () => void;
  onCompareSession?: (sessionId: string) => void;
  onFork?: (input?: { branchLabel?: string | null; turnId?: string | null }) => void;
  onForkLabelChange?: (text: string) => void;
  onLoadMoreEvents?: () => void;
  onLoadMoreMetrics?: () => void;
  onLoadMoreTranscript?: () => void;
  onOpenSession?: (sessionId: string) => void;
  onPromptChange?: (text: string) => void;
  onRequestCancellation?: () => void;
  onResolveApproval?: (input: { approvalId: string; decision: "approved" | "denied" }) => void;
  onSelectTab?: (tab: InspectorTab) => void;
  onSubmitAnswer?: (questionId: string) => void;
  onSubmitPrompt?: () => void;
  onRetryToolAttempt?: (toolAttemptId: string) => void;
  queue: AppQueue;
  stream: SessionStreamState;
};

export function SessionInspector({
  action = idleAction,
  activeTab,
  data,
  detailPages = idleDetailPages,
  drafts = emptyDrafts,
  error,
  loadState,
  onAnswerTextChange,
  onAbandonToolAttempt,
  onClearCompare,
  onCompareSession,
  onFork,
  onForkLabelChange,
  onLoadMoreEvents,
  onLoadMoreMetrics,
  onLoadMoreTranscript,
  onOpenSession,
  onPromptChange,
  onRequestCancellation,
  onResolveApproval,
  onSelectTab,
  onSubmitAnswer,
  onSubmitPrompt,
  onRetryToolAttempt,
  queue,
  stream,
}: SessionInspectorProps) {
  const [forkDialogRequest, setForkDialogRequest] = useState<ForkDialogRequest | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const previousSessionIdRef = useRef<string | null>(data.sessionId);

  useEffect(() => {
    if (data.sessionId === null || previousSessionIdRef.current === data.sessionId) {
      return;
    }
    previousSessionIdRef.current = data.sessionId;
    headingRef.current?.focus({ preventScroll: true });
  }, [data.sessionId]);

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
      <SessionHeader data={data} headingRef={headingRef} stream={stream} />
      <InspectorTabs activeTab={activeTab} data={data} onSelectTab={onSelectTab} queue={queue} />
      <InspectorTabContent
        action={action}
        activeTab={activeTab}
        data={data}
        detailPages={detailPages}
        drafts={drafts}
        forkDialogRequest={forkDialogRequest}
        onAnswerTextChange={onAnswerTextChange}
        onAbandonToolAttempt={onAbandonToolAttempt}
        onClearCompare={onClearCompare}
        onCompareSession={onCompareSession}
        onFork={onFork}
        onForkLabelChange={onForkLabelChange}
        onLoadMoreEvents={onLoadMoreEvents}
        onLoadMoreMetrics={onLoadMoreMetrics}
        onLoadMoreTranscript={onLoadMoreTranscript}
        onClearForkDialogRequest={() => {
          setForkDialogRequest(null);
        }}
        onOpenForkTurn={(turnId) => {
          setForkDialogRequest({ requestId: Date.now(), turnId });
          onSelectTab?.("actions");
        }}
        onOpenSession={onOpenSession}
        onPromptChange={onPromptChange}
        onRequestCancellation={onRequestCancellation}
        onResolveApproval={onResolveApproval}
        onSubmitAnswer={onSubmitAnswer}
        onSubmitPrompt={onSubmitPrompt}
        onRetryToolAttempt={onRetryToolAttempt}
        stream={stream}
      />
    </InspectorFrame>
  );
}

function InspectorTabContent({
  action,
  activeTab,
  data,
  detailPages = idleDetailPages,
  drafts,
  forkDialogRequest,
  onAnswerTextChange,
  onAbandonToolAttempt,
  onClearCompare,
  onCompareSession,
  onFork,
  onForkLabelChange,
  onLoadMoreEvents,
  onLoadMoreMetrics,
  onLoadMoreTranscript,
  onClearForkDialogRequest,
  onOpenForkTurn,
  onOpenSession,
  onPromptChange,
  onRequestCancellation,
  onResolveApproval,
  onSubmitAnswer,
  onSubmitPrompt,
  onRetryToolAttempt,
  stream,
}: Omit<SessionInspectorProps, "error" | "loadState" | "queue"> & {
  forkDialogRequest: ForkDialogRequest | null;
  onClearForkDialogRequest: () => void;
  onOpenForkTurn: (turnId: string | null) => void;
}) {
  const actionPane = (
    <OperatorActionPane
      action={action ?? idleAction}
      data={data}
      drafts={drafts ?? emptyDrafts}
      forkDialogRequest={forkDialogRequest}
      onClearForkDialogRequest={onClearForkDialogRequest}
      onAnswerTextChange={onAnswerTextChange}
      onAbandonToolAttempt={onAbandonToolAttempt}
      onFork={onFork}
      onForkLabelChange={onForkLabelChange}
      onPromptChange={onPromptChange}
      onRequestCancellation={onRequestCancellation}
      onResolveApproval={onResolveApproval}
      onSubmitAnswer={onSubmitAnswer}
      onSubmitPrompt={onSubmitPrompt}
      onRetryToolAttempt={onRetryToolAttempt}
      stream={stream}
    />
  );
  const lineagePane = (
    <LineagePane
      data={data}
      onClearCompare={onClearCompare}
      onCompareSession={onCompareSession}
      onOpenForkTurn={onOpenForkTurn}
      onOpenSession={onOpenSession}
    />
  );
  const comparePane = (
    <ComparePane data={data} onClearCompare={onClearCompare} onOpenSession={onOpenSession} />
  );

  switch (activeTab) {
    case "transcript":
      return (
        <TabPanel activeTab={activeTab}>
          {
            <TranscriptPane
              data={data}
              page={detailPages.transcript}
              onLoadMore={onLoadMoreTranscript}
            />
          }
        </TabPanel>
      );
    case "timeline":
      return (
        <TabPanel activeTab={activeTab}>
          {<TimelinePane data={data} onOpenForkTurn={onOpenForkTurn} />}
        </TabPanel>
      );
    case "actions":
      return <TabPanel activeTab={activeTab}>{actionPane}</TabPanel>;
    case "lineage":
      return <TabPanel activeTab={activeTab}>{lineagePane}</TabPanel>;
    case "compare":
      return <TabPanel activeTab={activeTab}>{comparePane}</TabPanel>;
    case "runtime":
      return <TabPanel activeTab={activeTab}>{<RuntimePane data={data} />}</TabPanel>;
    case "evidence":
      return (
        <TabPanel activeTab={activeTab} className="xl:grid-cols-2">
          <VerificationCues data={data} />
          <EvidencePane
            data={data}
            eventPage={detailPages.events}
            onLoadMoreEvents={onLoadMoreEvents}
            stream={stream}
          />
        </TabPanel>
      );
    case "metrics":
      return (
        <TabPanel activeTab={activeTab}>
          {<MetricsPane data={data} page={detailPages.metrics} onLoadMore={onLoadMoreMetrics} />}
        </TabPanel>
      );
    case "events":
      return (
        <TabPanel activeTab={activeTab}>
          {
            <EvidencePane
              data={data}
              eventPage={detailPages.events}
              onLoadMoreEvents={onLoadMoreEvents}
              stream={stream}
            />
          }
        </TabPanel>
      );
    case "overview":
    default:
      return <SessionOverviewTab actionPane={actionPane} data={data} stream={stream} />;
  }
}

function TabPanel({
  activeTab,
  children,
  className = "",
}: {
  activeTab: SessionInspectorProps["activeTab"];
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      aria-label={`${inspectorTabLabel(activeTab)} tab panel`}
      className={`grid gap-4 p-4 ${className}`}
      role="tabpanel"
      tabIndex={0}
    >
      {children}
    </div>
  );
}

function inspectorTabLabel(tab: SessionInspectorProps["activeTab"]): string {
  switch (tab) {
    case "transcript":
      return "Transcript";
    case "timeline":
      return "Timeline";
    case "actions":
      return "Actions";
    case "lineage":
      return "Lineage";
    case "compare":
      return "Compare";
    case "runtime":
      return "Runtime";
    case "evidence":
      return "Evidence";
    case "metrics":
      return "Metrics";
    case "events":
      return "Events";
    case "overview":
    default:
      return "Overview";
  }
}
