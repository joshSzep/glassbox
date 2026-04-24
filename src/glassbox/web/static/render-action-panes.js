import { escHtml, renderEmpty } from "./render-utils.js";

function renderForkCard(state) {
  const forkSubmission = state.forkSubmission ?? {
    state: "idle",
    error: null,
  };
  const isBusy = forkSubmission.state === "submitting";
  let statusHtml = "";

  if (forkSubmission.state === "submitting") {
    statusHtml = `<div class="composer-status">Creating child session…</div>`;
  } else if (forkSubmission.state === "failed" && forkSubmission.error) {
    statusHtml = `<div class="composer-status composer-status-error">${escHtml(forkSubmission.error)}</div>`;
  }

  if (!state.canFork || (state.branchableTurns ?? []).length === 0) {
    return `<div class="composer-card composer-blocked composer-fork-card">
      <div class="composer-label">Fork Unavailable</div>
      <div class="composer-help">${escHtml(state.forkBlockedReason ?? "This session is inspect-only right now.")}</div>
      ${statusHtml}
    </div>`;
  }

  const selectedForkTurnId = state.selectedForkTurnId ?? state.branchableTurns[0]?.turn_id ?? "";
  const optionsHtml = state.branchableTurns.map(turn => {
    const label = turn.turn_id === state.latestForkPointTurnId
      ? `${turn.label} (latest stable)`
      : turn.label;
    return `<option value="${escHtml(turn.turn_id)}"${turn.turn_id === selectedForkTurnId ? " selected" : ""}>${escHtml(label)}</option>`;
  }).join("");

  return `<div class="composer-card composer-fork-card">
    <div class="composer-label">Create Forked Session</div>
    <div class="composer-help">Choose a stable completed turn boundary, create a child session, then open it immediately in the dashboard.</div>
    ${statusHtml}
    <form id="fork-form" class="composer-form">
      <label class="composer-help" for="fork-turn-select">Fork point</label>
      <select id="fork-turn-select" class="composer-select" ${isBusy ? "disabled" : ""}>
        ${optionsHtml}
      </select>
      <label class="composer-help" for="fork-branch-label">Branch label (optional)</label>
      <input id="fork-branch-label" class="composer-input composer-input-singleline" type="text" maxlength="120" placeholder="alt-path" ${isBusy ? "disabled" : ""} />
      <div class="composer-actions">
        <button id="fork-submit" class="btn btn-submit" type="submit" ${isBusy ? "disabled" : ""}>Create Fork</button>
      </div>
    </form>
  </div>`;
}

function interactionMode(state) {
  if (state.status === "awaiting_user_input" && state.pendingQuestionId) {
    return "answer";
  }
  if (state.status === "running") {
    return "message";
  }
  return "blocked";
}

export function renderComposerPane(state) {
  const mode = interactionMode(state);
  const interaction = state.interactionSubmission ?? {
    kind: null,
    state: "idle",
    error: null,
  };
  const isBusy = interaction.state === "submitting" || interaction.state === "submitted";

  let primaryCard = "";
  if (mode === "blocked") {
    let reason = "Session actions are currently unavailable.";
    if (state.status === "awaiting_approval") {
      reason = [
        "Resolve the pending approval below before sending a new prompt or ",
        "answering the model's question.",
      ].join("");
    } else if (state.status === "completed") {
      reason = "This session is complete and cannot accept new input.";
    } else if (state.status === "failed") {
      reason = "This session failed. Start a new session or inspect the failure details.";
    }

    primaryCard = `<div class="composer-card composer-blocked">
      <div class="composer-label">Next Action Unavailable</div>
      <div class="composer-help">${escHtml(reason)}</div>
    </div>`;
  } else {
    const questionDetails = mode === "answer"
       ? `<div class="composer-question">${escHtml(state.pendingQuestionText ?? "Answer the pending model question.")}</div>
         <div class="composer-help">Question ID ${escHtml(state.pendingQuestionId ?? "unknown")}</div>
         <div class="composer-help">This sends an answer to the model's pending ask_user question. It does not start a new prompt.</div>`
       : `<div class="composer-help">Send a fresh user prompt after the previous turn has completed. Use this instead of answering a pending question or resolving an approval.</div>`;
    const buttonLabel = mode === "answer" ? "Send Answer" : "Send Prompt";
    const heading = mode === "answer" ? "Answer Pending Question" : "Continue Session";
    let statusHtml = "";

    if (interaction.state === "submitting") {
      statusHtml = `<div class="composer-status">Sending ${escHtml(interaction.kind ?? mode)}…</div>`;
    } else if (interaction.state === "submitted") {
      statusHtml = `<div class="composer-status">Request sent. Waiting for session update…</div>`;
    } else if (interaction.state === "failed" && interaction.error) {
      statusHtml = `<div class="composer-status composer-status-error">${escHtml(interaction.error)}</div>`;
    }

    primaryCard = `<div class="composer-card composer-${escHtml(mode)}">
      <div class="composer-label">${escHtml(heading)}</div>
      ${questionDetails}
      ${statusHtml}
      <form id="interaction-form" class="composer-form" data-mode="${escHtml(mode)}">
        <textarea
          id="interaction-input"
          class="composer-input"
          rows="4"
          placeholder="${escHtml(mode === "answer" ? "Type your answer" : "Type the next prompt")}"
          ${isBusy ? "disabled" : ""}
        ></textarea>
        <div class="composer-actions">
          <button
            id="interaction-submit"
            class="btn btn-submit"
            type="submit"
            ${isBusy ? "disabled" : ""}
          >${escHtml(buttonLabel)}</button>
        </div>
      </form>
    </div>`;
  }

  return `${primaryCard}${renderForkCard(state)}`;
}

export function renderApprovalsPane(state) {
  if (state.pendingApprovals.length === 0) {
    return renderEmpty("No pending approvals.");
  }

  return state.pendingApprovals.map(approval => {
    const resolutionState = approval.resolution_state ?? "idle";
    const resolutionDecision = approval.resolution_decision ?? null;
    const disabled = resolutionState === "submitting" || resolutionState === "submitted";
    let statusHtml = "";

    if (resolutionState === "submitting") {
      statusHtml = `<div class="approval-status">Submitting ${escHtml(resolutionDecision ?? "decision")}…</div>`;
    } else if (resolutionState === "submitted") {
      statusHtml = `<div class="approval-status">Decision sent. Waiting for session update…</div>`;
    } else if (resolutionState === "failed") {
      statusHtml = `<div class="approval-status approval-status-error">${escHtml(approval.resolution_error ?? "Resolution failed")}</div>`;
    }

    return `
    <div class="approval-card approval-${escHtml(resolutionState)}" id="approval-${escHtml(approval.approval_id)}">
      <div class="approval-subject">${escHtml(approval.subject)}</div>
      <div class="approval-reason">${escHtml(approval.reason)}</div>
      ${statusHtml}
      <div class="approval-actions">
        <button class="btn btn-approve"
          data-approval-id="${escHtml(approval.approval_id)}"
          data-decision="approved"
          ${disabled ? "disabled" : ""}>
          Approve
        </button>
        <button class="btn btn-deny"
          data-approval-id="${escHtml(approval.approval_id)}"
          data-decision="denied"
          ${disabled ? "disabled" : ""}>
          Deny
        </button>
      </div>
    </div>
  `;
  }).join("");
}
