import { describe, expect, it } from "vitest";

import {
  GlassboxApiError,
  buildApiUrl,
  createGlassboxApiClient,
  type FetchLike,
} from "../api/client";

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    status: 200,
    ...init,
  });
}

function createMockFetch(responses: Response[]): {
  calls: { input: RequestInfo | URL; init?: RequestInit }[];
  fetch: FetchLike;
} {
  const calls: { input: RequestInfo | URL; init?: RequestInit }[] = [];
  const fetch: FetchLike = async (input, init) => {
    calls.push({ input, init });
    const response = responses.shift();
    if (response === undefined) {
      throw new Error("unexpected fetch call");
    }
    return response;
  };
  return { calls, fetch };
}

describe("buildApiUrl", () => {
  it("builds same-origin and absolute API URLs while omitting empty query values", () => {
    expect(buildApiUrl(undefined, "/healthz")).toBe("/healthz");
    expect(
      buildApiUrl("http://127.0.0.1:8765/", "/sessions/aggregate", {
        limit: 25,
        queue: "approvals",
        status: null,
      }),
    ).toBe("http://127.0.0.1:8765/sessions/aggregate?limit=25&queue=approvals");
  });
});

describe("createGlassboxApiClient", () => {
  it("fetches health and aggregate data with typed request shaping", async () => {
    const abortController = new AbortController();
    const { calls, fetch } = createMockFetch([
      jsonResponse({ status: "ok", event_transport: { degraded: false } }),
      jsonResponse({ sessions: [] }),
    ]);
    const client = createGlassboxApiClient({ baseUrl: "http://api.test/", fetch });

    await expect(client.getHealth({ signal: abortController.signal })).resolves.toMatchObject({
      status: "ok",
    });
    await expect(
      client.getSessionAggregate({ limit: 10, queue: "action-needed" }),
    ).resolves.toMatchObject({ sessions: [] });

    expect(calls[0]).toMatchObject({
      input: "http://api.test/healthz",
      init: { method: "GET", signal: abortController.signal },
    });
    expect(calls[1]).toMatchObject({
      input: "http://api.test/sessions/aggregate?limit=10&queue=action-needed",
      init: { method: "GET" },
    });
  });

  it("shapes operator action requests", async () => {
    const { calls, fetch } = createMockFetch([
      jsonResponse({ status: "ok" }),
      jsonResponse({ status: "ok" }),
      jsonResponse({ status: "ok" }),
      jsonResponse({ status: "ok" }),
      jsonResponse({ child_session_id: "child" }),
      jsonResponse({ session_id: "compare" }),
    ]);
    const client = createGlassboxApiClient({ fetch });

    await client.resolveApproval({
      approvalId: "approval/1",
      decision: "approved",
      sessionId: "session/1",
    });
    await client.submitMessage({ sessionId: "session/1", text: "Continue" });
    await client.submitAnswer({ answer: "blue", questionId: "question/1", sessionId: "session/1" });
    await client.cancelTurn({ reason: "stop", sessionId: "session/1", turnId: "turn/1" });
    await client.forkSession({ branchLabel: "alt", sessionId: "session/1", turnId: "turn/1" });
    await client.getCompareSessionSnapshot("compare/1");

    expect(calls.map((call) => call.input)).toEqual([
      "/sessions/session%2F1/approvals/approval%2F1",
      "/sessions/session%2F1/messages",
      "/sessions/session%2F1/questions/question%2F1",
      "/sessions/session%2F1/cancel",
      "/sessions/session%2F1/fork",
      "/sessions/compare%2F1",
    ]);
    expect(calls[0].init?.body).toBe(JSON.stringify({ decision: "approved" }));
    expect(calls[1].init?.body).toBe(JSON.stringify({ text: "Continue" }));
    expect(calls[2].init?.body).toBe(JSON.stringify({ answer: "blue" }));
    expect(calls[3].init?.body).toBe(JSON.stringify({ reason: "stop", turn_id: "turn/1" }));
    expect(calls[4].init?.body).toBe(JSON.stringify({ branch_label: "alt", turn_id: "turn/1" }));
  });

  it("normalizes FastAPI validation errors", async () => {
    const { fetch } = createMockFetch([
      jsonResponse(
        { detail: [{ loc: ["body", "text"], msg: "Field required", type: "missing" }] },
        { status: 422 },
      ),
    ]);
    const client = createGlassboxApiClient({ fetch });

    await expect(client.submitMessage({ sessionId: "session-1", text: "" })).rejects.toMatchObject({
      issues: [{ msg: "Field required" }],
      kind: "validation",
      message: "Field required",
      status: 422,
    });
  });

  it("normalizes conflict, unavailable, network, and cancelled failures", async () => {
    const conflictClient = createGlassboxApiClient({
      fetch: async () => jsonResponse({ detail: "approval already resolved" }, { status: 409 }),
    });
    await expect(
      conflictClient.resolveApproval({
        approvalId: "approval-1",
        decision: "denied",
        sessionId: "session-1",
      }),
    ).rejects.toMatchObject({ kind: "conflict", message: "approval already resolved" });

    const unavailableClient = createGlassboxApiClient({
      fetch: async () => jsonResponse({ detail: "runtime unavailable" }, { status: 503 }),
    });
    await expect(unavailableClient.getHealth()).rejects.toMatchObject({
      kind: "unavailable",
      message: "runtime unavailable",
    });

    const networkClient = createGlassboxApiClient({
      fetch: async () => {
        throw new TypeError("failed to fetch");
      },
    });
    await expect(networkClient.getHealth()).rejects.toMatchObject({
      kind: "network",
      message: "failed to fetch",
    });

    const cancelledClient = createGlassboxApiClient({
      fetch: async () => {
        throw new DOMException("aborted", "AbortError");
      },
    });
    await expect(cancelledClient.getHealth()).rejects.toBeInstanceOf(GlassboxApiError);
    await expect(cancelledClient.getHealth()).rejects.toMatchObject({ kind: "cancelled" });
  });
});
