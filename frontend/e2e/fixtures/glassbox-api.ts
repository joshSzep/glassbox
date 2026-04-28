import type { Page, Route } from "@playwright/test";

import {
  defaultChildSessionId,
  defaultSessionId,
  makeV4ForkResponse,
  makeV4ScenarioAggregate,
  makeV4ScenarioSnapshot,
  makeV4ScenarioSseEnvelopes,
  v4ConsoleScenarioFixtures,
  type V4ConsoleScenarioId,
  v4FixtureSessionIds,
} from "../../tests/fixtures/session-state";

type ActionRequest = {
  body: unknown;
  method: string;
  url: string;
};

export type GlassboxApiFixtureState = {
  actions: ActionRequest[];
};

export { defaultChildSessionId, defaultSessionId };

export const scenarioFixtures = v4ConsoleScenarioFixtures;

export type ScreenshotScenarioId = V4ConsoleScenarioId;

export async function installGlassboxApiFixture(
  page: Page,
  scenarioId: ScreenshotScenarioId = "live-session",
): Promise<GlassboxApiFixtureState> {
  const state: GlassboxApiFixtureState = { actions: [] };
  const scenario = scenarioFixtures[scenarioId];
  const selectedSessionId = "sessionId" in scenario ? scenario.sessionId : undefined;
  let emittedLiveUpdate = false;

  await page.route("**/healthz", (route) =>
    route.fulfill({
      json: {
        event_transport: {
          degraded: scenarioId === "projection-degraded",
          dropped_events: 0,
          last_published_sequence: null,
          max_queue_depth: selectedSessionId === undefined ? 0 : 1,
          next_actions: [],
          queue_capacity: 64,
          queue_pressure: selectedSessionId === undefined ? 0 : 0.016,
          reconnect_hint: "use the client's last observed sequence as the after cursor",
          reconnect_mode: "resume with /sessions/{session_id}/events?after=SEQUENCE",
          state: scenarioId === "projection-degraded" ? "degraded" : "healthy",
          subscriber_count: selectedSessionId === undefined ? 0 : 1,
        },
        status: "ok",
      },
    }),
  );

  await page.route("**/sessions/aggregate**", (route) => {
    const url = new URL(route.request().url());
    route.fulfill({ json: makeV4ScenarioAggregate(scenarioId, url.searchParams.get("queue")) });
  });

  await page.route("**/sessions/*/events**", (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const isSelectedStream =
      selectedSessionId !== undefined && pathname.endsWith(`/sessions/${selectedSessionId}/events`);
    const envelopes =
      isSelectedStream && !emittedLiveUpdate
        ? makeV4ScenarioSseEnvelopes(scenarioId, selectedSessionId)
        : [];
    const body = envelopes.map(toSseMessage).join("");
    emittedLiveUpdate = emittedLiveUpdate || body.length > 0;

    route.fulfill({
      body,
      headers: {
        "cache-control": "no-cache",
        "content-type": "text/event-stream",
      },
      status: 200,
    });
  });

  for (const sessionId of v4FixtureSessionIds()) {
    await page.route(`**/sessions/${sessionId}`, (route) =>
      route.fulfill({ json: makeV4ScenarioSnapshot(sessionId, scenarioId) }),
    );
    await page.route(`**/sessions/${sessionId}/transcript**`, (route) => {
      const snapshot = makeV4ScenarioSnapshot(sessionId, scenarioId);
      route.fulfill({
        json: {
          items: snapshot.transcript,
          page: makeFixturePage(snapshot.transcript.length),
          session_id: sessionId,
        },
      });
    });
    await page.route(`**/sessions/${sessionId}/event-log**`, (route) => {
      route.fulfill({
        json: {
          items: makeFixtureEventLog(sessionId, scenarioId),
          page: makeFixturePage(3),
          session_id: sessionId,
        },
      });
    });
    await page.route(`**/sessions/${sessionId}/turn-metrics**`, (route) => {
      const snapshot = makeV4ScenarioSnapshot(sessionId, scenarioId);
      route.fulfill({
        json: {
          items: snapshot.turn_metrics,
          page: makeFixturePage(snapshot.turn_metrics.length),
          session_id: sessionId,
        },
      });
    });
  }

  await page.route("**/sessions/*/messages", (route) => recordAction(route, state));
  await page.route("**/sessions/*/questions/*", (route) => recordAction(route, state));
  await page.route("**/sessions/*/approvals/*", (route) => recordAction(route, state));
  await page.route("**/sessions/*/fork", (route) =>
    recordAction(route, state, makeV4ForkResponse()),
  );

  return state;
}

function makeFixturePage(returnedCount: number) {
  return {
    cursor: 0,
    has_more: false,
    limit: 80,
    next_cursor: null,
    returned_count: returnedCount,
  };
}

function makeFixtureEventLog(sessionId: string, scenarioId: ScreenshotScenarioId) {
  return makeV4ScenarioSseEnvelopes(scenarioId, sessionId).map((event) => ({
    created_at: "2026-04-23T00:00:00Z",
    event_id: `event-${event.sequence}`,
    event_type: event.event_type,
    event_version: 1,
    payload: event.payload,
    sequence: event.sequence,
    session_id: sessionId,
  }));
}

export function scenarioRoute(scenarioId: ScreenshotScenarioId): string {
  return scenarioFixtures[scenarioId].route;
}

async function recordAction(
  route: Route,
  state: GlassboxApiFixtureState,
  response: unknown = { status: "ok" },
) {
  state.actions.push({
    body: route.request().postDataJSON(),
    method: route.request().method(),
    url: new URL(route.request().url()).pathname,
  });
  await route.fulfill({ json: response });
}

function toSseMessage(envelope: Record<string, unknown>): string {
  return `event: ${String(envelope.event_type)}\ndata: ${JSON.stringify(envelope)}\n\n`;
}
