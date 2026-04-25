import {
  createIdleForkSubmission,
  createIdleInteractionSubmission,
  createState,
} from "./state-core.js";

function normalizeBranchableTurns(branchableTurns) {
  if (!Array.isArray(branchableTurns)) {
    return [];
  }

  return branchableTurns
    .filter(turn => turn && typeof turn.turn_id === "string")
    .map(turn => ({
      turn_id: turn.turn_id,
      sequence: Number.isFinite(turn.sequence) ? turn.sequence : 0,
      created_at: typeof turn.created_at === "string" ? turn.created_at : "",
      label: typeof turn.label === "string" ? turn.label : `Turn ${turn.turn_id.slice(0, 8)}`,
    }));
}

function defaultSelectedForkTurnId(snapshot) {
  const branchableTurns = normalizeBranchableTurns(snapshot.branchable_turns);
  if (typeof snapshot.latest_fork_point_turn_id === "string") {
    const latestTurn = branchableTurns.find(
      turn => turn.turn_id === snapshot.latest_fork_point_turn_id,
    );
    if (latestTurn) {
      return latestTurn.turn_id;
    }
  }

  return branchableTurns[0]?.turn_id ?? null;
}

export function upsertBranchableTurn(branchableTurns, branchableTurn) {
  const next = [
    branchableTurn,
    ...branchableTurns.filter(turn => turn.turn_id !== branchableTurn.turn_id),
  ];
  return next.sort((left, right) => right.sequence - left.sequence);
}

export function currentTurnLabel(state) {
  const currentTurnId = state.currentTurn?.turn_id ?? null;
  const triggerMessageId = state.currentTurn?.trigger_message_id ?? null;
  const transcriptMessage = triggerMessageId
    ? state.transcript.find(message => message.message_id === triggerMessageId)
    : null;
  const text = transcriptMessage?.parts?.map(part => part.text ?? "").join(" ").trim();
  if (text) {
    return text;
  }
  if (currentTurnId) {
    return `Turn ${currentTurnId.slice(0, 8)}`;
  }
  return "Completed turn";
}

function inferCurrentTurn(snapshot) {
  const activeToolCall = snapshot.active_tool_calls?.[0];
  if (activeToolCall?.turn_id) {
    return {
      turn_id: activeToolCall.turn_id,
      status: "running",
    };
  }

  const pendingApproval = snapshot.pending_approvals?.[0];
  if (pendingApproval?.turn_id) {
    return {
      turn_id: pendingApproval.turn_id,
      status: "awaiting_approval",
    };
  }

  if (typeof snapshot.current_turn_id === "string") {
    return {
      turn_id: snapshot.current_turn_id,
      status: typeof snapshot.status === "string" ? snapshot.status : "running",
    };
  }

  return null;
}

function normalizeSnapshotSessionFields(snapshot) {
  const branchableTurns = normalizeBranchableTurns(snapshot.branchable_turns);
  return {
    sessionId: snapshot.session_id,
    status: snapshot.status,
    modelName: snapshot.model_name,
    cwd: snapshot.cwd,
    approvalMode: snapshot.approval_mode,
    parentSessionId: snapshot.parent_session_id ?? null,
    forkedFromTurnId: snapshot.forked_from_turn_id ?? null,
    forkedFromSequence: snapshot.forked_from_sequence ?? null,
    branchLabel: snapshot.branch_label ?? null,
    childSessions: [...(snapshot.child_sessions ?? [])],
    branchableTurns,
    canFork: Boolean(snapshot.can_fork),
    latestForkPointTurnId: snapshot.latest_fork_point_turn_id ?? null,
    latestForkPointSequence: snapshot.latest_fork_point_sequence ?? null,
    forkBlockedReason: snapshot.fork_blocked_reason ?? null,
    selectedForkTurnId: defaultSelectedForkTurnId(snapshot),
    dashboardUrl: snapshot.dashboard_url ?? null,
    lastSequence: snapshot.last_sequence ?? 0,
    pendingApprovalId: snapshot.pending_approval_id ?? null,
    pendingQuestionId: snapshot.pending_question_id ?? null,
    pendingQuestionText: snapshot.pending_question_text ?? null,
    sessionFailureMessage: snapshot.session_failure_message ?? null,
    sessionFailureRetryable: snapshot.session_failure_retryable ?? null,
    runtimeContext: normalizeRuntimeContext(snapshot.runtime_context),
    currentTurn: inferCurrentTurn(snapshot),
    turnMetrics: [...(snapshot.turn_metrics ?? [])],
    transcript: [...(snapshot.transcript ?? [])],
    activeToolCalls: [...(snapshot.active_tool_calls ?? [])],
    pendingApprovals: [...(snapshot.pending_approvals ?? [])],
  };
}

