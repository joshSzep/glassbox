import type { components, paths } from "@/generated/api-types";

export type HealthResponse = components["schemas"]["HealthResponse"];
export type SessionSummaryResponse = components["schemas"]["SessionSummaryResponse"];
export type SessionAggregateResponse = components["schemas"]["SessionAggregateResponse"];
export type SessionSnapshotResponse = components["schemas"]["SessionSnapshotResponse"];
export type ActionAcceptedResponse = components["schemas"]["ActionAcceptedResponse"];
export type ForkSessionResponse = components["schemas"]["ForkSessionResponse"];
export type ApprovalDecision = components["schemas"]["ApprovalDecision"];
export type FastApiValidationIssue = NonNullable<
  components["schemas"]["HTTPValidationError"]["detail"]
>[number];

export type SessionAggregateQuery = NonNullable<
  paths["/sessions/aggregate"]["get"]["parameters"]["query"]
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
