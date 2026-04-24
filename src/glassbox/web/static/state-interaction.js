function updatePendingApproval(approvals, approvalId, updater) {
  let changed = false;
  const next = approvals.map(approval => {
    if (approval.approval_id !== approvalId) {
      return approval;
    }
    changed = true;
    return updater(approval);
  });

  return changed ? next : approvals;
}

export function beginApprovalResolution(state, approvalId, decision) {
  return {
    ...state,
    pendingApprovals: updatePendingApproval(
      state.pendingApprovals,
      approvalId,
      approval => ({
        ...approval,
        resolution_state: "submitting",
        resolution_decision: decision,
        resolution_error: null,
      }),
    ),
  };
}

export function confirmApprovalResolution(state, approvalId, decision) {
  return {
    ...state,
    pendingApprovals: updatePendingApproval(
      state.pendingApprovals,
      approvalId,
      approval => ({
        ...approval,
        resolution_state: "submitted",
        resolution_decision: decision,
        resolution_error: null,
      }),
    ),
  };
}

export function failApprovalResolution(state, approvalId, errorMessage) {
  return {
    ...state,
    pendingApprovals: updatePendingApproval(
      state.pendingApprovals,
      approvalId,
      approval => ({
        ...approval,
        resolution_state: "failed",
        resolution_error: errorMessage,
      }),
    ),
  };
}

export function beginInteractionSubmission(state, kind) {
  return {
    ...state,
    interactionSubmission: {
      kind,
      state: "submitting",
      error: null,
    },
  };
}

export function confirmInteractionSubmission(state, kind) {
  return {
    ...state,
    interactionSubmission: {
      kind,
      state: "submitted",
      error: null,
    },
  };
}

export function failInteractionSubmission(state, kind, errorMessage) {
  return {
    ...state,
    interactionSubmission: {
      kind,
      state: "failed",
      error: errorMessage,
    },
  };
}

export function beginForkSubmission(state) {
  return {
    ...state,
    forkSubmission: {
      state: "submitting",
      error: null,
    },
  };
}

export function confirmForkSubmission(state) {
  return {
    ...state,
    forkSubmission: {
      state: "idle",
      error: null,
    },
  };
}

export function failForkSubmission(state, errorMessage) {
  return {
    ...state,
    forkSubmission: {
      state: "failed",
      error: errorMessage,
    },
  };
}
