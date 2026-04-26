"use client";

import type { ReactNode } from "react";
import { AlertCircle, MessageSquareText, RadioTower } from "lucide-react";

import { VerificationCues } from "@/components/console/verification-cues";
import { OperatorActionPane } from "@/components/console/session-inspector/actions";
import { InspectorFrame, StateBlock } from "@/components/console/session-inspector/frame";
import { SessionHeader } from "@/components/console/session-inspector/header";
import {
  ActionSummaryPane,
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

const idleAction: ActionStatus = { error: null, kind: null, state: "idle" };
const emptyDrafts: DraftState = {
  answerTextByQuestionId: {},
  composerText: "",
  forkLabel: "",
  selectedCompareTargetId: null,
};

export type SessionInspectorProps = {
  action?: ActionStatus;
  activeTab: InspectorTab;
  data: DashboardState;
  drafts?: DraftState;
  error: string | null;
  loadState: LoadState;
  onAnswerTextChange?: (questionId: string, text: string) => void;
  onClearCompare?: () => void;
  onCompareSession?: (sessionId: string) => void;
  onFork?: (input?: { branchLabel?: string | null; turnId?: string | null }) => void;
  onForkLabelChange?: (text: string) => void;
  onOpenSession?: (sessionId: string) => void;
  onPromptChange?: (text: string) => void;
  onResolveApproval?: (input: { approvalId: string; decision: "approved" | "denied" }) => void;
  onSubmitAnswer?: (questionId: string) => void;
  onSubmitPrompt?: () => void;
  queue: AppQueue;
  stream: SessionStreamState;
};

export function SessionInspector({
  action = idleAction,
  activeTab,
  data,
  drafts = emptyDrafts,
  error,
  loadState,
  onAnswerTextChange,
  onClearCompare,
  onCompareSession,
  onFork,
  onForkLabelChange,
  onOpenSession,
  onPromptChange,
  onResolveApproval,
  onSubmitAnswer,
  onSubmitPrompt,
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
      <InspectorTabContent
        action={action}
        activeTab={activeTab}
        data={data}
        drafts={drafts}
        onAnswerTextChange={onAnswerTextChange}
        onClearCompare={onClearCompare}
        onCompareSession={onCompareSession}
        onFork={onFork}
        onForkLabelChange={onForkLabelChange}
        onOpenSession={onOpenSession}
        onPromptChange={onPromptChange}
        onResolveApproval={onResolveApproval}
        onSubmitAnswer={onSubmitAnswer}
        onSubmitPrompt={onSubmitPrompt}
        stream={stream}
      />
    </InspectorFrame>
  );
}

function InspectorTabContent({
  action,
  activeTab,
  data,
  drafts,
  onAnswerTextChange,
  onClearCompare,
  onCompareSession,
  onFork,
  onForkLabelChange,
  onOpenSession,
  onPromptChange,
  onResolveApproval,
  onSubmitAnswer,
  onSubmitPrompt,
  stream,
}: Omit<SessionInspectorProps, "error" | "loadState" | "queue">) {
  const actionPane = (
    <OperatorActionPane
      action={action ?? idleAction}
      data={data}
      drafts={drafts ?? emptyDrafts}
      onAnswerTextChange={onAnswerTextChange}
      onFork={onFork}
      onForkLabelChange={onForkLabelChange}
      onPromptChange={onPromptChange}
      onResolveApproval={onResolveApproval}
      onSubmitAnswer={onSubmitAnswer}
      onSubmitPrompt={onSubmitPrompt}
    />
  );
  const lineagePane = (
    <LineagePane
      data={data}
      onClearCompare={onClearCompare}
      onCompareSession={onCompareSession}
      onOpenSession={onOpenSession}
    />
  );
  const comparePane = (
    <ComparePane data={data} onClearCompare={onClearCompare} onOpenSession={onOpenSession} />
  );

  switch (activeTab) {
    case "transcript":
      return <TabPanel>{<TranscriptPane messages={data.transcript} />}</TabPanel>;
    case "timeline":
      return <TabPanel>{<TimelinePane data={data} />}</TabPanel>;
    case "actions":
      return <TabPanel>{actionPane}</TabPanel>;
    case "lineage":
      return <TabPanel>{lineagePane}</TabPanel>;
    case "compare":
      return <TabPanel>{comparePane}</TabPanel>;
    case "runtime":
      return <TabPanel>{<RuntimePane data={data} />}</TabPanel>;
    case "evidence":
      return (
        <TabPanel className="xl:grid-cols-2">
          <VerificationCues data={data} />
          <EvidencePane data={data} stream={stream} />
        </TabPanel>
      );
    case "metrics":
      return <TabPanel>{<MetricsPane data={data} />}</TabPanel>;
    case "events":
      return <TabPanel>{<EvidencePane data={data} stream={stream} />}</TabPanel>;
    case "overview":
    default:
      return (
        <TabPanel className="xl:grid-cols-2">
          {hasHighPriorityAction(data) ? actionPane : <ActionSummaryPane data={data} />}
          <TranscriptPane messages={latestTranscriptPreview(data)} />
        </TabPanel>
      );
  }
}

function TabPanel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`grid gap-4 p-4 ${className}`}>{children}</div>;
}

function hasHighPriorityAction(data: DashboardState): boolean {
  return (
    data.pendingApprovals.length > 0 ||
    data.pendingQuestionId !== null ||
    data.sessionFailureMessage !== null ||
    data.activeToolCalls.length > 0
  );
}

function latestTranscriptPreview(data: DashboardState) {
  return data.transcript.slice(-3);
}
