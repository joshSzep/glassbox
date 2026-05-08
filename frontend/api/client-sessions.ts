import type { components, paths } from "@/generated/api-types";

import type {
  ActionAcceptedResponse,
  ApprovalDecision,
  RequestJson,
  RequestOptions,
} from "./client-core";

export type SessionSummaryResponse = components["schemas"]["SessionSummaryResponse"];
export type SessionAggregateResponse = components["schemas"]["SessionAggregateResponse"];
export type SessionSnapshotResponse = components["schemas"]["SessionSnapshotResponse"];
export type SessionTranscriptPageResponse = components["schemas"]["SessionTranscriptPageResponse"];
export type SessionEventLogPageResponse = components["schemas"]["SessionEventLogPageResponse"];
export type SessionToolCallPageResponse = components["schemas"]["SessionToolCallPageResponse"];
export type SessionTurnMetricsPageResponse =
  components["schemas"]["SessionTurnMetricsPageResponse"];
export type SessionArtifactPageResponse = components["schemas"]["SessionArtifactPageResponse"];
export type ToolAttemptRecoveryResponse = components["schemas"]["ToolAttemptRecoveryResponse"];
export type ForkSessionResponse = components["schemas"]["ForkSessionResponse"];

export type SessionAggregateQuery = NonNullable<
  paths["/sessions/aggregate"]["get"]["parameters"]["query"]
>;
export type SessionTranscriptPageQuery = NonNullable<
  paths["/sessions/{session_id}/transcript"]["get"]["parameters"]["query"]
>;
export type SessionEventLogPageQuery = NonNullable<
  paths["/sessions/{session_id}/event-log"]["get"]["parameters"]["query"]
>;
export type SessionToolCallPageQuery = NonNullable<
  paths["/sessions/{session_id}/tool-calls"]["get"]["parameters"]["query"]
>;
export type SessionTurnMetricsPageQuery = NonNullable<
  paths["/sessions/{session_id}/turn-metrics"]["get"]["parameters"]["query"]
>;
export type SessionArtifactPageQuery = NonNullable<
  paths["/sessions/{session_id}/artifacts"]["get"]["parameters"]["query"]
>;

export function createSessionEndpoints(requestJson: RequestJson) {
  return {
    listSessions: (requestOptions?: RequestOptions) =>
      requestJson<SessionSummaryResponse[]>("GET", "/sessions", requestOptions),

    getSessionAggregate: (query: SessionAggregateQuery = {}, requestOptions?: RequestOptions) =>
      requestJson<SessionAggregateResponse>("GET", "/sessions/aggregate", {
        ...requestOptions,
        query,
      }),

    getSessionSnapshot: (sessionId: string, requestOptions?: RequestOptions) =>
      requestJson<SessionSnapshotResponse>(
        "GET",
        `/sessions/${encodeURIComponent(sessionId)}`,
        requestOptions,
      ),

    getCompareSessionSnapshot: (compareSessionId: string, requestOptions?: RequestOptions) =>
      requestJson<SessionSnapshotResponse>(
        "GET",
        `/sessions/${encodeURIComponent(compareSessionId)}`,
        requestOptions,
      ),

    getSessionTranscriptPage: (
      sessionId: string,
      query: SessionTranscriptPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<SessionTranscriptPageResponse>(
        "GET",
        `/sessions/${encodeURIComponent(sessionId)}/transcript`,
        { ...requestOptions, query },
      ),

    getSessionEventLogPage: (
      sessionId: string,
      query: SessionEventLogPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<SessionEventLogPageResponse>(
        "GET",
        `/sessions/${encodeURIComponent(sessionId)}/event-log`,
        { ...requestOptions, query },
      ),

    getSessionToolCallPage: (
      sessionId: string,
      query: SessionToolCallPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<SessionToolCallPageResponse>(
        "GET",
        `/sessions/${encodeURIComponent(sessionId)}/tool-calls`,
        { ...requestOptions, query },
      ),

    getSessionTurnMetricsPage: (
      sessionId: string,
      query: SessionTurnMetricsPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<SessionTurnMetricsPageResponse>(
        "GET",
        `/sessions/${encodeURIComponent(sessionId)}/turn-metrics`,
        { ...requestOptions, query },
      ),

    getSessionArtifactPage: (
      sessionId: string,
      query: SessionArtifactPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<SessionArtifactPageResponse>(
        "GET",
        `/sessions/${encodeURIComponent(sessionId)}/artifacts`,
        { ...requestOptions, query },
      ),

    resolveApproval: (
      input: { sessionId: string; approvalId: string; decision: ApprovalDecision },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/sessions/${encodeURIComponent(input.sessionId)}/approvals/${encodeURIComponent(
          input.approvalId,
        )}`,
        {
          ...requestOptions,
          body: { decision: input.decision },
        },
      ),

    submitMessage: (input: { sessionId: string; text: string }, requestOptions?: RequestOptions) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/sessions/${encodeURIComponent(input.sessionId)}/messages`,
        {
          ...requestOptions,
          body: { text: input.text },
        },
      ),

    submitAnswer: (
      input: { sessionId: string; questionId: string; answer: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/sessions/${encodeURIComponent(input.sessionId)}/questions/${encodeURIComponent(
          input.questionId,
        )}`,
        {
          ...requestOptions,
          body: { answer: input.answer },
        },
      ),

    cancelTurn: (
      input: { sessionId: string; reason?: string | null; turnId?: string | null },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/sessions/${encodeURIComponent(input.sessionId)}/cancel`,
        {
          ...requestOptions,
          body: {
            reason: input.reason ?? null,
            turn_id: input.turnId ?? null,
          },
        },
      ),

    retryToolAttempt: (
      input: {
        actor?: string;
        reason?: string | null;
        sessionId: string;
        toolAttemptId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ToolAttemptRecoveryResponse>(
        "POST",
        `/sessions/${encodeURIComponent(input.sessionId)}/tool-attempts/${encodeURIComponent(
          input.toolAttemptId,
        )}/retry`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            confirmed: true,
            reason: input.reason ?? null,
          },
        },
      ),

    abandonToolAttempt: (
      input: {
        actor?: string;
        reason: string;
        sessionId: string;
        toolAttemptId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ToolAttemptRecoveryResponse>(
        "POST",
        `/sessions/${encodeURIComponent(input.sessionId)}/tool-attempts/${encodeURIComponent(
          input.toolAttemptId,
        )}/abandon`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            confirmed: true,
            reason: input.reason,
          },
        },
      ),

    forkSession: (
      input: { sessionId: string; turnId?: string | null; branchLabel?: string | null },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ForkSessionResponse>(
        "POST",
        `/sessions/${encodeURIComponent(input.sessionId)}/fork`,
        {
          ...requestOptions,
          body: {
            branch_label: input.branchLabel ?? null,
            turn_id: input.turnId ?? null,
          },
        },
      ),
  };
}
