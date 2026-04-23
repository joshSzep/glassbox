import test from "node:test";
import assert from "node:assert/strict";

import {
  submitPendingQuestionAnswer,
  submitSessionMessage,
} from "../../src/glassbox/web/static/interaction-actions.js";
import { applyEvent, createState } from "../../src/glassbox/web/static/state.js";

test("submitSessionMessage keeps composer submitted until SSE confirmation", async () => {
  let state = createState();

  const result = await submitSessionMessage({
    sessionId: "session-123",
    text: "Continue with the next step",
    fetchImpl: async (url, init) => {
      assert.equal(url, "/sessions/session-123/messages");
      assert.equal(init.method, "POST");
      assert.equal(init.body, JSON.stringify({ text: "Continue with the next step" }));
      return {
        ok: true,
        status: 200,
        headers: { get: () => "application/json" },
        json: async () => ({ status: "ok" }),
      };
    },
    syncState: updater => {
      state = updater(state);
    },
  });

  assert.deepEqual(result, { ok: true });
  assert.equal(state.interactionSubmission.kind, "message");
  assert.equal(state.interactionSubmission.state, "submitted");

  state = applyEvent(state, {
    session_id: "session-123",
    sequence: 1,
    event_type: "UserMessageReceived",
    payload: {
      message_id: "message-1",
      text: "Continue with the next step",
    },
  });

  assert.equal(state.interactionSubmission.state, "idle");
});

test("submitPendingQuestionAnswer surfaces server errors and allows retry", async () => {
  let state = applyEvent(createState(), {
    session_id: "session-123",
    sequence: 1,
    event_type: "UserQuestionAsked",
    payload: {
      question_id: "question-1",
      question: "What colour should I use?",
    },
  });

  const result = await submitPendingQuestionAnswer({
    sessionId: "session-123",
    questionId: "question-1",
    answer: "blue",
    fetchImpl: async () => ({
      ok: false,
      status: 409,
      headers: { get: () => "application/json" },
      json: async () => ({ detail: "unknown question_id: question-1" }),
    }),
    syncState: updater => {
      state = updater(state);
    },
  });

  assert.deepEqual(result, {
    ok: false,
    error: "unknown question_id: question-1",
  });
  assert.equal(state.interactionSubmission.kind, "answer");
  assert.equal(state.interactionSubmission.state, "failed");
  assert.equal(state.interactionSubmission.error, "unknown question_id: question-1");
});

test("submitPendingQuestionAnswer keeps answer state submitted until SSE confirmation", async () => {
  let state = applyEvent(createState(), {
    session_id: "session-123",
    sequence: 1,
    event_type: "UserQuestionAsked",
    payload: {
      question_id: "question-1",
      question: "What colour should I use?",
    },
  });

  const result = await submitPendingQuestionAnswer({
    sessionId: "session-123",
    questionId: "question-1",
    answer: "blue",
    fetchImpl: async (url, init) => {
      assert.equal(url, "/sessions/session-123/questions/question-1");
      assert.equal(init.method, "POST");
      assert.equal(init.body, JSON.stringify({ answer: "blue" }));
      return {
        ok: true,
        status: 200,
        headers: { get: () => "application/json" },
        json: async () => ({ status: "ok" }),
      };
    },
    syncState: updater => {
      state = updater(state);
    },
  });

  assert.deepEqual(result, { ok: true });
  assert.equal(state.interactionSubmission.kind, "answer");
  assert.equal(state.interactionSubmission.state, "submitted");

  state = applyEvent(state, {
    session_id: "session-123",
    sequence: 2,
    event_type: "UserAnswerProvided",
    payload: {
      question_id: "question-1",
      answer: "blue",
    },
  });

  assert.equal(state.interactionSubmission.state, "idle");
  assert.equal(state.pendingQuestionId, null);
});
