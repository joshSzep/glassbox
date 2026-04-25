import test from "node:test";
import assert from "node:assert/strict";

import { createDashboardApp } from "../../src/glassbox/web/static/dashboard.js";
import {
  makeSessionAggregate,
  makeHistoricalSnapshot,
  makeSessionSnapshot as makeSnapshot,
  makeSessionSummary as makeSummary,
} from "./dashboard_test_fixtures.js";

function makeElement(id) {
  return {
    id,
    innerHTML: "",
    textContent: "",
    className: "",
    dataset: {},
    scrollHeight: 0,
    scrollTop: 0,
    querySelectorAll() {
      return [];
    },
    addEventListener() {},
    classList: {
      values: new Set(),
      toggle(name, enabled) {
        if (enabled) {
          this.values.add(name);
        } else {
          this.values.delete(name);
        }
      },
      contains(name) {
        return this.values.has(name);
      },
    },
  };
}

function createHarness({ search = "", responses }) {
  const ids = [
    "status-badge",
    "transcript-list",
    "turn-status",
    "metrics-list",
    "tool-calls-list",
    "live-output-list",
    "approvals-list",
    "composer-pane-body",
    "event-log-list",
    "session-browser-list",
    "session-id-display",
    "sse-indicator",
    "primary-pane-title",
  ];
  const elements = new Map(ids.map(id => [id, makeElement(id)]));
  const detailPaneIds = ["pane-composer", "pane-turn", "pane-metrics", "pane-tools", "pane-output", "pane-approvals", "pane-events"];
  const detailPanes = detailPaneIds.map(id => makeElement(id));
  const paneComposer = detailPanes[0];

  const documentImpl = {
    title: "Glassbox Dashboard",
    getElementById(id) {
      return elements.get(id) ?? null;
    },
    querySelectorAll(selector) {
      if (selector === ".session-detail-pane, #pane-composer") {
        return [paneComposer, ...detailPanes.slice(1)];
      }
      return [];
    },
    addEventListener() {},
  };

  const location = {
    pathname: "/",
    search,
  };
  const history = {
    pushState(_state, _title, url) {
      const [, query = ""] = String(url).split("?");
      location.search = query ? `?${query}` : "";
    },
    replaceState(_state, _title, url) {
      const [, query = ""] = String(url).split("?");
      location.search = query ? `?${query}` : "";
    },
  };
  const windowImpl = {
    location,
    history,
    timeouts: [],
    setTimeout(callback) {
      this.timeouts.push(callback);
    },
    addEventListener() {},
  };

  const fetchCalls = [];
  async function fetchImpl(url) {
    fetchCalls.push(url);
    assert.ok(url in responses, `unexpected fetch: ${url}`);
    if (Array.isArray(responses[url])) {
      const next = responses[url].shift();
      assert.ok(next, `no remaining responses for ${url}`);
      return next;
    }
    if (typeof responses[url] === "function") {
      return responses[url](url);
    }
    return responses[url];
  }

  const eventSources = [];
  class EventSourceImpl {
    constructor(url) {
      this.url = url;
      this.listeners = new Map();
      eventSources.push(this);
    }

    addEventListener(name, handler) {
      this.listeners.set(name, handler);
    }

    close() {
      this.closed = true;
    }

    emitOpen() {
      this.onopen?.();
    }

    emitError() {
      this.onerror?.();
    }
  }

  return {
    app: createDashboardApp({
      windowImpl,
      documentImpl,
      fetchImpl,
      EventSourceImpl,
    }),
    elements,
    fetchCalls,
    windowImpl,
    eventSources,
    detailPanes,
    flushTimeout() {
      const callback = windowImpl.timeouts.shift();
      if (callback) {
        callback();
      }
    },
  };
}

function okJson(payload) {
  return {
    ok: true,
    status: 200,
    async json() {
      return payload;
    },
  };
}

test("dashboard app init loads landing page and recent sessions at root", async () => {
  const harness = createHarness({
    responses: {
      "/sessions/aggregate": okJson(makeSessionAggregate([makeSummary("session-123")])),
    },
  });

  await harness.app.init();

  assert.deepEqual(harness.fetchCalls, ["/sessions/aggregate"]);
  assert.equal(harness.elements.get("primary-pane-title").textContent, "Operator Console");
  assert.match(harness.elements.get("transcript-list").innerHTML, /What needs attention now/);
  assert.match(harness.elements.get("session-browser-list").innerHTML, /session-1/);
  assert.equal(harness.elements.get("status-badge").textContent, "no session");
  assert.equal(harness.elements.get("sse-indicator").textContent, "○ index mode");
  assert.equal(harness.app.getState().sessionIndex.length, 1);
  assert.ok(harness.detailPanes.every(pane => pane.classList.contains("session-hidden")));
});

