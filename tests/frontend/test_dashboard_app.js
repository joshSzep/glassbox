import test from "node:test";
import assert from "node:assert/strict";

import { createDashboardApp } from "../../src/glassbox/web/static/dashboard.js";

function makeSummary(sessionId, overrides = {}) {
  return {
    session_id: sessionId,
    status: "running",
    model_name: "openai:gpt-5.4",
    cwd: `/tmp/${sessionId}`,
    approval_mode: "confirm",
    dashboard_url: null,
    created_at: "2026-04-23T00:00:00Z",
    updated_at: "2026-04-23T00:00:01Z",
    last_sequence: 4,
    pending_approval_id: null,
    pending_question_id: null,
    pending_question_text: null,
    session_failure_message: null,
    session_failure_retryable: null,
    latest_message_summary: "user: Inspect the repository",
    next_action_summary: "Send the next prompt",
    ...overrides,
  };
}

function makeSnapshot(sessionId) {
  return {
    session_id: sessionId,
    status: "running",
    current_turn_id: null,
    model_name: "openai:gpt-5.4",
    cwd: `/tmp/${sessionId}`,
    approval_mode: "confirm",
    dashboard_url: null,
    last_sequence: 4,
    pending_approval_id: null,
    pending_question_id: null,
    pending_question_text: null,
    session_failure_message: null,
    session_failure_retryable: null,
    transcript: [
      {
        message_id: "message-1",
        role: "user",
        parts: [{ kind: "text", text: "Inspect the repository" }],
      },
    ],
    active_tool_calls: [],
    pending_approvals: [],
    turn_metrics: [],
  };
}

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
    setTimeout() {},
    addEventListener() {},
  };

  const fetchCalls = [];
  async function fetchImpl(url) {
    fetchCalls.push(url);
    assert.ok(url in responses, `unexpected fetch: ${url}`);
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
      "/sessions": okJson([makeSummary("session-123")]),
    },
  });

  await harness.app.init();

  assert.deepEqual(harness.fetchCalls, ["/sessions"]);
  assert.equal(harness.elements.get("primary-pane-title").textContent, "Session Browser");
  assert.match(harness.elements.get("transcript-list").innerHTML, /Choose a recent session/);
  assert.match(harness.elements.get("session-browser-list").innerHTML, /session-1/);
  assert.equal(harness.elements.get("status-badge").textContent, "no session");
  assert.equal(harness.elements.get("sse-indicator").textContent, "○ index mode");
  assert.equal(harness.app.getState().sessionIndex.length, 1);
  assert.ok(harness.detailPanes.every(pane => pane.classList.contains("session-hidden")));
});

test("dashboard app openSession selects a recent session and updates the URL", async () => {
  const harness = createHarness({
    responses: {
      "/sessions": okJson([makeSummary("session-123")]),
      "/sessions/session-123": okJson(makeSnapshot("session-123")),
    },
  });

  await harness.app.init();
  await harness.app.openSession("session-123");

  assert.deepEqual(harness.fetchCalls, ["/sessions", "/sessions/session-123"]);
  assert.equal(harness.windowImpl.location.search, "?session=session-123");
  assert.equal(harness.elements.get("primary-pane-title").textContent, "Transcript");
  assert.match(harness.elements.get("transcript-list").innerHTML, /Inspect the repository/);
  assert.equal(harness.app.getState().sessionId, "session-123");
  assert.equal(harness.eventSources.length, 1);
});

test("dashboard app preserves deep-link navigation on init", async () => {
  const harness = createHarness({
    search: "?session=session-456",
    responses: {
      "/sessions": okJson([makeSummary("session-456")]),
      "/sessions/session-456": okJson(makeSnapshot("session-456")),
    },
  });

  await harness.app.init();

  assert.deepEqual(harness.fetchCalls, ["/sessions", "/sessions/session-456"]);
  assert.equal(harness.app.getState().selectedSessionId, "session-456");
  assert.equal(harness.app.getState().sessionId, "session-456");
  assert.equal(harness.windowImpl.location.search, "?session=session-456");
  assert.equal(harness.elements.get("primary-pane-title").textContent, "Transcript");
});
