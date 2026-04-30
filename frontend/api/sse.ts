import { buildApiUrl } from "./client";

export const glassboxEventTypes = [
  "SessionStarted",
  "SessionResumed",
  "SessionCompleted",
  "SessionFailed",
  "UserMessageReceived",
  "TranscriptMessageImported",
  "AssistantMessageStarted",
  "AssistantMessageDelta",
  "AssistantMessageCompleted",
  "TurnStarted",
  "TurnStatusChanged",
  "TurnCompleted",
  "TurnFailed",
  "CancellationRequested",
  "CancellationAcknowledged",
  "TurnCancelled",
  "ToolExecutionCancelled",
  "CancellationFailed",
  "ModelCallStarted",
  "ModelCallCompleted",
  "ModelToolCallRequested",
  "ToolExecutionStarted",
  "ToolOutputChunk",
  "ToolArtifactRecorded",
  "ReplayArtifactRecorded",
  "ToolExecutionCompleted",
  "ApprovalRequested",
  "ApprovalResolved",
  "UserQuestionAsked",
  "UserAnswerProvided",
  "LongRunPhaseChanged",
  "TaskCheckpointCreated",
  "ContextCompactionCreated",
  "ToolAttemptHeartbeat",
  "RecoveryDecisionRecorded",
  "ResumeOutcomeRecorded",
  "ProviderRecoveryRecorded",
  "RuntimeNoteRecorded",
  "RuntimeNoteImported",
  "ErrorRecorded",
] as const;

export type GlassboxEventType = (typeof glassboxEventTypes)[number];

export type GlassboxEventPayload<TEvent extends GlassboxEventType = GlassboxEventType> = {
  event_type?: TEvent;
} & Record<string, unknown>;

export type SseEventEnvelope<TEvent extends GlassboxEventType = GlassboxEventType> = {
  created_at: string;
  event_id: string;
  event_type: TEvent;
  payload: GlassboxEventPayload<TEvent>;
  sequence: number;
  session_id: string;
};

export type StreamDeliveryMode = "connecting" | "degraded" | "live" | "replaying_history";

export type SseStreamStatus = {
  after_sequence: number;
  canonical_last_sequence: number;
  history_truncated: boolean;
  last_delivered_sequence: number;
  message: string | null;
  projection_health: {
    degraded: boolean;
    lag: number;
    state: string;
  } | null;
  replayed_count: number;
  status: Exclude<StreamDeliveryMode, "connecting">;
  transport: {
    dropped_events: number;
    last_published_sequence: number | null;
    max_queue_depth: number;
    queue_capacity: number;
    subscriber_count: number;
  } | null;
};

export type SessionStreamStatus =
  | "connecting"
  | "historical_snapshot"
  | "live"
  | "live_unavailable"
  | "reconnecting";

export type SessionStreamState = {
  deliveryMode: StreamDeliveryMode;
  droppedEvents: number;
  error: string | null;
  lastSequence: number;
  projectionLag: number | null;
  replayedCount: number;
  retryCount: number;
  status: SessionStreamStatus;
};

export class GlassboxSseError extends Error {
  readonly detail: unknown;

  constructor(message: string, detail: unknown = null) {
    super(message);
    this.name = "GlassboxSseError";
    this.detail = detail;
  }
}

export type EventSourceMessageEvent = {
  data: string;
};

export type EventSourceLike = {
  addEventListener: (type: string, listener: (event: EventSourceMessageEvent) => void) => void;
  close: () => void;
  onerror: ((event: Event) => void) | null;
  onmessage: ((event: EventSourceMessageEvent) => void) | null;
  onopen: ((event: Event) => void) | null;
};

export type EventSourceConstructor = new (url: string) => EventSourceLike;

export type StreamScheduler = {
  clearTimeout: (timeoutId: unknown) => void;
  setTimeout: (callback: () => void, delayMs: number) => unknown;
};

export type SessionEventStreamOptions = {
  EventSourceImpl?: EventSourceConstructor;
  afterSequence?: number;
  baseUrl?: string;
  maxReconnectAttempts?: number;
  onControl?: (status: SseStreamStatus) => void;
  onEnvelope?: (envelope: SseEventEnvelope) => void;
  onError?: (error: GlassboxSseError) => void;
  onStateChange?: (state: SessionStreamState) => void;
  reconnectDelayMs?: number;
  scheduler?: StreamScheduler;
  sessionId: string;
};

const TERMINAL_EVENT_TYPES = new Set<GlassboxEventType>(["SessionCompleted", "SessionFailed"]);

const eventTypeSet = new Set<string>(glassboxEventTypes);
const streamStatusEventType = "glassbox.stream.status";

