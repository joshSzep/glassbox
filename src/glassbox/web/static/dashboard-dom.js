import { renderApprovalsPane, renderDashboardPanes } from "./render.js";

function indicatorPresentation(state) {
  if (state.streamState === "loading") {
    return { text: "○ loading", className: "" };
  }

  if (state.streamState === "connecting") {
    return { text: "○ connecting", className: "" };
  }

  if (state.streamState === "live") {
    return { text: "● live", className: "connected" };
  }

  if (state.streamState === "reconnecting") {
    return { text: "○ reconnecting", className: "warning" };
  }

  if (state.streamState === "unavailable") {
    return { text: "✕ live unavailable", className: "error" };
  }

  if (state.streamState === "historical") {
    return { text: "◌ historical snapshot", className: "historical" };
  }

  if (state.streamState === "index") {
    return { text: "○ index mode", className: "" };
  }

  return { text: "○ waiting", className: "" };
}

export function createDashboardDomBindings({
  documentImpl,
  onOpenSession,
  onCompareSession,
  onClearCompareSession,
  onSelectQueue,
  onResolveApproval,
  onSelectForkTurn,
  onSubmitComposer,
  onForkSession,
}) {
  const drafts = {
    message: "",
    answer: "",
    forkBranchLabel: "",
  };

  function byId(id) {
    return documentImpl.getElementById(id);
  }

  function hasActiveSession(state) {
    return Boolean(state.sessionId);
  }

  function resetDrafts() {
    drafts.message = "";
    drafts.answer = "";
    drafts.forkBranchLabel = "";
  }

  function renderIndicator(state) {
    const indicator = byId("sse-indicator");
    const presentation = indicatorPresentation(state);
    indicator.textContent = presentation.text;
    indicator.className = presentation.className;
  }

  function renderStatus(state) {
    const badge = byId("status-badge");
    if (!hasActiveSession(state)) {
      badge.textContent = state.sessionLoadState === "failed"
        ? "unavailable"
        : "no session";
      badge.className = state.sessionLoadState === "failed" ? "failed" : "idle";
      return;
    }

    badge.textContent = state.status;
    badge.className = state.status;
  }

  function renderHeader(state) {
    const sessionDisplay = byId("session-id-display");
    if (hasActiveSession(state)) {
      sessionDisplay.textContent = state.sessionId.slice(0, 8) + "\u2026";
      documentImpl.title = `Glassbox – ${state.sessionId.slice(0, 8)}`;
      return;
    }

    sessionDisplay.textContent = state.selectedSessionId
      ? `${state.selectedSessionId.slice(0, 8)} pending`
      : "standalone dashboard";
    documentImpl.title = "Glassbox Dashboard";
  }

  function renderPrimaryPane(state) {
    const title = byId("primary-pane-title");
    const element = byId("transcript-list");
    const panes = renderDashboardPanes(state);

    if (hasActiveSession(state)) {
      title.textContent = "Transcript";
      element.innerHTML = `${panes.selectedSessionSummary}${panes.transcript}`;
      element.querySelectorAll("[data-open-session-id]").forEach(button => {
        button.addEventListener("click", () => {
          void onOpenSession(button.dataset.openSessionId);
        });
      });
      element.querySelectorAll("[data-compare-session-id]").forEach(button => {
        button.addEventListener("click", () => {
          void onCompareSession(button.dataset.compareSessionId);
        });
      });
      element.querySelectorAll("[data-clear-compare]").forEach(button => {
        button.addEventListener("click", () => {
          onClearCompareSession();
        });
      });
      element.scrollTop = element.scrollHeight;
      return;
    }

    title.textContent = "Operator Console";
    element.innerHTML = panes.landing;
    element.scrollTop = 0;
  }

  function renderSessionBrowser(state) {
    const element = byId("session-browser-list");
    element.innerHTML = renderDashboardPanes(state).sessionBrowser;
    element.querySelectorAll("[data-queue]").forEach(button => {
      button.addEventListener("click", () => {
        void onSelectQueue(button.dataset.queue);
      });
    });
    element.querySelectorAll("[data-session-id]").forEach(button => {
      button.addEventListener("click", () => {
        void onOpenSession(button.dataset.sessionId);
      });
    });
  }

  function renderTurn(state) {
    byId("turn-status").innerHTML = renderDashboardPanes(state).turn;
  }

  function renderMetrics(state) {
    byId("metrics-list").innerHTML = renderDashboardPanes(state).metrics;
  }

  function renderToolCalls(state) {
    byId("tool-calls-list").innerHTML = renderDashboardPanes(state).toolCalls;
  }

  function renderLiveOutput(state) {
    const element = byId("live-output-list");
    element.innerHTML = renderDashboardPanes(state).liveOutput;
    element.scrollTop = element.scrollHeight;
  }

  function renderApprovals(state) {
    const element = byId("approvals-list");
    element.innerHTML = renderApprovalsPane(state);
    element.querySelectorAll(".btn[data-approval-id]").forEach(button => {
      button.addEventListener("click", () => {
        void onResolveApproval(button.dataset.approvalId, button.dataset.decision);
      });
    });
  }

  function bindForkControls(state) {
    const forkForm = byId("fork-form");
    const forkTurnSelect = byId("fork-turn-select");
    const forkBranchLabel = byId("fork-branch-label");

    if (forkTurnSelect) {
      forkTurnSelect.value = state.selectedForkTurnId ?? "";
      forkTurnSelect.addEventListener("change", () => {
        onSelectForkTurn(forkTurnSelect.value);
      });
    }
    if (forkBranchLabel) {
      forkBranchLabel.value = drafts.forkBranchLabel;
      forkBranchLabel.addEventListener("input", () => {
        drafts.forkBranchLabel = forkBranchLabel.value;
      });
    }
    if (forkForm) {
      forkForm.addEventListener("submit", async event => {
        event.preventDefault();
        await onForkSession({
          turnId: forkTurnSelect?.value ?? state.selectedForkTurnId,
          branchLabel: forkBranchLabel?.value ?? drafts.forkBranchLabel,
        });
      });
    }
  }

  function renderComposer(state) {
    const element = byId("composer-pane-body");
    element.innerHTML = renderDashboardPanes(state).composer;

    const form = byId("interaction-form");
    const input = byId("interaction-input");
    if (!form || !input) {
      bindForkControls(state);
      return;
    }

    const mode = form.dataset.mode;
    if (mode === "message" || mode === "answer") {
      input.value = drafts[mode] ?? "";
      input.addEventListener("input", () => {
        drafts[mode] = input.value;
      });
    }

    form.addEventListener("submit", async event => {
      event.preventDefault();
      await onSubmitComposer(form.dataset.mode, input.value);
    });

    bindForkControls(state);
  }

  function clearDraftForMode(mode) {
    if (mode === "message" || mode === "answer") {
      drafts[mode] = "";
    }
  }

  function clearForkDraft() {
    drafts.forkBranchLabel = "";
  }

  function rerenderComposer(state) {
    renderComposer(state);
  }

  function renderEventLog(state) {
    const element = byId("event-log-list");
    element.innerHTML = renderDashboardPanes(state).eventLog;
    element.scrollTop = element.scrollHeight;
  }

  function renderSessionVisibility(state) {
    documentImpl.querySelectorAll(".session-detail-pane, #pane-composer").forEach(element => {
      element.classList.toggle("session-hidden", !hasActiveSession(state));
    });
  }

  function renderAll(state) {
    renderHeader(state);
    renderStatus(state);
    renderIndicator(state);
    renderPrimaryPane(state);
    renderSessionBrowser(state);
    renderSessionVisibility(state);
    renderComposer(state);
    renderTurn(state);
    renderMetrics(state);
    renderToolCalls(state);
    renderLiveOutput(state);
    renderApprovals(state);
    renderEventLog(state);
  }

  return {
    clearDraftForMode,
    clearForkDraft,
    renderAll,
    rerenderComposer,
    resetDrafts,
  };
}
