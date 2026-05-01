import type { DraftState } from "@/stores/session-store-types";

export function createEmptyDraftState(): DraftState {
  return {
    answerTextByQuestionId: {},
    composerText: "",
    forkLabel: "",
    selectedCompareTargetId: null,
  };
}

export function withAnswerTextDraft(
  drafts: DraftState,
  questionId: string,
  text: string,
): DraftState {
  return {
    ...drafts,
    answerTextByQuestionId: {
      ...drafts.answerTextByQuestionId,
      [questionId]: text,
    },
  };
}

export function withoutAnswerTextDraft(drafts: DraftState, questionId: string): DraftState {
  const remainingAnswers = { ...drafts.answerTextByQuestionId };
  delete remainingAnswers[questionId];
  return { ...drafts, answerTextByQuestionId: remainingAnswers };
}
