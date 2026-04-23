/**
 * Session interaction action helpers.
 *
 * This module owns the browser-side request flow for submitting a new message
 * or answering a pending ask_user question so it can be tested without DOM
 * wiring.
 */

import {
  beginInteractionSubmission,
  confirmInteractionSubmission,
  failInteractionSubmission,
} from "./state.js";

export function buildSubmitSessionMessageRequest(sessionId, text) {
  return {
    url: `/sessions/${sessionId}/messages`,
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    },
  };
}

export function buildSubmitSessionAnswerRequest(sessionId, questionId, answer) {
  return {
    url: `/sessions/${sessionId}/questions/${questionId}`,
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer }),
    },
  };
}

async function readInteractionError(response) {
  const contentType = response.headers?.get?.("content-type") ?? "";
  if (contentType.includes("application/json") && typeof response.json === "function") {
    try {
      const data = await response.json();
      if (
        typeof data === "object"
        && data !== null
        && typeof data.detail === "string"
      ) {
        return data.detail;
      }
    } catch {
      // Fall through to generic text/status handling.
    }
  }

  if (typeof response.text === "function") {
    try {
      const text = await response.text();
      if (text.trim()) {
        return text.trim();
      }
    } catch {
      // Fall through to generic status handling.
    }
  }

  return `Request failed (${response.status})`;
}

async function submitInteractionRequest({
  kind,
  request,
  fetchImpl,
  syncState,
}) {
  syncState(current => beginInteractionSubmission(current, kind));

  let response;
  try {
    response = await fetchImpl(request.url, request.init);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network error";
    syncState(current => failInteractionSubmission(current, kind, message));
    return { ok: false, error: message };
  }

  if (!response.ok) {
    const message = await readInteractionError(response);
    syncState(current => failInteractionSubmission(current, kind, message));
    return { ok: false, error: message };
  }

  syncState(current => confirmInteractionSubmission(current, kind));
  return { ok: true };
}

export async function submitSessionMessage(params) {
  const { sessionId, text, fetchImpl, syncState } = params;
  return submitInteractionRequest({
    kind: "message",
    request: buildSubmitSessionMessageRequest(sessionId, text),
    fetchImpl,
    syncState,
  });
}

export async function submitPendingQuestionAnswer(params) {
  const { sessionId, questionId, answer, fetchImpl, syncState } = params;
  return submitInteractionRequest({
    kind: "answer",
    request: buildSubmitSessionAnswerRequest(sessionId, questionId, answer),
    fetchImpl,
    syncState,
  });
}
