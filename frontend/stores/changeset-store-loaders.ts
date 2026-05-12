import type {
  BranchSearchDetailResponse,
  ChangesetDetailResponse,
  ChangesetVerificationPlanPreviewResponse,
  GlassboxApiClient,
} from "@/api/client";
import type {
  ChangesetRepositoryIntelligenceState,
  ChangesetStoreState,
} from "@/stores/changeset-store";
import {
  createFailedChangesetDetailState,
  createIdleChangesetRepositoryIntelligenceState,
  createLoadingChangesetDetailState,
} from "@/stores/changeset-store-selectors";
import { errorMessage, type createRequestTracker } from "@/stores/store-actions";

export type ChangesetStoreSet = {
  (
    partial:
      | ChangesetStoreState
      | Partial<ChangesetStoreState>
      | ((state: ChangesetStoreState) => ChangesetStoreState | Partial<ChangesetStoreState>),
    replace?: false,
  ): void;
};

export type ChangesetStoreGet = () => ChangesetStoreState;
export type RequestTracker = ReturnType<typeof createRequestTracker>;

export const CHANGESET_PAGE_SIZE = 100;

export type ReloadSelectedChangesetOptions = {
  lastActionMessage: string | null;
};

export async function loadChangesetPage(input: {
  apiClient: GlassboxApiClient;
  listRequests: RequestTracker;
  query?: { sessionId?: string | null };
  set: ChangesetStoreSet;
}): Promise<void> {
  const currentRequestId = input.listRequests.next();
  input.set((state) => ({
    page: { ...state.page, error: null, loadState: "loading" },
  }));
  try {
    const page = await input.apiClient.getChangesetPage({
      limit: CHANGESET_PAGE_SIZE,
      session_id: input.query?.sessionId ?? undefined,
    });
    if (!input.listRequests.isCurrent(currentRequestId)) {
      return;
    }
    input.set({ page: { error: null, items: page.items, loadState: "loaded" } });
  } catch (error) {
    if (!input.listRequests.isCurrent(currentRequestId)) {
      return;
    }
    input.set((state) => ({
      page: { ...state.page, error: errorMessage(error), loadState: "failed" },
    }));
  }
}

export async function selectChangeset(input: {
  apiClient: GlassboxApiClient;
  changesetId: string;
  detailRequests: RequestTracker;
  set: ChangesetStoreSet;
}): Promise<void> {
  const currentRequestId = input.detailRequests.next();
  input.set({ detail: createLoadingChangesetDetailState(input.changesetId) });
  try {
    const detail = await input.apiClient.getChangesetDetail(input.changesetId);
    const [
      verificationPlan,
      commitReadiness,
      handoffReadiness,
      commitMessage,
      evidenceGraph,
      branchSearchDetail,
    ] = await Promise.all([
      input.apiClient.getChangesetVerificationPlan(input.changesetId),
      input.apiClient.getChangesetCommitReadiness(input.changesetId),
      input.apiClient.getChangesetHandoffReadiness(input.changesetId),
      input.apiClient.getChangesetCommitMessage(input.changesetId),
      input.apiClient.getChangesetEvidenceGraph(input.changesetId).catch(() => null),
      loadBranchSearchForChangeset(input.apiClient, detail),
    ]);
    const repositoryIntelligence = await loadRepositoryIntelligenceForChangeset(
      input.apiClient,
      verificationPlan,
    );
    if (!input.detailRequests.isCurrent(currentRequestId)) {
      return;
    }
    input.set({
      detail: {
        branchSearchDetail,
        commitMessage,
        commitReadiness,
        detail,
        evidenceGraph,
        error: null,
        handoffReadiness,
        lastActionMessage: null,
        loadState: "loaded",
        repositoryIntelligence,
        selectedChangesetId: input.changesetId,
        verificationPlan,
      },
    });
  } catch (error) {
    if (!input.detailRequests.isCurrent(currentRequestId)) {
      return;
    }
    input.set({
      detail: createFailedChangesetDetailState({
        changesetId: input.changesetId,
        error: errorMessage(error),
      }),
    });
  }
}

