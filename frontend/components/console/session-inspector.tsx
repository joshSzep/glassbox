"use client";

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
      <div className="grid gap-4 xl:grid-cols-2">
        <OperatorActionPane
          action={action}
          data={data}
          drafts={drafts}
          onAnswerTextChange={onAnswerTextChange}
          onFork={onFork}
          onForkLabelChange={onForkLabelChange}
          onPromptChange={onPromptChange}
          onResolveApproval={onResolveApproval}
          onSubmitAnswer={onSubmitAnswer}
          onSubmitPrompt={onSubmitPrompt}
        />
        <TranscriptPane messages={data.transcript} />
        <LineagePane
          data={data}
          onClearCompare={onClearCompare}
          onCompareSession={onCompareSession}
          onOpenSession={onOpenSession}
        />
        <ComparePane data={data} onClearCompare={onClearCompare} onOpenSession={onOpenSession} />
        <ActionSummaryPane data={data} />
        <RuntimePane data={data} />
        <VerificationCues data={data} />
        <MetricsPane data={data} />
        <EvidencePane data={data} stream={stream} />
      </div>
    </InspectorFrame>
  );
}
