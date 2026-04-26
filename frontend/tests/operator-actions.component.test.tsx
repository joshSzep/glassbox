import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { SessionInspector } from "../components/console/session-inspector";
import { createDashboardState, hydrateSelectedSession } from "../state/session-state";
import type { DraftState } from "../stores/dashboard-stores";
import { makeOperatorActionSessionSnapshot } from "./fixtures/session-state";
import { render, screen, userEvent, within } from "./test-utils";

const stream = {
  error: null,
  lastSequence: 8,
  retryCount: 0,
  status: "live" as const,
};

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
      onPromptChange: vi.fn(),
      onResolveApproval: vi.fn(),
      onSubmitAnswer: vi.fn(),
      onSubmitPrompt: vi.fn(),
    };

    render(<ActionHarness callbacks={callbacks} />);

    await user.clear(screen.getByLabelText("Continue session"));
    await user.type(screen.getByLabelText("Continue session"), "Inspect the degraded queue");
    await user.click(screen.getByRole("button", { name: "Send prompt" }));

    expect(callbacks.onPromptChange).toHaveBeenLastCalledWith("Inspect the degraded queue");
    expect(callbacks.onSubmitPrompt).toHaveBeenCalledTimes(1);

    await user.type(screen.getByLabelText("Answer pending question"), "Use the main branch");
    await user.click(screen.getByRole("button", { name: "Submit answer" }));

    expect(callbacks.onSubmitAnswer).toHaveBeenCalledWith("question-1");

    const approvals = screen.getByText("Pending approvals").closest("div");
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

    await user.type(screen.getByLabelText("Create fork"), "retry with focused context");
    await user.click(screen.getByRole("button", { name: "Fork Continue from tool result" }));

    expect(callbacks.onFork).toHaveBeenCalledWith({
      branchLabel: "retry with focused context",
      turnId: "turn-1",
    });
  });
});

function ActionHarness({
  callbacks,
}: {
  callbacks: {
    onFork: (input?: { branchLabel?: string | null; turnId?: string | null }) => void;
    onPromptChange: (text: string) => void;
    onResolveApproval: (input: { approvalId: string; decision: "approved" | "denied" }) => void;
    onSubmitAnswer: (questionId: string) => void;
    onSubmitPrompt: () => void;
  };
}) {
  const [drafts, setDrafts] = useState(() => makeDrafts());
  const data = hydrateSelectedSession(
    createDashboardState(),
    makeOperatorActionSessionSnapshot("session-1"),
  );

  return (
    <SessionInspector
      activeTab="actions"
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
      onResolveApproval={callbacks.onResolveApproval}
      onSubmitAnswer={callbacks.onSubmitAnswer}
      onSubmitPrompt={callbacks.onSubmitPrompt}
      queue="active"
      stream={stream}
    />
  );
}
