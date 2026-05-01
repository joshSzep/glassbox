import {
  createFailedActionStatus,
  createPendingActionStatus,
  createSucceededActionStatus,
} from "@/stores/store-actions";
import { withoutAnswerTextDraft } from "@/stores/session-store-drafts";
import { requireSelectedSessionId } from "@/stores/session-store-shared";
import type { SessionActionContext } from "@/stores/session-store-types";

export async function forkSessionAction(
  { actionRequests, apiClient, get, set }: SessionActionContext,
  input: { branchLabel?: string | null; turnId?: string | null } = {},
): Promise<string | null> {
  const sessionId = requireSelectedSessionId(get().data);
  const currentActionRequestId = actionRequests.next();
  set({ action: createPendingActionStatus("fork") });
  try {
    const fork = await apiClient.forkSession({
      branchLabel: (input.branchLabel ?? get().drafts.forkLabel) || null,
      sessionId,
      turnId: input.turnId ?? get().data.selectedForkTurnId,
    });
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set((state) => ({
        action: createSucceededActionStatus("fork"),
        drafts: { ...state.drafts, forkLabel: "" },
      }));
    }
    return fork.child_session_id;
  } catch (error) {
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createFailedActionStatus("fork", error) });
    }
    return null;
  }
}

export async function abandonToolAttemptAction(
  { actionRequests, apiClient, get, set }: SessionActionContext,
  { reason, toolAttemptId }: { reason?: string; toolAttemptId: string },
): Promise<void> {
  const sessionId = requireSelectedSessionId(get().data);
  const currentActionRequestId = actionRequests.next();
  set({ action: createPendingActionStatus("tool-abandon") });
  try {
    await apiClient.abandonToolAttempt({
      reason: reason ?? "dashboard abandoned stale tool attempt",
      sessionId,
      toolAttemptId,
    });
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createSucceededActionStatus("tool-abandon") });
    }
  } catch (error) {
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createFailedActionStatus("tool-abandon", error) });
    }
  }
}

export async function requestCancellationAction({
  actionRequests,
  apiClient,
  get,
  set,
}: SessionActionContext): Promise<void> {
  const data = get().data;
  const sessionId = requireSelectedSessionId(data);
  const currentActionRequestId = actionRequests.next();
  set({ action: createPendingActionStatus("cancel") });
  try {
    await apiClient.cancelTurn({
      reason: "operator requested cancellation from dashboard",
      sessionId,
      turnId: data.currentTurn?.turn_id ?? null,
    });
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createSucceededActionStatus("cancel") });
    }
  } catch (error) {
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createFailedActionStatus("cancel", error) });
    }
  }
}

export async function resolveApprovalAction(
  { actionRequests, apiClient, get, set }: SessionActionContext,
  input: { approvalId: string; decision: "approved" | "denied" },
): Promise<void> {
  const sessionId = requireSelectedSessionId(get().data);
  const currentActionRequestId = actionRequests.next();
  set({ action: createPendingActionStatus("approval") });
  try {
    await apiClient.resolveApproval({ ...input, sessionId });
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createSucceededActionStatus("approval") });
    }
  } catch (error) {
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createFailedActionStatus("approval", error) });
    }
  }
}

export async function submitAnswerAction(
  { actionRequests, apiClient, get, set }: SessionActionContext,
  { answer, questionId }: { answer?: string; questionId: string },
): Promise<void> {
  const sessionId = requireSelectedSessionId(get().data);
  const currentActionRequestId = actionRequests.next();
  const answerText = answer ?? get().drafts.answerTextByQuestionId[questionId] ?? "";
  set({ action: createPendingActionStatus("answer") });
  try {
    await apiClient.submitAnswer({ answer: answerText, questionId, sessionId });
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set((state) => ({
        action: createSucceededActionStatus("answer"),
        drafts: withoutAnswerTextDraft(state.drafts, questionId),
      }));
    }
  } catch (error) {
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createFailedActionStatus("answer", error) });
    }
  }
}

export async function submitPromptAction(
  { actionRequests, apiClient, get, set }: SessionActionContext,
  text?: string,
): Promise<void> {
  const sessionId = requireSelectedSessionId(get().data);
  const currentActionRequestId = actionRequests.next();
  const prompt = text ?? get().drafts.composerText;
  set({ action: createPendingActionStatus("prompt") });
  try {
    await apiClient.submitMessage({ sessionId, text: prompt });
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set((state) => ({
        action: createSucceededActionStatus("prompt"),
        drafts: { ...state.drafts, composerText: "" },
      }));
    }
  } catch (error) {
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createFailedActionStatus("prompt", error) });
    }
  }
}

export async function retryToolAttemptAction(
  { actionRequests, apiClient, get, set }: SessionActionContext,
  { toolAttemptId }: { toolAttemptId: string },
): Promise<void> {
  const sessionId = requireSelectedSessionId(get().data);
  const currentActionRequestId = actionRequests.next();
  set({ action: createPendingActionStatus("tool-retry") });
  try {
    await apiClient.retryToolAttempt({
      reason: "dashboard requested tool-attempt retry",
      sessionId,
      toolAttemptId,
    });
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createSucceededActionStatus("tool-retry") });
    }
  } catch (error) {
    if (actionRequests.isCurrent(currentActionRequestId)) {
      set({ action: createFailedActionStatus("tool-retry", error) });
    }
  }
}