export function decodeSseEventEnvelope(data: string): SseEventEnvelope {
  let parsed: unknown;
  try {
    parsed = JSON.parse(data) as unknown;
  } catch (error) {
    throw new GlassboxSseError("SSE event data was not valid JSON.", error);
  }

  if (!isRecord(parsed)) {
    throw new GlassboxSseError("SSE event data was not an object.", parsed);
  }

  const eventType = parsed.event_type;
  if (typeof eventType !== "string" || !eventTypeSet.has(eventType)) {
    throw new GlassboxSseError("SSE event type is not recognized.", parsed);
  }

  if (
    typeof parsed.event_id !== "string" ||
    typeof parsed.session_id !== "string" ||
    typeof parsed.sequence !== "number" ||
    typeof parsed.created_at !== "string" ||
    !isRecord(parsed.payload)
  ) {
    throw new GlassboxSseError("SSE event envelope is missing required fields.", parsed);
  }

  return {
    created_at: parsed.created_at,
    event_id: parsed.event_id,
    event_type: eventType as GlassboxEventType,
    payload: parsed.payload,
    sequence: parsed.sequence,
    session_id: parsed.session_id,
  };
}

export function createSessionEventStream(options: SessionEventStreamOptions) {
  const EventSourceImpl = options.EventSourceImpl ?? resolveEventSource();
  const scheduler = options.scheduler ?? defaultScheduler;
  const reconnectDelayMs = options.reconnectDelayMs ?? 3000;
  const maxReconnectAttempts = options.maxReconnectAttempts ?? 2;

  let eventSource: EventSourceLike | null = null;
  let reconnectTimer: unknown = null;
  let state: SessionStreamState = {
    deliveryMode: "connecting",
    droppedEvents: 0,
    error: null,
    lastSequence: options.afterSequence ?? 0,
    projectionLag: null,
    replayedCount: 0,
    retryCount: 0,
    status: "connecting",
  };

  function snapshot(): SessionStreamState {
    return { ...state };
  }

  function setState(next: Partial<SessionStreamState>): void {
    state = { ...state, ...next };
    options.onStateChange?.(snapshot());
  }

  function clearReconnectTimer(): void {
    if (reconnectTimer !== null) {
      scheduler.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function closeCurrentSource(): void {
    if (eventSource !== null) {
      eventSource.close();
      eventSource = null;
    }
  }

  function connect(reconnecting = false): void {
    clearReconnectTimer();
    closeCurrentSource();
    setState({
      deliveryMode: reconnecting ? state.deliveryMode : "connecting",
      error: reconnecting ? state.error : null,
      status: reconnecting ? "reconnecting" : "connecting",
    });

    const url = buildApiUrl(
      options.baseUrl,
      `/sessions/${encodeURIComponent(options.sessionId)}/events`,
      { after: state.lastSequence },
    );

    eventSource = new EventSourceImpl(url);
    eventSource.onopen = () => {
      setState({ error: null, retryCount: 0, status: "live" });
    };
    eventSource.onmessage = handleMessage;
    eventSource.onerror = () => {
      handleStreamError(new GlassboxSseError("The live event stream disconnected."));
    };

    eventSource.addEventListener(streamStatusEventType, handleStreamStatus);
    for (const eventType of glassboxEventTypes) {
      eventSource.addEventListener(eventType, handleMessage);
    }
  }

  function handleStreamStatus(event: EventSourceMessageEvent): void {
    let status: SseStreamStatus;
    try {
      status = decodeSseStreamStatus(event.data);
    } catch (error) {
      const streamError =
        error instanceof GlassboxSseError
          ? error
          : new GlassboxSseError("The live event stream emitted invalid status.", error);
      options.onError?.(streamError);
      return;
    }

    options.onControl?.(status);
    setState({
      deliveryMode: status.status,
      droppedEvents: status.transport?.dropped_events ?? state.droppedEvents,
      error: status.status === "degraded" ? status.message : null,
      lastSequence: Math.max(state.lastSequence, status.last_delivered_sequence),
      projectionLag: projectionLagFromStatus(status),
      replayedCount: state.replayedCount + status.replayed_count,
    });
  }

  function handleMessage(event: EventSourceMessageEvent): void {
    let envelope: SseEventEnvelope;
    try {
      envelope = decodeSseEventEnvelope(event.data);
    } catch (error) {
      const streamError =
        error instanceof GlassboxSseError
          ? error
          : new GlassboxSseError("The live event stream emitted an invalid event.", error);
      options.onError?.(streamError);
      return;
    }

    if (envelope.sequence <= state.lastSequence) {
      return;
    }

    setState({ lastSequence: envelope.sequence });
    options.onEnvelope?.(envelope);

    if (TERMINAL_EVENT_TYPES.has(envelope.event_type)) {
      closeCurrentSource();
      setState({ deliveryMode: "live", error: null, status: "historical_snapshot" });
    }
  }

  function handleStreamError(error: GlassboxSseError): void {
    closeCurrentSource();
    options.onError?.(error);

    if (state.retryCount >= maxReconnectAttempts) {
      setState({
        deliveryMode: "degraded",
        error:
          "Showing the last persisted snapshot only. The live stream could not be re-established.",
        status: "live_unavailable",
      });
      return;
    }

    setState({
      deliveryMode: "degraded",
      error: "Snapshot still available while the dashboard retries the live stream.",
      retryCount: state.retryCount + 1,
      status: "reconnecting",
    });

    reconnectTimer = scheduler.setTimeout(() => {
      reconnectTimer = null;
      connect(true);
    }, reconnectDelayMs);
  }

  function start(): void {
    connect(false);
  }

  function close(status: SessionStreamStatus = "historical_snapshot"): void {
    clearReconnectTimer();
    closeCurrentSource();
    setState({ error: null, status });
  }

  return {
    close,
    getState: snapshot,
    start,
  };
}

export function decodeSseStreamStatus(data: string): SseStreamStatus {
  let parsed: unknown;
  try {
    parsed = JSON.parse(data) as unknown;
  } catch (error) {
    throw new GlassboxSseError("SSE stream status data was not valid JSON.", error);
  }

  if (!isRecord(parsed)) {
    throw new GlassboxSseError("SSE stream status data was not an object.", parsed);
  }
  if (
    parsed.status !== "replaying_history" &&
    parsed.status !== "live" &&
    parsed.status !== "degraded"
  ) {
    throw new GlassboxSseError("SSE stream status is not recognized.", parsed);
  }
  if (
    typeof parsed.after_sequence !== "number" ||
    typeof parsed.last_delivered_sequence !== "number" ||
    typeof parsed.canonical_last_sequence !== "number" ||
    typeof parsed.replayed_count !== "number" ||
    typeof parsed.history_truncated !== "boolean" ||
    (parsed.message !== null && typeof parsed.message !== "string")
  ) {
    throw new GlassboxSseError("SSE stream status is missing required fields.", parsed);
  }

  return {
    after_sequence: parsed.after_sequence,
    canonical_last_sequence: parsed.canonical_last_sequence,
    history_truncated: parsed.history_truncated,
    last_delivered_sequence: parsed.last_delivered_sequence,
    message: parsed.message,
    projection_health: decodeProjectionHealth(parsed.projection_health),
    replayed_count: parsed.replayed_count,
    status: parsed.status,
    transport: decodeTransportStats(parsed.transport),
  };
}

function decodeProjectionHealth(value: unknown): SseStreamStatus["projection_health"] {
  if (value === null) {
    return null;
  }
  if (!isRecord(value)) {
    throw new GlassboxSseError("SSE stream projection health was not an object.", value);
  }
  if (
    typeof value.state !== "string" ||
    typeof value.lag !== "number" ||
    typeof value.degraded !== "boolean"
  ) {
    throw new GlassboxSseError("SSE stream projection health is missing fields.", value);
  }
  return {
    degraded: value.degraded,
    lag: value.lag,
    state: value.state,
  };
}

function decodeTransportStats(value: unknown): SseStreamStatus["transport"] {
  if (value === null) {
    return null;
  }
  if (!isRecord(value)) {
    throw new GlassboxSseError("SSE stream transport stats were not an object.", value);
  }
  if (
    typeof value.subscriber_count !== "number" ||
    typeof value.dropped_events !== "number" ||
    typeof value.queue_capacity !== "number" ||
    typeof value.max_queue_depth !== "number" ||
    (value.last_published_sequence !== null && typeof value.last_published_sequence !== "number")
  ) {
    throw new GlassboxSseError("SSE stream transport stats are missing fields.", value);
  }
  return {
    dropped_events: value.dropped_events,
    last_published_sequence: value.last_published_sequence,
    max_queue_depth: value.max_queue_depth,
    queue_capacity: value.queue_capacity,
    subscriber_count: value.subscriber_count,
  };
}

function projectionLagFromStatus(status: SseStreamStatus): number | null {
  return status.projection_health?.lag ?? null;
}

function resolveEventSource(): EventSourceConstructor {
  const EventSourceImpl = globalThis.EventSource;
  if (EventSourceImpl === undefined) {
    throw new GlassboxSseError("No EventSource implementation is available.");
  }
  return EventSourceImpl as unknown as EventSourceConstructor;
}

const defaultScheduler: StreamScheduler = {
  clearTimeout: (timeoutId) => globalThis.clearTimeout(timeoutId as ReturnType<typeof setTimeout>),
  setTimeout: (callback, delayMs) => globalThis.setTimeout(callback, delayMs),
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
