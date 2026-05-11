import type { GlassboxApiClient } from "@/api/client";
import {
  createFailedActionStatus,
  createPendingActionStatus,
  createSucceededActionStatus,
  runAsyncStoreAction,
} from "@/stores/store-actions";

import type { KnowledgeActionKind, KnowledgeStoreState } from "./knowledge-store";

type KnowledgeActionAccess = {
  apiClient: GlassboxApiClient;
  get: () => KnowledgeStoreState;
  set: (
    partial:
      | Partial<KnowledgeStoreState>
      | ((state: KnowledgeStoreState) => Partial<KnowledgeStoreState>),
  ) => void;
};

export async function runKnowledgeMemoryAction({
  action,
  get,
  kind,
  memoryId,
  set,
}: {
  action: () => Promise<unknown>;
  get: () => KnowledgeStoreState;
  kind: KnowledgeActionKind;
  memoryId: string | null;
  set: KnowledgeActionAccess["set"];
}): Promise<void> {
  await runAsyncStoreAction({
    action,
    kind,
    onSuccess: async () => {
      await get().loadMemoryPage();
      if (memoryId !== null) {
        await get().selectMemory(memoryId);
      }
    },
    setAction: (status) => set({ action: status }),
  });
}

export async function previewPruneMemoryAction(
  { apiClient, set }: KnowledgeActionAccess,
  input: { memoryId: string; reason?: string | null },
): Promise<void> {
  set({ action: createPendingActionStatus("preview-prune-memory") });
  try {
    const preview = await apiClient.previewWorkspaceMemoryPrune({
      memoryId: input.memoryId,
      reason: input.reason,
    });
    set((state) => ({
      action: createSucceededActionStatus("preview-prune-memory"),
      memory: { ...state.memory, preview },
    }));
  } catch (error) {
    set({ action: createFailedActionStatus("preview-prune-memory", error) });
  }
}

export async function rebuildRepositoryIndexAction(
  { apiClient, get, set }: KnowledgeActionAccess,
  input: {
    background?: boolean;
    sessionId?: string | null;
  } = {},
): Promise<void> {
  set({ action: createPendingActionStatus("rebuild-index") });
  try {
    const rebuild = await apiClient.rebuildRepositoryIndex({
      background: input.background,
      sessionId: input.sessionId,
    });
    set((state) => ({
      action: createSucceededActionStatus("rebuild-index"),
      repository: { ...state.repository, rebuild },
    }));
    await get().loadRepositoryStatus();
    if (get().repository.query.trim()) {
      await get().searchRepositoryIndex();
    }
  } catch (error) {
    set({ action: createFailedActionStatus("rebuild-index", error) });
  }
}
