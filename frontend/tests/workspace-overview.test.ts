import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { WorkspaceOverview } from "../components/console/workspace-overview";
import { createDashboardState, hydrateSessionAggregate } from "../state/session-state";
import {
  makeProjectionHealth,
  makeSessionAggregate,
  makeSessionSummary,
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
    expect(markup).toContain("/tmp/glassbox");
    expect(markup).toContain("approval-session");
    expect(markup).toContain("Approve command execution");
    expect(markup).toContain("/app/sessions/approval-session?queue=approvals");
    expect(markup).toContain("Questions");
  });

  it("renders loading, empty, error, and degraded states", () => {
    const emptyState = hydrateSessionAggregate(createDashboardState(), makeSessionAggregate([]));
    expect(renderOverview(emptyState, "loading", null, "all")).toContain(
      "Loading workspace queues",
    );
    expect(renderOverview(emptyState, "loaded", null, "all")).toContain(
      "No sessions in this queue",
    );
    expect(renderOverview(emptyState, "failed", "network unavailable", "all")).toContain(
      "network unavailable",
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

    expect(renderOverview(degradedState, "loaded", null, "degraded")).toContain("2 degraded");
    expect(renderOverview(degradedState, "loaded", null, "degraded")).toContain("stale");
  });
});

function renderOverview(
  data: ReturnType<typeof createDashboardState>,
  loadState: "failed" | "idle" | "loaded" | "loading",
  error: string | null,
  selectedQueue: "active" | "all" | "approvals" | "degraded",
): string {
  return renderToStaticMarkup(
    React.createElement(WorkspaceOverview, {
      data,
      error,
      loadState,
      selectedQueue,
    }),
  );
}
