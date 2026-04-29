export type LoadState = "failed" | "idle" | "loaded" | "loading";

export type AsyncActionPhase = "failed" | "idle" | "pending" | "succeeded";

export type StoreActionStatus<K extends string> = {
  error: string | null;
  kind: K | null;
  state: AsyncActionPhase;
};

export type RequestTracker = {
  current: () => number;
  invalidate: () => void;
  isCurrent: (requestId: number) => boolean;
  next: () => number;
};

export function createRequestTracker(): RequestTracker {
  let requestId = 0;
  return {
    current: () => requestId,
    invalidate: () => {
      requestId += 1;
    },
    isCurrent: (currentRequestId) => currentRequestId === requestId,
    next: () => {
      requestId += 1;
      return requestId;
    },
  };
}

export function createIdleActionStatus<K extends string>(): StoreActionStatus<K> {
  return { error: null, kind: null, state: "idle" };
}

export function createPendingActionStatus<K extends string>(kind: K): StoreActionStatus<K> {
  return { error: null, kind, state: "pending" };
}

export function createSucceededActionStatus<K extends string>(kind: K): StoreActionStatus<K> {
  return { error: null, kind, state: "succeeded" };
}

export function createFailedActionStatus<K extends string>(
  kind: K,
  error: unknown,
): StoreActionStatus<K> {
  return { error: errorMessage(error), kind, state: "failed" };
}

export async function runAsyncStoreAction<K extends string>({
  action,
  kind,
  onSuccess,
  setAction,
}: {
  action: () => Promise<unknown>;
  kind: K;
  onSuccess?: () => Promise<void> | void;
  setAction: (status: StoreActionStatus<K>) => void;
}) {
  setAction(createPendingActionStatus(kind));
  try {
    await action();
    setAction(createSucceededActionStatus(kind));
    await onSuccess?.();
  } catch (error) {
    setAction(createFailedActionStatus(kind, error));
  }
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected Glassbox dashboard error.";
}
