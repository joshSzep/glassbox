import type { DashboardState } from "@/state/session-state";

export function requireSelectedSessionId(data: DashboardState): string {
  if (data.sessionId === null) {
    throw new Error("No selected session is loaded.");
  }
  return data.sessionId;
}
