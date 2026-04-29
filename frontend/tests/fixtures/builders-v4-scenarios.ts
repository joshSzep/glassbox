import type { components } from "@/generated/api-types";
import type { SseEventEnvelope } from "../../api/sse";

import { makeEnvelope } from "./builders-actions";
import {
  makeProjectionHealth,
  makeRuntimeContext,
  makeSessionAggregate,
  makeSessionSnapshot,
} from "./builders-basic";
import {
  makeV4ActiveToolCall,
  makeV4Approval,
  makeV4ArtifactRuntimeContext,
  makeV4ChildSessionSummary,
  makeV4LargeTranscript,
  makeV4ScenarioSummaries,
  makeV4Transcript,
  makeV4TurnMetrics,
} from "./builders-v4-helpers";
import {
  defaultChildSessionId,
  defaultSessionId,
  largeTranscriptSessionId,
  type V4ConsoleScenarioId,
} from "./scenario-definitions";

export function makeV4ScenarioAggregate(
  scenarioId: V4ConsoleScenarioId,
  queue: string | null = null,
): components["schemas"]["SessionAggregateResponse"] {
  const sessions = scenarioId === "empty-workspace" ? [] : makeV4ScenarioSummaries();
  const filteredSessions =
    queue === null || queue === "all"
      ? sessions
      : sessions.filter((session) => session.queue_memberships.includes(queue));
  const degradedCount = sessions.filter((session) => session.projection_health.degraded).length;

  return makeSessionAggregate(filteredSessions, {
    projection_health_counts: {
      degraded: degradedCount,
      ok: Math.max(sessions.length - degradedCount, 0),
      stale: degradedCount,
      unavailable: 0,
    },
    queue,
    queue_counts: {
      action_needed: sessions.filter((session) => session.action_needed).length,
      active: sessions.filter((session) => session.queue_memberships.includes("active")).length,
      approvals: sessions.filter((session) => session.queue_memberships.includes("approvals"))
        .length,
      degraded: sessions.filter((session) => session.queue_memberships.includes("degraded")).length,
      failures: sessions.filter((session) => session.queue_memberships.includes("failures")).length,
      historical: sessions.filter((session) => session.historical_only).length,
      questions: sessions.filter((session) => session.queue_memberships.includes("questions"))
        .length,
      total: sessions.length,
    },
    runtime: {
      background_job_abandoned_count: 0,
      background_job_failed_count: 0,
      background_job_retryable_count: 0,
      dashboard_url: "http://127.0.0.1:3210/app",
      health: sessions.length === 0 ? null : "ok",
      health_url: "/healthz",
      pid: sessions.length === 0 ? null : 1234,
      session_index_url: "/sessions/aggregate",
      started_at: sessions.length === 0 ? null : "2026-04-23T00:00:00Z",
      state: sessions.length === 0 ? "not_running" : "running",
      workspace_root: "/tmp/glassbox-v4-audit",
    },
  });
}

export function makeV4ScenarioSnapshot(
  sessionId: string,
  scenarioId: V4ConsoleScenarioId = "live-session",
): components["schemas"]["SessionSnapshotResponse"] {
  const base = makeSessionSnapshot(sessionId, {
    branchable_turns: [
      {
        created_at: "2026-04-23T00:00:03Z",
        label: "Continue from tool result",
        sequence: 8,
        turn_id: "turn-1",
      },
    ],
    can_fork: true,
    fork_blocked_reason: null,
    latest_fork_point_sequence: 8,
    latest_fork_point_turn_id: "turn-1",
    runtime_context: makeRuntimeContext({
      repository_context: {
        additional_directory_count: 0,
        additional_file_count: 0,
        high_signal_paths: ["src/glassbox", "frontend/components/console"],
        project_markers: ["pyproject.toml", "frontend/package.json"],
        top_level_directories: ["src", "tests", "frontend"],
        top_level_files: ["README.md"],
        workspace_name: "glassbox",
      },
      runtime_notes: [
        { category: "runtime", inherited: false, message: "Fixture runtime is stable." },
      ],
    }),
    session_policy_summary: {
      allow_count: 0,
      approve_count: 1,
      blocked_count: 0,
      command_count: 1,
      deny_count: 0,
      highest_risk_level: "medium",
      read_only_count: 0,
      total_decisions: 1,
      workspace_write_count: 1,
    },
    transcript: makeV4Transcript(sessionId),
    turn_metrics: [makeV4TurnMetrics(sessionId === "failed-session")],
  });

  return specializeV4Snapshot(base, sessionId, scenarioId);
}

