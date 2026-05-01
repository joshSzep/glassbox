import { describe, expect, it } from "vitest";

import {
  applySessionEvent,
  createDashboardState,
  hydrateCompareSession,
  hydrateSelectedSession,
  hydrateSessionAggregate,
  hydrateSessionSnapshot,
} from "../state/session-state";
import {
  largeTranscriptSessionId,
  makeEnvelope,
  makeKnowledgePosture,
  makeRuntimeContext,
  makeV4ScenarioAggregate,
  makeV4ScenarioSnapshot,
  makeV4ScenarioSseEnvelopes,
  makeSessionAggregate,
  makeSessionSnapshot,
  makeSessionSummary,
  v4ConsoleScenarioFixtures,
  type V4ConsoleScenarioId,
} from "./fixtures/session-state";

describe("session state hydration", () => {
  it("hydrates aggregate queues, projection health, runtime summaries, and rows", () => {
    const session = makeSessionSummary("session-1", {
      action_needed: true,
      pending_approval_id: "approval-1",
      queue_memberships: ["approvals", "action-needed"],
    });
    const state = hydrateSessionAggregate(
      createDashboardState(),
      makeSessionAggregate([session], {
        knowledge_posture: makeKnowledgePosture({ overall_status: "stale" }),
        queue: "approvals",
        sort: "updated_at",
      }),
    );

    expect(state.selectedQueue).toBe("approvals");
    expect(state.sessionIndex).toEqual([session]);
    expect(state.queueCounts.approvals).toBe(1);
    expect(state.projectionHealthCounts.ok).toBe(1);
    expect(state.runtimeSummary.workspace_root).toBe("/tmp/workspace");
    expect(state.knowledgePosture?.overall_status).toBe("stale");
    expect(state.sessionIndexSort).toBe("updated_at");
  });

  it("hydrates selected snapshots with lineage, runtime context, metrics, approvals, and tools", () => {
    const state = hydrateSessionSnapshot(
      makeSessionSnapshot("session-1", {
        active_tool_calls: [
          {
            completed_at: null,
            policy_outcome: "approve",
            policy_reason: "writes files",
            policy_risk_level: "workspace_write",
            policy_source_kind: "tool",
            policy_source_label: "patch",
            started_at: "2026-04-23T00:00:02Z",
            status: "running",
            summary: null,
            tool_call_id: "tool-1",
            tool_name: "apply_patch",
            turn_id: "turn-1",
          },
        ],
        branch_label: "alt",
        branchable_turns: [
          { created_at: "2026-04-23T00:00:01Z", label: "first", sequence: 1, turn_id: "turn-1" },
          { created_at: "2026-04-23T00:00:03Z", label: "latest", sequence: 3, turn_id: "turn-3" },
        ],
        budget_posture: {
          budget: null,
          checkpoint_approval_required: false,
          last_decision: "exhausted",
          last_detail: "step budget exhausted",
          last_limit_name: "steps",
          last_reason: "budget_exhausted",
          last_sequence: 12,
          mode: "test-driven",
          next_checkpoint_due_in_seconds: null,
          quiet_window_policy: "allow",
          remaining: null,
          retry_delay_remaining_seconds: null,
          session_id: "session-1",
          task_id: null,
          unattended_remaining_seconds: null,
          updated_at: "2026-04-23T00:00:05Z",
          usage: {
            artifact_bytes: 0,
            branch_attempts: 0,
            command_operations: 0,
            retry_delay_seconds: 0,
            seconds_since_checkpoint: 0,
            steps: 4,
            tool_calls: 1,
            unattended_seconds: 0,
            verification_attempts: 1,
            wall_clock_seconds: 15,
            write_operations: 1,
          },
        },
        can_fork: true,
        child_sessions: [
          {
            branch_label: "child",
            latest_message_summary: "child work",
            session_id: "child-1",
            status: "completed",
            updated_at: "2026-04-23T00:00:04Z",
          },
        ],
        current_turn_id: "turn-1",
        latest_fork_point_sequence: 3,
        latest_fork_point_turn_id: "turn-3",
        parent_session_id: "parent-1",
        pending_approval_id: "approval-1",
        pending_approvals: [
          {
            approval_id: "approval-1",
            policy_outcome: "approve",
            policy_risk_level: "workspace_write",
            policy_source_kind: "tool",
            policy_source_label: "patch",
            reason: "needs write approval",
            requested_at: "2026-04-23T00:00:03Z",
            subject: "apply patch",
            turn_id: "turn-1",
          },
        ],
        pending_question_id: "question-1",
        pending_question_text: "Which branch?",
        runtime_context: makeRuntimeContext({
          runtime_notes: [{ category: "note", inherited: false, message: "Keep tests green" }],
          working_set: {
            additional_item_count: 0,
            items: [
              {
                inherited: false,
                reasons: ["recently changed"],
                signal_types: ["git"],
                subject: "frontend/state/session-state.ts",
                subject_kind: "file",
                summary: "state core",
              },
            ],
          },
        }),
        turn_metrics: [
          {
            completed_at: null,
            failed_tool_call_count: 0,
            model_call_count: 1,
            model_duration_ms_total: 15,
            model_input_tokens_total: 10,
            model_output_tokens_total: 20,
            started_at: "2026-04-23T00:00:02Z",
            succeeded_tool_call_count: 0,
            tool_call_count: 1,
            tool_duration_ms_total: 0,
            turn_duration_ms: null,
            turn_id: "turn-1",
          },
        ],
      }),
    );

    expect(state.selectedSessionId).toBe("session-1");
    expect(state.parentSessionId).toBe("parent-1");
    expect(state.branchLabel).toBe("alt");
    expect(state.branchableTurns.map((turn) => turn.turn_id)).toEqual(["turn-3", "turn-1"]);
    expect(state.selectedForkTurnId).toBe("turn-3");
    expect(state.childSessions[0]?.session_id).toBe("child-1");
    expect(state.budgetPosture).toMatchObject({
      last_limit_name: "steps",
      last_reason: "budget_exhausted",
      mode: "test-driven",
    });
    expect(state.pendingApprovals[0]).toMatchObject({ resolution_state: "idle" });
    expect(state.activeToolCalls[0]?.tool_name).toBe("apply_patch");
    expect(state.runtimeContext?.repository_context.workspace_name).toBe("glassbox");
    expect(state.runtimeContext?.working_set?.items?.[0]?.subject).toBe(
      "frontend/state/session-state.ts",
    );
    expect(state.turnMetrics[0]?.model_call_count).toBe(1);
  });

  it("hydrates compare snapshots without replacing the selected session", () => {
    const selected = hydrateSessionSnapshot(makeSessionSnapshot("selected"));
    const compared = hydrateCompareSession(
      selected,
      makeSessionSnapshot("compare", {
        projection_health: {
          canonical_last_sequence: 8,
          degraded: true,
          detail: "projection lag",
          estimated_rebuild_event_count: 8,
          lag: 2,
          projected_last_sequence: 6,
          projected_progress_ratio: 0.75,
          state: "stale",
        },
      }),
    );

    expect(compared.sessionId).toBe("selected");
    expect(compared.compareSessionId).toBe("compare");
    expect(compared.compareSession?.projectionHealth?.state).toBe("stale");
  });

  it("hydrates v4 console scenarios through the real reducer path", () => {
    const aggregateState = hydrateSessionAggregate(
      createDashboardState(),
      makeV4ScenarioAggregate("all-queues"),
    );
    const scenarioEntries = Object.entries(v4ConsoleScenarioFixtures) as [
      V4ConsoleScenarioId,
      (typeof v4ConsoleScenarioFixtures)[V4ConsoleScenarioId],
    ][];

    expect(aggregateState.sessionIndex.map((session) => session.session_id)).toEqual(
      expect.arrayContaining([
        "approval-session",
        "question-session",
        "failed-session",
        "degraded-session",
        largeTranscriptSessionId,
      ]),
    );

    for (const [scenarioId, scenario] of scenarioEntries) {
      if (!("sessionId" in scenario)) {
        continue;
      }
      const snapshot = makeV4ScenarioSnapshot(scenario.sessionId, scenarioId);
      const selected = makeV4ScenarioSseEnvelopes(scenarioId, scenario.sessionId).reduce(
        applySessionEvent,
        hydrateSelectedSession(aggregateState, snapshot),
      );

      expect(selected.selectedSessionId).toBe(scenario.sessionId);
      expect(selected.status).toBeTruthy();
      expect(selected.runtimeContext?.repository_context.workspace_name).toBe("glassbox");
    }
  });

  it("keeps the noisy v4 scenario realistic under reducer hydration", () => {
    const snapshot = makeV4ScenarioSnapshot(largeTranscriptSessionId, "large-transcript");
    const state = makeV4ScenarioSseEnvelopes("large-transcript", largeTranscriptSessionId).reduce(
      applySessionEvent,
      hydrateSelectedSession(createDashboardState(), snapshot),
    );

    expect(state.transcript).toHaveLength(19);
    expect(state.pendingApprovals[0]?.subject).toBe("apply patch");
    expect(state.activeToolCalls[0]?.tool_name).toBe("pnpm test");
    expect(state.liveOutput[0]?.chunk).toContain("long validation line");
    expect(state.runtimeContext?.artifact_context?.summaries).toHaveLength(3);
    expect(state.runtimeContext?.runtime_notes?.map((note) => note.category)).toEqual([
      "runtime",
      "artifact",
    ]);
  });
});

