import { describe, expect, it } from "vitest";

import {
  GlassboxSseError,
  createSessionEventStream,
  decodeSseEventEnvelope,
  type EventSourceLike,
  type EventSourceMessageEvent,
  type SessionStreamState,
  type SseEventEnvelope,
} from "../api/sse";

class FakeEventSource implements EventSourceLike {
  static instances: FakeEventSource[] = [];

  listeners = new Map<string, ((event: EventSourceMessageEvent) => void)[]>();
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: EventSourceMessageEvent) => void) | null = null;
  onopen: ((event: Event) => void) | null = null;
  closed = false;

  constructor(readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: EventSourceMessageEvent) => void): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close(): void {
    this.closed = true;
  }

  open(): void {
    this.onopen?.(new Event("open"));
  }

  fail(): void {
    this.onerror?.(new Event("error"));
  }

  emit(envelope: SseEventEnvelope): void {
    const event = { data: JSON.stringify(envelope) };
    this.listeners.get(envelope.event_type)?.forEach((listener) => listener(event));
  }
}

function resetFakeEventSources(): void {
  FakeEventSource.instances = [];
}

function envelope(sequence: number, eventType: SseEventEnvelope["event_type"]): SseEventEnvelope {
  return {
    created_at: "2026-04-26T00:00:00Z",
    event_id: `event-${sequence}`,
    event_type: eventType,
    payload: { event_type: eventType },
    sequence,
    session_id: "session-1",
  };
}

function createManualScheduler() {
  const callbacks: (() => void)[] = [];
  return {
    callbacks,
    scheduler: {
      clearTimeout: () => undefined,
      setTimeout: (callback: () => void) => {
        callbacks.push(callback);
        return callbacks.length;
      },
    },
  };
}

describe("decodeSseEventEnvelope", () => {
  it("decodes typed Glassbox SSE envelopes", () => {
    expect(decodeSseEventEnvelope(JSON.stringify(envelope(7, "ToolOutputChunk")))).toMatchObject({
      event_type: "ToolOutputChunk",
      sequence: 7,
    });
  });

  it("rejects malformed or unknown event data", () => {
    expect(() => decodeSseEventEnvelope("not json")).toThrow(GlassboxSseError);
    expect(() =>
      decodeSseEventEnvelope(
        JSON.stringify({ ...envelope(1, "SessionStarted"), event_type: "Nope" }),
      ),
    ).toThrow(GlassboxSseError);
  });
});

describe("createSessionEventStream", () => {
  it("opens the session events URL and transitions from connecting to live", () => {
    resetFakeEventSources();
    const states: SessionStreamState[] = [];
    const stream = createSessionEventStream({
      EventSourceImpl: FakeEventSource,
      afterSequence: 3,
      baseUrl: "http://api.test",
      onStateChange: (state) => states.push(state),
      sessionId: "session/1",
    });

    stream.start();
    expect(FakeEventSource.instances[0].url).toBe(
      "http://api.test/sessions/session%2F1/events?after=3",
    );
    FakeEventSource.instances[0].open();

    expect(states.map((state) => state.status)).toEqual(["connecting", "live"]);
  });

  it("dispatches decoded events and resumes after the latest sequence", () => {
    resetFakeEventSources();
    const { callbacks, scheduler } = createManualScheduler();
    const received: SseEventEnvelope[] = [];
    const states: SessionStreamState[] = [];
    const stream = createSessionEventStream({
      EventSourceImpl: FakeEventSource,
      maxReconnectAttempts: 2,
      onEnvelope: (receivedEnvelope) => received.push(receivedEnvelope),
      onStateChange: (state) => states.push(state),
      reconnectDelayMs: 1,
      scheduler,
      sessionId: "session-1",
    });

    stream.start();
    const firstSource = FakeEventSource.instances[0];
    firstSource.open();
    firstSource.emit(envelope(5, "AssistantMessageCompleted"));
    firstSource.fail();

    expect(received).toHaveLength(1);
    expect(stream.getState()).toMatchObject({ lastSequence: 5, status: "reconnecting" });
    expect(callbacks).toHaveLength(1);

    callbacks[0]();
    expect(FakeEventSource.instances[1].url).toBe("/sessions/session-1/events?after=5");
    expect(firstSource.closed).toBe(true);
    expect(states.map((state) => state.status)).toContain("reconnecting");
  });

  it("marks the stream unavailable after retry attempts are exhausted", () => {
    resetFakeEventSources();
    const { callbacks, scheduler } = createManualScheduler();
    const errors: GlassboxSseError[] = [];
    const stream = createSessionEventStream({
      EventSourceImpl: FakeEventSource,
      maxReconnectAttempts: 1,
      onError: (error) => errors.push(error),
      scheduler,
      sessionId: "session-1",
    });

    stream.start();
    FakeEventSource.instances[0].fail();
    callbacks[0]();
    FakeEventSource.instances[1].fail();

    expect(errors).toHaveLength(2);
    expect(stream.getState()).toMatchObject({
      retryCount: 1,
      status: "live_unavailable",
    });
  });

  it("moves terminal session events to historical snapshot state", () => {
    resetFakeEventSources();
    const stream = createSessionEventStream({
      EventSourceImpl: FakeEventSource,
      sessionId: "session-1",
    });

    stream.start();
    FakeEventSource.instances[0].open();
    FakeEventSource.instances[0].emit(envelope(9, "SessionCompleted"));

    expect(FakeEventSource.instances[0].closed).toBe(true);
    expect(stream.getState()).toMatchObject({
      lastSequence: 9,
      status: "historical_snapshot",
    });
  });
});