export async function reloadSelectedChangeset(
  apiClient: GlassboxApiClient,
  changesetId: string,
  set: ChangesetStoreSet,
  options: ReloadSelectedChangesetOptions,
): Promise<void> {
  const detail = await apiClient.getChangesetDetail(changesetId);
  const [
    verificationPlan,
    commitReadiness,
    handoffReadiness,
    commitMessage,
    evidenceGraph,
    branchSearchDetail,
  ] = await Promise.all([
    apiClient.getChangesetVerificationPlan(changesetId),
    apiClient.getChangesetCommitReadiness(changesetId),
    apiClient.getChangesetHandoffReadiness(changesetId),
    apiClient.getChangesetCommitMessage(changesetId),
    apiClient.getChangesetEvidenceGraph(changesetId).catch(() => null),
    loadBranchSearchForChangeset(apiClient, detail),
  ]);
  const repositoryIntelligence = await loadRepositoryIntelligenceForChangeset(
    apiClient,
    verificationPlan,
  );
  set({
    detail: {
      branchSearchDetail,
      commitMessage,
      commitReadiness,
      detail,
      evidenceGraph,
      error: null,
      handoffReadiness,
      lastActionMessage: options.lastActionMessage,
      loadState: "loaded",
      repositoryIntelligence,
      selectedChangesetId: changesetId,
      verificationPlan,
    },
  });
}

export async function loadBranchSearchForChangeset(
  apiClient: GlassboxApiClient,
  detail: ChangesetDetailResponse,
): Promise<BranchSearchDetailResponse | null> {
  const searchId = detail.changeset.branch_search_id;
  if (searchId === null || searchId === undefined) {
    return null;
  }
  try {
    return await apiClient.getBranchSearchDetail(searchId);
  } catch {
    return null;
  }
}

export async function loadRepositoryIntelligenceForChangeset(
  apiClient: GlassboxApiClient,
  verificationPlan: ChangesetVerificationPlanPreviewResponse,
): Promise<ChangesetRepositoryIntelligenceState> {
  const changedPaths = verificationPlan.changed_paths.slice(0, 6);
  if (changedPaths.length === 0) {
    return createIdleChangesetRepositoryIntelligenceState("loaded");
  }

  const [freshnessResult, verificationResult, recipesResult, ...pathResults] =
    await Promise.allSettled([
      apiClient.getRepositoryIntelligenceFreshness(),
      apiClient.recommendRepositoryIntelligenceVerification({ paths: changedPaths }),
      apiClient.listRepositoryIntelligenceCommandRecipes({ limit: 8 }),
      ...changedPaths.slice(0, 4).map((path) => apiClient.inspectRepositoryIntelligencePath(path)),
    ]);

  const freshness = freshnessResult.status === "fulfilled" ? freshnessResult.value : null;
  const verification = verificationResult.status === "fulfilled" ? verificationResult.value : null;
  const listedRecipes = recipesResult.status === "fulfilled" ? recipesResult.value.items : [];
  const pathInspections = pathResults.flatMap((result) =>
    result.status === "fulfilled" ? [result.value] : [],
  );
  const commandRecipes = dedupeCommandRecipes([
    ...pathInspections.flatMap((inspection) => inspection.command_recipes),
    ...listedRecipes,
  ]);
  const firstError = [freshnessResult, verificationResult, recipesResult, ...pathResults].find(
    (result) => result.status === "rejected",
  );

  return {
    commandRecipes,
    error:
      firstError !== undefined && firstError.status === "rejected"
        ? errorMessage(firstError.reason)
        : null,
    freshness,
    loadState:
      freshness === null && verification === null && pathInspections.length === 0
        ? "failed"
        : "loaded",
    pathInspections,
    verification,
  };
}

function dedupeCommandRecipes(
  recipes: ChangesetRepositoryIntelligenceState["commandRecipes"],
): ChangesetRepositoryIntelligenceState["commandRecipes"] {
  const seen = new Set<string>();
  const deduped: ChangesetRepositoryIntelligenceState["commandRecipes"] = [];
  for (const recipe of recipes) {
    if (seen.has(recipe.recipe_id)) {
      continue;
    }
    seen.add(recipe.recipe_id);
    deduped.push(recipe);
  }
  return deduped;
}
