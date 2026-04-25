export function createDashboardTransport({
  fetchImpl,
  EventSourceImpl,
}) {
  async function fetchSessionAggregate({ queue = "all", sort = "priority" } = {}) {
    const params = new URLSearchParams();
    if (queue && queue !== "all") {
      params.set("queue", queue);
    }
    if (sort && sort !== "priority") {
      params.set("sort", sort);
    }
    const query = params.toString();
    const response = await fetchImpl(query ? `/sessions/aggregate?${query}` : "/sessions/aggregate");
    return response;
  }

  async function fetchSessionSnapshot(sessionId) {
    const response = await fetchImpl(`/sessions/${sessionId}`);
    return response;
  }

  function openSessionEventStream(
    sessionId,
    afterSequence,
    { onOpen, onEnvelope, onError },
  ) {
    const url = `/sessions/${sessionId}/events?after=${afterSequence}`;
    const eventSource = new EventSourceImpl(url);

    function handleFrame(evt) {
      try {
        onEnvelope(JSON.parse(evt.data));
      } catch {
        // ignore parse errors
      }
    }

    eventSource.onopen = onOpen;
    eventSource.onmessage = handleFrame;
    [
      "SessionStarted", "SessionResumed", "SessionCompleted", "SessionFailed",
      "UserMessageReceived", "AssistantMessageCompleted",
      "ApprovalRequested", "ApprovalResolved",
      "UserQuestionAsked", "UserAnswerProvided",
      "TurnStarted", "TurnStatusChanged", "TurnCompleted", "TurnFailed",
      "ToolExecutionStarted", "ToolExecutionCompleted",
      "ToolOutputChunk",
      "ModelCallStarted", "ModelCallCompleted",
    ].forEach(name => eventSource.addEventListener(name, handleFrame));
    eventSource.onerror = onError;

    return eventSource;
  }

  return {
    fetchSessionAggregate,
    fetchSessionSnapshot,
    openSessionEventStream,
  };
}
