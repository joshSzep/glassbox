import { describe, expect, it } from "vitest";

import {
  buildAppRoute,
  createDefaultAppRoute,
  openLineageTargetRoute,
  parseAppRoute,
  recoverInvalidSessionRoute,
  selectQueueRoute,
  selectSessionRoute,
  setCompareRoute,
  setInspectorTabRoute,
  type AppRouteState,
} from "../routing/app-route";

describe("app route parsing", () => {
  it("parses the default /app route", () => {
    expect(parseAppRoute("/app")).toEqual(createDefaultAppRoute());
  });

  it("parses migration-compatible ?session deep links", () => {
    expect(parseAppRoute("/app?session=session-1&queue=approvals")).toEqual({
      compareSessionId: null,
      queue: "approvals",
      selectedSessionId: "session-1",
      tab: "overview",
    });
  });

  it("parses canonical session, compare, and inspector links", () => {
    expect(parseAppRoute("/app/sessions/session%2F1?compare=parent-1&tab=evidence")).toEqual({
      compareSessionId: "parent-1",
      queue: "all",
      selectedSessionId: "session/1",
      tab: "evidence",
    });
  });

  it("parses queue links and ignores invalid URL state", () => {
    expect(parseAppRoute("/app/queues/questions?session=&tab=not-real")).toEqual({
      compareSessionId: null,
      queue: "questions",
      selectedSessionId: null,
      tab: "overview",
    });
    expect(parseAppRoute("/app/queues/not-real")).toEqual(createDefaultAppRoute());
  });
});

describe("app route building", () => {
  it("round trips queue and selected-session route state", () => {
    const route: AppRouteState = {
      compareSessionId: null,
      queue: "failures",
      selectedSessionId: "session-1",
      tab: "timeline",
    };

    expect(buildAppRoute(route)).toBe("/app/sessions/session-1?queue=failures&tab=timeline");
    expect(parseAppRoute(buildAppRoute(route))).toEqual(route);
  });

  it("round trips compare links and supports a future root flip", () => {
    const route: AppRouteState = {
      compareSessionId: "child-1",
      queue: "all",
      selectedSessionId: "session/1",
      tab: "compare",
    };

    expect(buildAppRoute(route, { basePath: "/" })).toBe(
      "/sessions/session%2F1?compare=child-1&tab=compare",
    );
    expect(parseAppRoute(buildAppRoute(route, { basePath: "/" }), { basePath: "/" })).toEqual(
      route,
    );
  });

  it("omits large or default UI state from queue-only routes", () => {
    expect(
      buildAppRoute({
        compareSessionId: null,
        queue: "approvals",
        selectedSessionId: null,
        tab: "overview",
      }),
    ).toBe("/app/queues/approvals");
  });
});

describe("app navigation helpers", () => {
  it("selects queues, sessions, lineage targets, compare targets, and tabs", () => {
    const route = createDefaultAppRoute();
    const queued = selectQueueRoute(route, "active");
    const selected = selectSessionRoute(queued, "session-1");
    const compared = setCompareRoute(selected, "parent-1");
    const tabbed = setInspectorTabRoute(compared, "lineage");
    const lineage = openLineageTargetRoute(tabbed, "child-1");

    expect(queued).toMatchObject({ queue: "active", selectedSessionId: null });
    expect(selected).toMatchObject({ queue: "active", selectedSessionId: "session-1" });
    expect(compared).toMatchObject({ compareSessionId: "parent-1", tab: "compare" });
    expect(tabbed).toMatchObject({ compareSessionId: "parent-1", tab: "lineage" });
    expect(lineage).toMatchObject({
      compareSessionId: null,
      queue: "active",
      selectedSessionId: "child-1",
      tab: "overview",
    });
  });

  it("recovers invalid sessions back to the current queue", () => {
    const route = parseAppRoute(
      "/app/sessions/missing?queue=degraded&compare=parent-1&tab=compare",
    );

    expect(recoverInvalidSessionRoute(route)).toEqual({
      compareSessionId: null,
      queue: "degraded",
      selectedSessionId: null,
      tab: "overview",
    });
    expect(buildAppRoute(recoverInvalidSessionRoute(route))).toBe("/app/queues/degraded");
  });
});
