/**
 * Pure dashboard state model and event reducer.
 *
 * The browser keeps a local projection derived from the snapshot endpoint plus
 * incremental SSE events. This module is intentionally side-effect free so it
 * can be unit tested directly.
 */

/**
 * @typedef {{kind: string, text: string}} MessagePart
 * @typedef {{message_id: string, role: string, parts: MessagePart[], created_at?: string}} TranscriptMessage
 * @typedef {{tool_call_id: string, turn_id: string, tool_name: string, status: string, started_at?: string | null}} ActiveToolCall
 * @typedef {{approval_id: string, turn_id?: string, subject: string, reason: string, requested_at?: string, resolution_state?: string, resolution_decision?: string | null, resolution_error?: string | null}} PendingApproval
 * @typedef {{turn_id: string, status: string, trigger_message_id?: string, outcome?: string, error_message?: string}} CurrentTurn
 * @typedef {{turn_id: string, started_at?: string | null, completed_at?: string | null, turn_duration_ms?: number | null, model_call_count: number, model_duration_ms_total: number, model_input_tokens_total: number, model_output_tokens_total: number, tool_call_count: number, tool_duration_ms_total: number, succeeded_tool_call_count: number, failed_tool_call_count: number}} TurnMetrics
 * @typedef {{turn_id: string, tool_call_id: string, stream: string, chunk: string}} LiveOutputEntry
 * @typedef {{sequence: number, event_type: string}} EventLogEntry
 * @typedef {{workspace_name: string, high_signal_paths: string[], top_level_directories: string[], additional_directory_count: number, top_level_files: string[], additional_file_count: number, project_markers: string[]}} RepositoryContextSummary
 * @typedef {{category: string, message: string, inherited: boolean, source_session_id?: string | null}} RuntimeContextNote
 * @typedef {{subject_kind: string, subject: string, summary: string, reasons: string[], signal_types: string[], inherited: boolean}} WorkingSetItem
 * @typedef {{items: WorkingSetItem[], additional_item_count: number}} WorkingSetSummary
 * @typedef {{repository_context: RepositoryContextSummary, runtime_notes: RuntimeContextNote[], additional_runtime_note_count: number, working_set: WorkingSetSummary}} RuntimeContextSummary
 * @typedef {{summary_kind: string, source_tool_name: string, artifact_kind: string, artifact_path: string, summary: string, freshness: string, target_paths: string[], keyword_filter?: string | null, failing_tests: string[], failure_count: number, error_count: number, timed_out: boolean, inherited: boolean, source_tool_call_id?: string | null}} ArtifactBackedContextSummary
 * @typedef {{summaries: ArtifactBackedContextSummary[], additional_summary_count: number}} ArtifactBackedContext
 * @typedef {{repository_context: RepositoryContextSummary, runtime_notes: RuntimeContextNote[], additional_runtime_note_count: number, working_set: WorkingSetSummary, artifact_context: ArtifactBackedContext}} RuntimeContextSummary
 * @typedef {{kind: "message" | "answer" | null, state: "idle" | "submitting" | "submitted" | "failed", error: string | null}} InteractionSubmission
 * @typedef {{state: "idle" | "submitting" | "failed", error: string | null}} ForkSubmission
 * @typedef {{session_id: string, status: string, branch_label: string | null, updated_at: string, latest_message_summary: string | null}} ChildSessionSummary
 * @typedef {{turn_id: string, sequence: number, created_at: string, label: string}} BranchableTurn
 * @typedef {{state: string, canonical_last_sequence?: number, projected_last_sequence?: number | null, lag?: number, degraded: boolean, detail?: string | null}} ProjectionHealthSummary
 * @typedef {{session_id: string, status: string, model_name: string, cwd: string, approval_mode: string, parent_session_id: string | null, forked_from_turn_id: string | null, forked_from_sequence: number | null, branch_label: string | null, child_session_count: number, can_fork: boolean, latest_fork_point_turn_id: string | null, latest_fork_point_sequence: number | null, fork_blocked_reason: string | null, dashboard_url: string | null, created_at: string, updated_at: string, last_sequence: number, pending_approval_id: string | null, pending_question_id: string | null, pending_question_text: string | null, session_failure_message: string | null, session_failure_retryable: boolean | null, latest_message_summary: string | null, next_action_summary: string, queue_memberships?: string[], priority_bucket?: string, priority_rank?: number, action_needed?: boolean, live_actionable?: boolean, historical_only?: boolean, has_active_turn?: boolean, projection_health?: ProjectionHealthSummary}} SessionSummary
 * @typedef {{total: number, approvals: number, questions: number, failures: number, degraded: number, active: number, action_needed: number, historical: number}} QueueCounts
 * @typedef {{ok: number, stale: number, unavailable: number, degraded: number}} ProjectionHealthCounts
 * @typedef {{workspace_root: string | null, state: string, health: string | null, pid: number | null, dashboard_url: string | null, health_url: string | null, session_index_url: string | null, started_at: string | null}} RuntimeSummary
 *
 * @typedef {Object} DashboardState
 * @property {string | null} sessionId
 * @property {string} status
 * @property {string | null} modelName
 * @property {string | null} cwd
 * @property {string | null} approvalMode
 * @property {string | null} parentSessionId
 * @property {string | null} forkedFromTurnId
 * @property {number | null} forkedFromSequence
 * @property {string | null} branchLabel
 * @property {ChildSessionSummary[]} childSessions
 * @property {BranchableTurn[]} branchableTurns
 * @property {boolean} canFork
 * @property {string | null} latestForkPointTurnId
 * @property {number | null} latestForkPointSequence
 * @property {string | null} forkBlockedReason
 * @property {string | null} selectedForkTurnId
 * @property {string | null} dashboardUrl
 * @property {number} lastSequence
 * @property {string | null} pendingApprovalId
 * @property {string | null} pendingQuestionId
 * @property {string | null} pendingQuestionText
 * @property {string | null} sessionFailureMessage
 * @property {boolean | null} sessionFailureRetryable
 * @property {RuntimeContextSummary | null} runtimeContext
 * @property {CurrentTurn | null} currentTurn
 * @property {TurnMetrics[]} turnMetrics
 * @property {TranscriptMessage[]} transcript
 * @property {ActiveToolCall[]} activeToolCalls
 * @property {LiveOutputEntry[]} liveOutput
 * @property {PendingApproval[]} pendingApprovals
 * @property {EventLogEntry[]} eventLog
 * @property {InteractionSubmission} interactionSubmission
 * @property {ForkSubmission} forkSubmission
 * @property {SessionSummary[]} sessionIndex
 * @property {"idle" | "loading" | "loaded" | "failed"} sessionIndexState
 * @property {string | null} sessionIndexError
 * @property {string} selectedQueue
 * @property {QueueCounts} queueCounts
 * @property {ProjectionHealthCounts} projectionHealthCounts
 * @property {RuntimeSummary} runtimeSummary
 * @property {"priority" | "updated_at"} sessionIndexSort
 * @property {string | null} selectedSessionId
 * @property {"idle" | "loading" | "loaded" | "failed"} sessionLoadState
 * @property {string | null} sessionLoadError
 * @property {"idle" | "index" | "loading" | "connecting" | "live" | "reconnecting" | "unavailable" | "historical"} streamState
 * @property {string | null} streamError
 * @property {number} streamRetryCount
 */

