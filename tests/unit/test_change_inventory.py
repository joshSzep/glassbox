"""Tests for the change inventory artifact contract."""

from pathlib import Path

from glassbox.core import EventEnvelope
from glassbox.core import ModelToolCallRequested
from glassbox.core import TaskCheckpointCreated
from glassbox.core import TaskVerificationPlanned
from glassbox.core import ToolExecutionCompleted
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.runtime.change_inventory import CHANGE_INVENTORY_ARTIFACT_KIND
from glassbox.runtime.change_inventory import CHANGE_INVENTORY_REDACTION
from glassbox.runtime.change_inventory import ChangeInventoryLimits
from glassbox.runtime.change_inventory import change_inventory_artifact_json
from glassbox.runtime.change_inventory import change_inventory_from_diff_summary
from glassbox.runtime.change_inventory import change_inventory_provenance_from_events
from glassbox.tools.workflow import DiffFileSummary
from glassbox.tools.workflow import DiffSummaryArtifact
from glassbox.tools.workflow import DiffSummaryResult
from glassbox.tools.workflow import DiffSummaryScope
from glassbox.tools.workflow import PatchRiskSummary


def test_change_inventory_artifact_contract_from_diff_summary() -> None:
    diff_summary = DiffSummaryResult(
        scope=DiffSummaryScope.WORKSPACE,
        files=[
            DiffFileSummary(
                path="src/glassbox/runtime/change_inventory.py",
                change_kind="modified",
                insertions=20,
                deletions=1,
            ),
            DiffFileSummary(
                path="tests/unit/test_change_inventory.py",
                change_kind="untracked",
                insertions=8,
                deletions=0,
                test_file=True,
            ),
            DiffFileSummary(
                path="glassbox.profile.json",
                change_kind="modified",
                insertions=1,
                deletions=1,
                policy_sensitive=True,
            ),
        ],
    )

    artifact = change_inventory_from_diff_summary(diff_summary)
    payload = artifact.model_dump(mode="json")

    assert artifact.artifact_kind == CHANGE_INVENTORY_ARTIFACT_KIND
    assert artifact.redaction == CHANGE_INVENTORY_REDACTION
    assert artifact.raw_diff_included is False
    assert artifact.raw_file_contents_included is False
    assert artifact.summary.changed_path_count == 3
    assert artifact.summary.included_path_count == 3
    assert artifact.summary.test_path_count == 1
    assert artifact.summary.policy_sensitive_path_count == 1
    assert artifact.summary.risk_level == "high"
    assert artifact.summary.high_risk_path_count == 2
    assert artifact.summary.unresolved_risk_count == 3
    assert artifact.paths[1].staged_state == "untracked"
    assert artifact.paths[1].provenance_confidence == "unknown"
    assert "missing_provenance" in artifact.paths[1].risk_tags
    assert "policy_sensitive" in artifact.paths[2].risk_tags
    assert artifact.summary.provenance_unknown_path_count == 3
    assert artifact.summary.externally_modified_path_count == 2
    assert "raw diffs" in artifact.limitations[0]
    assert payload["schema_version"] == 1


def test_change_inventory_attaches_direct_and_inferred_provenance() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    checkpoint_id = new_task_checkpoint_id()
    task_id = new_task_id()
    verification_id = new_task_verification_id()
    diff_summary = DiffSummaryResult(
        scope=DiffSummaryScope.WORKSPACE,
        files=[
            DiffFileSummary(
                path="src/glassbox/runtime/change_inventory.py",
                change_kind="modified",
                insertions=20,
                deletions=1,
            ),
            DiffFileSummary(
                path="tests/unit/test_change_inventory.py",
                change_kind="modified",
                insertions=12,
                deletions=0,
                test_file=True,
            ),
            DiffFileSummary(
                path="docs/change-inventory.md",
                change_kind="modified",
                insertions=4,
                deletions=1,
                docs_file=True,
            ),
            DiffFileSummary(
                path="README.md",
                change_kind="modified",
                insertions=1,
                deletions=0,
            ),
        ],
    )
    events = [
        EventEnvelope(
            session_id=session_id,
            sequence=1,
            payload=ModelToolCallRequested(
                turn_id=turn_id,
                tool_call_id=tool_call_id,
                tool_name="apply_patch",
                arguments_json=(
                    '{"patch": "*** Update File: '
                    'src/glassbox/runtime/change_inventory.py"}'
                ),
            ),
        ),
        EventEnvelope(
            session_id=session_id,
            sequence=2,
            payload=TaskCheckpointCreated(
                checkpoint_id=checkpoint_id,
                objective="finish provenance",
                completed_step="attached test provenance",
                next_action="run tests",
                recovery_guidance="resume at validation",
                task_id=task_id,
                turn_id=turn_id,
                touched_files=["tests/unit/test_change_inventory.py"],
            ),
        ),
        EventEnvelope(
            session_id=session_id,
            sequence=3,
            payload=TaskVerificationPlanned(
                task_id=task_id,
                verification=VerificationPlanEntry(
                    verification_id=verification_id,
                    check_name="docs",
                    kind=VerificationCheckKind.COMMAND,
                    command=["pytest", "tests/unit/test_change_inventory.py"],
                    source=VerificationPlanSource.CHANGED_PATHS,
                    rationale="docs inventory changed",
                    changed_paths=[Path("docs/change-inventory.md")],
                ),
            ),
        ),
        EventEnvelope(
            session_id=session_id,
            sequence=4,
            payload=ToolExecutionCompleted(
                turn_id=turn_id,
                tool_call_id=tool_call_id,
                success=True,
                summary="Updated docs/change-inventory.md",
            ),
        ),
    ]

    artifact = change_inventory_from_diff_summary(
        diff_summary,
        provenance_events=events,
    )
    by_path = {entry.path: entry for entry in artifact.paths}

    assert (
        by_path["src/glassbox/runtime/change_inventory.py"].provenance_confidence
        == "direct"
    )
    assert (
        by_path["src/glassbox/runtime/change_inventory.py"].source_evidence_refs[0].kind
        == "tool_call"
    )
    assert (
        by_path["tests/unit/test_change_inventory.py"].source_evidence_refs[0].kind
        == "task_checkpoint"
    )
    assert by_path["docs/change-inventory.md"].provenance_confidence == "inferred"
    assert by_path["README.md"].provenance_confidence == "unknown"
    readme_note = by_path["README.md"].provenance_note
    assert readme_note is not None
    assert "manual or externally modified" in readme_note
    assert artifact.summary.provenance_direct_path_count == 2
    assert artifact.summary.provenance_inferred_path_count == 1
    assert artifact.summary.provenance_unknown_path_count == 1
    assert artifact.summary.risk_level == "high"
    assert (
        "runtime_schema"
        in by_path["src/glassbox/runtime/change_inventory.py"].risk_tags
    )
    assert "missing_provenance" in by_path["README.md"].risk_tags


