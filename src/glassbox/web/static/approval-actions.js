/**
 * Approval action helpers.
 *
 * This module owns the browser-side request/response flow for approval
 * resolution so it can be tested without DOM wiring.
 */

import {
  beginApprovalResolution,
  confirmApprovalResolution,
  failApprovalResolution,
} from "./state.js";

/**
 * @param {string} sessionId
 * @param {string} approvalId
 * @param {string} decision
 * @returns {{url: string, init: RequestInit}}
 */
export function buildResolveApprovalRequest(sessionId, approvalId, decision) {
  return {
    url: `/sessions/${sessionId}/approvals/${approvalId}`,
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    },
  };
}

/**
 * @param {Response | {status: number, headers?: {get?: (name: string) => string | null}, json?: () => Promise<unknown>, text?: () => Promise<string>}} response
 * @returns {Promise<string>}
 */
async function readApprovalError(response) {
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

/**
 * @param {{
 *   sessionId: string,
 *   approvalId: string,
 *   decision: string,
 *   fetchImpl: (url: string, init: RequestInit) => Promise<Response | {ok: boolean, status: number, headers?: {get?: (name: string) => string | null}, json?: () => Promise<unknown>, text?: () => Promise<string>}>,
 *   syncState: (updater: (state: import("./state.js").DashboardState) => import("./state.js").DashboardState) => void,
 * }} params
 * @returns {Promise<{ok: true} | {ok: false, error: string}>}
 */
export async function resolvePendingApproval(params) {
  const { sessionId, approvalId, decision, fetchImpl, syncState } = params;
  const { url, init } = buildResolveApprovalRequest(sessionId, approvalId, decision);

  syncState(current => beginApprovalResolution(current, approvalId, decision));

  let response;
  try {
    response = await fetchImpl(url, init);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network error";
    syncState(current => failApprovalResolution(current, approvalId, message));
    return { ok: false, error: message };
  }

  if (!response.ok) {
    const message = await readApprovalError(response);
    syncState(current => failApprovalResolution(current, approvalId, message));
    return { ok: false, error: message };
  }

  syncState(current => confirmApprovalResolution(current, approvalId, decision));
  return { ok: true };
}
