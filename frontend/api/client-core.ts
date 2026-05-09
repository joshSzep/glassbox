import type { components } from "@/generated/api-types";

export type HealthResponse = components["schemas"]["HealthResponse"];
export type ActionAcceptedResponse = components["schemas"]["ActionAcceptedResponse"];
export type ApprovalDecision = components["schemas"]["ApprovalDecision"];
export type FastApiValidationIssue = NonNullable<
  components["schemas"]["HTTPValidationError"]["detail"]
>[number];

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

type QueryPrimitive = string | number | boolean;
type QueryValue = QueryPrimitive | QueryPrimitive[] | null | undefined;
export type Query = Record<string, QueryValue>;

export type JsonRequestOptions = RequestOptions & {
  body?: unknown;
  query?: Query;
};

export type RequestJson = <T>(
  method: "GET" | "POST",
  path: string,
  requestOptions?: JsonRequestOptions,
) => Promise<T>;

export function createRequestJson(options: GlassboxApiClientOptions = {}): RequestJson {
  const fetchImpl = options.fetch ?? globalThis.fetch?.bind(globalThis);
  const baseUrl = options.baseUrl ?? process.env.NEXT_PUBLIC_GLASSBOX_API_BASE_URL;

  if (fetchImpl === undefined) {
    throw new GlassboxApiError({
      kind: "network",
      message: "No fetch implementation is available for Glassbox API requests.",
    });
  }

  return <T>(method: "GET" | "POST", path: string, requestOptions: JsonRequestOptions = {}) =>
    requestJsonWithFetch<T>(fetchImpl, baseUrl, method, path, requestOptions);
}

export function createCoreEndpoints(requestJson: RequestJson) {
  return {
    getHealth: (requestOptions?: RequestOptions) =>
      requestJson<HealthResponse>("GET", "/healthz", requestOptions),
  };
}

export async function requestJsonWithFetch<T>(
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
    if (Array.isArray(value)) {
      for (const item of value) {
        params.append(key, String(item));
      }
    } else if (value !== undefined && value !== null) {
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
