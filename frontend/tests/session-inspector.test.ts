import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SessionInspector } from "../components/console/session-inspector";
import { WorkspaceOverview } from "../components/console/workspace-overview";
import {
  createDashboardState,
  type DashboardState,
  hydrateCompareSession,
  hydrateSelectedSession,
} from "../state/session-state";
import {
  makeProjectionHealth,
  makeRuntimeContext,
  makeSessionAggregate,
  makeSessionSnapshot,
  makeSessionSummary,
  makeV4ScenarioSnapshot,
} from "./fixtures/session-state";

const stream = {
  error: null,
  lastSequence: 12,
  retryCount: 0,
  status: "live" as const,
};

describe("session inspector", () => {
  it("renders overview with priority action, status, narrative, and scoped evidence", () => {
    const data = makeRichSessionData();

    const markup = renderToStaticMarkup(
      React.createElement(SessionInspector, {
        activeTab: "overview",
        data,
        error: null,
        loadState: "loaded",
        queue: "active",
        stream,
      }),
    );

    expect(markup).toContain("Next action");
    expect(markup).toContain("awaiting approval");
    expect(markup).toContain("Review the pending approval before continuing.");
    expect(markup).toContain("Session readout");
    expect(markup).toContain("Runtime owner");
    expect(markup).toContain("Recent narrative");
    expect(markup).toContain("Decision context");
    expect(markup).toContain("Health attention");
    expect(markup).toContain("projection degraded");
    expect(markup).toContain("Continue session");
    expect(markup).toContain("Answer pending question");
    expect(markup).toContain("Approve");
    expect(markup).toContain("Deny");
    expect(markup).toContain("Create fork");
    expect(markup).toContain("Transcript");
    expect(markup).toContain("session-1");
    expect(markup).toContain("projection stale");
    expect(markup).toContain("I will inspect the console.");
    expect(markup).not.toContain("Runtime context");
    expect(markup).not.toContain("Event evidence");
    expect(markup).not.toContain("Verification cues");
    expect(markup).not.toContain("Open compared");
  });

  it("prioritizes overview next actions across selected-session states", () => {
    const cases = [
      ["approval-session", "pending-approval", "awaiting approval"],
      ["question-session", "pending-question", "awaiting answer"],
      ["failed-session", "failed-session", "retryable failure"],
      ["active-session", "live-session", "active tool call"],
      ["historical-session", "historical-session", "historical snapshot"],
      ["degraded-session", "projection-degraded", "projection degraded"],
    ] as const;

    for (const [sessionId, scenarioId, expectedText] of cases) {
      const snapshot =
        sessionId === "active-session"
          ? makeSessionSnapshot(sessionId, {
              active_tool_calls: [
                {
                  completed_at: null,
                  policy_outcome: "allow",
                  policy_reason: "read only",
                  policy_risk_level: "low",
                  policy_source_kind: "tool_policy",
                  policy_source_label: "default",
                  started_at: "2026-04-23T00:00:02Z",
                  status: "running",
                  summary: "Run verification suite",
                  tool_call_id: "tool-active",
                  tool_name: "pytest",
                  turn_id: "turn-1",
                },
              ],
            })
          : makeV4ScenarioSnapshot(sessionId, scenarioId);
      const data = hydrateSelectedSession(createDashboardState(), snapshot);
      const markup = renderInspectorTab(data, "overview");

      expect(markup).toContain(expectedText);
    }
  });

  it("renders only the active inspector tab content", () => {
    const data = makeRichSessionData();

    const runtimeMarkup = renderInspectorTab(data, "runtime");
    expect(runtimeMarkup).toContain("Runtime context");
    expect(runtimeMarkup).toContain("Working set");
    expect(runtimeMarkup).toContain("Runtime notes");
    expect(runtimeMarkup).toContain("Artifact provenance");
    expect(runtimeMarkup).toContain("frontend/app/page.tsx");
    expect(runtimeMarkup).not.toContain("Continue session");
    expect(runtimeMarkup).not.toContain("Inspect the console");

    const compareMarkup = renderInspectorTab(data, "compare");
    expect(compareMarkup).toContain("Compare");
    expect(compareMarkup).toContain("Open compared");
    expect(compareMarkup).toContain("parent-1");
    expect(compareMarkup).not.toContain("frontend/app/page.tsx");

    const evidenceMarkup = renderInspectorTab(data, "evidence");
    expect(evidenceMarkup).toContain("Verification cues");
    expect(evidenceMarkup).toContain("Evidence overview");
    expect(evidenceMarkup).toContain("Stream state");
    expect(evidenceMarkup).toContain("Projection details");
    expect(evidenceMarkup).toContain("Raw metric details");
    expect(evidenceMarkup).toContain("Event evidence");
    expect(evidenceMarkup).toContain("pytest passed");

    const metricsMarkup = renderInspectorTab(data, "metrics");
    expect(metricsMarkup).toContain("Metrics");
    expect(metricsMarkup).toContain("Metrics summary");
    expect(metricsMarkup).toContain("Raw turn metrics");
    expect(metricsMarkup).toContain("Tokens");
    expect(metricsMarkup).toContain("6.5s");
    expect(metricsMarkup).not.toContain("Continue session");
  });

  it("preserves direct links for inspector tabs", () => {
    const data = makeRichSessionData();
    const markup = renderInspectorTab(data, "lineage");

    expect(markup).toContain("/app/sessions/session-1?queue=active&amp;compare=parent-1");
    expect(markup).toContain("tab=transcript");
    expect(markup).toContain("tab=lineage");
    expect(markup).toContain("tab=evidence");
    expect(markup).toContain("tab=events");
  });

  it("renders lineage and transcript as scoped tab content", () => {
    const data = makeRichSessionData();

    const lineageMarkup = renderInspectorTab(data, "lineage");
    expect(lineageMarkup).toContain("Lineage and turns");
    expect(lineageMarkup).toContain("Current lineage anchor");
    expect(lineageMarkup).toContain("Current session");
    expect(lineageMarkup).toContain("Child sessions");
    expect(lineageMarkup).toContain("Forkable turns");
    expect(lineageMarkup).toContain("Parent parent-1");
    expect(lineageMarkup).toContain("Compare parent-1");
    expect(lineageMarkup).toContain("Open child-1");
    expect(lineageMarkup).toContain("Open fork flow for Continue from tool result");
    expect(lineageMarkup).not.toContain("Continue session");

    const transcriptMarkup = renderInspectorTab(data, "transcript");
    expect(transcriptMarkup).toContain("Transcript");
    expect(transcriptMarkup).toContain("Inspect the console");
    expect(transcriptMarkup).toContain("Latest activity");
    expect(transcriptMarkup).toContain("Session narrative turns");
    expect(transcriptMarkup).toContain("Approval: apply patch");
    expect(transcriptMarkup).toContain("Live stdout");
    expect(transcriptMarkup).not.toContain("Lineage and turns");
  });

  it("renders a focused timeline with jumps, metrics, and fork affordances", () => {
    const data = makeRichSessionData();

    const markup = renderInspectorTab(data, "timeline");

    expect(markup).toContain("Timeline");
    expect(markup).toContain("Timeline jumps");
    expect(markup).toContain("Timeline turns");
    expect(markup).toContain("Active turn");
    expect(markup).toContain("Pending action");
    expect(markup).toContain("Fork boundary");
    expect(markup).toContain("1 model");
    expect(markup).toContain("2 pending intervention");
    expect(markup).toContain("1 active tool");
    expect(markup).toContain("1 live output");
    expect(markup).toContain("Open fork flow for Continue from tool result");
    expect(markup).not.toContain("Session narrative turns");
  });

  it("renders transcript narrative states across fixture scenarios", () => {
    const cases = [
      ["approval-session", "pending-approval", "Approval:"],
      ["question-session", "pending-question", "Question"],
      ["failed-session", "failed-session", "Retryable failure"],
      ["historical-session", "historical-session", "historical"],
      ["large-transcript-session", "large-transcript", "Live stdout"],
    ] as const;

    for (const [sessionId, scenarioId, expectedText] of cases) {
      const data = hydrateSelectedSession(
        createDashboardState(),
        makeV4ScenarioSnapshot(sessionId, scenarioId),
      );
      const markup = renderInspectorTab(
        scenarioId === "large-transcript"
          ? {
              ...data,
              liveOutput: [
                {
                  chunk: "pnpm test output is still streaming",
                  stream: "stdout",
                  tool_call_id: "tool-1",
                  turn_id: "turn-1",
                },
              ],
            }
          : data,
        "transcript",
      );

      expect(markup).toContain("Transcript");
      expect(markup).toContain("Latest activity");
      expect(markup).toContain(expectedText);
      expect(markup).toContain("Turn metrics");
    }
  });

  function makeRichSessionData() {
    const selected = hydrateSelectedSession(
      createDashboardState(),
      makeSessionSnapshot("session-1", {
        active_tool_calls: [
          {
            completed_at: null,
            policy_outcome: "allow",
            policy_reason: "read only",
            policy_risk_level: "low",
            policy_source_kind: "tool_policy",
            policy_source_label: "default",
            started_at: "2026-04-23T00:00:02Z",
            status: "running",
            summary: "Run pytest for the frontend shell",
            tool_call_id: "tool-1",
            tool_name: "pytest",
            turn_id: "turn-1",
          },
        ],
        branchable_turns: [
          {
            created_at: "2026-04-23T00:00:03Z",
            label: "Continue from tool result",
            sequence: 8,
            turn_id: "turn-1",
          },
        ],
        child_sessions: [
          {
            branch_label: "retry with context",
            latest_message_summary: "assistant: try again",
            session_id: "child-1",
            status: "running",
            updated_at: "2026-04-23T00:00:04Z",
          },
        ],
        current_turn_id: "turn-1",
        parent_session_id: "parent-1",
        pending_approval_id: "approval-1",
        pending_approvals: [
          {
            approval_id: "approval-1",
            policy_outcome: "approve",
            policy_risk_level: "medium",
            policy_source_kind: "tool_policy",
            policy_source_label: "workspace-write",
            reason: "writes to the workspace",
            requested_at: "2026-04-23T00:00:05Z",
            subject: "apply patch",
            turn_id: "turn-1",
          },
        ],
        pending_question_id: "question-1",
        pending_question_text: "Which branch should be inspected?",
        projection_health: makeProjectionHealth({ degraded: true, state: "stale" }),
        runtime_context: makeRuntimeContext({
          runtime_notes: [{ category: "policy", inherited: false, message: "Approval pending" }],
          working_set: {
            additional_item_count: 0,
            items: [
              {
                inherited: false,
                reasons: ["opened"],
                signal_types: ["file"],
                subject: "frontend/app/page.tsx",
                subject_kind: "file",
                summary: "Current console entrypoint",
              },
            ],
          },
        }),
        transcript: [
          {
            created_at: "2026-04-23T00:00:00Z",
            message_id: "message-1",
            parts: [{ kind: "text", text: "Inspect the console" }],
            role: "user",
          },
          {
            created_at: "2026-04-23T00:00:01Z",
            message_id: "message-2",
            parts: [{ kind: "text", text: "I will inspect the console." }],
            role: "assistant",
          },
        ],
        turn_metrics: [
          {
            completed_at: "2026-04-23T00:00:08Z",
            failed_tool_call_count: 0,
            model_call_count: 1,
            model_duration_ms_total: 2000,
            model_input_tokens_total: 100,
            model_output_tokens_total: 50,
            started_at: "2026-04-23T00:00:02Z",
            succeeded_tool_call_count: 1,
            tool_call_count: 1,
            tool_duration_ms_total: 500,
            turn_duration_ms: 6500,
            turn_id: "turn-1",
          },
        ],
      }),
    );
    return {
      ...hydrateCompareSession(
        selected,
        makeSessionSnapshot("parent-1", {
          branch_label: "mainline",
          parent_session_id: null,
          transcript: [
            {
              created_at: "2026-04-23T00:00:00Z",
              message_id: "parent-message-1",
              parts: [{ kind: "text", text: "Original prompt" }],
              role: "user",
            },
          ],
        }),
      ),
      eventLog: [{ event_type: "ToolExecutionStarted", sequence: 11 }],
      liveOutput: [
        { chunk: "pytest passed", stream: "stdout", tool_call_id: "tool-1", turn_id: "turn-1" },
      ],
      selectedSessionId: "session-1",
    };
  }

  function renderInspectorTab(
    data: DashboardState,
    activeTab: Parameters<typeof SessionInspector>[0]["activeTab"],
  ) {
    return renderToStaticMarkup(
      React.createElement(SessionInspector, {
        activeTab,
        data,
        error: null,
        loadState: "loaded",
        queue: "active",
        stream,
      }),
    );
  }

  it("renders loading and failed selected-session states", () => {
    const loading = { ...createDashboardState(), selectedSessionId: "session-1" };
    expect(
      renderToStaticMarkup(
        React.createElement(SessionInspector, {
          activeTab: "overview",
          data: loading,
          error: null,
          loadState: "loading",
          queue: "active",
          stream,
        }),
      ),
    ).toContain("Loading selected session");

    expect(
      renderToStaticMarkup(
        React.createElement(SessionInspector, {
          activeTab: "overview",
          data: loading,
          error: "session not found",
          loadState: "failed",
          queue: "active",
          stream,
        }),
      ),
    ).toContain("session not found");
  });

  it("renders the inspector beside the selected queue row", () => {
    const aggregate = hydrateSelectedSession(
      createDashboardState(),
      makeSessionSnapshot("session-1"),
    );
    const data = {
      ...aggregate,
      sessionIndex: [makeSessionSummary("session-1")],
    };

    const markup = renderToStaticMarkup(
      React.createElement(WorkspaceOverview, {
        data: {
          ...data,
          ...hydrateSelectedSession(createDashboardState(), makeSessionSnapshot("session-1")),
          sessionIndex: makeSessionAggregate([makeSessionSummary("session-1")]).sessions,
        },
        error: null,
        inspector: React.createElement("aside", null, "Inspector pane"),
        loadState: "loaded",
        selectedQueue: "active",
        selectedSessionId: "session-1",
      }),
    );

    expect(markup).toContain('data-state="selected"');
    expect(markup).toContain("Inspector pane");
  });
});
