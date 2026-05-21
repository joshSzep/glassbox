import { describe, expect, it } from "vitest";

import {
  buildAppRoute,
  createDefaultAppRoute,
  openLineageTargetRoute,
  parseAppRoute,
  recoverInvalidSessionRoute,
  selectChangesetRoute,
  selectChangesetSurfaceRoute,
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
      selectedChangesetId: null,
      selectedSessionId: "session-1",
      selectedTaskId: null,
      surface: "sessions",
      tab: "overview",
      taskQueue: "active",
    });
  });

  it("parses canonical session, compare, and inspector links", () => {
    expect(parseAppRoute("/app/sessions/session%2F1?compare=parent-1&tab=evidence")).toEqual({
      compareSessionId: "parent-1",
      queue: "all",
      selectedChangesetId: null,
      selectedSessionId: "session/1",
      selectedTaskId: null,
      surface: "sessions",
      tab: "evidence",
      taskQueue: "active",
    });
  });

  it("parses queue links and ignores invalid URL state", () => {
    expect(parseAppRoute("/app/queues/questions?session=&tab=not-real")).toEqual({
      compareSessionId: null,
      queue: "questions",
      selectedChangesetId: null,
      selectedSessionId: null,
      selectedTaskId: null,
      surface: "sessions",
      tab: "overview",
      taskQueue: "active",
    });
    expect(parseAppRoute("/app/queues/not-real")).toEqual(createDefaultAppRoute());
  });

  it("parses task queue and selected task links", () => {
    expect(parseAppRoute("/app/tasks?taskQueue=blocked")).toMatchObject({
      selectedTaskId: null,
      surface: "tasks",
      taskQueue: "blocked",
    });
    expect(parseAppRoute("/app/tasks/task%2F1?taskQueue=failed")).toMatchObject({
      selectedTaskId: "task/1",
      surface: "tasks",
      taskQueue: "failed",
    });
  });

  it("parses changeset list and selected changeset links", () => {
    expect(parseAppRoute("/app/changesets")).toMatchObject({
      selectedChangesetId: null,
      surface: "changesets",
    });
    expect(parseAppRoute("/app/changesets/change%2F1")).toMatchObject({
      selectedChangesetId: "change/1",
      surface: "changesets",
    });
  });

  it("parses the local handoff cockpit route", () => {
    expect(parseAppRoute("/app/handoffs")).toMatchObject({
      selectedSessionId: null,
      surface: "handoffs",
    });
  });
});

describe("app route building", () => {
  it("round trips queue and selected-session route state", () => {
    const route: AppRouteState = {
      compareSessionId: null,
      queue: "failures",
      selectedChangesetId: null,
      selectedSessionId: "session-1",
      selectedTaskId: null,
      surface: "sessions",
      tab: "timeline",
      taskQueue: "active",
    };

    expect(buildAppRoute(route)).toBe("/app/sessions/session-1?queue=failures&tab=timeline");
    expect(parseAppRoute(buildAppRoute(route))).toEqual(route);
  });

  it("round trips compare links and supports a future root flip", () => {
    const route: AppRouteState = {
      compareSessionId: "child-1",
      queue: "all",
      selectedChangesetId: null,
      selectedSessionId: "session/1",
      selectedTaskId: null,
      surface: "sessions",
      tab: "compare",
      taskQueue: "active",
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
        selectedChangesetId: null,
        selectedSessionId: null,
        tab: "overview",
      }),
    ).toBe("/app/queues/approvals");
    expect(
      buildAppRoute({
        compareSessionId: null,
        queue: "all",
        selectedChangesetId: null,
        selectedSessionId: null,
        selectedTaskId: "task/1",
        surface: "tasks",
        tab: "overview",
        taskQueue: "blocked",
      }),
    ).toBe("/app/tasks/task%2F1?taskQueue=blocked");
    expect(
      buildAppRoute({
        compareSessionId: null,
        queue: "all",
        selectedChangesetId: "change/1",
        selectedSessionId: null,
        surface: "changesets",
        tab: "overview",
      }),
    ).toBe("/app/changesets/change%2F1");
    expect(
      buildAppRoute({
        compareSessionId: null,
        queue: "all",
        selectedSessionId: null,
        surface: "handoffs",
        tab: "overview",
      }),
    ).toBe("/app/handoffs");
  });
});

describe("app navigation helpers", () => {
  it("selects queues, sessions, changesets, lineage targets, compare targets, and tabs", () => {
    const route = createDefaultAppRoute();
    const queued = selectQueueRoute(route, "active");
    const selected = selectSessionRoute(queued, "session-1");
    const compared = setCompareRoute(selected, "parent-1");
    const tabbed = setInspectorTabRoute(compared, "lineage");
    const lineage = openLineageTargetRoute(tabbed, "child-1");
    const changesetList = selectChangesetSurfaceRoute(lineage);
    const changeset = selectChangesetRoute(changesetList, "change-1");

    expect(queued).toMatchObject({ queue: "active", selectedSessionId: null });
    expect(selected).toMatchObject({ queue: "active", selectedSessionId: "session-1" });
    expect(compared).toMatchObject({ compareSessionId: "parent-1", tab: "compare" });
    expect(tabbed).toMatchObject({ compareSessionId: "parent-1", tab: "lineage" });
    expect(lineage).toMatchObject({
      compareSessionId: null,
      queue: "active",
      selectedChangesetId: null,
      selectedSessionId: "child-1",
      tab: "overview",
    });
    expect(changesetList).toMatchObject({
      selectedChangesetId: null,
      selectedSessionId: null,
      surface: "changesets",
    });
    expect(changeset).toMatchObject({
      selectedChangesetId: "change-1",
      selectedSessionId: null,
      surface: "changesets",
    });
  });

  it("recovers invalid sessions back to the current queue", () => {
    const route = parseAppRoute(
      "/app/sessions/missing?queue=degraded&compare=parent-1&tab=compare",
    );

    expect(recoverInvalidSessionRoute(route)).toEqual({
      compareSessionId: null,
      queue: "degraded",
      selectedChangesetId: null,
      selectedSessionId: null,
      selectedTaskId: null,
      surface: "sessions",
      tab: "overview",
      taskQueue: "active",
    });
    expect(buildAppRoute(recoverInvalidSessionRoute(route))).toBe("/app/queues/degraded");
  });
});
