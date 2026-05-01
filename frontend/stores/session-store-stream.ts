import {
  createSessionEventStream,
  type SessionStreamState,
  type SseEventEnvelope,
} from "@/api/sse";
import { applySessionEvent } from "@/state/session-state";
import type {
  SessionEventStreamFactory,
  SessionEventStreamHandle,
  SessionStoreGet,
  SessionStoreSet,
} from "@/stores/session-store-types";

export function createSessionStreamController({
  createEventStream = createSessionEventStream,
  get,
  set,
}: {
  createEventStream?: SessionEventStreamFactory;
  get: SessionStoreGet;
  set: SessionStoreSet;
}) {
  let streamHandle: SessionEventStreamHandle | null = null;

  const closeStream = () => {
    streamHandle?.close();
    streamHandle = null;
  };

  return {
    applyStreamEnvelope: (envelope: SseEventEnvelope) => {
      set((state) => ({
        data: applySessionEvent(state.data, envelope),
        stream: {
          ...state.stream,
          lastSequence: Math.max(state.stream.lastSequence, envelope.sequence),
        },
      }));
    },
    closeStream,
    connectStream: () => {
      const sessionId = get().data.sessionId;
      if (sessionId === null) {
        return;
      }
      closeStream();
      streamHandle = createEventStream({
        afterSequence: get().data.lastSequence,
        onEnvelope: (envelope) => get().applyStreamEnvelope(envelope),
        onStateChange: (stream) => set({ stream }),
        sessionId,
      });
      streamHandle.start();
    },
    disconnectStream: () => {
      closeStream();
      set({ stream: createIdleStreamState() });
    },
  };
}

export function createIdleStreamState(): SessionStreamState {
  return {
    deliveryMode: "connecting",
    droppedEvents: 0,
    error: null,
    lastSequence: 0,
    projectionLag: null,
    replayedCount: 0,
    retryCount: 0,
    status: "historical_snapshot",
  };
}
