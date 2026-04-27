export const defaultSessionId = "session-1";
export const defaultChildSessionId = "child-1";
export const largeTranscriptSessionId = "large-transcript-session";

type CriticalViewport = "desktop" | "narrow-desktop" | "tablet" | "mobile";

type V4ConsoleScenarioFixture = {
  childSessionId?: string;
  compareSessionId?: string;
  criticalViewports: CriticalViewport[];
  expectedOperatorDecision: string;
  mobileOverflowExpectations: string[];
  route: string;
  sessionId?: string;
  summary: string;
};

export const v4ConsoleScenarioFixtures = {
  "empty-workspace": {
    criticalViewports: ["desktop", "mobile"],
    expectedOperatorDecision: "Confirm there is no current operator work.",
    mobileOverflowExpectations: ["workspace status and empty queue copy wrap without clipping"],
    route: "/app",
    summary: "Empty workspace with no current operator work.",
  },
  "all-queues": {
    criticalViewports: ["desktop", "narrow-desktop", "mobile"],
    expectedOperatorDecision: "Pick the highest-priority pending approval before lower queues.",
    mobileOverflowExpectations: [
      "queue rows expose next action and pending subject as stacked text",
      "no session summary requires horizontal scrolling",
    ],
    route: "/app",
    sessionId: defaultSessionId,
    summary: "Workspace overview with mixed action queues and recent sessions.",
  },
  "live-session": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision:
      "Continue or answer the live session while preserving stream context.",
    mobileOverflowExpectations: [
      "composer and answer controls remain reachable before passive diagnostics",
      "live output wraps inside the selected-session flow",
    ],
    route: `/app?session=${defaultSessionId}&queue=active`,
    sessionId: defaultSessionId,
    summary: "Live running session with stream output and active tool context.",
  },
  "historical-session": {
    criticalViewports: ["desktop", "mobile"],
    expectedOperatorDecision:
      "Inspect a completed session without mistaking it for broken live work.",
    mobileOverflowExpectations: ["historical status and unavailable live actions wrap clearly"],
    route: "/app?session=historical-session&queue=historical",
    sessionId: "historical-session",
    summary: "Completed historical snapshot with no expected live stream.",
  },
  "failed-session": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision: "Decide whether the retryable failure needs inspection or recovery.",
    mobileOverflowExpectations: [
      "failure summary appears before generic evidence",
      "retry guidance wraps without covering queue rows",
    ],
    route: "/app?session=failed-session&queue=failures",
    sessionId: "failed-session",
    summary: "Failed session with retryable failure summary visible.",
  },
  "pending-approval": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision:
      "Approve or deny the requested workspace write with risk context visible.",
    mobileOverflowExpectations: [
      "approve and deny buttons stay in the primary action area",
      "approval subject, reason, and risk label wrap without clipping",
    ],
    route: "/app?session=approval-session&queue=approvals",
    sessionId: "approval-session",
    summary: "Session awaiting explicit tool approval.",
  },
  "pending-question": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision: "Answer the pending ask_user question before sending new prompts.",
    mobileOverflowExpectations: [
      "question text and answer control stay above transcript/evidence detail",
      "answer copy wraps inside the action card",
    ],
    route: "/app?session=question-session&queue=questions",
    sessionId: "question-session",
    summary: "Session awaiting an ask_user answer.",
  },
  "branched-session": {
    childSessionId: defaultChildSessionId,
    criticalViewports: ["desktop", "mobile"],
    expectedOperatorDecision:
      "Inspect child lineage and decide whether to fork from the latest boundary.",
    mobileOverflowExpectations: [
      "lineage rows and fork controls wrap without hiding branch labels",
    ],
    route: `/app?session=${defaultSessionId}&queue=active`,
    sessionId: defaultSessionId,
    summary: "Session with parent and child lineage plus forkable turn evidence.",
  },
  "compare-view": {
    compareSessionId: "parent-session",
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision:
      "Compare the selected session against its parent before branch triage.",
    mobileOverflowExpectations: [
      "compare target and compared transcript remain readable in a stacked layout",
      "long branch labels wrap without pushing actions off screen",
    ],
    route: `/app?session=${defaultSessionId}&queue=active&compare=parent-session&tab=compare`,
    sessionId: defaultSessionId,
    summary: "Selected session with a parent compare target loaded.",
  },
  "projection-degraded": {
    criticalViewports: ["desktop", "mobile"],
    expectedOperatorDecision:
      "Check projection health while preserving confidence in canonical events.",
    mobileOverflowExpectations: [
      "projection detail and repair guidance wrap as advisory health copy",
    ],
    route: "/app?session=degraded-session&queue=degraded",
    sessionId: "degraded-session",
    summary: "Projection-degraded session whose canonical events remain inspectable.",
  },
  "artifact-drift": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision:
      "Inspect artifact-backed drift cues without treating them as runtime failure.",
    mobileOverflowExpectations: [
      "artifact labels and summaries have visible separation",
      "long artifact and target paths wrap within evidence panels",
    ],
    route: "/app?session=artifact-session&queue=active",
    sessionId: "artifact-session",
    summary: "Runtime-context snapshot with artifact-backed verification and drift cues.",
  },
  "large-transcript": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision:
      "Keep the current action visible while scanning a noisy live session.",
    mobileOverflowExpectations: [
      "long transcript entries wrap without widening the viewport",
      "active tool output and artifact cues do not bury the pending approval",
    ],
    route: `/app?session=${largeTranscriptSessionId}&queue=active&tab=transcript`,
    sessionId: largeTranscriptSessionId,
    summary:
      "Noisy live session with long transcript, tool output, runtime notes, approvals, and artifacts.",
  },
} satisfies Record<string, V4ConsoleScenarioFixture>;

export type V4ConsoleScenarioId = keyof typeof v4ConsoleScenarioFixtures;