function normalizeComparableSession(snapshot) {
  return {
    ...normalizeSnapshotSessionFields(snapshot),
    createdAt: snapshot.created_at ?? null,
    updatedAt: snapshot.updated_at ?? null,
    projectionHealth: snapshot.projection_health ?? null,
  };
}

function normalizeRuntimeContext(snapshotRuntimeContext) {
  if (!snapshotRuntimeContext || !snapshotRuntimeContext.repository_context) {
    return null;
  }

  const repositoryContext = snapshotRuntimeContext.repository_context;
  return {
    repository_context: {
      workspace_name: typeof repositoryContext.workspace_name === "string"
        ? repositoryContext.workspace_name
        : "workspace",
      high_signal_paths: Array.isArray(repositoryContext.high_signal_paths)
        ? [...repositoryContext.high_signal_paths]
        : [],
      top_level_directories: Array.isArray(repositoryContext.top_level_directories)
        ? [...repositoryContext.top_level_directories]
        : [],
      additional_directory_count: Number.isFinite(repositoryContext.additional_directory_count)
        ? repositoryContext.additional_directory_count
        : 0,
      top_level_files: Array.isArray(repositoryContext.top_level_files)
        ? [...repositoryContext.top_level_files]
        : [],
      additional_file_count: Number.isFinite(repositoryContext.additional_file_count)
        ? repositoryContext.additional_file_count
        : 0,
      project_markers: Array.isArray(repositoryContext.project_markers)
        ? [...repositoryContext.project_markers]
        : [],
    },
    runtime_notes: Array.isArray(snapshotRuntimeContext.runtime_notes)
      ? snapshotRuntimeContext.runtime_notes
        .filter(note => note && typeof note.category === "string")
        .map(note => ({
          category: note.category,
          message: typeof note.message === "string" ? note.message : "",
          inherited: Boolean(note.inherited),
          source_session_id: typeof note.source_session_id === "string"
            ? note.source_session_id
            : null,
        }))
      : [],
    additional_runtime_note_count: Number.isFinite(snapshotRuntimeContext.additional_runtime_note_count)
      ? snapshotRuntimeContext.additional_runtime_note_count
      : 0,
    working_set: {
      items: Array.isArray(snapshotRuntimeContext.working_set?.items)
        ? snapshotRuntimeContext.working_set.items
          .filter(item => item && typeof item.subject_kind === "string" && typeof item.subject === "string")
          .map(item => ({
            subject_kind: item.subject_kind,
            subject: item.subject,
            summary: typeof item.summary === "string" ? item.summary : "",
            reasons: Array.isArray(item.reasons) ? item.reasons.filter(reason => typeof reason === "string") : [],
            signal_types: Array.isArray(item.signal_types) ? item.signal_types.filter(signalType => typeof signalType === "string") : [],
            inherited: Boolean(item.inherited),
          }))
        : [],
      additional_item_count: Number.isFinite(snapshotRuntimeContext.working_set?.additional_item_count)
        ? snapshotRuntimeContext.working_set.additional_item_count
        : 0,
    },
    artifact_context: {
      summaries: Array.isArray(snapshotRuntimeContext.artifact_context?.summaries)
        ? snapshotRuntimeContext.artifact_context.summaries
          .filter(summary => summary && typeof summary.summary_kind === "string")
          .map(summary => ({
            summary_kind: summary.summary_kind,
            source_tool_name: typeof summary.source_tool_name === "string" ? summary.source_tool_name : "",
            artifact_kind: typeof summary.artifact_kind === "string" ? summary.artifact_kind : "",
            artifact_path: typeof summary.artifact_path === "string" ? summary.artifact_path : "",
            summary: typeof summary.summary === "string" ? summary.summary : "",
            freshness: typeof summary.freshness === "string" ? summary.freshness : "fresh",
            target_paths: Array.isArray(summary.target_paths) ? summary.target_paths.filter(path => typeof path === "string") : [],
            keyword_filter: typeof summary.keyword_filter === "string" ? summary.keyword_filter : null,
            failing_tests: Array.isArray(summary.failing_tests) ? summary.failing_tests.filter(testName => typeof testName === "string") : [],
            failure_count: Number.isFinite(summary.failure_count) ? summary.failure_count : 0,
            error_count: Number.isFinite(summary.error_count) ? summary.error_count : 0,
            timed_out: Boolean(summary.timed_out),
            inherited: Boolean(summary.inherited),
            source_tool_call_id: typeof summary.source_tool_call_id === "string"
              ? summary.source_tool_call_id
              : null,
          }))
        : [],
      additional_summary_count: Number.isFinite(snapshotRuntimeContext.artifact_context?.additional_summary_count)
        ? snapshotRuntimeContext.artifact_context.additional_summary_count
        : 0,
    },
  };
}

