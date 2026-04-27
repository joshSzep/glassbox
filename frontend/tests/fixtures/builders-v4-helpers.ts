import type { components } from "@/generated/api-types";

import { defaultChildSessionId, defaultSessionId } from "./scenario-definitions";
import { makeProjectionHealth, makeSessionSummary } from "./builders-basic";

export function makeV4ChildSessionSummary(): components["schemas"]["ChildSessionSummaryResponse"] {
  return {
    branch_label: "retry with narrower context",
    latest_message_summary: "assistant: retrying from fork point",
    session_id: defaultChildSessionId,
    status: "running",
    updated_at: "2026-04-23T00:00:04Z",
  };
}

export function makeV4ScenarioSummaries(): components["schemas"]["OperatorSessionSummaryResponse"][] {
  return [
    makeSessionSummary("approval-session", {
      action_needed: true,
      latest_message_summary: "assistant: requested workspace write approval",
      next_action_summary: "Review pending approval",
      pending_approval_id: "approval-1",
      priority_bucket: "approval",
      priority_rank: 1,
      queue_memberships: ["approvals", "action-needed"],
    }),
    makeSessionSummary("question-session", {
      action_needed: true,
      latest_message_summary: "assistant: needs branch selection",
      next_action_summary: "Answer pending question",
      pending_question_id: "question-1",
      pending_question_text: "Which branch should be inspected?",
      priority_bucket: "question",
      priority_rank: 2,
      queue_memberships: ["questions", "action-needed"],
    }),
    makeSessionSummary("failed-session", {
      action_needed: true,
      latest_message_summary: "tool: pytest failed",
      next_action_summary: "Inspect retryable failure",
      priority_bucket: "failure",
      priority_rank: 3,
      queue_memberships: ["failures", "action-needed"],
      session_failure_message: "frontend e2e workflow failed after action submit",
      session_failure_retryable: true,
      status: "failed",
    }),
    makeSessionSummary("degraded-session", {
      latest_message_summary: "projection health is stale",
      next_action_summary: "Check projection health",
      priority_bucket: "degraded",
      priority_rank: 4,
      projection_health: makeProjectionHealth({
        degraded: true,
        detail: "projection lag",
        lag: 3,
        state: "stale",
      }),
      queue_memberships: ["degraded"],
    }),
    makeSessionSummary(defaultSessionId, {
      action_needed: true,
      branch_label: "mainline",
      child_session_count: 1,
      latest_message_summary: "assistant: running frontend validation",
      next_action_summary: "Answer pending question",
      pending_approval_id: "approval-1",
      pending_question_id: "question-1",
      pending_question_text: "Which branch should be inspected?",
      priority_bucket: "action_needed",
      priority_rank: 5,
      queue_memberships: ["active", "questions", "approvals", "action-needed"],
    }),
    makeSessionSummary("artifact-session", {
      latest_message_summary: "artifact summary indicates drift",
      next_action_summary: "Inspect artifact-backed drift evidence",
      priority_bucket: "active",
      priority_rank: 6,
      queue_memberships: ["active"],
    }),
    makeSessionSummary("large-transcript-session", {
      action_needed: true,
      latest_message_summary: "tool output and transcript are noisy",
      next_action_summary: "Review approval without losing live output context",
      pending_approval_id: "approval-1",
      priority_bucket: "approval",
      priority_rank: 7,
      queue_memberships: ["active", "approvals", "action-needed"],
    }),
    makeSessionSummary("historical-session", {
      has_active_turn: false,
      historical_only: true,
      latest_message_summary: "assistant: completed dashboard migration",
      live_actionable: false,
      next_action_summary: "Review historical snapshot",
      priority_bucket: "historical",
      priority_rank: 9,
      queue_memberships: ["historical"],
      status: "completed",
    }),
  ];
}

export function makeV4ActiveToolCall(): components["schemas"]["ActiveToolCallResponse"] {
  return {
    completed_at: null,
    policy_outcome: "approve",
    policy_reason: "writes files during noisy validation",
    policy_risk_level: "workspace_write",
    policy_source_kind: "tool_policy",
    policy_source_label: "workspace-write",
    started_at: "2026-04-23T00:00:02Z",
    status: "running",
    summary: "Run frontend validation with verbose output",
    tool_call_id: "tool-1",
    tool_name: "pnpm test",
    turn_id: "turn-1",
  };
}