test("dashboard app openSession selects a recent session and updates the URL", async () => {
  const harness = createHarness({
    responses: {
      "/sessions/aggregate": okJson(makeSessionAggregate([makeSummary("session-123")])),
      "/sessions/session-123": okJson(makeSnapshot("session-123")),
    },
  });

  await harness.app.init();
  await harness.app.openSession("session-123");

  assert.deepEqual(harness.fetchCalls, ["/sessions/aggregate", "/sessions/session-123"]);
  assert.equal(harness.windowImpl.location.search, "?session=session-123");
  assert.equal(harness.elements.get("primary-pane-title").textContent, "Transcript");
  assert.match(
    harness.elements.get("transcript-list").innerHTML,
    /Selected session/,
  );
  assert.match(
    harness.elements.get("transcript-list").innerHTML,
    /Send the next prompt/,
  );
  assert.match(harness.elements.get("transcript-list").innerHTML, /Inspect the repository/);
  assert.equal(harness.app.getState().sessionId, "session-123");
  assert.equal(harness.eventSources.length, 1);
});

test("dashboard app preserves deep-link navigation on init", async () => {
  const harness = createHarness({
    search: "?session=session-456",
    responses: {
      "/sessions/aggregate": okJson(makeSessionAggregate([makeSummary("session-456")])),
      "/sessions/session-456": okJson(makeSnapshot("session-456")),
    },
  });

  await harness.app.init();

  assert.deepEqual(harness.fetchCalls, ["/sessions/aggregate", "/sessions/session-456"]);
  assert.equal(harness.app.getState().selectedSessionId, "session-456");
  assert.equal(harness.app.getState().sessionId, "session-456");
  assert.equal(harness.windowImpl.location.search, "?session=session-456");
  assert.equal(harness.elements.get("primary-pane-title").textContent, "Transcript");
});

test("dashboard app retries a disconnected live stream before marking it unavailable", async () => {
  const harness = createHarness({
    responses: {
      "/sessions/aggregate": okJson(makeSessionAggregate([makeSummary("session-123")])),
      "/sessions/session-123": okJson(makeSnapshot("session-123")),
    },
  });

  await harness.app.init();
  await harness.app.openSession("session-123");

  harness.eventSources[0].emitOpen();
  assert.equal(harness.elements.get("sse-indicator").textContent, "● live");

  harness.eventSources[0].emitError();
  assert.equal(harness.elements.get("sse-indicator").textContent, "○ reconnecting");

  harness.flushTimeout();
  assert.equal(harness.eventSources.length, 2);

  harness.eventSources[1].emitError();
  harness.flushTimeout();
  assert.equal(harness.eventSources.length, 3);

  harness.eventSources[2].emitError();
  assert.equal(harness.elements.get("sse-indicator").textContent, "✕ live unavailable");
  assert.match(
    harness.elements.get("transcript-list").innerHTML,
    /persisted snapshot only/,
  );
});

test("dashboard app treats completed sessions as historical snapshots", async () => {
  const harness = createHarness({
    responses: {
      "/sessions/aggregate": okJson(makeSessionAggregate([
        makeSummary("session-789", {
          status: "completed",
          next_action_summary: "Inspect completed session",
        }),
      ])),
      "/sessions/session-789": okJson(makeHistoricalSnapshot("session-789")),
    },
  });

  await harness.app.init();
  await harness.app.openSession("session-789");

  assert.equal(harness.eventSources.length, 0);
  assert.equal(harness.elements.get("sse-indicator").textContent, "◌ historical snapshot");
  assert.match(
    harness.elements.get("transcript-list").innerHTML,
    /Historical snapshot/,
  );
});

test("dashboard app clears stale deep links back to the session index", async () => {
  const harness = createHarness({
    search: "?session=missing-session",
    responses: {
      "/sessions/aggregate": okJson(makeSessionAggregate([makeSummary("session-123")])),
      "/sessions/missing-session": {
        ok: false,
        status: 404,
        async json() {
          return { detail: "not found" };
        },
      },
    },
  });

  await harness.app.init();

  assert.equal(harness.windowImpl.location.search, "");
  assert.equal(harness.app.getState().sessionLoadState, "failed");
  assert.equal(harness.elements.get("sse-indicator").textContent, "○ index mode");
  assert.match(harness.elements.get("transcript-list").innerHTML, /Session unavailable/);
  assert.match(harness.elements.get("transcript-list").innerHTML, /recovered to the session index/);
});

