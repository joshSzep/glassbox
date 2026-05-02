import type { components, paths } from "@/generated/api-types";

export type HealthResponse = components["schemas"]["HealthResponse"];
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
export type TaskListPageResponse = components["schemas"]["TaskListPageResponse"];
export type TaskDetailResponse = components["schemas"]["TaskDetailResponse"];
export type TaskStepPageResponse = components["schemas"]["TaskStepPageResponse"];
export type TaskEventPageResponse = components["schemas"]["TaskEventPageResponse"];
export type BackgroundJobDetailResponse = components["schemas"]["BackgroundJobDetailResponse"];
export type TaskContinuationWindowActionResponse =
  components["schemas"]["TaskContinuationWindowActionResponse"];
export type TaskPauseWindowResponse = components["schemas"]["TaskPauseWindowResponse"];
export type ActionAcceptedResponse = components["schemas"]["ActionAcceptedResponse"];
export type BranchCandidateActionResponse = components["schemas"]["BranchCandidateActionResponse"];
export type BranchSearchDetailResponse = components["schemas"]["BranchSearchDetailResponse"];
export type BranchSearchListPageResponse = components["schemas"]["BranchSearchListPageResponse"];
export type ChangesetDetailResponse = components["schemas"]["ChangesetDetailResponse"];
export type ChangesetListPageResponse = components["schemas"]["ChangesetListPageResponse"];
export type ChangesetActionResponse = components["schemas"]["ChangesetActionResponse"];
export type CommitReadinessResponse = components["schemas"]["CommitReadinessResponse"];
export type CommitMessageSuggestionResponse =
  components["schemas"]["CommitMessageSuggestionResponse"];
export type ChangesetReviewBriefGenerateResponse =
  components["schemas"]["ChangesetReviewBriefGenerateResponse"];
export type ChangesetVerificationPlanPreviewResponse =
  components["schemas"]["ChangesetVerificationPlanPreviewResponse"];
export type WorkspaceMemoryListPageResponse =
  components["schemas"]["WorkspaceMemoryListPageResponse"];
export type WorkspaceMemoryDetailResponse = components["schemas"]["WorkspaceMemoryDetailResponse"];
export type WorkspaceMemoryPrunePreviewResponse =
  components["schemas"]["WorkspaceMemoryPrunePreviewResponse"];
export type RepositoryIndexStatusResponse = components["schemas"]["RepositoryIndexStatusResponse"];
export type RepositoryIndexSearchPageResponse =
  components["schemas"]["RepositoryIndexSearchPageResponse"];
export type RepositoryIndexEntryDetailResponse =
  components["schemas"]["RepositoryIndexEntryDetailResponse"];
export type RepositoryIndexRebuildResponse =
  components["schemas"]["RepositoryIndexRebuildResponse"];
export type ForkSessionResponse = components["schemas"]["ForkSessionResponse"];
export type ApprovalDecision = components["schemas"]["ApprovalDecision"];
export type AutonomyBudget = components["schemas"]["AutonomyBudget"];
export type AutonomyMode = components["schemas"]["AutonomyMode"];
export type WorkspaceMemoryKind = components["schemas"]["WorkspaceMemoryKind"];
export type WorkspaceMemoryState = components["schemas"]["WorkspaceMemoryState"];
export type FastApiValidationIssue = NonNullable<
  components["schemas"]["HTTPValidationError"]["detail"]
>[number];

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
export type TaskListPageQuery = NonNullable<paths["/tasks"]["get"]["parameters"]["query"]>;
export type BranchSearchListPageQuery = NonNullable<
  paths["/branch-searches"]["get"]["parameters"]["query"]
>;
export type ChangesetListPageQuery = NonNullable<
  paths["/changesets"]["get"]["parameters"]["query"]
>;
export type TaskStepPageQuery = NonNullable<
  paths["/tasks/{task_id}/steps"]["get"]["parameters"]["query"]