export function makeV4Approval(): components["schemas"]["PendingApprovalResponse"] {
  return {
    approval_id: "approval-1",
    policy_outcome: "approve",
    policy_risk_level: "medium",
    policy_source_kind: "tool_policy",
    policy_source_label: "workspace-write",
    reason: "writes to the workspace",
    requested_at: "2026-04-23T00:00:05Z",
    subject: "apply patch",
    turn_id: "turn-1",
  };
}

export function makeV4ArtifactRuntimeContext(): Partial<
  components["schemas"]["RuntimeContextSnapshot"]
> {
  return {
    artifact_context: {
      additional_summary_count: 0,
      summaries: [
        makeV4ArtifactSummary(
          "evals/impact.json",
          "One browser workflow regressed after dashboard shell changes.",
        ),
        makeV4ArtifactSummary(
          "evals/bundles/context.branch-inherited.json",
          "Replay context was inherited from the parent branch.",
          true,
        ),
        makeV4ArtifactSummary(
          "evals/coverage.json",
          "Coverage artifact is current for this branch.",
        ),
      ],
    },
    working_set: {
      additional_item_count: 0,
      items: [
        {
          inherited: true,
          reasons: ["branch parent"],
          signal_types: ["file"],
          subject: "frontend/components/console/session-inspector.tsx",
          subject_kind: "file",
          summary: "Inherited inspector work from the compared branch.",
        },
      ],
    },
  };
}

export function makeV4Transcript(sessionId: string, firstText = "Inspect the operator workflow") {
  return [
    {
      created_at: "2026-04-23T00:00:00Z",
      message_id: `${sessionId}-message-1`,
      parts: [{ kind: "text", text: firstText }],
      role: "user",
    },
    {
      created_at: "2026-04-23T00:00:01Z",
      message_id: `${sessionId}-message-2`,
      parts: [{ kind: "text", text: "I will inspect the current dashboard state." }],
      role: "assistant",
    },
  ] satisfies components["schemas"]["TranscriptMessageResponse"][];
}

export function makeV4LargeTranscript(
  sessionId: string,
): components["schemas"]["TranscriptMessageResponse"][] {
  return Array.from({ length: 18 }, (_, index) => ({
    created_at: `2026-04-23T00:00:${String(index).padStart(2, "0")}Z`,
    message_id: `${sessionId}-message-${index + 1}`,
    parts: [{ kind: "text", text: largeTranscriptText(index) }],
    role: index % 2 === 0 ? "user" : "assistant",
  }));
}

export function makeV4TurnMetrics(
  failedToolCall = false,
): components["schemas"]["TurnMetricsResponse"] {
  return {
    completed_at: "2026-04-23T00:00:08Z",
    failed_tool_call_count: failedToolCall ? 1 : 0,
    model_call_count: 1,
    model_duration_ms_total: 2000,
    model_input_tokens_total: 100,
    model_output_tokens_total: 50,
    started_at: "2026-04-23T00:00:02Z",
    succeeded_tool_call_count: failedToolCall ? 0 : 1,
    tool_call_count: 1,
    tool_duration_ms_total: 500,
    turn_duration_ms: 6500,
    turn_id: "turn-1",
  };
}

function makeV4ArtifactSummary(path: string, summary: string, inherited = false) {
  return {
    artifact_kind: inherited ? "replay" : "eval",
    artifact_path: path,
    error_count: 0,
    failing_tests: inherited ? [] : ["frontend operator workflow"],
    failure_count: inherited ? 0 : 1,
    freshness: inherited ? "stale" : "fresh",
    inherited,
    provenance_class: "artifact_backed_summary",
    source_tool_name: inherited ? "glassbox replay run" : "glassbox eval run",
    summary,
    summary_kind: inherited ? "context-drift" : "eval-impact",
    target_paths: inherited
      ? ["docs/tasks-v4.md"]
      : ["frontend/components/console/workspace-overview.tsx"],
    timed_out: false,
  } satisfies components["schemas"]["ArtifactBackedContextSummarySnapshot"];
}

function largeTranscriptText(index: number): string {
  return index % 2 === 0
    ? `Operator turn ${index + 1}: keep the approval visible while reading a long transcript entry with file paths like frontend/components/console/session-inspector.tsx.`
    : `Assistant turn ${index + 1}: validation is still streaming, artifact evidence is advisory, and the action rail should not be pushed below diagnostics.`;
}
