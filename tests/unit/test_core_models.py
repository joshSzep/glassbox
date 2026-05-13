"""Unit tests for Glassbox core Pydantic models."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from glassbox.core import AutonomyBudget
from glassbox.core import ClaimSupport
from glassbox.core import ClaimSupportState
from glassbox.core import EvidenceGraph
from glassbox.core import EvidenceGraphConfidence
from glassbox.core import EvidenceGraphEdge
from glassbox.core import EvidenceGraphEdgeKind
from glassbox.core import EvidenceGraphFreshness
from glassbox.core import EvidenceGraphMissingEvidence
from glassbox.core import EvidenceGraphNode
from glassbox.core import EvidenceGraphNodeKind
from glassbox.core import EvidenceGraphProvenance
from glassbox.core import EvidenceGraphRedactionStatus
from glassbox.core import EvidenceGraphVisibility
from glassbox.core import ForkedSession
from glassbox.core import InheritedTranscriptMessage
from glassbox.core import MessagePart
from glassbox.core import NextAction
from glassbox.core import NextActionCommandRecipe
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSafetyClass
from glassbox.core import NextActionSeverity
from glassbox.core import NextActionSurface
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import PolicyDecision
from glassbox.core import RepositoryIndexEntityKind
from glassbox.core import RepositoryIndexEntry
from glassbox.core import RepositoryIndexFreshness
from glassbox.core import RepositoryIndexProvenance
from glassbox.core import RepositoryIndexSnapshot
from glassbox.core import RepositoryIndexSourceType
from glassbox.core import ResolvedForkPoint
from glassbox.core import SessionConfig
from glassbox.core import SessionRecord
from glassbox.core import SessionState
from glassbox.core import SessionStatus
from glassbox.core import TaskBlockedReason
from glassbox.core import TaskPlanSnapshot
from glassbox.core import TaskStepProposal
from glassbox.core import TaskStepRecord
from glassbox.core import TaskStepStatus
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import TaskVerificationLedgerSummary
from glassbox.core import TaskVerificationRecord
from glassbox.core import TaskVerificationStatus
from glassbox.core import ToolCallRecord
from glassbox.core import ToolExecutionStatus
from glassbox.core import TranscriptMessage
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanSource
from glassbox.core import WorkspaceMemoryEntry
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import WorkspaceMemoryProvenance
from glassbox.core import WorkspaceMemorySourceType
from glassbox.core import WorkspaceMemoryState
from glassbox.core import new_approval_id
from glassbox.core import new_artifact_id
from glassbox.core import new_message_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.core import new_workspace_memory_id
from glassbox.runtime.next_actions import next_actions_from_summaries


def test_session_config_round_trip() -> None:
    config = SessionConfig(
        model_name="openai:gpt-5.4",
        cwd=Path("/tmp/glassbox"),
        approval_mode="confirm",
    )

    restored = SessionConfig.model_validate(config.model_dump(mode="python"))

    assert restored == config
    assert restored.approval_mode == "confirm"
    assert restored.dashboard_url is None


def test_operator_flow_models_and_types_keep_core_compatibility_exports() -> None:
    from glassbox.core.models import NextAction as models_next_action
    from glassbox.core.models_operator_flow import NextAction as owner_next_action
    from glassbox.core.types import NextActionPriority as types_priority
    from glassbox.core.types_operator_flow import NextActionPriority as owner_priority

    assert NextAction is owner_next_action
    assert models_next_action is owner_next_action
    assert NextActionPriority is owner_priority
    assert types_priority is owner_priority


def test_session_config_round_trip_preserves_dashboard_url() -> None:
    config = SessionConfig(
        model_name="openai:gpt-5.4",
        cwd=Path("/tmp/glassbox"),
        approval_mode="confirm",
        dashboard_url="http://127.0.0.1:8765/",
    )

    restored = SessionConfig.model_validate(config.model_dump(mode="python"))

    assert restored == config
    assert restored.dashboard_url == "http://127.0.0.1:8765/"


def test_session_config_round_trip_preserves_lineage_metadata() -> None:
    config = SessionConfig(
        model_name="openai:gpt-5.4",
        cwd=Path("/tmp/glassbox"),
        approval_mode="confirm",
        parent_session_id=new_session_id(),
        forked_from_turn_id=new_turn_id(),
        forked_from_sequence=12,
        branch_label="investigate-alt-path",
    )

    restored = SessionConfig.model_validate(config.model_dump(mode="python"))

    assert restored == config


def test_session_record_round_trip_preserves_lineage_metadata() -> None:
    record = SessionRecord(
        session_id=new_session_id(),
        status=SessionStatus.RUNNING,
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
        updated_at=datetime(2026, 4, 16, 0, 5, tzinfo=UTC),
        cwd=Path("/tmp/glassbox"),
        model_name="openai:gpt-5.4",
        approval_mode="confirm",
        last_sequence=4,
        parent_session_id=new_session_id(),
        forked_from_turn_id=new_turn_id(),
        forked_from_sequence=3,
        branch_label="alt-branch",
    )

    restored = SessionRecord.model_validate(record.model_dump(mode="python"))

    assert restored == record


def test_session_state_round_trip() -> None:
    state = SessionState(
        session_id=new_session_id(),
        status=SessionStatus.RUNNING,
        current_turn_id=new_turn_id(),
        last_sequence=5,
        pending_approval_id=new_approval_id(),
    )

    restored = SessionState.model_validate(state.model_dump(mode="python"))

    assert restored == state


def test_transcript_message_round_trip() -> None:
    message = TranscriptMessage(
        message_id=new_message_id(),
        role="assistant",
        parts=[MessagePart(kind="text", text="hello")],
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )

    restored = TranscriptMessage.model_validate(message.model_dump(mode="python"))

    assert restored == message


def test_workspace_memory_entry_validates_provenance_and_state() -> None:
    session_id = new_session_id()
    memory = WorkspaceMemoryEntry(
        memory_id=new_workspace_memory_id(),
        session_id=session_id,
        kind=WorkspaceMemoryKind.CONVENTION,
        state=WorkspaceMemoryState.ACTIVE,
        content="Use uv run pytest for backend validation.",
        summary="backend tests use uv",
        provenance=WorkspaceMemoryProvenance(
            source_type=WorkspaceMemorySourceType.SESSION_EVENT,
            session_id=session_id,
            source_sequence=4,
            source_label="operator confirmed note",
        ),
        created_at=datetime(2026, 4, 29, tzinfo=UTC),
        updated_at=datetime(2026, 4, 29, tzinfo=UTC),
        tags=["testing", "commands"],
        last_sequence=5,
    )

    restored = WorkspaceMemoryEntry.model_validate(memory.model_dump(mode="python"))

    assert restored == memory
    assert restored.provenance.session_id == session_id


def test_workspace_memory_provenance_requires_source_links() -> None:
    with pytest.raises(ValidationError):
        WorkspaceMemoryProvenance(
            source_type=WorkspaceMemorySourceType.SESSION_EVENT,
            session_id=new_session_id(),
        )

    with pytest.raises(ValidationError):
        WorkspaceMemoryProvenance(source_type=WorkspaceMemorySourceType.ARTIFACT)

    provenance = WorkspaceMemoryProvenance(
        source_type=WorkspaceMemorySourceType.ARTIFACT,
        artifact_id=new_artifact_id(),
    )

    assert provenance.source_type == WorkspaceMemorySourceType.ARTIFACT


def test_next_action_round_trip_preserves_v16_priority_and_evidence() -> None:
    action = NextAction(
        action_id="changeset-refresh:cs_123",
        title="Refresh changeset inventory",
        summary="Refresh stale inventory before trusting verification posture.",
        kind=NextActionKind.REFRESH,
        priority=NextActionPriority.ACTION_NEEDED,
        severity=NextActionSeverity.HIGH,
        safety_class=NextActionSafetyClass.COMMAND_RECIPE,
        target=NextActionTarget(
            kind=NextActionTargetKind.CHANGESET,
            target_id="cs_123",
            label="Changeset cs_123",
        ),
        command=NextActionCommandRecipe(
            command=["glassbox", "changeset", "refresh", "cs_123", "--cwd", "."],
            display="glassbox changeset refresh cs_123 --cwd .",
            purpose="Refresh structured inventory evidence for this changeset.",
            requires_approval=False,
        ),
        supporting_evidence=[
            NextActionEvidenceRef(
                kind=NextActionEvidenceKind.ARTIFACT,
                ref_id="artifact:inventory",
                summary="latest inventory is stale",
                freshness="stale",
            )
        ],
        stale_evidence=[
            NextActionEvidenceRef(
                kind=NextActionEvidenceKind.VERIFICATION,
                ref_id="verification:pytest",
                summary="pytest evidence predates inventory",
                freshness="stale",
            )
        ],
        limitations=["recommended commands are not approval to execute"],
        recommended_surfaces=[NextActionSurface.CLI, NextActionSurface.DASHBOARD],
    )

    restored = NextAction.model_validate(action.model_dump(mode="python"))

    assert restored == action
    assert restored.priority == NextActionPriority.ACTION_NEEDED
    assert restored.command is not None
    assert restored.command.expected_exit_codes == [0]


def test_next_action_rejects_command_without_command_safety_class() -> None:
    with pytest.raises(ValidationError):
        NextAction(
            action_id="bad-action",
            title="Run hidden command",
            summary="This shape should be rejected.",
            kind=NextActionKind.VERIFY,
            priority=NextActionPriority.RECOMMENDED,
            safety_class=NextActionSafetyClass.READ_ONLY,
            target=NextActionTarget(kind=NextActionTargetKind.TASK),
            command=NextActionCommandRecipe(
                command=["uv", "run", "pytest"],
                display="uv run pytest",
                purpose="Run tests.",
            ),
        )


def test_next_action_compatibility_helpers_wrap_legacy_strings() -> None:
    actions = next_actions_from_summaries(
        ["Inspect session", "Inspect session", "Resolve pending approval"],
        target_kind=NextActionTargetKind.SESSION,
        target_id="session_123",
        priority=NextActionPriority.ACTION_NEEDED,
    )

    assert [action.summary for action in actions] == [
        "Inspect session",
        "Resolve pending approval",
    ]
    assert actions[0].target.kind == NextActionTargetKind.SESSION
    assert actions[0].action_id.startswith("next-action:session:")


def test_evidence_graph_round_trip_preserves_claim_support() -> None:
    generated_at = datetime(2026, 5, 10, tzinfo=UTC)
    graph = EvidenceGraph(
        graph_id="graph:changeset:cs_123",
        target=NextActionTarget(
            kind=NextActionTargetKind.CHANGESET,
            target_id="cs_123",
        ),
        generated_at=generated_at,
        nodes=[
            EvidenceGraphNode(
                node_id="artifact:inventory",
                kind=EvidenceGraphNodeKind.ARTIFACT,
                title="Change inventory",
                summary="Inventory covers three changed paths.",
                provenance=[
                    EvidenceGraphProvenance(
                        source_kind="artifact",
                        source_id="artifact:inventory",
                        source_path=".glassbox/artifacts/inventory.json",
                        summary="managed changeset inventory artifact",
                    )
                ],
                freshness=EvidenceGraphFreshness.FRESH,
                confidence=EvidenceGraphConfidence.HIGH,
                redaction_status=EvidenceGraphRedactionStatus.SAFE_SUMMARY,
                visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
            ),
            EvidenceGraphNode(
                node_id="claim:verification-ready",
                kind=EvidenceGraphNodeKind.CLAIM,
                title="Verification ready",
                summary="Verification posture can be inspected.",
                freshness=EvidenceGraphFreshness.UNKNOWN,
                confidence=EvidenceGraphConfidence.MEDIUM,
            ),
        ],
        edges=[
            EvidenceGraphEdge(
                edge_id="edge:inventory-supports-claim",
                kind=EvidenceGraphEdgeKind.SUPPORTS,
                from_node_id="artifact:inventory",
                to_node_id="claim:verification-ready",
                summary="fresh inventory supports verification readiness scope",
                confidence=EvidenceGraphConfidence.HIGH,
            )
        ],
        claims=[
            ClaimSupport(
                claim_id="claim:verification-ready",
                title="Verification ready",
                summary="Fresh inventory supports verification readiness scope.",
                state=ClaimSupportState.SUPPORTED,
                confidence=EvidenceGraphConfidence.HIGH,
                supporting_edge_ids=["edge:inventory-supports-claim"],
                visibility=EvidenceGraphVisibility.REVIEWER_SAFE,
            )
        ],
    )

    restored = EvidenceGraph.model_validate(graph.model_dump(mode="python"))

    assert restored == graph
    assert restored.claims[0].state == ClaimSupportState.SUPPORTED
    assert restored.nodes[0].visibility == EvidenceGraphVisibility.REVIEWER_SAFE


def test_evidence_graph_rejects_edges_to_missing_nodes() -> None:
    with pytest.raises(ValidationError):
        EvidenceGraph(
            graph_id="graph:bad",
            target=NextActionTarget(kind=NextActionTargetKind.TASK),
            generated_at=datetime(2026, 5, 10, tzinfo=UTC),
            nodes=[
                EvidenceGraphNode(
                    node_id="claim:ready",
                    kind=EvidenceGraphNodeKind.CLAIM,
                    title="Ready",
                    summary="Ready claim.",
                )
            ],
            edges=[
                EvidenceGraphEdge(
                    edge_id="edge:missing",
                    kind=EvidenceGraphEdgeKind.SUPPORTS,
                    from_node_id="artifact:missing",
                    to_node_id="claim:ready",
                    summary="missing artifact cannot support claim",
                )
            ],
        )


def test_evidence_graph_missing_evidence_can_link_safe_next_action() -> None:
    action = next_actions_from_summaries(
        ["glassbox changeset verification-plan CHANGESET --cwd ."],
        target_kind=NextActionTargetKind.CHANGESET,
        target_id="cs_123",
        kind=NextActionKind.VERIFY,
        priority=NextActionPriority.RECOMMENDED,
    )[0]

    missing = EvidenceGraphMissingEvidence(
        missing_id="missing:verification-plan",
        kind=EvidenceGraphNodeKind.VERIFICATION_CHECK,
        summary="No retained verification plan exists yet.",
        safe_next_actions=[action],
    )

    restored = EvidenceGraphMissingEvidence.model_validate(
        missing.model_dump(mode="python")
    )

    assert restored.safe_next_actions[0].kind == NextActionKind.VERIFY


def test_invalidated_workspace_memory_requires_reason() -> None:
    with pytest.raises(ValidationError):
        WorkspaceMemoryEntry(
            memory_id=new_workspace_memory_id(),
            session_id=new_session_id(),
            kind=WorkspaceMemoryKind.FACT,
            state=WorkspaceMemoryState.INVALIDATED,
            content="Old command no longer works.",
            provenance=WorkspaceMemoryProvenance(
                source_type=WorkspaceMemorySourceType.OPERATOR,
                source_label="manual note",
            ),
            created_at=datetime(2026, 4, 29, tzinfo=UTC),
            updated_at=datetime(2026, 4, 29, tzinfo=UTC),
            last_sequence=7,
        )


def test_repository_index_snapshot_validates_entries_and_provenance() -> None:
    timestamp = datetime(2026, 4, 29, tzinfo=UTC)
    entry = RepositoryIndexEntry(
        entry_id="command:pytest",
        kind=RepositoryIndexEntityKind.COMMAND,
        name="pytest",
        summary="Backend tests run through uv.",
        path=Path("pyproject.toml"),
        provenance=[
            RepositoryIndexProvenance(
                source_type=RepositoryIndexSourceType.MANIFEST,
                path=Path("pyproject.toml"),
                line_start=1,
                line_end=20,
            )
        ],
        tags=["validation"],
        updated_at=timestamp,
    )

    snapshot = RepositoryIndexSnapshot(
        workspace_root=Path("/tmp/glassbox"),
        status=RepositoryIndexFreshness.FRESH,
        built_at=timestamp,
        source_digest="a" * 64,
        entries=[entry],
    )

    restored = RepositoryIndexSnapshot.model_validate(
        snapshot.model_dump(mode="python")
    )

    assert restored == snapshot
    assert restored.entries[0].provenance[0].line_end == 20


def test_repository_index_rejects_ambiguous_contract_shapes() -> None:
    timestamp = datetime(2026, 4, 29, tzinfo=UTC)
    provenance = RepositoryIndexProvenance(
        source_type=RepositoryIndexSourceType.FILE_SYSTEM,
        path=Path("src/glassbox/__init__.py"),
    )

    with pytest.raises(ValidationError):
        RepositoryIndexProvenance(
            source_type=RepositoryIndexSourceType.STATIC_ANALYSIS,
            path=Path("src/glassbox/core/models.py"),
            line_start=10,
            line_end=9,
        )

    with pytest.raises(ValidationError):
        RepositoryIndexEntry(
            entry_id="symbol:missing",
            kind=RepositoryIndexEntityKind.SYMBOL,
            name="missing",
            path=Path("src/glassbox/core/models.py"),
            provenance=[provenance],
            updated_at=timestamp,
        )

    with pytest.raises(ValidationError):
        RepositoryIndexSnapshot(
            workspace_root=Path("/tmp/glassbox"),
            status=RepositoryIndexFreshness.FAILED,
        )

    with pytest.raises(ValidationError):
        RepositoryIndexSnapshot(
            workspace_root=Path("/tmp/glassbox"),
            status=RepositoryIndexFreshness.FRESH,
            built_at=timestamp,
            entries=[
                RepositoryIndexEntry(
                    entry_id="file:duplicate",
                    kind=RepositoryIndexEntityKind.FILE,
                    name="models.py",
                    path=Path("src/glassbox/core/models.py"),
                    provenance=[provenance],
                    updated_at=timestamp,
                ),
                RepositoryIndexEntry(
                    entry_id="file:duplicate",
                    kind=RepositoryIndexEntityKind.FILE,
                    name="events.py",
                    path=Path("src/glassbox/core/events.py"),
                    provenance=[provenance],
                    updated_at=timestamp,
                ),
            ],
        )


def test_resolved_fork_point_round_trip() -> None:
    fork_point = ResolvedForkPoint(
        parent_session_id=new_session_id(),
        turn_id=new_turn_id(),
        sequence=8,
        inherited_messages=[
            InheritedTranscriptMessage(
                source_message_id=new_message_id(),
                source_turn_id=new_turn_id(),
                role="assistant",
                parts=[MessagePart(kind="text", text="prior answer")],
                created_at=datetime(2026, 4, 16, 12, 4, tzinfo=UTC),
            )
        ],
    )

    restored = ResolvedForkPoint.model_validate(fork_point.model_dump(mode="python"))

    assert restored == fork_point


def test_forked_session_round_trip() -> None:
    forked_session = ForkedSession(
        child_session_id=new_session_id(),
        parent_session_id=new_session_id(),
        forked_from_turn_id=new_turn_id(),
        forked_from_sequence=11,
        branch_label="alt-branch",
        inherited_message_count=2,
        last_sequence=3,
    )

    restored = ForkedSession.model_validate(forked_session.model_dump(mode="python"))

    assert restored == forked_session


def test_tool_call_record_round_trip() -> None:
    record = ToolCallRecord(
        tool_call_id=new_tool_call_id(),
        turn_id=new_turn_id(),
        tool_name="read_file",
        status=ToolExecutionStatus.REQUESTED,
        summary="Queued for execution",
    )

    restored = ToolCallRecord.model_validate(record.model_dump(mode="python"))

    assert restored == record


def test_policy_decision_round_trip() -> None:
    decision = PolicyDecision(
        allowed=True,
        requires_approval=False,
        reason="Read-only operation within workspace",
        outcome="allow",
        risk_level="read_only",
        source_kind="default",
        source_label="read_only",
    )

    restored = PolicyDecision.model_validate(decision.model_dump(mode="python"))

    assert restored == decision


def test_autonomy_budget_rejects_contradictory_risk_limits() -> None:
    with pytest.raises(ValidationError):
        AutonomyBudget(
            max_steps=4,
            max_tool_calls=10,
            max_write_operations=1,
            max_command_operations=0,
            max_wall_clock_seconds=300,
            max_verification_attempts=1,
            max_branch_attempts=0,
            max_artifact_bytes=1000,
            allowed_risk_buckets=["read_only"],
        )

    with pytest.raises(ValidationError):
        AutonomyBudget(
            max_steps=4,
            max_tool_calls=10,
            max_write_operations=0,
            max_command_operations=0,
            max_wall_clock_seconds=300,
            max_verification_attempts=1,
            max_branch_attempts=0,
            max_artifact_bytes=1000,
            allowed_risk_buckets=["read_only", "command"],
        )


def test_task_plan_snapshot_round_trip() -> None:
    task_id = new_task_id()
    step_id = new_task_step_id()
    plan = TaskPlanSnapshot(
        task_id=task_id,
        title="Add task models",
        goal="Make task plans durable",
        steps=[
            TaskStepProposal(
                step_id=step_id,
                title="Define event payloads",
                description="Add core task-plan event payloads",
                order=0,
            )
        ],
    )

    restored = TaskPlanSnapshot.model_validate(plan.model_dump(mode="python"))

    assert restored == plan
    assert restored.status == "proposed"


def test_task_query_records_round_trip() -> None:
    task_id = new_task_id()
    step_id = new_task_step_id()
    step = TaskStepRecord(
        task_id=task_id,
        step_id=step_id,
        title="Define projection",
        order=1,
        status=TaskStepStatus.PENDING,
        blocked_reason=TaskBlockedReason.AWAITING_APPROVAL,
    )
    verification = TaskVerificationRecord(
        task_id=task_id,
        verification_id=new_task_verification_id(),
        step_id=step_id,
        status=TaskVerificationStatus.PLANNED,
        check_name="pytest",
    )
    ledger = TaskVerificationLedgerRecord(
        session_id=new_session_id(),
        task_id=task_id,
        verification_id=new_task_verification_id(),
        step_id=step_id,
        status=TaskVerificationStatus.PASSED,
        check_name="pytest",
        kind=VerificationCheckKind.TEST,
        source=VerificationPlanSource.OPERATOR,
        command=["uv", "run", "pytest"],
        changed_paths=[Path("src/glassbox/runtime/verification.py")],
        attempt_count=1,
        latest_attempt=1,
        last_success_sequence=42,
        summary="tests passed",
        updated_at=datetime.now(UTC),
        last_sequence=42,
    )
    ledger_summary = TaskVerificationLedgerSummary(
        task_id=task_id,
        total_count=1,
        passed_count=1,
        failed_count=0,
        running_count=0,
        skipped_count=0,
        accepted_risk_count=0,
        latest_success_verification_id=ledger.verification_id,
        latest_success_check_name=ledger.check_name,
        latest_success_sequence=ledger.last_success_sequence,
        current_posture="verified",
    )

    assert TaskStepRecord.model_validate(step.model_dump(mode="python")) == step
    assert (
        TaskVerificationRecord.model_validate(verification.model_dump(mode="python"))
        == verification
    )
    assert (
        TaskVerificationLedgerRecord.model_validate(ledger.model_dump(mode="python"))
        == ledger
    )
    assert (
        TaskVerificationLedgerSummary.model_validate(
            ledger_summary.model_dump(mode="python")
        )
        == ledger_summary
    )


def test_task_step_proposal_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        TaskStepProposal(
            step_id=new_task_step_id(),
            title="",
            order=0,
        )


def test_session_state_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        SessionState.model_validate(
            {
                "session_id": new_session_id(),
                "status": "paused",
            }
        )


def test_session_state_rejects_negative_sequence() -> None:
    with pytest.raises(ValidationError):
        SessionState(
            session_id=new_session_id(),
            status=SessionStatus.IDLE,
            last_sequence=-1,
        )


def test_message_part_rejects_invalid_kind() -> None:
    with pytest.raises(ValidationError):
        MessagePart.model_validate({"kind": "markdown", "text": "hello"})


def test_transcript_message_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        TranscriptMessage.model_validate(
            {
                "message_id": new_message_id(),
                "role": "tool",
                "parts": [{"kind": "text", "text": "hello"}],
                "created_at": datetime(2026, 4, 16, tzinfo=UTC),
            }
        )


def test_session_config_rejects_invalid_approval_mode() -> None:
    with pytest.raises(ValidationError):
        SessionConfig(
            model_name="openai:gpt-5.4",
            cwd=Path("/tmp/glassbox"),
            approval_mode="invalid-mode",
        )


def test_session_config_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SessionConfig.model_validate(
            {
                "model_name": "openai:gpt-5.4",
                "cwd": "/tmp/glassbox",
                "approval_mode": "confirm",
                "unexpected": True,
            }
        )
