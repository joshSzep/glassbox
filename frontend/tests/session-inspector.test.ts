import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SessionInspector } from "../components/console/session-inspector";
import { WorkspaceOverview } from "../components/console/workspace-overview";
import { createDashboardState, hydrateSelectedSession } from "../state/session-state";
import {
  makeProjectionHealth,
  makeRuntimeContext,
  makeSessionAggregate,
  makeSessionSnapshot,
  makeSessionSummary,
} from "./fixtures/session-state";

const stream = {
  error: null,
  lastSequence: 12,
  retryCount: 0,
  status: "live" as const,
};

describe("session inspector", () => {
  it("renders selected-session header, transcript, actions, runtime, metrics, and evidence", () => {
    const data = {
      ...hydrateSelectedSession(
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
      ),
      eventLog: [{ event_type: "ToolExecutionStarted", sequence: 11 }],
      liveOutput: [
        { chunk: "pytest passed", stream: "stdout", tool_call_id: "tool-1", turn_id: "turn-1" },
      ],
    };

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

    expect(markup).toContain("Continue session");
    expect(markup).toContain("Answer pending question");
    expect(markup).toContain("Approve");
    expect(markup).toContain("Deny");
    expect(markup).toContain("Create fork");
    expect(markup).toContain("session-1");
    expect(markup).toContain("projection stale");
    expect(markup).toContain("I will inspect the console.");
    expect(markup).toContain("Run pytest for the frontend shell");
    expect(markup).toContain("Which branch should be inspected?");
    expect(markup).toContain("frontend/app/page.tsx");
    expect(markup).toContain("6.5s");
    expect(markup).toContain("pytest passed");
    expect(markup).toContain("ToolExecutionStarted");
  });

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
