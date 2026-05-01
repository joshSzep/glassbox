import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SessionStreamState } from "../api/sse";
import { WorkspaceOverview } from "../components/console/workspace-overview";
import {
  createDashboardState,
  hydrateSelectedSession,
  hydrateSessionAggregate,
} from "../state/session-state";
import {
  makeProjectionHealth,
  makeKnowledgePosture,
  makeProviderEvidence,
  makeSessionAggregate,
  makeSessionSnapshot,
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
            long_run_status: {
              ...makeSessionSummary("long-run-template").long_run_status,
              state: "paused",
              progress_summary: "session awaiting approval",
            },
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
    expect(markup).toContain("long run paused");
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
    expect(markup).toContain("uv run glassbox artifacts prune --dry-run --json --cwd .");
    expect(markup).toContain("before any non-dry-run cleanup");
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
          knowledge_posture: makeKnowledgePosture({ overall_status: "stale" }),
          queue: "degraded",
        },
      ),
    );

    expect(renderOverview(degradedState, "loaded", null, "degraded")).toContain(
      "2 projection alerts",
    );
    expect(renderOverview(degradedState, "loaded", null, "degraded")).toContain("knowledge stale");
    expect(renderOverview(degradedState, "loaded", null, "degraded")).toContain("stale");
    expect(renderOverview(degradedState, "loaded", null, "degraded")).toContain(
      "uv run glassbox projection check --all --cwd .",
    );
  });

  it("surfaces incomplete turn recovery posture in attention rows", () => {
    const recoveryState = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([
        makeSessionSummary("recovery-session", {
          action_needed: true,
          has_active_turn: false,
          next_action_summary: "Retry with a new prompt or fork",
          priority_bucket: "recovery",
          queue_memberships: ["active", "action-needed"],
          turn_recovery_posture: {
            next_action: "Retry with a new prompt or fork",
            reason: "provider stream was interrupted after restart",
            recovery_decision_id: "recovery-1",
            safe_to_resume: false,
            source_event_type: "RecoveryDecisionRecorded",
            state: "non_resumable",
            turn_id: "turn-1",
          },
        }),
      ]),
    );

    const markup = renderOverview(recoveryState, "loaded", null, "active");

    expect(markup).toContain("Retry with a new prompt or fork");
    expect(markup).toContain("Turn turn-1: non_resumable; exact resume unsafe");
    expect(markup).toContain("provider stream was interrupted after restart");
  });

  it("surfaces stale long-run progress in attention rows", () => {
    const staleState = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([
        makeSessionSummary("stale-session", {
          action_needed: true,
          long_run_status: {
            ...makeSessionSummary("long-run-template").long_run_status,
            current_attempt_tool_name: "pytest",
            heartbeat_age_seconds: 600,
            progress_summary: "pytest: heartbeat 600s ago",
            state: "stale",
            stuck_reason: "tool attempt heartbeat expired",
          },
          next_action_summary: "Inspect stale tool attempt",
          priority_bucket: "stale",
          queue_memberships: ["active", "action-needed"],
        }),
      ]),
    );

    const markup = renderOverview(staleState, "loaded", null, "active");

    expect(markup).toContain("Inspect stale tool attempt");
    expect(markup).toContain("long run stale");
    expect(markup).toContain("pytest: heartbeat 600s ago");
    expect(markup).toContain("tool attempt heartbeat expired");
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
      deliveryMode: "live",
      droppedEvents: 0,
      error: null,
      lastSequence: 12,
      projectionLag: 0,
      replayedCount: 0,
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

    const staleRuntime = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([], {
        runtime: {
          background_job_abandoned_count: 0,
          background_job_failed_count: 0,
          background_job_retryable_count: 0,
          dashboard_url: null,
          health: null,
          health_url: null,
          pid: 1234,
          session_index_url: null,
          started_at: "2026-04-23T00:00:00Z",
          state: "stale",
          workspace_root: "/tmp/glassbox",
        },
      }),
    );
    expect(renderOverview(staleRuntime, "loaded", null, "all")).toContain("Runtime owner stale");
    expect(renderOverview(staleRuntime, "loaded", null, "all")).toContain("stale owner");

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

  it("renders provider recovery guidance for retry and provider switch decisions", () => {
    const retryState = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([makeSessionSummary("provider-session")]),
    );
    const retrySnapshot = makeSessionSnapshot("provider-session", {
      latest_provider_recovery: {
        action: "retry_scheduled",
        attempt: 1,
        backoff_seconds: 4,
        checkpoint_id: null,
        created_at: "2026-04-30T12:00:00Z",
        degraded: false,
        failure_kind: "rate_limit",
        last_sequence: 5,
        max_attempts: 3,
        model_name: "gpt-5.4",
        next_retry_at: "2026-04-30T12:00:04Z",
        operator_next_action: "wait for bounded retry",
        provider: "openai",
        reason: "rate limit exceeded",
        retryable: true,
        safe_to_continue: true,
        session_id: "provider-session",
        task_id: null,
        turn_id: "turn-1",
      },
    });
    const retryMarkup = renderOverview(
      hydrateSelectedSession(retryState, retrySnapshot),
      "loaded",
      null,
      "active",
      "provider-session",
    );

    expect(retryMarkup).toContain("Retry within budget, or pause before switching provider.");
    expect(retryMarkup).toContain("bounded retry");

    const degradedMarkup = renderOverview(
      hydrateSelectedSession(
        retryState,
        makeSessionSnapshot("provider-session", {
          latest_provider_recovery: {
            ...retrySnapshot.latest_provider_recovery!,
            action: "retry_exhausted",
            degraded: true,
            safe_to_continue: false,
          },
        }),
      ),
      "loaded",
      null,
      "active",
      "provider-session",
    );

    expect(degradedMarkup).toContain(
      "Pause work, run diagnostics, and consider an operator-approved provider switch.",
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
  stream?: SessionStreamState,
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