def test_change_inventory_provenance_index_uses_candidate_paths_for_text_evidence() -> (
    None
):
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()

    provenance = change_inventory_provenance_from_events(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=7,
                payload=ToolExecutionCompleted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    success=True,
                    summary="verified src/glassbox/runtime/change_inventory.py",
                ),
            )
        ],
        candidate_paths=["src/glassbox/runtime/change_inventory.py"],
    )

    refs = provenance["src/glassbox/runtime/change_inventory.py"]
    assert refs[0].confidence == "inferred"
    assert refs[0].event_sequence == 7


def test_change_inventory_classifies_path_risk_from_patterns() -> None:
    artifact = change_inventory_from_diff_summary(
        DiffSummaryResult(
            scope=DiffSummaryScope.WORKSPACE,
            files=[
                DiffFileSummary(
                    path="docs/change-inventory.md",
                    change_kind="modified",
                    insertions=3,
                    deletions=1,
                    docs_file=True,
                ),
                DiffFileSummary(
                    path="uv.lock",
                    change_kind="modified",
                    insertions=900,
                    deletions=10,
                    generated=True,
                ),
                DiffFileSummary(
                    path="src/glassbox/llm/provider_config.py",
                    change_kind="modified",
                    insertions=4,
                    deletions=0,
                ),
            ],
        )
    )
    by_path = {entry.path: entry for entry in artifact.paths}

    assert artifact.summary.risk_level == "high"
    assert "docs" in by_path["docs/change-inventory.md"].risk_tags
    assert by_path["uv.lock"].risk_level == "high"
    assert {"generated", "large_change", "packaging_release"}.issubset(
        set(by_path["uv.lock"].risk_tags)
    )
    assert (
        "provider_security" in by_path["src/glassbox/llm/provider_config.py"].risk_tags
    )


def test_change_inventory_prefers_artifact_payload_and_path_limit() -> None:
    files = [
        DiffFileSummary(
            path=f"src/package_{index}/module.py",
            change_kind="modified",
            insertions=index,
            deletions=0,
        )
        for index in range(5)
    ]
    diff_summary = DiffSummaryResult(
        scope=DiffSummaryScope.WORKSPACE,
        files=files[:1],
        artifact_payload=DiffSummaryArtifact(
            scope=DiffSummaryScope.WORKSPACE,
            path_filters=[],
            risk_summary=PatchRiskSummary(touched_files=len(files)),
            files=files,
        ),
    )

    artifact = change_inventory_from_diff_summary(
        diff_summary,
        limits=ChangeInventoryLimits(max_paths=2),
    )

    assert artifact.summary.changed_path_count == 5
    assert artifact.summary.included_path_count == 2
    assert artifact.summary.omitted_path_count == 3
    assert artifact.truncated is True
    assert [entry.path for entry in artifact.paths] == [
        "src/package_0/module.py",
        "src/package_1/module.py",
    ]


def test_change_inventory_redacts_unsafe_paths_and_enforces_size_limit() -> None:
    diff_summary = DiffSummaryResult(
        scope=DiffSummaryScope.WORKSPACE,
        files=[
            DiffFileSummary(
                path="/Users/example/secret.txt",
                change_kind="modified",
                insertions=1,
                deletions=0,
            ),
            *[
                DiffFileSummary(
                    path=f"src/{index}/{'x' * 80}.py",
                    change_kind="modified",
                    insertions=1,
                    deletions=0,
                )
                for index in range(30)
            ],
        ],
    )

    artifact = change_inventory_from_diff_summary(
        diff_summary,
        limits=ChangeInventoryLimits(max_paths=31, max_json_bytes=4096),
    )
    content = change_inventory_artifact_json(artifact)

    assert artifact.paths[0].path == "<redacted-path>"
    assert artifact.size_limited is True
    assert artifact.summary.omitted_path_count > 0
    assert len(content.encode("utf-8")) <= 4096
