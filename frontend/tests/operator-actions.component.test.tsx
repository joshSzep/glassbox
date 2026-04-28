import { useState } from "react";
import { cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionInspector } from "../components/console/session-inspector";
import type { SessionStreamState } from "../api/sse";
import type { components } from "../generated/api-types";
import {
  createDashboardState,
  hydrateSelectedSession,
  type DashboardState,
} from "../state/session-state";
import type { ActionStatus, DraftState } from "../stores/dashboard-stores";
import { makeOperatorActionSessionSnapshot, makeProjectionHealth } from "./fixtures/session-state";
import { render, screen, userEvent, waitFor, within } from "./test-utils";

const stream = {
  error: null,
  lastSequence: 8,
  retryCount: 0,
  status: "live" as const,
};

afterEach(() => {
  cleanup();
});

function makeDrafts(overrides: Partial<DraftState> = {}): DraftState {
  return {
    answerTextByQuestionId: {},
    composerText: "Continue from the latest evidence",
    forkLabel: "",
    selectedCompareTargetId: null,
    ...overrides,
  };
}

describe("operator action component harness", () => {
  it("exercises prompt, question, approval, and fork controls with Testing Library", async () => {
    const user = userEvent.setup();
    const callbacks = {
      onFork: vi.fn(),
      onCompareSession: vi.fn(),
      onOpenSession: vi.fn(),
      onPromptChange: vi.fn(),
      onRequestCancellation: vi.fn(),
      onResolveApproval: vi.fn(),
      onSubmitAnswer: vi.fn(),
      onSubmitPrompt: vi.fn(),
    };

    render(
      <ActionHarness
        callbacks={callbacks}
        dataOverrides={{ currentTurn: { status: "running", turn_id: "turn-1" } }}
      />,
    );

    await user.clear(screen.getByLabelText("Continue session"));
    await user.type(screen.getByLabelText("Continue session"), "Inspect the degraded queue");
    await user.click(screen.getByRole("button", { name: "Send prompt" }));

    expect(callbacks.onPromptChange).toHaveBeenLastCalledWith("Inspect the degraded queue");
    expect(callbacks.onSubmitPrompt).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Cancel turn" }));
    expect(callbacks.onRequestCancellation).toHaveBeenCalledTimes(1);

    await user.type(screen.getByLabelText("Answer pending question"), "Use the main branch");
    await user.click(screen.getByRole("button", { name: "Submit answer" }));

    expect(callbacks.onSubmitAnswer).toHaveBeenCalledWith("question-1");

    const approvals = screen.getByText("Pending approvals").closest("section");
    expect(approvals).not.toBeNull();
    await user.click(within(approvals as HTMLElement).getByRole("button", { name: "Approve" }));
    await user.click(within(approvals as HTMLElement).getByRole("button", { name: "Deny" }));

    expect(callbacks.onResolveApproval).toHaveBeenNthCalledWith(1, {
      approvalId: "approval-1",
      decision: "approved",
    });
    expect(callbacks.onResolveApproval).toHaveBeenNthCalledWith(2, {
      approvalId: "approval-1",
      decision: "denied",
    });

    await user.click(screen.getByRole("button", { name: "Create fork" }));
    await user.type(screen.getByLabelText("Fork label"), "retry with focused context");
    await user.click(screen.getByRole("button", { name: "Select Continue from tool result" }));
    await user.click(screen.getByRole("button", { name: "Fork selected point" }));

    expect(callbacks.onFork).toHaveBeenCalledWith({
      branchLabel: "retry with focused context",
      turnId: "turn-1",
    });
  });

  it("places approvals and questions before the composer", () => {
    render(<ActionHarness callbacks={makeCallbacks()} />);

    const text =
      screen.getByRole("complementary", { name: "Selected session inspector" }).textContent ?? "";

    expect(text.indexOf("Pending approvals")).toBeLessThan(text.indexOf("Answer pending question"));
    expect(text.indexOf("Answer pending question")).toBeLessThan(text.indexOf("Continue session"));
  });

  it("moves focus to the selected-session heading when the selected session changes", async () => {
    const callbacks = makeCallbacks();
    const { rerender } = render(
      <ActionHarness callbacks={callbacks} snapshotOverrides={{ session_id: "session-1" }} />,
    );

    rerender(
      <ActionHarness callbacks={callbacks} snapshotOverrides={{ session_id: "session-2" }} />,
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "session-2" })).toHaveFocus();
    });
  });

  it("forks from the latest point when no branchable turns are available", async () => {
    const user = userEvent.setup();
    const callbacks = makeCallbacks();

    render(
      <ActionHarness
        callbacks={callbacks}
        snapshotOverrides={{ branchable_turns: [], latest_fork_point_turn_id: null }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Create fork" }));
    await user.type(screen.getByLabelText("Fork label"), "latest branch");
    await user.click(screen.getByRole("button", { name: "Fork latest point" }));

    expect(callbacks.onFork).toHaveBeenCalledWith({ branchLabel: "latest branch", turnId: null });
  });

  it("opens the fork flow from branchable turns exposed in the timeline", async () => {
    const user = userEvent.setup();
    const callbacks = makeCallbacks();

    render(<ActionHarness callbacks={callbacks} initialActiveTab="timeline" />);

    await user.click(
      screen.getByRole("button", { name: "Open fork flow for Continue from tool result" }),
    );
    await user.type(screen.getByLabelText("Fork label"), "timeline branch");
    expect(screen.getByText("Continue from tool result · sequence 8")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Fork selected point" }));

    expect(callbacks.onFork).toHaveBeenCalledWith({
      branchLabel: "timeline branch",
      turnId: "turn-1",
    });
  });

  it("opens compare, child, and fork flows from the lineage navigator", async () => {
    const user = userEvent.setup();
    const callbacks = makeCallbacks();

    render(
      <ActionHarness
        callbacks={callbacks}
        initialActiveTab="lineage"
        snapshotOverrides={{
          child_sessions: [
            {
              branch_label: "retry with focused context",
              latest_message_summary: "assistant: retrying from fork point",
              session_id: "child-1",
              status: "running",
              updated_at: "2026-04-23T00:00:04Z",
            },
          ],
        }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Compare child-1" }));
    await user.click(screen.getByRole("button", { name: "Open child-1" }));
    await user.click(
      screen.getByRole("button", { name: "Open fork flow for Continue from tool result" }),
    );
    await user.click(screen.getByRole("button", { name: "Fork selected point" }));

    expect(callbacks.onCompareSession).toHaveBeenCalledWith("child-1");
    expect(callbacks.onOpenSession).toHaveBeenCalledWith("child-1");
    expect(callbacks.onFork).toHaveBeenCalledWith({ branchLabel: null, turnId: "turn-1" });
  });

  it("surfaces pending, success, conflict, validation, and network action feedback", () => {
    const cases: { action: ActionStatus; expected: string }[] = [
      { action: { error: null, kind: "prompt", state: "pending" }, expected: "sending prompt" },
      { action: { error: null, kind: "answer", state: "succeeded" }, expected: "answer submitted" },
      {
        action: { error: "approval conflict: already resolved", kind: "approval", state: "failed" },
        expected: "conflict",
      },
      {
        action: { error: "validation error: prompt is empty", kind: "prompt", state: "failed" },
        expected: "validation error",
      },
      {
        action: { error: "network failure: retry request", kind: "fork", state: "failed" },
        expected: "network error",
      },
    ];

    for (const { action, expected } of cases) {
      const { unmount } = render(<ActionHarness action={action} callbacks={makeCallbacks()} />);
      expect(screen.getByText(expected)).toBeVisible();
      unmount();
    }
  });

  it("surfaces historical, live-unavailable, projection, and runtime recovery copy", () => {
    const cases: { expected: string; props: ActionHarnessOverrides }[] = [
      {
        expected: "historical-only",
        props: { snapshotOverrides: { status: "completed" } },
      },
      {
        expected: "live unavailable",
        props: {
          streamOverride: { error: "Live stream disconnected.", status: "live_unavailable" },
        },
      },
      {
        expected: "projection degraded",
        props: {
          snapshotOverrides: {
            projection_health: makeProjectionHealth({ degraded: true, state: "stale" }),
          },
        },
      },
      {
        expected: "runtime offline",
        props: {
          dataOverrides: { runtimeContext: null },
          snapshotOverrides: {
            pending_approvals: [],
            pending_question_id: null,
          },
        },
      },
    ];

    for (const { expected, props } of cases) {
      const { unmount } = render(<ActionHarness callbacks={makeCallbacks()} {...props} />);
      expect(screen.getAllByText(expected)[0]).toBeVisible();
      unmount();
    }
  });
});

function makeCallbacks() {
  return {
    onFork: vi.fn(),
    onCompareSession: vi.fn(),
    onOpenSession: vi.fn(),
    onPromptChange: vi.fn(),
    onRequestCancellation: vi.fn(),
    onResolveApproval: vi.fn(),
    onSubmitAnswer: vi.fn(),
    onSubmitPrompt: vi.fn(),
  };
}

type ActionHarnessProps = {
  action?: ActionStatus;
  callbacks: {
    onFork: (input?: { branchLabel?: string | null; turnId?: string | null }) => void;
    onCompareSession: (sessionId: string) => void;
    onOpenSession: (sessionId: string) => void;
    onPromptChange: (text: string) => void;
    onRequestCancellation: () => void;
    onResolveApproval: (input: { approvalId: string; decision: "approved" | "denied" }) => void;
    onSubmitAnswer: (questionId: string) => void;
    onSubmitPrompt: () => void;
  };
  dataOverrides?: Partial<DashboardState>;
  initialActiveTab?: Parameters<typeof SessionInspector>[0]["activeTab"];
  snapshotOverrides?: Partial<components["schemas"]["SessionSnapshotResponse"]>;
  streamOverride?: Partial<SessionStreamState>;
};

type ActionHarnessOverrides = Omit<ActionHarnessProps, "callbacks">;

function ActionHarness({
  action = { error: null, kind: null, state: "idle" },
  callbacks,
  dataOverrides = {},
  initialActiveTab = "actions",
  snapshotOverrides = {},
  streamOverride = {},
}: ActionHarnessProps) {
  const [activeTab, setActiveTab] = useState(initialActiveTab);
  const [drafts, setDrafts] = useState(() => makeDrafts());
  const data = {
    ...hydrateSelectedSession(
      createDashboardState(),
      makeOperatorActionSessionSnapshot("session-1", snapshotOverrides),
    ),
    ...dataOverrides,
  };
  const mergedStream: SessionStreamState = {
    error: streamOverride.error ?? stream.error,
    lastSequence: streamOverride.lastSequence ?? stream.lastSequence,
    retryCount: streamOverride.retryCount ?? stream.retryCount,
    status: streamOverride.status ?? stream.status,
  };

  return (
    <SessionInspector
      activeTab={activeTab}
      action={action}
      data={data}
      drafts={drafts}
      error={null}
      loadState="loaded"
      onAnswerTextChange={(questionId, text) => {
        setDrafts((current) => ({
          ...current,
          answerTextByQuestionId: { ...current.answerTextByQuestionId, [questionId]: text },
        }));
      }}
      onFork={callbacks.onFork}
      onForkLabelChange={(text) => {
        setDrafts((current) => ({ ...current, forkLabel: text }));
      }}
      onPromptChange={(text) => {
        callbacks.onPromptChange(text);
        setDrafts((current) => ({ ...current, composerText: text }));
      }}
      onRequestCancellation={callbacks.onRequestCancellation}
      onCompareSession={callbacks.onCompareSession}
      onOpenSession={callbacks.onOpenSession}
      onResolveApproval={callbacks.onResolveApproval}
      onSelectTab={setActiveTab}
      onSubmitAnswer={callbacks.onSubmitAnswer}
      onSubmitPrompt={callbacks.onSubmitPrompt}
      queue="active"
      stream={mergedStream}
    />
  );
}