function runtimeContextNoteKey(note) {
  return [
    note.source_session_id ?? "local",
    note.category,
    note.message,
  ].join("\u0000");
}

export function upsertRuntimeContextNote(runtimeContext, note) {
  if (!runtimeContext) {
    return runtimeContext;
  }

  const existingIndex = runtimeContext.runtime_notes.findIndex(
    existing => runtimeContextNoteKey(existing) === runtimeContextNoteKey(note),
  );
  if (existingIndex >= 0) {
    const nextNotes = [...runtimeContext.runtime_notes];
    nextNotes[existingIndex] = note;
    return {
      ...runtimeContext,
      runtime_notes: nextNotes,
    };
  }

  if (runtimeContext.additional_runtime_note_count > 0) {
    return {
      ...runtimeContext,
      additional_runtime_note_count: runtimeContext.additional_runtime_note_count + 1,
    };
  }

  if (runtimeContext.runtime_notes.length >= 8) {
    return {
      ...runtimeContext,
      additional_runtime_note_count: 1,
    };
  }

  return {
    ...runtimeContext,
    runtime_notes: [...runtimeContext.runtime_notes, note],
  };
}

export function hydrateFromSnapshot(snapshot) {
  return {
    ...createState(),
    ...normalizeSnapshotSessionFields(snapshot),
    selectedSessionId: snapshot.session_id,
    liveOutput: [],
    eventLog: [],
    interactionSubmission: createIdleInteractionSubmission(),
    forkSubmission: createIdleForkSubmission(),
    sessionLoadState: "loaded",
  };
}

export function hydrateCompareSession(state, snapshot) {
  return {
    ...state,
    compareSessionId: snapshot.session_id,
    compareSession: normalizeComparableSession(snapshot),
    compareSessionLoadState: "loaded",
    compareSessionLoadError: null,
  };
}

export function selectForkTurn(state, turnId) {
  const selectedTurn = state.branchableTurns.find(turn => turn.turn_id === turnId);
  return {
    ...state,
    selectedForkTurnId: selectedTurn?.turn_id ?? state.selectedForkTurnId,
  };
}