>;
export type TaskEventPageQuery = NonNullable<
  paths["/tasks/{task_id}/events"]["get"]["parameters"]["query"]
>;
export type WorkspaceMemoryListPageQuery = NonNullable<
  paths["/memory"]["get"]["parameters"]["query"]
>;
export type RepositoryIndexSearchQuery = NonNullable<
  paths["/repo/index/search"]["get"]["parameters"]["query"]
>;

export type ApiErrorKind =
  | "cancelled"
  | "conflict"
  | "http"
  | "network"
  | "not_found"
  | "unavailable"
  | "validation";

export class GlassboxApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly detail: unknown;
  readonly issues: FastApiValidationIssue[];

  constructor({
    kind,
    message,
    status = null,
    detail = null,
    issues = [],
  }: {
    kind: ApiErrorKind;
    message: string;
    status?: number | null;
    detail?: unknown;
    issues?: FastApiValidationIssue[];
  }) {
    super(message);
    this.name = "GlassboxApiError";
    this.kind = kind;
    this.status = status;
    this.detail = detail;
    this.issues = issues;
  }
}

export type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export type RequestOptions = {
  signal?: AbortSignal;
};

export type GlassboxApiClientOptions = {
  baseUrl?: string;
  fetch?: FetchLike;
};

type QueryValue = string | number | boolean | null | undefined;
type Query = Record<string, QueryValue>;

type JsonRequestOptions = RequestOptions & {
  body?: unknown;
  query?: Query;
};