/**
 * @typedef {Object} SessionSnapshot
 * @property {string} session_id
 * @property {string} status
 * @property {string | null} current_turn_id
 * @property {string} model_name
 * @property {string} cwd
 * @property {string} approval_mode
 * @property {string | null} parent_session_id
 * @property {string | null} forked_from_turn_id
 * @property {number | null} forked_from_sequence
 * @property {string | null} branch_label
 * @property {ChildSessionSummary[]} child_sessions
 * @property {BranchableTurn[]} branchable_turns
 * @property {boolean} can_fork
 * @property {string | null} latest_fork_point_turn_id
 * @property {number | null} latest_fork_point_sequence
 * @property {string | null} fork_blocked_reason
 * @property {string | null} dashboard_url
 * @property {number} last_sequence
 * @property {string | null} pending_approval_id
 * @property {string | null} pending_question_id
 * @property {string | null} pending_question_text
 * @property {string | null} session_failure_message
 * @property {boolean | null} session_failure_retryable
 * @property {TranscriptMessage[]} transcript
 * @property {ActiveToolCall[]} active_tool_calls
 * @property {PendingApproval[]} pending_approvals
 * @property {TurnMetrics[]} turn_metrics
 * @property {RuntimeContextSummary | null} runtime_context
 */

/**
 * @typedef {Object} EventEnvelope
 * @property {string} session_id
 * @property {number} sequence
 * @property {string} event_type
 * @property {Record<string, unknown>} payload
 */

export { createState } from "./state-core.js";
export { hydrateFromSnapshot, selectForkTurn } from "./state-snapshot.js";
export {
  beginSessionAggregateLoad,
  hydrateSessionAggregate,
  failSessionAggregateLoad,
  beginSessionIndexLoad,
  hydrateSessionIndex,
  failSessionIndexLoad,
  beginSessionSelection,
  clearSessionSelection,
  failSessionSelection,
  beginLiveStreamConnection,
  markLiveStreamConnected,
  markLiveStreamReconnecting,
  markLiveStreamUnavailable,
  markHistoricalSnapshot,
} from "./state-stream.js";
export {
  beginApprovalResolution,
  confirmApprovalResolution,
  failApprovalResolution,
  beginInteractionSubmission,
  confirmInteractionSubmission,
  failInteractionSubmission,
  beginForkSubmission,
  confirmForkSubmission,
  failForkSubmission,
} from "./state-interaction.js";
export { applyEvent } from "./state-events.js";
