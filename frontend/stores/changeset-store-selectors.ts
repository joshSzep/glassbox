import type {
  ChangesetDetailState,
  ChangesetPageState,
  ChangesetRepositoryIntelligenceState,
} from "@/stores/changeset-store";

export function createIdleChangesetPageState(): ChangesetPageState {
  return { error: null, items: [], loadState: "idle" };
}

export function createIdleChangesetDetailState(): ChangesetDetailState {
  return {
    branchSearchDetail: null,
    commitMessage: null,
    commitReadiness: null,
    detail: null,
    error: null,
    handoffReadiness: null,
    lastActionMessage: null,
    loadState: "idle",
    repositoryIntelligence: createIdleChangesetRepositoryIntelligenceState(),
    selectedChangesetId: null,
    verificationPlan: null,
  };
}

export function createLoadingChangesetDetailState(changesetId: string): ChangesetDetailState {
  return {
    branchSearchDetail: null,
    commitMessage: null,
    commitReadiness: null,
    detail: null,
    error: null,
    handoffReadiness: null,
    lastActionMessage: null,
    loadState: "loading",
    repositoryIntelligence: createIdleChangesetRepositoryIntelligenceState("loading"),
    selectedChangesetId: changesetId,
    verificationPlan: null,
  };
}

export function createFailedChangesetDetailState({
  changesetId,
  error,
}: {
  changesetId: string;
  error: string;
}): ChangesetDetailState {
  return {
    branchSearchDetail: null,
    commitMessage: null,
    commitReadiness: null,
    detail: null,
    error,
    handoffReadiness: null,
    lastActionMessage: null,
    loadState: "failed",
    repositoryIntelligence: createIdleChangesetRepositoryIntelligenceState(),
    selectedChangesetId: changesetId,
    verificationPlan: null,
  };
}

export function createIdleChangesetRepositoryIntelligenceState(
  loadState: ChangesetRepositoryIntelligenceState["loadState"] = "idle",
): ChangesetRepositoryIntelligenceState {
  return {
    commandRecipes: [],
    error: null,
    freshness: null,
    loadState,
    pathInspections: [],
    verification: null,
  };
}

export function requireSelectedChangesetId(detail: ChangesetDetailState): string {
  if (detail.selectedChangesetId === null) {
    throw new Error("No changeset is selected.");
  }
  return detail.selectedChangesetId;
}