export function createGlassboxApiClient(options: GlassboxApiClientOptions = {}) {
  const fetchImpl = options.fetch ?? globalThis.fetch?.bind(globalThis);
  const baseUrl = options.baseUrl ?? process.env.NEXT_PUBLIC_GLASSBOX_API_BASE_URL;

  if (fetchImpl === undefined) {
    throw new GlassboxApiError({
      kind: "network",
      message: "No fetch implementation is available for Glassbox API requests.",
    });
  }

  const requestJson = <T>(
    method: "GET" | "POST",
    path: string,
    requestOptions: JsonRequestOptions = {},
  ) => requestJsonWithFetch<T>(fetchImpl, baseUrl, method, path, requestOptions);

  return {
    getHealth: (requestOptions?: RequestOptions) =>
      requestJson<HealthResponse>("GET", "/healthz", requestOptions),

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

    getTaskPage: (query: TaskListPageQuery = {}, requestOptions?: RequestOptions) =>
      requestJson<TaskListPageResponse>("GET", "/tasks", { ...requestOptions, query }),

    getTaskDetail: (taskId: string, requestOptions?: RequestOptions) =>
      requestJson<TaskDetailResponse>(
        "GET",
        `/tasks/${encodeURIComponent(taskId)}`,
        requestOptions,
      ),

    getTaskStepPage: (
      taskId: string,
      query: TaskStepPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<TaskStepPageResponse>("GET", `/tasks/${encodeURIComponent(taskId)}/steps`, {
        ...requestOptions,
        query,
      }),

    getTaskEventPage: (
      taskId: string,
      query: TaskEventPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<TaskEventPageResponse>("GET", `/tasks/${encodeURIComponent(taskId)}/events`, {
        ...requestOptions,
        query,
      }),

    approveTaskPlan: (
      input: { actor?: string; reason?: string | null; taskId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/approve-plan`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    continueTask: (
      input: {
        checkpointId?: string | null;
        continueForMinutes?: number | null;
        reason?: string | null;
        requestedBy?: string;
        taskId: string;
        verifyRepair?: boolean;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<BackgroundJobDetailResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/continue`,
        {
          ...requestOptions,
          body: {
            checkpoint_id: input.checkpointId ?? null,
            continue_for_minutes: input.continueForMinutes ?? null,
            reason: input.reason ?? null,
            requested_by: input.requestedBy ?? "operator",
            verify_repair: input.verifyRepair ?? true,
          },
        },
      ),

    resolveTaskContinuationWindow: (
      input: {
        checkpointId?: string | null;
        decidedBy?: string;
        decision?: ApprovalDecision;
        reason?: string | null;
        requestedBy?: string;
        requestedMinutes: number;
        taskId: string;
        verifyRepair?: boolean;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<TaskContinuationWindowActionResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/continuation-window`,
        {
          ...requestOptions,
          body: {
            checkpoint_id: input.checkpointId ?? null,
            decided_by: input.decidedBy ?? "operator",
            decision: input.decision ?? "approved",
            reason: input.reason ?? null,
            requested_by: input.requestedBy ?? "operator",
            requested_minutes: input.requestedMinutes,
            verify_repair: input.verifyRepair ?? true,
          },
        },
      ),

    scheduleTaskPauseWindow: (
      input: {
        checkpointId?: string | null;
        pauseBefore?: string | null;
        policy: components["schemas"]["PauseWindowPolicy"];
        reason?: string | null;
        taskId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<TaskPauseWindowResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/pause-window`,
        {
          ...requestOptions,
          body: {
            actor: "operator",
            checkpoint_id: input.checkpointId ?? null,
            pause_before: input.pauseBefore ?? null,
            policy: input.policy,
            reason: input.reason ?? null,
          },
        },
      ),

    cancelTaskPauseWindow: (
      input: {
        pauseWindowId: string;
        reason?: string | null;
        taskId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<TaskPauseWindowResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/pause-window/${encodeURIComponent(
          input.pauseWindowId,
        )}/cancel`,
        {
          ...requestOptions,
          body: {
            actor: "operator",
            reason: input.reason ?? "operator override",
          },
        },
      ),

    pauseTask: (
      input: {
        actor?: string;
        detail?: string | null;
        reason?: components["schemas"]["TaskBlockedReason"];
        taskId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/pause`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            detail: input.detail ?? null,
            reason: input.reason ?? "manual_pause",
          },
        },
      ),

    resumeTask: (
      input: { actor?: string; reason?: string | null; taskId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/resume`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    cancelTask: (
      input: { actor?: string; reason?: string | null; taskId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/cancel`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    adjustTaskBudget: (
      input: {
        actor?: string;
        budget: AutonomyBudget;
        detail?: string | null;
        mode: AutonomyMode;
        reason?: string | null;
        taskId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/budget`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            budget: input.budget,
            detail: input.detail ?? null,
            mode: input.mode,
            reason: input.reason ?? null,
          },
        },
      ),

    cancelBackgroundJob: (
      input: { actor?: string; jobId: string; reason?: string | null },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<BackgroundJobDetailResponse>(
        "POST",
        `/jobs/${encodeURIComponent(input.jobId)}/cancel`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    getBranchSearchPage: (query: BranchSearchListPageQuery = {}, requestOptions?: RequestOptions) =>
      requestJson<BranchSearchListPageResponse>("GET", "/branch-searches", {
        ...requestOptions,
        query,
      }),

    getBranchSearchDetail: (searchId: string, requestOptions?: RequestOptions) =>
      requestJson<BranchSearchDetailResponse>(
        "GET",
        `/branch-searches/${encodeURIComponent(searchId)}`,
        requestOptions,
      ),

    markBranchCandidate: (
      input: {
        action: "needs-review" | "reject" | "select";
        actor?: string;
        candidateId: string;
        reason: string;
        searchId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<BranchCandidateActionResponse>(
        "POST",
        `/branch-searches/${encodeURIComponent(input.searchId)}/candidates/${encodeURIComponent(
          input.candidateId,
        )}/${input.action}`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason },
        },
      ),

    getChangesetPage: (query: ChangesetListPageQuery = {}, requestOptions?: RequestOptions) =>
      requestJson<ChangesetListPageResponse>("GET", "/changesets", {
        ...requestOptions,
        query,
      }),

    getChangesetDetail: (changesetId: string, requestOptions?: RequestOptions) =>
      requestJson<ChangesetDetailResponse>(
        "GET",
        `/changesets/${encodeURIComponent(changesetId)}`,
        requestOptions,
      ),

    getChangesetVerificationPlan: (changesetId: string, requestOptions?: RequestOptions) =>
      requestJson<ChangesetVerificationPlanPreviewResponse>(
        "GET",
        `/changesets/${encodeURIComponent(changesetId)}/verification-plan`,
        requestOptions,
      ),

    getChangesetCommitReadiness: (changesetId: string, requestOptions?: RequestOptions) =>
      requestJson<CommitReadinessResponse>(
        "GET",
        `/changesets/${encodeURIComponent(changesetId)}/commit-readiness`,
        requestOptions,
      ),

    getChangesetCommitMessage: (changesetId: string, requestOptions?: RequestOptions) =>
      requestJson<CommitMessageSuggestionResponse>(
        "GET",
        `/changesets/${encodeURIComponent(changesetId)}/commit-message`,
        requestOptions,
      ),

    generateChangesetReviewBrief: (
      input: { actor?: string; changesetId: string; includeMarkdown?: boolean },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ChangesetReviewBriefGenerateResponse>(
        "POST",
        `/changesets/${encodeURIComponent(input.changesetId)}/brief`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            include_markdown: input.includeMarkdown ?? false,
          },
        },
      ),

    refreshChangeset: (
      input: { actor?: string; changesetId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ChangesetActionResponse>(
        "POST",
        `/changesets/${encodeURIComponent(input.changesetId)}/refresh`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator" },
        },
      ),

    listWorkspaceMemory: (
      query: WorkspaceMemoryListPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<WorkspaceMemoryListPageResponse>("GET", "/memory", { ...requestOptions, query }),

    getWorkspaceMemoryDetail: (memoryId: string, requestOptions?: RequestOptions) =>
      requestJson<WorkspaceMemoryDetailResponse>(
        "GET",
        `/memory/${encodeURIComponent(memoryId)}`,
        requestOptions,
      ),

    confirmWorkspaceMemory: (
      input: { actor?: string; memoryId: string; reason?: string | null },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<WorkspaceMemoryDetailResponse>(
        "POST",
        `/memory/${encodeURIComponent(input.memoryId)}/confirm`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    invalidateWorkspaceMemory: (
      input: { actor?: string; memoryId: string; reason: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<WorkspaceMemoryDetailResponse>(
        "POST",
        `/memory/${encodeURIComponent(input.memoryId)}/invalidate`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason },
        },
      ),

    previewWorkspaceMemoryPrune: (
      input: { actor?: string; memoryId: string; reason?: string | null },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<WorkspaceMemoryPrunePreviewResponse>(
        "POST",
        `/memory/${encodeURIComponent(input.memoryId)}/prune-preview`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    pruneWorkspaceMemory: (
      input: { actor?: string; memoryId: string; reason: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<WorkspaceMemoryDetailResponse>(
        "POST",
        `/memory/${encodeURIComponent(input.memoryId)}/prune`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason },
        },
      ),

    getRepositoryIndexStatus: (requestOptions?: RequestOptions) =>
      requestJson<RepositoryIndexStatusResponse>("GET", "/repo/index/status", requestOptions),

    searchRepositoryIndex: (query: RepositoryIndexSearchQuery, requestOptions?: RequestOptions) =>
      requestJson<RepositoryIndexSearchPageResponse>("GET", "/repo/index/search", {
        ...requestOptions,
        query,
      }),

    getRepositoryIndexEntryDetail: (entryId: string, requestOptions?: RequestOptions) =>
      requestJson<RepositoryIndexEntryDetailResponse>(
        "GET",
        `/repo/index/entries/${encodeURIComponent(entryId)}`,
        requestOptions,
      ),

    rebuildRepositoryIndex: (
      input: {
        background?: boolean;
        requestedBy?: string;
        sessionId?: string | null;
      } = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<RepositoryIndexRebuildResponse>("POST", "/repo/index/rebuild", {
        ...requestOptions,
        body: {
          background: input.background ?? true,
          requested_by: input.requestedBy ?? "operator",
          session_id: input.sessionId ?? null,
        },
      }),

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

export type GlassboxApiClient = ReturnType<typeof createGlassboxApiClient>;

async function requestJsonWithFetch<T>(
  fetchImpl: FetchLike,
  baseUrl: string | undefined,
  method: "GET" | "POST",
  path: string,
  { body, query, signal }: JsonRequestOptions,
): Promise<T> {
  let response: Response;

  try {
    response = await fetchImpl(buildApiUrl(baseUrl, path, query), {
      body: body === undefined ? undefined : JSON.stringify(body),
      headers: body === undefined ? undefined : { "content-type": "application/json" },
      method,
      signal,
    });
  } catch (error) {
    throw normalizeFetchError(error);
  }

  const payload = await readResponsePayload(response);
  if (!response.ok) {
    throw normalizeHttpError(response.status, payload);
  }

  return payload as T;
}

export function buildApiUrl(baseUrl: string | undefined, path: string, query?: Query): string {
  const normalizedBaseUrl = (baseUrl ?? "").replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${normalizedBaseUrl}${normalizedPath}`;
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null) {
      params.set(key, String(value));
    }
  }

  const queryString = params.toString();
  return queryString ? `${url}?${queryString}` : url;
}

async function readResponsePayload(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text.length === 0) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function normalizeFetchError(error: unknown): GlassboxApiError {
  if (isAbortError(error)) {
    return new GlassboxApiError({
      kind: "cancelled",
      message: "The Glassbox API request was cancelled.",
    });
  }

  return new GlassboxApiError({
    kind: "network",
    message: error instanceof Error ? error.message : "Glassbox API request failed.",
    detail: error,
  });
}

function normalizeHttpError(status: number, payload: unknown): GlassboxApiError {
  const detail = extractDetail(payload);
  const issues = extractValidationIssues(payload);

  if (status === 422 && issues.length > 0) {
    return new GlassboxApiError({
      kind: "validation",
      message: formatValidationMessage(issues),
      status,
      detail,
      issues,
    });
  }

  return new GlassboxApiError({
    kind: errorKindForStatus(status),
    message: typeof detail === "string" ? detail : `Glassbox API request failed (${status}).`,
    status,
    detail,
  });
}

function errorKindForStatus(status: number): ApiErrorKind {
  if (status === 404) {
    return "not_found";
  }
  if (status === 409) {
    return "conflict";
  }
  if (status === 503) {
    return "unavailable";
  }
  return "http";
}

function extractDetail(payload: unknown): unknown {
  if (payload !== null && typeof payload === "object" && "detail" in payload) {
    return (payload as { detail: unknown }).detail;
  }
  return payload;
}

function extractValidationIssues(payload: unknown): FastApiValidationIssue[] {
  const detail = extractDetail(payload);
  if (!Array.isArray(detail)) {
    return [];
  }
  return detail.filter(isValidationIssue);
}

function isValidationIssue(value: unknown): value is FastApiValidationIssue {
  return value !== null && typeof value === "object" && "msg" in value;
}

function formatValidationMessage(issues: FastApiValidationIssue[]): string {
  return issues
    .map((issue) => (typeof issue.msg === "string" ? issue.msg : "Validation error"))
    .join("; ");
}

function isAbortError(error: unknown): boolean {
  return (
    error !== null &&
    typeof error === "object" &&
    "name" in error &&
    (error as { name: unknown }).name === "AbortError"
  );
}
