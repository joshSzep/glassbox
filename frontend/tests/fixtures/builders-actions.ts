import type { components } from "@/generated/api-types";
import type { SseEventEnvelope } from "../../api/sse";

import { defaultSessionId } from "./scenario-definitions";
import { makeSessionSnapshot } from "./builders-basic";

export function makeOperatorActionSessionSnapshot(
  sessionId = "session-1",
  overrides: Partial<components["schemas"]["SessionSnapshotResponse"]> = {},
): components["schemas"]["SessionSnapshotResponse"] {
  return makeSessionSnapshot(sessionId, {
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
    ...overrides,
  });
}

export function makeEnvelope(
  sequence: number,
  eventType: SseEventEnvelope["event_type"],
  payload: Record<string, unknown>,
  sessionId = defaultSessionId,
): SseEventEnvelope {
  return {
    created_at: `2026-04-23T00:00:${String(sequence).padStart(2, "0")}Z`,
    event_id: `event-${sequence}`,
    event_type: eventType,
    payload: { event_type: eventType, ...payload },
    sequence,
    session_id: sessionId,
  };
}