export function makeV4ScenarioSseEnvelopes(
  scenarioId: V4ConsoleScenarioId,
  sessionId: string,
): SseEventEnvelope[] {
  if (scenarioId === "large-transcript") {
    return [
      makeEnvelope(
        5,
        "ToolOutputChunk",
        {
          chunk: "pnpm test -- --runInBand produced a long validation line that should wrap.",
          stream: "stdout",
          tool_call_id: "tool-1",
          turn_id: "turn-1",
        },
        sessionId,
      ),
      makeEnvelope(
        6,
        "AssistantMessageCompleted",
        {
          message_id: "message-live-large",
          parts: [{ kind: "text", text: "Live output is still arriving while approval waits." }],
        },
        sessionId,
      ),
    ];
  }

  if (scenarioId === "live-session" || scenarioId === "pending-question") {
    return [
      makeEnvelope(
        5,
        "AssistantMessageCompleted",
        {
          message_id: "message-live",
          parts: [{ kind: "text", text: "Live SSE update received by the browser." }],
        },
        sessionId,
      ),
    ];
  }

  return [];
}

export function makeV4ForkResponse(): components["schemas"]["ForkSessionResponse"] {
  return {
    branch_label: "retry with narrower context",
    child_session_id: defaultChildSessionId,
    forked_from_sequence: 8,
    forked_from_turn_id: "turn-1",
    inherited_message_count: 2,
    last_sequence: 8,
    parent_session_id: defaultSessionId,
  };
}

export function v4FixtureSessionIds(): string[] {
  return [
    defaultSessionId,
    defaultChildSessionId,
    "approval-session",
    "question-session",
    "failed-session",
    "historical-session",
    "degraded-session",
    "artifact-session",
    largeTranscriptSessionId,
    "parent-session",
  ];
}

function specializeV4Snapshot(
  base: components["schemas"]["SessionSnapshotResponse"],
  sessionId: string,
  scenarioId: V4ConsoleScenarioId,
): components["schemas"]["SessionSnapshotResponse"] {
  if (sessionId === "approval-session") {
    return { ...base, pending_approval_id: "approval-1", pending_approvals: [makeV4Approval()] };
  }
  if (sessionId === "question-session" || sessionId === defaultSessionId) {
    return makeQuestionSnapshot(base, sessionId, scenarioId);
  }
  if (sessionId === "failed-session") {
    return {
      ...base,
      session_failure_message: "frontend e2e workflow failed after action submit",
      session_failure_retryable: true,
      status: "failed",
    };
  }
  if (sessionId === "historical-session") {
    return {
      ...base,
      can_fork: false,
      current_turn_id: null,
      fork_blocked_reason: "Historical snapshot has no live fork point.",
      status: "completed",
    };
  }
  if (sessionId === "degraded-session") {
    return {
      ...base,
      projection_health: makeProjectionHealth({
        degraded: true,
        detail: "projection lag",
        lag: 3,
        state: "stale",
      }),
    };
  }
  if (sessionId === "artifact-session") {
    return { ...base, runtime_context: makeRuntimeContext(makeV4ArtifactRuntimeContext()) };
  }
  if (sessionId === largeTranscriptSessionId) {
    return makeLargeTranscriptSnapshot(base);
  }
  if (sessionId === "parent-session") {
    return {
      ...base,
      branch_label: "mainline",
      parent_session_id: null,
      session_id: "parent-session",
      status: "completed",
      transcript: makeV4Transcript("parent-session", "Original parent prompt"),
    };
  }
  if (sessionId === defaultChildSessionId) {
    return {
      ...base,
      branch_label: "retry with narrower context",
      parent_session_id: defaultSessionId,
      session_id: defaultChildSessionId,
    };
  }
  return {
    ...base,
    child_sessions:
      scenarioId === "branched-session" || scenarioId === "compare-view"
        ? [makeV4ChildSessionSummary()]
        : [],
    parent_session_id: scenarioId === "compare-view" ? "parent-session" : null,
  };
}

function makeQuestionSnapshot(
  base: components["schemas"]["SessionSnapshotResponse"],
  sessionId: string,
  scenarioId: V4ConsoleScenarioId,
) {
  return {
    ...base,
    child_sessions:
      sessionId === defaultSessionId &&
      (scenarioId === "branched-session" || scenarioId === "compare-view")
        ? [makeV4ChildSessionSummary()]
        : base.child_sessions,
    pending_approval_id: sessionId === defaultSessionId ? "approval-1" : null,
    pending_approvals: sessionId === defaultSessionId ? [makeV4Approval()] : [],
    pending_question_id: "question-1",
    pending_question_text: "Which branch should be inspected?",
  };
}

function makeLargeTranscriptSnapshot(base: components["schemas"]["SessionSnapshotResponse"]) {
  return {
    ...base,
    active_tool_calls: [makeV4ActiveToolCall()],
    pending_approval_id: "approval-1",
    pending_approvals: [makeV4Approval()],
    runtime_context: makeRuntimeContext({
      ...makeV4ArtifactRuntimeContext(),
      additional_runtime_note_count: 1,
      runtime_notes: [
        { category: "runtime", inherited: false, message: "Tool output is still streaming." },
        {
          category: "artifact",
          inherited: true,
          message: "Inherited eval context may be stale for this branch.",
          source_session_id: "parent-session",
        },
      ],
    }),
    transcript: makeV4LargeTranscript(largeTranscriptSessionId),
  };
}