describe("session event reduction", () => {
  it("reduces transcript, questions, approvals, tools, metrics, runtime notes, and fork points", () => {
    let state = hydrateSelectedSession(createDashboardState(), makeSessionSnapshot("session-1"));

    state = applySessionEvent(
      state,
      makeEnvelope(5, "UserMessageReceived", {
        message_id: "message-2",
        text: "Continue",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(6, "TurnStarted", {
        trigger_message_id: "message-2",
        turn_id: "turn-1",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(7, "ModelCallCompleted", {
        duration_ms: 50,
        input_tokens: 10,
        output_tokens: 20,
        turn_id: "turn-1",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(8, "ToolExecutionStarted", {
        policy_outcome: "approve",
        policy_reason: "writes files",
        policy_risk_level: "workspace_write",
        policy_source_kind: "tool",
        policy_source_label: "apply_patch",
        tool_call_id: "tool-1",
        tool_name: "apply_patch",
        turn_id: "turn-1",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(9, "ToolOutputChunk", {
        chunk: "patched",
        stream: "stdout",
        tool_call_id: "tool-1",
        turn_id: "turn-1",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(10, "ApprovalRequested", {
        approval_id: "approval-1",
        reason: "needs write approval",
        subject: "apply patch",
        turn_id: "turn-1",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(11, "ApprovalResolved", {
        approval_id: "approval-1",
        decision: "approved",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(12, "UserQuestionAsked", {
        question: "Which color?",
        question_id: "question-1",
        turn_id: "turn-1",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(13, "UserAnswerProvided", {
        answer: "blue",
        question_id: "question-1",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(14, "RuntimeNoteRecorded", {
        category: "decision",
        message: "Use generated types",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(15, "ToolExecutionCompleted", {
        success: true,
        tool_call_id: "tool-1",
        turn_id: "turn-1",
      }),
    );
    state = applySessionEvent(
      state,
      makeEnvelope(16, "TurnCompleted", {
        outcome: "completed",
        turn_id: "turn-1",
      }),
    );

    expect(state.lastSequence).toBe(16);
    expect(state.eventLog).toHaveLength(12);
    expect(state.transcript.at(-1)).toMatchObject({ message_id: "message-2", role: "user" });
    expect(state.pendingApprovalId).toBeNull();
    expect(state.pendingApprovals).toEqual([]);
    expect(state.pendingQuestionId).toBeNull();
    expect(state.liveOutput[0]).toMatchObject({ chunk: "patched" });
    expect(state.activeToolCalls).toEqual([]);
    expect(state.sessionPolicySummary).toMatchObject({
      approve_count: 1,
      highest_risk_level: "workspace_write",
      workspace_write_count: 1,
    });
    expect(state.runtimeContext?.runtime_notes?.[0]).toMatchObject({
      category: "decision",
      message: "Use generated types",
    });
    expect(state.turnMetrics[0]).toMatchObject({
      model_call_count: 1,
      succeeded_tool_call_count: 1,
      tool_call_count: 1,
      turn_id: "turn-1",
    });
    expect(state.canFork).toBe(true);
    expect(state.latestForkPointTurnId).toBe("turn-1");
    expect(state.branchableTurns[0]).toMatchObject({ label: "Continue", sequence: 16 });
  });

  it("records terminal session state from completed and failed events", () => {
    const completed = applySessionEvent(
      hydrateSessionSnapshot(makeSessionSnapshot("session-1")),
      makeEnvelope(5, "SessionCompleted", { reason: "done" }),
    );
    expect(completed.status).toBe("completed");
    expect(completed.currentTurn).toBeNull();

    const failed = applySessionEvent(
      completed,
      makeEnvelope(6, "SessionFailed", { error_message: "boom", retryable: true }),
    );
    expect(failed.status).toBe("failed");
    expect(failed.sessionFailureMessage).toBe("boom");
    expect(failed.sessionFailureRetryable).toBe(true);
  });
});
