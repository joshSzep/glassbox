"""Core domain package for Glassbox."""

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import BackgroundJobAbandoned
from glassbox.core.events import BackgroundJobCancellationRequested
from glassbox.core.events import BackgroundJobCancelled
from glassbox.core.events import BackgroundJobClaimed
from glassbox.core.events import BackgroundJobCompleted
from glassbox.core.events import BackgroundJobCreated
from glassbox.core.events import BackgroundJobFailed
from glassbox.core.events import BackgroundJobHeartbeat
from glassbox.core.events import BackgroundJobPaused
from glassbox.core.events import BackgroundJobProgressRecorded
from glassbox.core.events import BackgroundJobRecoveryRecorded
from glassbox.core.events import BackgroundJobRetryExhausted
from glassbox.core.events import BackgroundJobRetryRequested
from glassbox.core.events import BackgroundJobStarted
from glassbox.core.events import BranchCandidateExecuted
from glassbox.core.events import BranchCandidateForked
from glassbox.core.events import BranchCandidateNeedsReview
from glassbox.core.events import BranchCandidatePlanned
from glassbox.core.events import BranchCandidateRejected
from glassbox.core.events import BranchCandidatesCompared
from glassbox.core.events import BranchCandidateSelected
from glassbox.core.events import BranchCandidateVerified
from glassbox.core.events import BranchSearchAbandoned
from glassbox.core.events import BranchSearchStarted
from glassbox.core.events import BudgetDecisionRecorded
from glassbox.core.events import BudgetExhausted
from glassbox.core.events import BudgetOverrideRequested
from glassbox.core.events import BudgetOverrideResolved
from glassbox.core.events import CancellationAcknowledged
from glassbox.core.events import CancellationFailed
from glassbox.core.events import CancellationRequested
from glassbox.core.events import ChangesetArchived
from glassbox.core.events import ChangesetCandidateAdopted
from glassbox.core.events import ChangesetCreated
from glassbox.core.events import ChangesetInventoryRefreshed
from glassbox.core.events import ChangesetReadinessDecided
from glassbox.core.events import ChangesetReviewBriefCreated
from glassbox.core.events import ChangesetSourceAttached
from glassbox.core.events import ChangesetVerificationPostureUpdated
from glassbox.core.events import ContextCompactionCreated
from glassbox.core.events import ContextCompactionFreshnessChanged
from glassbox.core.events import ContinuationWindowExpired
from glassbox.core.events import ContinuationWindowRequested
from glassbox.core.events import ContinuationWindowResolved
from glassbox.core.events import ErrorRecorded
from glassbox.core.events import EventEnvelope
from glassbox.core.events import EventPayload
from glassbox.core.events import EventPayloadType
from glassbox.core.events import LongRunPhaseChanged
from glassbox.core.events import ManualEvidenceArchived
from glassbox.core.events import ManualEvidenceAttached
from glassbox.core.events import ManualEvidenceRejected
from glassbox.core.events import ManualEvidenceSuperseded
from glassbox.core.events import ModelCallCompleted
from glassbox.core.events import ModelCallStarted
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import PauseWindowCancelled
from glassbox.core.events import PauseWindowScheduled
from glassbox.core.events import PauseWindowTriggered
from glassbox.core.events import ProviderRecoveryRecorded
from glassbox.core.events import RecoveryDecisionRecorded
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import ResumeOutcomeRecorded
from glassbox.core.events import ReviewFeedbackArchived
from glassbox.core.events import ReviewFeedbackCreated
from glassbox.core.events import ReviewFeedbackDispositionUpdated
from glassbox.core.events import ReviewFeedbackFixupInventoryAttached
from glassbox.core.events import ReviewFeedbackReopened
from glassbox.core.events import ReviewFeedbackResolved
from glassbox.core.events import ReviewFeedbackRiskAccepted
from glassbox.core.events import ReviewFeedbackScopeAttached
from glassbox.core.events import RuntimeNoteRecorded
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionResumed
from glassbox.core.events import SessionStarted
from glassbox.core.events import TaskAbandoned
from glassbox.core.events import TaskCancelled
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.events import TaskCreated
from glassbox.core.events import TaskPaused
from glassbox.core.events import TaskPlanProposed
from glassbox.core.events import TaskPlanRevised
from glassbox.core.events import TaskResumed
from glassbox.core.events import TaskStatusChanged
from glassbox.core.events import TaskStepCompleted
from glassbox.core.events import TaskStepFailed
from glassbox.core.events import TaskStepSkipped
from glassbox.core.events import TaskStepStarted
from glassbox.core.events import TaskVerificationCompleted
from glassbox.core.events import TaskVerificationFailed
from glassbox.core.events import TaskVerificationPlanned
from glassbox.core.events import TaskVerificationResidualRiskAccepted
from glassbox.core.events import TaskVerificationRetried
from glassbox.core.events import TaskVerificationSkipped
from glassbox.core.events import TaskVerificationStarted
from glassbox.core.events import TaskVerificationStreamed
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.events import ToolExecutionCancelled
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import ToolOutputChunk
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.events import TurnCancelled
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
from glassbox.core.events import TurnStatusChanged
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.events import WorkspaceMemoryCandidateRejected
from glassbox.core.events import WorkspaceMemoryConfirmed
from glassbox.core.events import WorkspaceMemoryCreated
from glassbox.core.events import WorkspaceMemoryImported
from glassbox.core.events import WorkspaceMemoryInvalidated
from glassbox.core.events import WorkspaceMemoryPruned
from glassbox.core.events import WorkspaceMemoryUpdated
from glassbox.core.events import WorkspaceMemoryUsedInContext
from glassbox.core.events import WorktreeCleanupRecorded
from glassbox.core.events import WorktreeCreated
from glassbox.core.events import WorktreeStatusRecorded
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import BackgroundJobId
from glassbox.core.ids import BranchCandidateId
from glassbox.core.ids import BranchSearchId
from glassbox.core.ids import BudgetOverrideId
from glassbox.core.ids import ChangesetId
from glassbox.core.ids import ContextCompactionId
from glassbox.core.ids import EventId
from glassbox.core.ids import ManualEvidenceId
from glassbox.core.ids import MessageId
from glassbox.core.ids import PauseWindowId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import RecoveryDecisionId
from glassbox.core.ids import ReviewFeedbackId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskCheckpointId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskStepId
from glassbox.core.ids import TaskVerificationId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.core.ids import WorktreeId
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_artifact_id
from glassbox.core.ids import new_background_job_id
from glassbox.core.ids import new_branch_candidate_id
from glassbox.core.ids import new_branch_search_id
from glassbox.core.ids import new_budget_override_id
from glassbox.core.ids import new_changeset_id
from glassbox.core.ids import new_context_compaction_id
from glassbox.core.ids import new_event_id
from glassbox.core.ids import new_manual_evidence_id
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_pause_window_id
from glassbox.core.ids import new_question_id
from glassbox.core.ids import new_recovery_decision_id
from glassbox.core.ids import new_review_feedback_id
from glassbox.core.ids import new_session_id
from glassbox.core.ids import new_task_checkpoint_id
from glassbox.core.ids import new_task_id
from glassbox.core.ids import new_task_step_id
from glassbox.core.ids import new_task_verification_id
from glassbox.core.ids import new_tool_attempt_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.core.ids import new_workspace_memory_id
from glassbox.core.ids import new_worktree_id
from glassbox.core.models import AutonomyBudget
from glassbox.core.models import AutonomyBudgetPostureRecord
from glassbox.core.models import AutonomyBudgetRemaining
from glassbox.core.models import AutonomyBudgetUsage
from glassbox.core.models import AutonomySelection
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.models import BranchCandidateRecord
from glassbox.core.models import BranchSearchRecord
from glassbox.core.models import ChangesetInventoryRecord
from glassbox.core.models import ChangesetReadinessRecord
from glassbox.core.models import ChangesetRecord
from glassbox.core.models import ChangesetReviewBriefRecord
from glassbox.core.models import ChangesetSourceRecord
from glassbox.core.models import ChangesetVerificationPostureRecord
from glassbox.core.models import CheckpointAbsenceRecord
from glassbox.core.models import CommandEnvironmentSummary
from glassbox.core.models import CommandToolchainVersion
from glassbox.core.models import ContextCompactionRecord
from glassbox.core.models import ForkedSession
from glassbox.core.models import InheritedTranscriptMessage
from glassbox.core.models import LongRunStatusRecord
from glassbox.core.models import ManualEvidenceRecord
from glassbox.core.models import MessagePart
from glassbox.core.models import PolicyDecision
from glassbox.core.models import PolicyDecisionTrace
from glassbox.core.models import ProjectionHealth
from glassbox.core.models import ProviderRecoveryRecord
from glassbox.core.models import QuietWindowPolicy
from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceMemoryReference
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligencePathHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSourceManifest
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.core.models import ResolvedForkPoint
from glassbox.core.models import ReviewFeedbackFixupInventoryRecord
from glassbox.core.models import ReviewFeedbackFixupPathRecord
from glassbox.core.models import ReviewFeedbackFixupPathSummary
from glassbox.core.models import ReviewFeedbackRecord
from glassbox.core.models import ReviewFeedbackScopeRecord
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import SessionConfig
from glassbox.core.models import SessionRecord
from glassbox.core.models import SessionState
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.models import TaskPlanSnapshot
from glassbox.core.models import TaskRecord
from glassbox.core.models import TaskStepProposal
from glassbox.core.models import TaskStepRecord
from glassbox.core.models import TaskVerificationLedgerRecord
from glassbox.core.models import TaskVerificationLedgerSummary
from glassbox.core.models import TaskVerificationRecord
from glassbox.core.models import ToolAttemptRecord
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TranscriptMessage
from glassbox.core.models import TurnRecoveryPosture
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.models import WorkspaceMemoryProvenance
from glassbox.core.models_evidence_graph import ClaimSupport
from glassbox.core.models_evidence_graph import EvidenceGraph
from glassbox.core.models_evidence_graph import EvidenceGraphEdge
from glassbox.core.models_evidence_graph import EvidenceGraphMissingEvidence
from glassbox.core.models_evidence_graph import EvidenceGraphNode
from glassbox.core.models_evidence_graph import EvidenceGraphProvenance
from glassbox.core.models_handoff import HandoffCompatibilitySummary
from glassbox.core.models_handoff import HandoffDigestSummary
from glassbox.core.models_handoff import HandoffLabel
from glassbox.core.models_handoff import HandoffLocalOnlySummary
from glassbox.core.models_handoff import HandoffPackageManifest
from glassbox.core.models_handoff import HandoffReadiness
from glassbox.core.models_handoff import HandoffReadinessReason
from glassbox.core.models_handoff import HandoffRedactionSummary
from glassbox.core.models_handoff import HandoffSafeCommand
from glassbox.core.models_handoff import HandoffSourceRef
from glassbox.core.models_operator_flow import MaintenanceCue
from glassbox.core.models_operator_flow import NextAction
from glassbox.core.models_operator_flow import NextActionCommandRecipe
from glassbox.core.models_operator_flow import NextActionEvidenceRef
from glassbox.core.models_operator_flow import NextActionTarget
from glassbox.core.models_operator_flow import OperatorQueueDedupeKey
from glassbox.core.models_operator_flow import OperatorQueueEvidenceSummary
from glassbox.core.models_operator_flow import OperatorQueueItem
from glassbox.core.models_verification_plan import VerificationFailureDigest
from glassbox.core.models_verification_plan import VerificationPlan
from glassbox.core.models_verification_plan import VerificationPlanEntry
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import ApprovalMode
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import AutonomyEscalationReason
from glassbox.core.types import AutonomyMode
from glassbox.core.types import BackgroundJobFailureKind
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import BackgroundJobRecoveryReason
from glassbox.core.types import BackgroundJobState
from glassbox.core.types import BranchCandidateStatus
from glassbox.core.types import BranchCandidateVerificationStatus
from glassbox.core.types import BranchSearchStatus
from glassbox.core.types import ChangesetInventoryFreshness
from glassbox.core.types import ChangesetReadinessKind
from glassbox.core.types import ChangesetReadinessState
from glassbox.core.types import ChangesetRiskLevel
from glassbox.core.types import ChangesetSourceKind
from glassbox.core.types import ChangesetVerificationState
from glassbox.core.types import CheckpointAbsenceReason
from glassbox.core.types import CommandPurpose
from glassbox.core.types import CommandReviewRelevance
from glassbox.core.types import ContextCompactionFreshness
from glassbox.core.types import ContextCompactionScope
from glassbox.core.types import LongRunPhase
from glassbox.core.types import LongRunPhaseState
from glassbox.core.types import ManualEvidenceFreshness
from glassbox.core.types import ManualEvidenceKind
from glassbox.core.types import ManualEvidenceRedactionStatus
from glassbox.core.types import ManualEvidenceState
from glassbox.core.types import ManualEvidenceTargetKind
from glassbox.core.types import PauseWindowPolicy
from glassbox.core.types import ProviderRecoveryAction
from glassbox.core.types import ProviderRecoveryKind
from glassbox.core.types import RecoveryDecision
from glassbox.core.types import RepositoryIndexEntityKind
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceCommandRisk
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types import RepositoryIntelligencePackageKind
from glassbox.core.types import RepositoryIntelligencePathKind
from glassbox.core.types import RepositoryIntelligenceReleaseSurfaceKind
from glassbox.core.types import ResumeOutcomeStatus
from glassbox.core.types import ReviewFeedbackDisposition
from glassbox.core.types import ReviewFeedbackKind
from glassbox.core.types import ReviewFeedbackProvenance
from glassbox.core.types import ReviewFeedbackScopeKind
from glassbox.core.types import ReviewFixupSourceKind
from glassbox.core.types import ReviewResponseState
from glassbox.core.types import SessionStatus
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import ToolAttemptRetryClassification
from glassbox.core.types import ToolAttemptStatus
from glassbox.core.types import ToolExecutionStatus
from glassbox.core.types import TurnRecoveryState
from glassbox.core.types import TurnStatus
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemorySourceType
from glassbox.core.types import WorkspaceMemoryState
from glassbox.core.types import WorktreeSourceKind
from glassbox.core.types import WorktreeState
from glassbox.core.types_evidence_graph import ClaimSupportState
from glassbox.core.types_evidence_graph import EvidenceGraphConfidence
from glassbox.core.types_evidence_graph import EvidenceGraphEdgeKind
from glassbox.core.types_evidence_graph import EvidenceGraphFreshness
from glassbox.core.types_evidence_graph import EvidenceGraphNodeKind
from glassbox.core.types_evidence_graph import EvidenceGraphRedactionStatus
from glassbox.core.types_evidence_graph import EvidenceGraphVisibility
from glassbox.core.types_handoff import HandoffCompatibilityState
from glassbox.core.types_handoff import HandoffEvidenceFreshness
from glassbox.core.types_handoff import HandoffIntent
from glassbox.core.types_handoff import HandoffLabelMetadataPosture
from glassbox.core.types_handoff import HandoffLabelSource
from glassbox.core.types_handoff import HandoffPackageKind
from glassbox.core.types_handoff import HandoffReadinessReasonKind
from glassbox.core.types_handoff import HandoffReadinessState
from glassbox.core.types_handoff import HandoffRedactionPosture
from glassbox.core.types_handoff import HandoffSourceKind
from glassbox.core.types_operator_flow import MaintenanceCueKind
from glassbox.core.types_operator_flow import NextActionEvidenceKind
from glassbox.core.types_operator_flow import NextActionKind
from glassbox.core.types_operator_flow import NextActionPriority
from glassbox.core.types_operator_flow import NextActionSafetyClass
from glassbox.core.types_operator_flow import NextActionSeverity
from glassbox.core.types_operator_flow import NextActionSurface
from glassbox.core.types_operator_flow import NextActionTargetKind
from glassbox.core.types_operator_flow import OperatorQueueDedupeScope
from glassbox.core.types_operator_flow import OperatorQueueDismissalPolicy
from glassbox.core.types_operator_flow import OperatorQueueFamily
from glassbox.core.types_operator_flow import OperatorQueueState
from glassbox.core.types_verification_plan import VerificationCheckKind
from glassbox.core.types_verification_plan import VerificationFailureCategory
from glassbox.core.types_verification_plan import VerificationPlanLifecycleState
from glassbox.core.types_verification_plan import VerificationPlanSource

