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

export type SessionStreamStatus =
  | "connecting"
  | "historical_snapshot"
  | "live"
  | "live_unavailable"
  | "reconnecting";

export type SessionStreamState = {
  error: string | null;
  lastSequence: number;
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
  onEnvelope?: (envelope: SseEventEnvelope) => void;
  onError?: (error: GlassboxSseError) => void;
  onStateChange?: (state: SessionStreamState) => void;
  reconnectDelayMs?: number;
  scheduler?: StreamScheduler;
  sessionId: string;
};

const TERMINAL_EVENT_TYPES = new Set<GlassboxEventType>(["SessionCompleted", "SessionFailed"]);

const eventTypeSet = new Set<string>(glassboxEventTypes);

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
    error: null,
    lastSequence: options.afterSequence ?? 0,
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

    for (const eventType of glassboxEventTypes) {
      eventSource.addEventListener(eventType, handleMessage);
    }
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
      setState({ error: null, status: "historical_snapshot" });
    }
  }

  function handleStreamError(error: GlassboxSseError): void {
    closeCurrentSource();
    options.onError?.(error);

    if (state.retryCount >= maxReconnectAttempts) {
      setState({
        error:
          "Showing the last persisted snapshot only. The live stream could not be re-established.",
        status: "live_unavailable",
      });
      return;
    }

    setState({
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
