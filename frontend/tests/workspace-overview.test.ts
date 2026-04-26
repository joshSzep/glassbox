import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { WorkspaceOverview } from "../components/console/workspace-overview";
import { createDashboardState, hydrateSessionAggregate } from "../state/session-state";
import {
  makeProjectionHealth,
  makeSessionAggregate,
  makeSessionSummary,
  makeV4ScenarioAggregate,
} from "./fixtures/session-state";

describe("workspace overview console", () => {
  it("renders runtime, queue counts, and prioritized aggregate rows", () => {
    const state = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate(
        [
          makeSessionSummary("approval-session", {
            action_needed: true,
            next_action_summary: "Approve command execution",
            pending_approval_id: "approval-1",
            queue_memberships: ["approvals", "action-needed"],
          }),
          makeSessionSummary("question-session", {
            next_action_summary: "Answer pending question",
            pending_question_id: "question-1",
            pending_question_text: "Which branch should be used?",
            queue_memberships: ["questions"],
          }),
        ],
        {
          queue: "approvals",
          runtime: {
            dashboard_url: null,
            health: "ok",
            health_url: null,
            pid: 1234,
            session_index_url: null,
            started_at: "2026-04-23T00:00:00Z",
            state: "running",
            workspace_root: "/tmp/glassbox",
          },
        },
      ),
    );

    const markup = renderOverview(state, "loaded", null, "approvals");

    expect(markup).toContain("runtime online");
    expect(markup).toContain("projection fresh");
    expect(markup).toContain("Queue approvals");
    expect(markup).toContain("/tmp/glassbox");
    expect(markup).toContain("approval-session");
    expect(markup).toContain("Approve command execution");
    expect(markup).toContain("/app/sessions/approval-session?queue=approvals");
    expect(markup).toContain("Questions");
  });

  it("renders loading, empty, error, and degraded states", () => {
    const emptyState = hydrateSessionAggregate(createDashboardState(), makeSessionAggregate([]));
    expect(renderOverview(emptyState, "idle", null, "all")).toContain("runtime offline");
    expect(renderOverview(emptyState, "idle", null, "all")).toContain("not loaded");
    expect(renderOverview(emptyState, "loading", null, "all")).toContain(
      "Loading workspace queues",
    );
    expect(renderOverview(emptyState, "loading", null, "all")).toContain("refreshing");
    expect(renderOverview(emptyState, "loaded", null, "all")).toContain(
      "No sessions in this queue",
    );
    expect(renderOverview(emptyState, "failed", "network unavailable", "all")).toContain(
      "network unavailable",
    );
    expect(renderOverview(emptyState, "failed", "network unavailable", "all")).toContain(
      "refresh failed",
    );

    const degradedState = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate(
        [
          makeSessionSummary("degraded-session", {
            projection_health: makeProjectionHealth({ degraded: true, state: "stale" }),
            queue_memberships: ["degraded"],
          }),
        ],
        {
          projection_health_counts: { degraded: 1, ok: 0, stale: 1, unavailable: 0 },
          queue: "degraded",
        },
      ),
    );

    expect(renderOverview(degradedState, "loaded", null, "degraded")).toContain(
      "2 projection alerts",
    );
    expect(renderOverview(degradedState, "loaded", null, "degraded")).toContain("stale");
  });

  it("renders route-aware status rail context and stream states", () => {
    const runningState = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([makeSessionSummary("session-1")], {
        queue: "active",
        runtime: {
          dashboard_url: null,
          health: "ok",
          health_url: null,
          pid: 1234,
          session_index_url: null,
          started_at: "2026-04-23T00:00:00Z",
          state: "running",
          workspace_root: "/tmp/glassbox",
        },
      }),
    );
    const selectedMarkup = renderOverview(runningState, "loaded", null, "active", "session-1", {
      error: null,
      lastSequence: 12,
      retryCount: 0,
      status: "live",
    });

    expect(selectedMarkup).toContain("Session session-1");
    expect(selectedMarkup).toContain("stream live");

    const degradedRuntime = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([], {
        runtime: {
          dashboard_url: null,
          health: "degraded",
          health_url: null,
          pid: 1234,
          session_index_url: null,
          started_at: "2026-04-23T00:00:00Z",
          state: "degraded",
          workspace_root: "/tmp/glassbox",
        },
      }),
    );
    expect(renderOverview(degradedRuntime, "loaded", null, "all")).toContain("runtime degraded");

    const missingProjection = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([], {
        projection_health_counts: { degraded: 0, ok: 0, stale: 0, unavailable: 1 },
      }),
    );
    expect(renderOverview(missingProjection, "loaded", null, "all")).toContain(
      "1 projection missing",
    );
  });

  it("renders dense attention rows for urgent, degraded, active, and historical sessions", () => {
    const state = hydrateSessionAggregate(
      createDashboardState(),
      makeV4ScenarioAggregate("all-queues"),
    );
    const markup = renderOverview(state, "loaded", null, "all", "approval-session");

    expect(markup).toContain("Session attention rows");
    expect(markup).toContain("Review pending approval");
    expect(markup).toContain("Approval approval-1");
    expect(markup).toContain("Answer pending question");
    expect(markup).toContain("Question Which branch should be inspected?");
    expect(markup).toContain("Inspect retryable failure");
    expect(markup).toContain("Retryable failure: frontend e2e workflow failed");
    expect(markup).toContain("Projection stale: canonical events remain authoritative.");
    expect(markup).toContain("Review historical snapshot");
    expect(markup).toContain("historical only");
    expect(markup).toContain('data-state="selected"');
    expect(markup).toContain("/app/sessions/approval-session");
  });

  it("renders queue filter counts, all-session filter, and priority summary", () => {
    const state = hydrateSessionAggregate(
      createDashboardState(),
      makeV4ScenarioAggregate("all-queues", "approvals"),
    );
    const markup = renderOverview(state, "loaded", null, "approvals");

    expect(markup).toContain("Queue priority summary");
    expect(markup).toContain("Top priority");
    expect(markup).toContain("3 approvals");
    expect(markup).toContain("Review approval risk before prompts");
    expect(markup).toContain("All");
    expect(markup).toContain("/app");
    expect(markup).toContain('aria-current="page"');
    expect(markup).toContain("Showing 3 of 8 server-prioritized sessions.");
    expect(markup).toContain("5 rows are hidden by the current queue filter.");
    expect(markup).toContain("3 shown");
  });
});

function renderOverview(
  data: ReturnType<typeof createDashboardState>,
  loadState: "failed" | "idle" | "loaded" | "loading",
  error: string | null,
  selectedQueue:
    | "active"
    | "all"
    | "approvals"
    | "degraded"
    | "failures"
    | "historical"
    | "questions",
  selectedSessionId: string | null = null,
  stream?: {
    error: string | null;
    lastSequence: number;
    retryCount: number;
    status: "connecting" | "historical_snapshot" | "live" | "live_unavailable" | "reconnecting";
  },
): string {
  return renderToStaticMarkup(
    React.createElement(WorkspaceOverview, {
      data,
      error,
      loadState,
      selectedQueue,
      selectedSessionId,
      stream,
    }),
  );
}
