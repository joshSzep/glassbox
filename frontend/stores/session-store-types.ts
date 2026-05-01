import type { StoreApi } from "zustand/vanilla";

import type { GlassboxApiClient } from "@/api/client";
import type {
  createSessionEventStream,
  SessionEventStreamOptions,
  SessionStreamState,
  SseEventEnvelope,
} from "@/api/sse";
import type { DashboardState } from "@/state/session-state";
import type { LoadState, StoreActionStatus } from "@/stores/store-actions";

export type ActionKind =
  | "answer"
  | "approval"
  | "cancel"
  | "fork"
  | "prompt"
  | "tool-abandon"
  | "tool-retry";
export type DetailPageKind = "events" | "metrics" | "transcript";
export type ActionStatus = StoreActionStatus<ActionKind>;

export type DetailPageStatus = {
  error: string | null;
  hasMore: boolean;
  nextCursor: number | null;
  state: LoadState;
};

export type DetailPageState = Record<DetailPageKind, DetailPageStatus>;

export type DraftState = {
  answerTextByQuestionId: Record<string, string>;
  composerText: string;
  forkLabel: string;
  selectedCompareTargetId: string | null;
};

export type SessionEventStreamHandle = ReturnType<typeof createSessionEventStream>;
export type SessionEventStreamFactory = (
  options: SessionEventStreamOptions,
) => SessionEventStreamHandle;

export type SessionStoreState = {
  action: ActionStatus;
  applyStreamEnvelope: (envelope: SseEventEnvelope) => void;
  clearCompareSession: () => void;
  connectStream: () => void;
  data: DashboardState;
  detailPages: DetailPageState;
  disconnectStream: () => void;
  drafts: DraftState;
  error: string | null;
  forkSession: (input?: {
    branchLabel?: string | null;
    turnId?: string | null;
  }) => Promise<string | null>;
  loadCompareSession: (sessionId: string) => Promise<void>;
  loadMoreEvents: () => Promise<void>;
  loadMoreMetrics: () => Promise<void>;
  loadMoreTranscript: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  loadState: LoadState;
  abandonToolAttempt: (input: { reason?: string; toolAttemptId: string }) => Promise<void>;
  requestCancellation: () => Promise<void>;
  resetForRoute: (sessionId?: string | null) => void;
  resolveApproval: (input: {
    approvalId: string;
    decision: "approved" | "denied";
  }) => Promise<void>;
  setAnswerText: (questionId: string, text: string) => void;
  setComposerText: (text: string) => void;
  setForkLabel: (text: string) => void;
  setSelectedCompareTarget: (sessionId: string | null) => void;
  stream: SessionStreamState;
  submitAnswer: (input: { answer?: string; questionId: string }) => Promise<void>;
  submitPrompt: (text?: string) => Promise<void>;
  retryToolAttempt: (input: { toolAttemptId: string }) => Promise<void>;
};

export type SessionStoreApi = StoreApi<SessionStoreState>;
export type SessionStoreSet = SessionStoreApi["setState"];
export type SessionStoreGet = SessionStoreApi["getState"];
export type SessionActionContext = {
  actionRequests: ReturnType<typeof import("@/stores/store-actions").createRequestTracker>;
  apiClient: GlassboxApiClient;
  get: SessionStoreGet;
  set: SessionStoreSet;
};
