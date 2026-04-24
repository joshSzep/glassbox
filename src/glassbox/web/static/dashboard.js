/**
 * Glassbox dashboard — browser entry point.
 *
 * Handles DOM manipulation, session index loading, snapshot loading, SSE
 * subscription, and approval actions. All state logic lives in ./state.js.
 *
 * On load:
 *   1. Fetch the recent-session index from GET /sessions.
 *   2. Read ?session=<uuid> from the query string, if present.
 *   3. Fetch the selected snapshot from GET /sessions/<id>.
 *   4. Hydrate the state model from the snapshot.
 *   5. Render the full UI.
 *   6. Open an SSE connection to GET /sessions/<id>/events?after=<last_seq>
 *      and apply incremental updates via the reducer.
 */

import {
} from "./state.js";
import { createDashboardController } from "./dashboard-controller.js";
import { createDashboardDomBindings } from "./dashboard-dom.js";
import { createDashboardTransport } from "./dashboard-transport.js";

export function createDashboardApp({
  windowImpl = window,
  documentImpl = document,
  fetchImpl = fetch,
  EventSourceImpl = EventSource,
} = {}) {
  const transport = createDashboardTransport({ fetchImpl, EventSourceImpl });
  let controller = null;
  const domBindings = createDashboardDomBindings({
    documentImpl,
    onOpenSession: (sessionId) => controller.openSession(sessionId),
    onResolveApproval: (approvalId, decision) => controller.handleResolveApproval(approvalId, decision),
    onSelectForkTurn: (turnId) => controller.handleSelectForkTurn(turnId),
    onSubmitComposer: (mode, value) => controller.handleSubmitComposer(mode, value),
    onForkSession: (params) => controller.forkCurrentSession(params),
  });
  controller = createDashboardController({
    windowImpl,
    fetchImpl,
    transport,
    domBindings,
  });

  return {
    init: () => controller.init(),
    openSession: (sessionId, options) => controller.openSession(sessionId, options),
    forkCurrentSession: (params) => controller.forkCurrentSession(params),
    syncFromLocation: (options) => controller.syncFromLocation(options),
    getState: () => controller.getState(),
    destroy: () => controller.destroy(),
  };
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    const app = createDashboardApp();
    void app.init();
    window.addEventListener("popstate", () => {
      void app.syncFromLocation({ replaceHistory: false });
    });
  });
}
