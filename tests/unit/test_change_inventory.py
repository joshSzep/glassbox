"""Tests for the change inventory artifact contract."""

from glassbox.runtime.change_inventory import CHANGE_INVENTORY_ARTIFACT_KIND
from glassbox.runtime.change_inventory import CHANGE_INVENTORY_REDACTION
from glassbox.runtime.change_inventory import ChangeInventoryLimits
from glassbox.runtime.change_inventory import change_inventory_artifact_json
from glassbox.runtime.change_inventory import change_inventory_from_diff_summary
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
    assert artifact.paths[1].staged_state == "untracked"
    assert artifact.paths[1].provenance_confidence == "unknown"
    assert "raw diffs" in artifact.limitations[0]
    assert payload["schema_version"] == 1


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
