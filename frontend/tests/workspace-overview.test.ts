import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { WorkspaceOverview } from "../components/console/workspace-overview";
import { createDashboardState, hydrateSessionAggregate } from "../state/session-state";
import {
  makeProjectionHealth,
  makeProviderEvidence,
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
            background_job_failed_count: 2,
            background_job_retryable_count: 1,
            background_job_abandoned_count: 0,
          },
        },
      ),
    );

    const markup = renderOverview(state, "loaded", null, "approvals");

    expect(markup).toContain("runtime online");
    expect(markup).toContain("projection fresh");
    expect(markup).toContain("1 retryable job");
    expect(markup).toContain("Workspace Attention");
    expect(markup).toContain("Approval needed");
    expect(markup).toContain("Approve command execution");
    expect(markup).toContain("/app/sessions/approval-session?queue=approvals");
    expect(markup).toContain("Queue approvals");
    expect(markup).toContain("Metric Patterns");
    expect(markup).toContain("Workspace metric patterns");
    expect(markup).toContain("Queue timing");
    expect(markup).toContain("Action waits");
    expect(markup).toContain("Projection pressure");
    expect(markup).toContain("Recovery Cues");
    expect(markup).toContain("Background jobs");
    expect(markup).toContain("uv run glassbox job list --state failed --cwd .");
    expect(markup).toContain("Repository index");
    expect(markup).toContain("uv run glassbox repo index status --cwd .");
    expect(markup).toContain("retained versus current source digest");
    expect(markup).toContain("Artifact pressure");
    expect(markup).toContain("Provider evidence");
    expect(markup).toContain("/tmp/glassbox");
    expect(markup).toContain("approval-session");
    expect(markup).toContain("Approve command execution");
    expect(markup).toContain("/app/sessions/approval-session?queue=approvals");
    expect(markup).toContain("Questions");
  });

  it("renders loading, empty, error, and degraded states", () => {
    const emptyState = hydrateSessionAggregate(createDashboardState(), makeSessionAggregate([]));
    expect(renderOverview(emptyState, "idle", null, "all")).toContain("runtime offline");
    expect(renderOverview(emptyState, "idle", null, "all")).toContain("No workspace action needed");
    expect(renderOverview(emptyState, "idle", null, "all")).toContain(
      "No approvals, questions, failures, degraded projections, or provider cues need attention.",
    );
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
    expect(renderOverview(degradedState, "loaded", null, "degraded")).toContain(
      "uv run glassbox projection check --all --cwd .",
    );
  });

  it("renders route-aware status rail context and stream states", () => {
    const runningState = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([makeSessionSummary("session-1")], {
        queue: "active",
        runtime: {
          background_job_abandoned_count: 0,
          background_job_failed_count: 0,
          background_job_retryable_count: 0,
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
          background_job_abandoned_count: 0,
          background_job_failed_count: 0,
          background_job_retryable_count: 0,
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
    expect(renderOverview(degradedRuntime, "loaded", null, "all")).toContain(
      "uv run glassbox daemon status --cwd .",
    );

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

  it("renders provider evidence cues for fresh, stale, missing, and warning states", () => {
    const freshState = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([], {
        provider_evidence: makeProviderEvidence({
          freshness_status: "fresh",
          latest_status: "passed",
          model_name: "openai:gpt-5.4",
          next_actions: ["inspect provider canary evidence /tmp/provider-canary-summary.json"],
          provider: "openai",
          summary_count: 1,
        }),
      }),
    );
    const freshMarkup = renderOverview(freshState, "loaded", null, "all");
    expect(freshMarkup).toContain("Provider evidence");
    expect(freshMarkup).toContain("openai openai:gpt-5.4");
    expect(freshMarkup).toContain("advisory fresh evidence");
    expect(freshMarkup).toContain("uv run glassbox provider diagnostics --cwd .");
    expect(freshMarkup).toContain("uv run glassbox provider canary evidence --cwd .");

    const staleState = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([], {
        provider_evidence: makeProviderEvidence({
          freshness_status: "stale",
          latest_status: "passed",
          model_name: "openai:gpt-5.4",
          provider: "openai",
        }),
      }),
    );
    expect(renderOverview(staleState, "loaded", null, "all")).toContain(
      "Provider evidence is stale for openai:gpt-5.4; advisory only.",
    );

    const missingMarkup = renderOverview(
      hydrateSessionAggregate(createDashboardState(), makeSessionAggregate([])),
      "loaded",
      null,
      "all",
    );
    expect(missingMarkup).toContain("provider not configured");
    expect(missingMarkup).toContain("advisory missing evidence");

    const warningMarkup = renderOverview(
      hydrateSessionAggregate(
        createDashboardState(),
        makeSessionAggregate([], {
          provider_evidence: makeProviderEvidence({
            freshness_status: "warning",
            latest_status: "warning",
            model_name: "anthropic:claude-sonnet-4",
            provider: "anthropic",
          }),
        }),
      ),
      "loaded",
      null,
      "all",
    );
    expect(warningMarkup).toContain("Provider evidence advisory");
    expect(warningMarkup).toContain("advisory warning evidence");
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

  it("renders a mobile return path for selected-session drill-in", () => {
    const state = hydrateSessionAggregate(
      createDashboardState(),
      makeV4ScenarioAggregate("all-queues", "questions"),
    );
    const markup = renderOverview(
      state,
      "loaded",
      null,
      "questions",
      "session-1",
      undefined,
      React.createElement("aside", null, "Inspector pane"),
    );

    expect(markup).toContain("Back to Questions queue");
    expect(markup).toContain("/app/queues/questions");
    expect(markup).toContain("xl:hidden");
    expect(markup).toContain("Inspector pane");
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
  inspector?: React.ReactNode,
): string {
  return renderToStaticMarkup(
    React.createElement(WorkspaceOverview, {
      data,
      error,
      inspector,
      loadState,
      selectedQueue,
      selectedSessionId,
      stream,
    }),
  );
}
