/**
 * Pure dashboard pane renderers.
 *
 * These functions take the reducer state and return HTML strings for the
 * dashboard panes. They are side-effect free so frontend tests can validate
 * pane output without a browser DOM.
 */
import {
  renderLandingPane,
  renderSelectedSessionSummary,
  renderSessionBrowserPane,
} from "./render-session-panes.js";
import {
  renderLiveOutputPane,
  renderTranscriptPane,
  renderTurnPane,
} from "./render-activity-panes.js";
import {
  renderApprovalsPane,
  renderComposerPane,
} from "./render-action-panes.js";
import {
  renderEventLogPane,
  renderMetricsPane,
  renderToolCallsPane,
} from "./render-diagnostics-panes.js";

export {
  renderLandingPane,
  renderSelectedSessionSummary,
  renderSessionBrowserPane,
  renderLiveOutputPane,
  renderTranscriptPane,
  renderTurnPane,
  renderApprovalsPane,
  renderComposerPane,
  renderEventLogPane,
  renderMetricsPane,
  renderToolCallsPane,
};

export function renderDashboardPanes(state) {
  return {
    composer: renderComposerPane(state),
    landing: renderLandingPane(state),
    selectedSessionSummary: renderSelectedSessionSummary(state),
    sessionBrowser: renderSessionBrowserPane(state),
    transcript: renderTranscriptPane(state),
    turn: renderTurnPane(state),
    metrics: renderMetricsPane(state),
    toolCalls: renderToolCallsPane(state),
    liveOutput: renderLiveOutputPane(state),
    approvals: renderApprovalsPane(state),
    eventLog: renderEventLogPane(state),
  };
}