__all__ = [
    "ApprovalMode",
    "ApprovalDecision",
    "ApprovalId",
    "ApprovalRequested",
    "ApprovalResolved",
    "ApprovalStatus",
    "AutonomyBudget",
    "AutonomyBudgetPostureRecord",
    "AutonomyBudgetRemaining",
    "AutonomyBudgetUsage",
    "AutonomyEscalationReason",
    "AutonomyMode",
    "AutonomySelection",
    "AssistantMessageCompleted",
    "AssistantMessageDelta",
    "AssistantMessageStarted",
    "ArtifactId",
    "BackgroundJobAbandoned",
    "BackgroundJobCancellationRequested",
    "BackgroundJobCancelled",
    "BackgroundJobClaimed",
    "BackgroundJobCompleted",
    "BackgroundJobCreated",
    "BackgroundJobFailed",
    "BackgroundJobFailureKind",
    "BackgroundJobHeartbeat",
    "BackgroundJobId",
    "BackgroundJobKind",
    "BackgroundJobPaused",
    "BackgroundJobProgressRecorded",
    "BackgroundJobRecord",
    "BackgroundJobRecoveryReason",
    "BackgroundJobRecoveryRecorded",
    "BackgroundJobRetryExhausted",
    "BackgroundJobRetryRequested",
    "BackgroundJobStarted",
    "BackgroundJobState",
    "BranchCandidateExecuted",
    "BranchCandidateForked",
    "BranchCandidateId",
    "BranchCandidateNeedsReview",
    "BranchCandidatePlanned",
    "BranchCandidateRecord",
    "BranchCandidateRejected",
    "BranchCandidateSelected",
    "BranchCandidateStatus",
    "BranchCandidateVerificationStatus",
    "BranchCandidateVerified",
    "BranchCandidatesCompared",
    "BranchSearchAbandoned",
    "BranchSearchId",
    "BranchSearchRecord",
    "BranchSearchStarted",
    "BranchSearchStatus",
    "BudgetDecisionRecorded",
    "BudgetExhausted",
    "BudgetOverrideId",
    "BudgetOverrideRequested",
    "BudgetOverrideResolved",
    "CancellationAcknowledged",
    "CancellationFailed",
    "CancellationRequested",
    "ChangesetArchived",
    "ChangesetCandidateAdopted",
    "ChangesetCreated",
    "ChangesetId",
    "ChangesetInventoryFreshness",
    "ChangesetInventoryRecord",
    "ChangesetInventoryRefreshed",
    "ChangesetReadinessDecided",
    "ChangesetReadinessKind",
    "ChangesetReadinessRecord",
    "ChangesetReadinessState",
    "ChangesetRecord",
    "ChangesetRiskLevel",
    "ChangesetReviewBriefRecord",
    "ChangesetReviewBriefCreated",
    "ChangesetSourceAttached",
    "ChangesetSourceKind",
    "ChangesetSourceRecord",
    "ChangesetVerificationPostureRecord",
    "ChangesetVerificationPostureUpdated",
    "ChangesetVerificationState",
    "CheckpointAbsenceReason",
    "CheckpointAbsenceRecord",
    "ClaimSupport",
    "ClaimSupportState",
    "CommandPurpose",
    "CommandReviewRelevance",
    "CommandEnvironmentSummary",
    "CommandToolchainVersion",
    "ContextCompactionCreated",
    "ContextCompactionFreshnessChanged",
    "ContextCompactionFreshness",
    "ContextCompactionId",
    "ContextCompactionRecord",
    "ContextCompactionScope",
    "ContinuationWindowExpired",
    "ContinuationWindowRequested",
    "ContinuationWindowResolved",
    "ErrorRecorded",
    "EventId",
    "EventEnvelope",
    "EventPayload",
    "EventPayloadType",
    "EvidenceGraph",
    "EvidenceGraphConfidence",
    "EvidenceGraphEdge",
    "EvidenceGraphEdgeKind",
    "EvidenceGraphFreshness",
    "EvidenceGraphMissingEvidence",
    "EvidenceGraphNode",
    "EvidenceGraphNodeKind",
    "EvidenceGraphProvenance",
    "EvidenceGraphRedactionStatus",
    "EvidenceGraphVisibility",
    "ForkedSession",
    "HandoffCompatibilityState",
    "HandoffCompatibilitySummary",
    "HandoffDigestSummary",
    "HandoffEvidenceFreshness",
    "HandoffIntent",
    "HandoffLabel",
    "HandoffLabelMetadataPosture",
    "HandoffLabelSource",
    "HandoffLocalOnlySummary",
    "HandoffPackageKind",
    "HandoffPackageManifest",
    "HandoffReadiness",
    "HandoffReadinessReason",
    "HandoffReadinessReasonKind",
    "HandoffReadinessState",
    "HandoffRedactionPosture",
    "HandoffRedactionSummary",
    "HandoffSafeCommand",
    "HandoffSourceKind",
    "HandoffSourceRef",
    "InheritedTranscriptMessage",
    "LongRunPhase",
    "LongRunPhaseChanged",
    "LongRunPhaseState",
    "LongRunStatusRecord",
    "MaintenanceCue",
    "MaintenanceCueKind",
    "ManualEvidenceArchived",
    "ManualEvidenceAttached",
    "ManualEvidenceFreshness",
    "ManualEvidenceId",
    "ManualEvidenceKind",
    "ManualEvidenceRecord",
    "ManualEvidenceRedactionStatus",
    "ManualEvidenceRejected",
    "ManualEvidenceState",
    "ManualEvidenceSuperseded",
    "ManualEvidenceTargetKind",
    "MessagePart",
    "MessageId",
    "ModelCallCompleted",
    "ModelCallStarted",
    "ModelToolCallRequested",
    "NextAction",
    "NextActionCommandRecipe",
    "NextActionEvidenceKind",
    "NextActionEvidenceRef",
    "NextActionKind",
    "NextActionPriority",
    "NextActionSafetyClass",
    "NextActionSeverity",
    "NextActionSurface",
    "NextActionTarget",
    "NextActionTargetKind",
    "OperatorQueueDedupeKey",
    "OperatorQueueDedupeScope",
    "OperatorQueueDismissalPolicy",
    "OperatorQueueEvidenceSummary",
    "OperatorQueueFamily",
    "OperatorQueueItem",
    "OperatorQueueState",
    "PauseWindowCancelled",
    "PauseWindowId",
    "PauseWindowPolicy",
    "PauseWindowScheduled",
    "PauseWindowTriggered",
    "PolicyDecision",
    "PolicyDecisionTrace",
    "ProjectionHealth",
    "ProviderRecoveryAction",
    "ProviderRecoveryKind",
    "ProviderRecoveryRecord",
    "ProviderRecoveryRecorded",
    "QuietWindowPolicy",
    "QuestionId",
    "RecoveryDecision",
    "RecoveryDecisionId",
    "RecoveryDecisionRecorded",
    "ReviewFeedbackArchived",
    "ReviewFeedbackCreated",
    "ReviewFeedbackDisposition",
    "ReviewFeedbackDispositionUpdated",
    "ReviewFeedbackFixupInventoryAttached",
    "ReviewFeedbackFixupInventoryRecord",
    "ReviewFeedbackFixupPathRecord",
    "ReviewFeedbackFixupPathSummary",
    "ReviewFeedbackId",
    "ReviewFeedbackKind",
    "ReviewFeedbackProvenance",
    "ReviewFeedbackReopened",
    "ReviewFeedbackResolved",
    "ReviewFeedbackRiskAccepted",
    "ReviewFeedbackRecord",
    "ReviewFeedbackScopeAttached",
    "ReviewFeedbackScopeKind",
    "ReviewFeedbackScopeRecord",
    "ReviewFixupSourceKind",
    "ReviewResponseState",
    "RepositoryIntelligenceCommandRecipe",
    "RepositoryIntelligenceCommandRisk",
    "RepositoryIntelligenceConfidence",
    "RepositoryIntelligenceMemoryReference",
    "RepositoryIntelligenceOwnershipHint",
    "RepositoryIntelligencePackageBoundary",
    "RepositoryIntelligencePackageKind",
    "RepositoryIntelligencePathHint",
    "RepositoryIntelligencePathKind",
    "RepositoryIntelligenceReleaseSurface",
    "RepositoryIntelligenceReleaseSurfaceKind",
    "RepositoryIntelligenceSourceManifest",
    "RepositoryIntelligenceSubsystem",
    "RepositoryIndexEntry",
    "RepositoryIndexEntityKind",
    "RepositoryIndexFreshness",
    "RepositoryIndexProvenance",
    "RepositoryIndexSnapshot",
    "RepositoryIndexSourceType",
    "ResumeOutcomeRecorded",
    "ResumeOutcomeStatus",
    "ResolvedForkPoint",
    "ReplayArtifactRecorded",
    "RuntimeNoteRecord",
    "RuntimeNoteRecorded",
    "SessionCompleted",
    "SessionFailed",
    "SessionId",
    "SessionConfig",
    "SessionRecord",
    "SessionResumed",
    "SessionStarted",
    "SessionStatus",
    "SessionState",
    "TaskAbandoned",
    "TaskBlockedReason",
    "TaskCancelled",
    "TaskCheckpointCreated",
    "TaskCheckpointId",
    "TaskCheckpointRecord",
    "TaskCreated",
    "TaskId",
    "TaskPaused",
    "TaskPlanProposed",
    "TaskPlanRevised",
    "TaskPlanSnapshot",
    "TaskPlanStatus",
    "TaskRecord",
    "TaskResumed",
    "TaskStatusChanged",
    "TaskStepCompleted",
    "TaskStepFailed",
    "TaskStepId",
    "TaskStepProposal",
    "TaskStepRecord",
    "TaskStepSkipped",
    "TaskStepStarted",
    "TaskStepStatus",
    "TaskVerificationCompleted",
    "TaskVerificationFailed",
    "TaskVerificationId",
    "TaskVerificationLedgerRecord",
    "TaskVerificationLedgerSummary",
    "TaskVerificationPlanned",
    "TaskVerificationRecord",
    "TaskVerificationResidualRiskAccepted",
    "TaskVerificationRetried",
    "TaskVerificationSkipped",
    "TaskVerificationStarted",
    "TaskVerificationStreamed",
    "TaskVerificationStatus",
    "ToolCallId",
    "ToolArtifactRecorded",
    "ToolAttemptHeartbeat",
    "ToolAttemptId",
    "ToolAttemptRetryClassification",
    "ToolAttemptStatus",
    "ToolAttemptRecord",
    "ToolCallRecord",
    "ToolExecutionCompleted",
    "ToolExecutionCancelled",
    "ToolExecutionStarted",
    "ToolOutputChunk",
    "ToolExecutionStatus",
    "TranscriptMessageImported",
    "TranscriptMessage",
    "TurnId",
    "TurnCompleted",
    "TurnCancelled",
    "TurnFailed",
    "TurnRecoveryPosture",
    "TurnRecoveryState",
    "TurnStarted",
    "TurnStatus",
    "TurnStatusChanged",
    "UserAnswerProvided",
    "UserMessageReceived",
    "UserQuestionAsked",
    "VerificationCheckKind",
    "VerificationFailureCategory",
    "VerificationFailureDigest",
    "VerificationPlan",
    "VerificationPlanEntry",
    "VerificationPlanLifecycleState",
    "VerificationPlanSource",
    "WorktreeCleanupRecorded",
    "WorktreeCreated",
    "WorktreeId",
    "WorktreeSourceKind",
    "WorktreeState",
    "WorktreeStatusRecorded",
    "WorkspaceMemoryConfirmed",
    "WorkspaceMemoryCandidateRejected",
    "WorkspaceMemoryCreated",
    "WorkspaceMemoryEntry",
    "WorkspaceMemoryId",
    "WorkspaceMemoryImported",
    "WorkspaceMemoryInvalidated",
    "WorkspaceMemoryKind",
    "WorkspaceMemoryProvenance",
    "WorkspaceMemoryPruned",
    "WorkspaceMemorySourceType",
    "WorkspaceMemoryState",
    "WorkspaceMemoryUpdated",
    "WorkspaceMemoryUsedInContext",
    "new_approval_id",
    "new_artifact_id",
    "new_background_job_id",
    "new_branch_candidate_id",
    "new_branch_search_id",
    "new_budget_override_id",
    "new_changeset_id",
    "new_context_compaction_id",
    "new_event_id",
    "new_manual_evidence_id",
    "new_message_id",
    "new_pause_window_id",
    "new_question_id",
    "new_recovery_decision_id",
    "new_review_feedback_id",
    "new_session_id",
    "new_task_checkpoint_id",
    "new_task_id",
    "new_task_step_id",
    "new_task_verification_id",
    "new_tool_attempt_id",
    "new_tool_call_id",
    "new_turn_id",
    "new_worktree_id",
    "new_workspace_memory_id",
]
