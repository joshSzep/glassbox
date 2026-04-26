import { describe, expect, it } from "vitest";

import {
  buildSessionNarrative,
  createDashboardState,
  hydrateSelectedSession,
} from "../state/session-state";
import {
  defaultSessionId,
  largeTranscriptSessionId,
  makeSessionSnapshot,
  makeV4ScenarioSnapshot,
} from "./fixtures/session-state";

function hydrate(snapshot: ReturnType<typeof makeSessionSnapshot>) {
  return hydrateSelectedSession(createDashboardState(), snapshot);
}

function itemKinds(turns: ReturnType<typeof buildSessionNarrative>["turns"]) {
  return turns.flatMap((turn) => turn.items.map((item) => item.kind));
}

describe("session narrative grouping", () => {
  it("groups a normal live session around the explicit turn metadata", () => {
    const data = hydrate(makeV4ScenarioSnapshot(defaultSessionId, "live-session"));
    const narrative = buildSessionNarrative(data);
    const turn = narrative.turns.find((candidate) => candidate.turnId === "turn-1");

    expect(narrative.sessionId).toBe(defaultSessionId);
    expect(turn).toBeDefined();
    expect(turn?.status).toBe("awaiting-approval");
    expect(turn?.items.map((item) => item.kind)).toEqual(
      expect.arrayContaining(["metric", "fork-boundary", "approval", "question", "message"]),
    );
  });

  it("keeps question-only sessions honest when no question turn id exists", () => {
    const data = hydrate(makeV4ScenarioSnapshot("question-session", "pending-question"));
    const narrative = buildSessionNarrative(data);
    const questionTurn = narrative.turns.find((turn) =>
      turn.items.some((item) => item.kind === "question"),
    );

    expect(questionTurn).toMatchObject({ isFallback: true, status: "awaiting-answer" });
    expect(questionTurn?.title).toBe("Pending question");
  });

  it("places failed sessions on the latest metric turn", () => {
    const data = hydrate(makeV4ScenarioSnapshot("failed-session", "failed-session"));
    const narrative = buildSessionNarrative(data);
    const failedTurn = narrative.turns.find((turn) => turn.status === "failed");

    expect(failedTurn?.turnId).toBe("turn-1");
    expect(failedTurn?.items.map((item) => item.kind)).toContain("failure");
  });

  it("groups active tools and live output with their turn", () => {
    const data = {
      ...hydrate(makeV4ScenarioSnapshot(largeTranscriptSessionId, "large-transcript")),
      liveOutput: [
        {
          chunk: "streaming validation output",
          stream: "stdout",
          tool_call_id: "tool-1",
          turn_id: "turn-1",
        },
      ],
    };
    const narrative = buildSessionNarrative(data);
    const activeTurn = narrative.turns.find((turn) => turn.turnId === "turn-1");

    expect(activeTurn?.status).toBe("awaiting-approval");
    expect(activeTurn?.items.map((item) => item.kind)).toEqual(
      expect.arrayContaining(["tool-call", "live-output"]),
    );
  });

  it("preserves partial-history transcript order in a fallback group", () => {
    const data = hydrate(
      makeSessionSnapshot("partial-history", {
        branchable_turns: [
          {
            created_at: "2026-04-23T00:00:03Z",
            label: "First turn",
            sequence: 1,
            turn_id: "turn-1",
          },
          {
            created_at: "2026-04-23T00:00:05Z",
            label: "Second turn",
            sequence: 2,
            turn_id: "turn-2",
          },
        ],
        transcript: [
          {
            created_at: "2026-04-23T00:00:00Z",
            message_id: "message-1",
            parts: [{ kind: "text", text: "first" }],
            role: "user",
          },
          {
            created_at: "2026-04-23T00:00:01Z",
            message_id: "message-2",
            parts: [{ kind: "text", text: "second" }],
            role: "assistant",
          },
        ],
        turn_metrics: [
          {
            completed_at: "2026-04-23T00:00:04Z",
            failed_tool_call_count: 0,
            model_call_count: 1,
            model_duration_ms_total: 100,
            model_input_tokens_total: 10,
            model_output_tokens_total: 20,
            started_at: "2026-04-23T00:00:02Z",
            succeeded_tool_call_count: 1,
            tool_call_count: 1,
            tool_duration_ms_total: 50,
            turn_duration_ms: 150,
            turn_id: "turn-1",
          },
          {
            completed_at: "2026-04-23T00:00:06Z",
            failed_tool_call_count: 0,
            model_call_count: 1,
            model_duration_ms_total: 100,
            model_input_tokens_total: 10,
            model_output_tokens_total: 20,
            started_at: "2026-04-23T00:00:05Z",
            succeeded_tool_call_count: 0,
            tool_call_count: 0,
            tool_duration_ms_total: 0,
            turn_duration_ms: 100,
            turn_id: "turn-2",
          },
        ],
      }),
    );
    const narrative = buildSessionNarrative(data);
    const transcriptTurn = narrative.turns.find((turn) => turn.id === "transcript-unassigned");

    expect(transcriptTurn).toMatchObject({ isFallback: true, turnId: null });
    expect(
      transcriptTurn?.items.map((item) =>
        item.kind === "message" ? item.message.message_id : null,
      ),
    ).toEqual(["message-1", "message-2"]);
  });

  it("keeps minimal legacy snapshot data readable", () => {
    const data = {
      ...hydrate(makeSessionSnapshot("legacy-session")),
      eventLog: [{ event_type: "SessionStarted", sequence: 1 }],
    };
    const narrative = buildSessionNarrative(data);

    expect(itemKinds(narrative.turns)).toEqual(["message", "event-evidence"]);
    expect(narrative.turns.every((turn) => turn.isFallback)).toBe(true);
  });
});