test("dashboard app creates a fork and opens the child session", async () => {
  const harness = createHarness({
    responses: {
      "/sessions/aggregate": [
        okJson(makeSessionAggregate([makeSummary("session-parent")], {
          queue_counts: {
            total: 1,
            approvals: 0,
            questions: 0,
            failures: 0,
            degraded: 0,
            active: 1,
            action_needed: 0,
            historical: 0,
          },
        })),
        okJson(makeSessionAggregate([
          makeSummary("session-child", {
            parent_session_id: "session-parent",
            forked_from_turn_id: "turn-2",
            forked_from_sequence: 8,
            branch_label: "alt-path",
          }),
          makeSummary("session-parent", {
            can_fork: true,
            latest_fork_point_turn_id: "turn-2",
            latest_fork_point_sequence: 8,
          }),
        ])),
      ],
      "/sessions/session-parent": okJson({
        ...makeHistoricalSnapshot("session-parent"),
        can_fork: true,
        latest_fork_point_turn_id: "turn-2",
        latest_fork_point_sequence: 8,
        branchable_turns: [
          {
            turn_id: "turn-2",
            sequence: 8,
            created_at: "2026-04-23T00:00:02Z",
            label: "Inspect the repository",
          },
        ],
      }),
      "/sessions/session-parent/fork": okJson({
        child_session_id: "session-child",
        parent_session_id: "session-parent",
        forked_from_turn_id: "turn-2",
        forked_from_sequence: 8,
        branch_label: "alt-path",
        inherited_message_count: 2,
        last_sequence: 3,
      }),
      "/sessions/session-child": okJson({
        ...makeSnapshot("session-child"),
        status: "completed",
        parent_session_id: "session-parent",
        forked_from_turn_id: "turn-2",
        forked_from_sequence: 8,
        branch_label: "alt-path",
      }),
    },
  });

  await harness.app.init();
  await harness.app.openSession("session-parent");
  const result = await harness.app.forkCurrentSession({
    turnId: "turn-2",
    branchLabel: "alt-path",
  });

  assert.deepEqual(result, {
    ok: true,
    data: {
      child_session_id: "session-child",
      parent_session_id: "session-parent",
      forked_from_turn_id: "turn-2",
      forked_from_sequence: 8,
      branch_label: "alt-path",
      inherited_message_count: 2,
      last_sequence: 3,
    },
  });
  assert.deepEqual(harness.fetchCalls, [
    "/sessions/aggregate",
    "/sessions/session-parent",
    "/sessions/session-parent/fork",
    "/sessions/aggregate",
    "/sessions/session-child",
  ]);
  assert.equal(harness.windowImpl.location.search, "?session=session-child");
  assert.equal(harness.app.getState().sessionId, "session-child");
  assert.equal(harness.app.getState().parentSessionId, "session-parent");
  assert.equal(harness.app.getState().branchLabel, "alt-path");
});

test("dashboard app queue selection updates the URL and reloads aggregate data", async () => {
  const harness = createHarness({
    responses: {
      "/sessions/aggregate": okJson(makeSessionAggregate([makeSummary("session-123")])),
      "/sessions/aggregate?queue=approvals": okJson(makeSessionAggregate([
        makeSummary("session-approval", {
          status: "awaiting_approval",
          pending_approval_id: "approval-1",
          next_action_summary: "Resolve pending approval",
          queue_memberships: ["approvals", "active", "action-needed"],
          priority_bucket: "approvals",
        }),
      ], {
        queue: "approvals",
        queue_counts: {
          total: 1,
          approvals: 1,
          questions: 0,
          failures: 0,
          degraded: 0,
          active: 1,
          action_needed: 1,
          historical: 0,
        },
      })),
    },
  });

  await harness.app.init();
  await harness.app.selectQueue("approvals");

  assert.deepEqual(harness.fetchCalls, [
    "/sessions/aggregate",
    "/sessions/aggregate?queue=approvals",
  ]);
  assert.equal(harness.windowImpl.location.search, "?queue=approvals");
  assert.equal(harness.app.getState().selectedQueue, "approvals");
  assert.match(harness.elements.get("session-browser-list").innerHTML, /Approvals/);
  assert.match(harness.elements.get("session-browser-list").innerHTML, /Resolve pending approval/);
});
