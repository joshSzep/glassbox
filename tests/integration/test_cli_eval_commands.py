"""Integration tests for CLI eval commands."""

import json
import shutil
from pathlib import Path

import pytest

from glassbox.cli import main
from tests.integration.cli_test_support import _export_eval_bundle
from tests.integration.cli_test_support import _list_sessions
from tests.integration.cli_test_support import _run_baseline_session
from tests.integration.cli_test_support import _write_eval_case
from tests.integration.cli_test_support import _write_eval_coverage
from tests.integration.cli_test_support import _write_eval_impact
from tests.integration.cli_test_support import _write_eval_profiles


def test_cli_eval_run_reports_mixed_outcomes_and_writes_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    manifest_bundle_path = tmp_path / "evals" / "bundles" / "drift.manifest.json"
    manifest_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    manifest_payload["model_calls"][0]["manifest"]["prepared_turn"]["user_prompt"] = (
        "Unexpected prompt"
    )
    manifest_bundle_path.write_text(
        json.dumps(manifest_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke", "tooling"],
    )
    _write_eval_case(
        tmp_path,
        case_id="drift.manifest",
        title="Manifest drift",
        bundle_name=manifest_bundle_path.name,
        tags=["smoke", "provider-mode"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["replay_portability"],
            "verification_stages": ["release-candidate"],
        },
    )
    output_dir = tmp_path / "eval-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    manifest_case = next(
        case_payload
        for case_payload in summary["cases"]
        if case_payload["case_id"] == "drift.manifest"
    )
    manifest_artifact = json.loads(
        (output_dir / "drift.manifest.json").read_text(encoding="utf-8")
    )

    assert exit_code == 11
    assert "Selected cases: 2" in captured.out
    assert "Passed: 1" in captured.out
    assert "Failed: 1" in captured.out
    assert "drift.manifest: manifest drift (failed)" in captured.out
    assert "Triage: prepared turn drifted before model execution" in captured.out
    assert (
        "First reported change: prepared turn no longer matches recorded manifest"
        in captured.out
    )
    assert "Next inspect: Inspect the recorded prepared turn manifest" in captured.out
    assert "Owner: runtime.replay" in captured.out
    assert "Capabilities: replay_portability" in captured.out
    assert "Release stages: release-candidate" in captured.out
    assert str(output_dir.resolve()) in captured.out
    assert summary["selected_case_count"] == 2
    assert summary["passed_case_count"] == 1
    assert summary["failed_case_count"] == 1
    assert summary["exit_code"] == 11
    assert summary["outcome_counts"]["exact_match"] == 1
    assert summary["outcome_counts"]["manifest_drift"] == 1
    assert (
        manifest_case["triage_headline"]
        == "prepared turn drifted before model execution"
    )
    assert manifest_case["triage_first_relevant_change"] == (
        "prepared turn no longer matches recorded manifest"
    )
    assert manifest_case["triage_recommended_inspection_path"].startswith(
        "Inspect the recorded prepared turn manifest"
    )
    assert manifest_artifact["triage_headline"] == (
        "prepared turn drifted before model execution"
    )
    assert manifest_artifact["replay_result"]["triage"]["classification"] == (
        "manifest_drift"
    )
    for case_payload in summary["cases"]:
        assert Path(case_payload["artifact_path"]).is_file()


def test_cli_eval_run_supports_tag_filter_and_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    approval_bundle_path = tmp_path / "evals" / "bundles" / "approval.patch.json"
    shutil.copyfile(bundle_path, approval_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke", "tooling"],
    )
    _write_eval_case(
        tmp_path,
        case_id="approval.patch",
        title="Patch approval",
        bundle_name=approval_bundle_path.name,
        tags=["approval", "tooling"],
    )
    output_dir = tmp_path / "tagged-eval-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "--tag",
            "approval",
            "--json",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["selected_case_count"] == 1
    assert payload["passed_case_count"] == 1
    assert payload["failed_case_count"] == 0
    assert payload["cases"][0]["case_id"] == "approval.patch"
    assert payload["cases"][0]["passed"] is True
    assert Path(payload["summary_path"]).is_file()


def test_cli_eval_run_supports_profile_selection_and_tag_narrowing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke_bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    context_bundle_path = tmp_path / "evals" / "bundles" / "context.branch.json"
    shutil.copyfile(smoke_bundle_path, context_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=smoke_bundle_path.name,
        tags=["smoke", "tooling"],
        release_contract={
            "owner": "runtime.replay",
            "verification_stages": ["commit-time", "push-time"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="context.branch",
        title="Context branch smoke",
        bundle_name=context_bundle_path.name,
        tags=["smoke", "context"],
        release_contract={
            "owner": "runtime.context",
            "verification_stages": ["commit-time", "push-time"],
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            }
        ],
    )
    _write_eval_coverage(
        tmp_path,
        profiles=[
            {
                "capability_id": "branching",
                "title": "Branching",
                "criticality": "release-critical",
                "verification_stages": ["commit-time"],
                "expected_case_ids": ["context.branch"],
            }
        ],
    )
    output_dir = tmp_path / "profiled-eval-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "--profile",
            "commit-smoke",
            "--tag",
            "context",
            "--json",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["profile_id"] == "commit-smoke"
    assert payload["profile_verification_stage"] == "commit-time"
    assert payload["coverage_audit"]["covered_capability_count"] == 1
    assert payload["selected_case_count"] == 1
    assert payload["cases"][0]["case_id"] == "context.branch"


def test_cli_eval_run_uses_workspace_profile_verification_default(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    branch_bundle_path = tmp_path / "evals" / "bundles" / "context.branch.json"
    shutil.copyfile(bundle_path, branch_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke"],
    )
    _write_eval_case(
        tmp_path,
        case_id="context.branch",
        title="Branch context",
        bundle_name=branch_bundle_path.name,
        tags=["context"],
        release_contract={"verification_stages": ["commit-time"]},
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-context",
                "title": "Commit context",
                "verification_stage": "commit-time",
                "tags": ["context"],
                "blocking": True,
            }
        ],
    )
    (tmp_path / "glassbox.profile.json").write_text(
        json.dumps(
            {
                "profile_version": 1,
                "verification": {"eval_profile": "commit-context"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "workspace-profile-eval-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "--json",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["profile_id"] == "commit-context"
    assert payload["profile_verification_stage"] == "commit-time"
    assert payload["selected_case_count"] == 1
    assert payload["cases"][0]["case_id"] == "context.branch"


def test_cli_eval_audit_reports_uncovered_critical_capabilities(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke_bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    extra_bundle_path = tmp_path / "evals" / "bundles" / "smoke.extra.json"
    branch_bundle_path = tmp_path / "evals" / "bundles" / "branch.case.json"
    shutil.copyfile(smoke_bundle_path, extra_bundle_path)
    shutil.copyfile(smoke_bundle_path, branch_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=smoke_bundle_path.name,
        tags=["smoke"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["smoke_validation"],
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="smoke.extra",
        title="Extra smoke",
        bundle_name=extra_bundle_path.name,
        tags=["smoke"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["smoke_validation"],
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="branch.case",
        title="Branch case",
        bundle_name=branch_bundle_path.name,
        tags=["context"],
        release_contract={
            "owner": "runtime.context",
            "capabilities": ["branching"],
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            }
        ],
    )
    _write_eval_coverage(
        tmp_path,
        profiles=[
            {
                "capability_id": "smoke_validation",
                "title": "Smoke validation",
                "criticality": "release-critical",
                "verification_stages": ["commit-time"],
                "expected_case_ids": ["smoke.readme"],
            },
            {
                "capability_id": "branching",
                "title": "Branching",
                "criticality": "release-critical",
                "verification_stages": ["commit-time"],
                "expected_case_ids": ["branch.case"],
            },
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "audit",
            "--profile",
            "commit-smoke",
            "--json",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["uncovered_release_critical_capability_ids"] == ["branching"]
    assert payload["unmapped_case_ids"] == ["smoke.extra"]
    assert payload["redundant_case_ids"] == ["smoke.extra"]


def test_cli_eval_profiles_lists_live_provider_canary_track(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "blocking": True,
            },
            {
                "profile_id": "live-provider-canary",
                "title": "Live provider canary",
                "verification_stage": "advisory",
                "track": "live-provider-canary",
                "blocking": False,
                "tags": ["live-provider"],
            },
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "profile",
            "list",
            "--track",
            "live-provider-canary",
            "--json",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert [profile["profile_id"] for profile in payload] == ["live-provider-canary"]
    assert payload[0]["track"] == "live-provider-canary"
    assert payload[0]["blocking"] is False


def test_cli_eval_profile_show_reports_one_profile(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "description": "Fast blocking smoke coverage.",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
                "budget": {
                    "max_selected_case_count": 2,
                    "allow_unsupported_cases": False,
                    "promotion_policy": "Promote only cheap deterministic cases.",
                },
            },
            {
                "profile_id": "advisory-context",
                "title": "Advisory context",
                "verification_stage": "advisory",
                "blocking": False,
            },
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "profile",
            "show",
            "commit-smoke",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Profile: commit-smoke" in captured.out
    assert "Title: Commit smoke" in captured.out
    assert "Budget:" in captured.out
    assert "Max selected cases: 2" in captured.out
    assert "Promote only cheap deterministic cases." in captured.out
    assert "advisory-context" not in captured.out


def test_cli_eval_profile_show_supports_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "live-provider-canary",
                "title": "Live provider canary",
                "verification_stage": "advisory",
                "track": "live-provider-canary",
                "blocking": False,
                "tags": ["live-provider"],
            }
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "profile",
            "show",
            "live-provider-canary",
            "--json",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["profile_id"] == "live-provider-canary"
    assert payload["track"] == "live-provider-canary"
    assert payload["blocking"] is False


def test_cli_eval_case_list_filters_by_tag_and_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name="readme.json",
        tags=["smoke", "tooling"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["replay_portability"],
            "severity": "high",
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="approval.patch",
        title="Patch approval",
        bundle_name="patch.json",
        tags=["approval", "tooling"],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "case",
            "list",
            "--tag",
            "smoke",
            "--json",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert [case["case_id"] for case in payload] == ["smoke.readme"]
    assert payload[0]["title"] == "README smoke"
    assert payload[0]["release_contract"]["severity"] == "high"


def test_cli_eval_case_show_reports_manifest_details(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name="readme.json",
        tags=["smoke", "tooling"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["replay_portability"],
            "severity": "high",
            "verification_stages": ["commit-time", "push-time"],
        },
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "case",
            "show",
            "smoke.readme",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Case: smoke.readme" in captured.out
    assert "Title: README smoke" in captured.out
    assert "Owner: runtime.replay" in captured.out
    assert "Capabilities: replay_portability" in captured.out
    assert "Verification stages: commit-time, push-time" in captured.out


def test_cli_eval_recommend_reports_cases_profiles_and_reasons(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke_bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    context_bundle_path = tmp_path / "evals" / "bundles" / "context.branch.json"
    shutil.copyfile(smoke_bundle_path, context_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=smoke_bundle_path.name,
        tags=["smoke", "tooling"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["smoke_validation", "replay_portability"],
            "verification_stages": ["commit-time", "push-time"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="context.branch",
        title="Context branch",
        bundle_name=context_bundle_path.name,
        tags=["context"],
        release_contract={
            "owner": "runtime.context",
            "capabilities": ["branching"],
            "verification_stages": ["release-candidate"],
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
                "budget": {
                    "max_selected_case_count": 2,
                    "allow_advisory_cases": False,
                },
            },
            {
                "profile_id": "push-confirmation",
                "title": "Push confirmation",
                "verification_stage": "push-time",
                "tags": ["smoke"],
                "blocking": True,
                "budget": {
                    "max_selected_case_count": 2,
                    "max_recorded_model_call_count": 4,
                    "allow_advisory_cases": False,
                },
            },
            {
                "profile_id": "release-candidate",
                "title": "Release candidate",
                "verification_stage": "release-candidate",
                "blocking": True,
            },
        ],
    )
    _write_eval_coverage(
        tmp_path,
        profiles=[
            {
                "capability_id": "replay_portability",
                "title": "Replay portability",
                "criticality": "release-critical",
                "verification_stages": ["commit-time", "push-time"],
                "expected_case_ids": ["smoke.readme"],
            },
            {
                "capability_id": "branching",
                "title": "Branching",
                "criticality": "release-critical",
                "verification_stages": ["release-candidate"],
                "expected_case_ids": ["context.branch"],
            },
        ],
    )
    _write_eval_impact(
        tmp_path,
        rules=[
            {
                "rule_id": "runtime-replay",
                "title": "Replay runtime",
                "path_globs": ["src/glassbox/runtime/replay*.py"],
                "owners": ["runtime.replay"],
                "capabilities": ["replay_portability"],
            }
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "recommend",
            "src/glassbox/runtime/replay_execution.py",
            "--json",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["matched_rule_ids"] == ["runtime-replay"]
    assert payload["unmatched_paths"] == []
    assert [case["case_id"] for case in payload["cases"]] == ["smoke.readme"]
    assert payload["cases"][0]["confidence"] == "owner-derived"
    assert payload["cases"][0]["reasons"][0]["confidence"] == "owner-derived"
    assert payload["cases"][0]["reasons"][0]["group"] == "owner-derived-rule"
    assert "owner runtime.replay" in payload["cases"][0]["reasons"][0]["summary"]
    assert payload["cheapest_next_command"] == (
        "uv run glassbox eval run smoke.readme --cwd ."
    )
    assert [group["group"] for group in payload["reason_groups"]] == [
        "owner-derived-rule",
        "capability-derived-rule",
        "stage-derived-profile",
    ]
    assert [profile["profile_id"] for profile in payload["profiles"]] == [
        "commit-smoke",
        "push-confirmation",
    ]
    assert [
        surface["verification_stage"] for surface in payload["release_surfaces"]
    ] == [
        "commit-time",
        "push-time",
        "release-candidate",
        "advisory",
    ]
    assert [surface["surface"] for surface in payload["long_run_surfaces"]] == [
        "immediate",
        "checkpoint",
        "pre-resume",
        "pre-merge",
        "release-candidate",
    ]
    assert payload["long_run_surfaces"][0]["impacted"] is True
    assert payload["long_run_surfaces"][3]["recommended_profile_ids"] == [
        "commit-smoke",
        "push-confirmation",
    ]
    assert payload["release_surfaces"][0] == {
        "verification_stage": "commit-time",
        "impacted": True,
        "recommended_case_ids": ["smoke.readme"],
        "recommended_profile_ids": ["commit-smoke"],
        "blocking_profile_ids": ["commit-smoke"],
        "impacted_capability_ids": ["smoke_validation", "replay_portability"],
        "owner_ids": ["runtime.replay"],
        "profile_budget_notes": [
            "commit-smoke: case limit 2; advisory cases disallowed"
        ],
        "release_gate_commands": [],
        "release_gate_notes": [],
    }
    assert payload["release_surfaces"][2]["impacted"] is False
    assert payload["release_surfaces"][3]["impacted"] is False
    assert all(
        profile["confidence"] == "stage-derived" for profile in payload["profiles"]
    )
    assert (
        "uv run glassbox eval run smoke.readme --cwd ." in payload["suggested_commands"]
    )
    assert (
        "uv run glassbox eval run --profile commit-smoke --cwd ."
        in payload["suggested_commands"]
    )
    assert [
        entry["eval_profile_id"] for entry in payload["verification_plan_entries"]
    ] == ["commit-smoke", "push-confirmation", None]
    assert payload["verification_plan_entries"][2]["eval_case_id"] == "smoke.readme"
    assert payload["skipped_verification_checks"] == []


def test_cli_eval_recommend_distinguishes_release_profiles_from_full_gates(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "release-candidate",
                "title": "Release candidate",
                "verification_stage": "release-candidate",
                "blocking": True,
            }
        ],
    )
    _write_eval_coverage(tmp_path, profiles=[])
    _write_eval_impact(
        tmp_path,
        rules=[
            {
                "rule_id": "release-path-governance",
                "title": "Release paths",
                "path_globs": [
                    "scripts/validate_v*_release_gate.py",
                    "docs/v*-release-candidate.md",
                    "scripts/validate_package_contents.py",
                ],
                "profile_ids": ["release-candidate"],
            }
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "recommend",
            "scripts/validate_v10_release_gate.py",
            "docs/v10-release-candidate.md",
            "scripts/validate_package_contents.py",
            "--json",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    release_surface = payload["release_surfaces"][2]

    assert exit_code == 0
    assert [profile["profile_id"] for profile in payload["profiles"]] == [
        "release-candidate"
    ]
    assert payload["suggested_commands"] == [
        "uv run glassbox eval run --profile release-candidate --cwd ."
    ]
    assert payload["cheapest_next_command"] == (
        "uv run glassbox eval run --profile release-candidate --cwd ."
    )
    assert release_surface["recommended_profile_ids"] == ["release-candidate"]
    assert release_surface["release_gate_commands"] == [
        "uv run python scripts/validate_v10_release_gate.py",
        "uv run python scripts/validate_package_contents.py",
    ]
    release_gate_group = next(
        group
        for group in payload["reason_groups"]
        if group["group"] == "release-gate-recommendation"
    )
    assert release_gate_group["release_gate_commands"] == [
        "uv run python scripts/validate_v10_release_gate.py",
        "uv run python scripts/validate_package_contents.py",
    ]

    exit_code = main(
        [
            "eval",
            "recommend",
            "scripts/validate_v10_release_gate.py",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Cheapest next command:" in captured.out
    assert "Full gates:" in captured.out
    assert "uv run python scripts/validate_v10_release_gate.py" in captured.out


def test_cli_eval_recommend_reports_live_provider_canary_as_skipped_check(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "live-provider-canary",
                "title": "Live provider canary",
                "verification_stage": "advisory",
                "track": "live-provider-canary",
                "blocking": False,
            }
        ],
    )
    _write_eval_coverage(tmp_path, profiles=[])
    _write_eval_impact(
        tmp_path,
        rules=[
            {
                "rule_id": "provider-readiness",
                "title": "Provider readiness",
                "path_globs": ["docs/providers.md"],
                "profile_ids": ["live-provider-canary"],
            }
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "recommend",
            "docs/providers.md",
            "--json",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["matched_rule_ids"] == ["provider-readiness"]
    assert [profile["profile_id"] for profile in payload["profiles"]] == [
        "live-provider-canary"
    ]
    assert payload["suggested_commands"] == []
    assert payload["verification_plan_entries"] == []
    assert payload["skipped_verification_checks"] == [
        {
            "target_type": "profile",
            "target_id": "live-provider-canary",
            "reason": "live-provider canary profiles require explicit selection",
        }
    ]
    advisory_surface = payload["release_surfaces"][3]
    assert advisory_surface["verification_stage"] == "advisory"
    assert advisory_surface["impacted"] is True
    assert advisory_surface["recommended_profile_ids"] == ["live-provider-canary"]
    pre_resume_surface = next(
        surface
        for surface in payload["long_run_surfaces"]
        if surface["surface"] == "pre-resume"
    )
    assert pre_resume_surface["impacted"] is True
    assert pre_resume_surface["recommended_profile_ids"] == []
    assert pre_resume_surface["suggested_commands"] == []


def test_cli_eval_recommend_reports_coverage_manifest_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "blocking": True,
            }
        ],
    )
    _write_eval_coverage(
        tmp_path,
        profiles=[
            {
                "capability_id": "smoke_validation",
                "title": "Smoke validation",
                "criticality": "release-critical",
                "verification_stages": ["commit-time"],
                "expected_case_ids": [],
            }
        ],
    )
    _write_eval_impact(tmp_path, rules=[])
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "recommend",
            "evals/coverage.json",
            "--json",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["coverage_audit_recommended"] is True
    assert payload["cases"] == []
    assert payload["profiles"] == []
    assert payload["warnings"] == [
        "Touched eval coverage manifest; run eval audit because "
        "capability-to-case expectations may have changed."
    ]
    assert payload["suggested_commands"] == ["uv run glassbox eval audit --cwd ."]


def test_cli_eval_recommend_reports_verification_recipes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "blocking": True,
            }
        ],
    )
    _write_eval_coverage(tmp_path, profiles=[])
    _write_eval_impact(tmp_path, rules=[])
    recipes_path = tmp_path / "evals" / "recipes.json"
    recipes_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "recipes": [
                    {
                        "recipe_id": "frontend-dashboard",
                        "title": "Frontend dashboard",
                        "path_globs": ["frontend/**/*.tsx"],
                        "commands": [
                            "pnpm --dir frontend lint",
                            "pnpm --dir frontend test",
                        ],
                        "profile_ids": ["commit-smoke"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "recommend",
            "frontend/components/console/workspace-overview.tsx",
            "--json",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["recipes"] == [
        {
            "recipe_id": "frontend-dashboard",
            "title": "Frontend dashboard",
            "confidence": "direct",
            "source": "recipe",
            "freshness": "unknown",
            "matched_paths": ["frontend/components/console/workspace-overview.tsx"],
            "component_ids": [],
            "commands": [
                "pnpm --dir frontend lint",
                "pnpm --dir frontend test",
            ],
            "profile_ids": ["commit-smoke"],
            "case_ids": [],
            "notes": None,
            "limitations": [],
            "safe_next_commands": [],
        }
    ]

    exit_code = main(
        [
            "eval",
            "recommend",
            "frontend/components/console/workspace-overview.tsx",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Verification recipes:" in captured.out
    assert "frontend-dashboard: Frontend dashboard" in captured.out
    assert "pnpm --dir frontend test" in captured.out


def test_cli_eval_report_rejects_live_provider_canary_profile(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "live-provider-canary",
                "title": "Live provider canary",
                "verification_stage": "advisory",
                "track": "live-provider-canary",
                "blocking": False,
            }
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "report",
            "live-provider-canary",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "eval report only supports deterministic profiles" in captured.err
    assert "live-provider-canary" in captured.err


def test_cli_eval_promote_creates_case_bundle_and_review_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            },
            {
                "profile_id": "push-confirmation",
                "title": "Push confirmation",
                "verification_stage": "push-time",
                "tags": ["smoke"],
                "blocking": True,
            },
        ],
    )
    _write_eval_coverage(
        tmp_path,
        profiles=[
            {
                "capability_id": "replay_portability",
                "title": "Replay portability",
                "criticality": "release-critical",
                "verification_stages": ["commit-time", "push-time"],
                "expected_case_ids": ["smoke.promoted"],
            }
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "case",
            "promote",
            "smoke.promoted",
            str(session_id),
            "--title",
            "Promoted smoke case",
            "--tag",
            "smoke",
            "--owner",
            "runtime.replay",
            "--capability",
            "replay_portability",
            "--severity",
            "high",
            "--verification-stage",
            "commit-time",
            "--verification-stage",
            "push-time",
            "--reason",
            "Initial promotion for smoke verification.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    case_path = tmp_path / "evals" / "cases" / "smoke.promoted.json"
    bundle_path = tmp_path / "evals" / "bundles" / "smoke.promoted.json"
    report_path = (
        tmp_path / ".glassbox" / "evals" / "baseline-updates" / "smoke.promoted.json"
    )
    case_payload = json.loads(case_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "Operation: promote" in captured.out
    assert "Likely owners: runtime.replay" in captured.out
    assert "Blocking profiles: commit-smoke, push-confirmation" in captured.out
    assert "Impacted capabilities:" in captured.out
    assert case_path.is_file()
    assert bundle_path.is_file()
    assert report_path.is_file()
    assert case_payload["release_contract"]["owner"] == "runtime.replay"
    assert case_payload["baseline_history"][0]["operation"] == "promote"
    assert case_payload["baseline_history"][0]["rationale"] == (
        "Initial promotion for smoke verification."
    )
    assert report_payload["operation"] == "promote"
    assert report_payload["acknowledgement_required"] is False
    assert report_payload["likely_change_owners"] == ["runtime.replay"]
    assert report_payload["impacted_blocking_profile_ids"] == [
        "commit-smoke",
        "push-confirmation",
    ]
    assert [
        capability["capability_id"]
        for capability in report_payload["impacted_capabilities"]
    ] == ["replay_portability"]
    assert [
        profile["profile_id"] for profile in report_payload["impacted_profiles"]
    ] == ["commit-smoke", "push-confirmation"]

    run_exit_code = main(
        [
            "eval",
            "run",
            "smoke.promoted",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "promoted-output"),
        ]
    )
    run_capture = capsys.readouterr()

    assert run_exit_code == 0
    assert "smoke.promoted: exact match (passed)" in run_capture.out


def test_cli_eval_refresh_requires_acknowledgement_for_blocking_case(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, initial_session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    second_exit_code = main(
        [
            "session",
            "run",
            "Inspect the repository again",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    refresh_session_id = next(
        session.session_id
        for session in _list_sessions(db_path)
        if session.session_id != initial_session_id
    )
    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["replay_portability"],
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            }
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "case",
            "refresh",
            "smoke.readme",
            str(refresh_session_id),
            "--reason",
            "Intentional refresh after session capture update.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert second_exit_code == 0
    assert exit_code == 1
    assert "requires --acknowledge-policy" in captured.err
    assert "commit-smoke" in captured.err


def test_cli_eval_refresh_rejects_blocking_case_without_release_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, initial_session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    second_exit_code = main(
        [
            "session",
            "run",
            "Inspect the repository again",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    refresh_session_id = next(
        session.session_id
        for session in _list_sessions(db_path)
        if session.session_id != initial_session_id
    )
    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke"],
        release_contract={
            "verification_stages": ["commit-time"],
        },
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "case",
            "refresh",
            "smoke.readme",
            str(refresh_session_id),
            "--reason",
            "Intentional refresh after session capture update.",
            "--acknowledge-policy",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert second_exit_code == 0
    assert exit_code == 1
    assert "requires owner and capabilities metadata" in captured.err


def test_cli_eval_refresh_updates_bundle_manifest_history_and_review_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, initial_session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            }
        ],
    )
    _write_eval_coverage(
        tmp_path,
        profiles=[
            {
                "capability_id": "replay_portability",
                "title": "Replay portability",
                "criticality": "release-critical",
                "verification_stages": ["commit-time"],
                "expected_case_ids": ["smoke.promoted"],
            }
        ],
    )
    _ = capsys.readouterr()

    promote_exit_code = main(
        [
            "eval",
            "case",
            "promote",
            "smoke.promoted",
            str(initial_session_id),
            "--title",
            "Promoted smoke case",
            "--tag",
            "smoke",
            "--owner",
            "runtime.replay",
            "--capability",
            "replay_portability",
            "--severity",
            "high",
            "--verification-stage",
            "commit-time",
            "--reason",
            "Initial promotion for smoke verification.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()

    second_exit_code = main(
        [
            "session",
            "run",
            "Summarize the tests.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()
    refresh_session_id = next(
        session.session_id
        for session in _list_sessions(db_path)
        if session.session_id != initial_session_id
    )

    refresh_exit_code = main(
        [
            "eval",
            "case",
            "refresh",
            "smoke.promoted",
            str(refresh_session_id),
            "--reason",
            "Prompt changed intentionally for a refreshed smoke baseline.",
            "--acknowledge-policy",
            "--notes",
            "Refreshed after updating the source prompt.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    case_path = tmp_path / "evals" / "cases" / "smoke.promoted.json"
    report_path = (
        tmp_path / ".glassbox" / "evals" / "baseline-updates" / "smoke.promoted.json"
    )
    case_payload = json.loads(case_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert promote_exit_code == 0
    assert second_exit_code == 0
    assert refresh_exit_code == 0
    assert "Operation: refresh" in captured.out
    assert "Likely owners: runtime.replay" in captured.out
    assert "Blocking profiles: commit-smoke" in captured.out
    assert len(case_payload["baseline_history"]) == 2
    assert case_payload["baseline_history"][-1]["operation"] == "refresh"
    assert case_payload["baseline_history"][-1]["rationale"] == (
        "Prompt changed intentionally for a refreshed smoke baseline."
    )
    assert case_payload["notes"] == "Refreshed after updating the source prompt."
    assert report_payload["operation"] == "refresh"
    assert report_payload["acknowledgement_required"] is True
    assert report_payload["acknowledgement_received"] is True
    assert report_payload["baseline_history_count_after"] == 2
    assert report_payload["manifest_field_changes"]["baseline_history"]["after"]
    assert report_payload["likely_change_owners"] == ["runtime.replay"]
    assert report_payload["impacted_blocking_profile_ids"] == ["commit-smoke"]
    assert (
        report_payload["impacted_capabilities"][0]["criticality"] == "release-critical"
    )
    assert report_payload["impacted_profiles"][0]["profile_id"] == "commit-smoke"

    run_exit_code = main(
        [
            "eval",
            "run",
            "smoke.promoted",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "refreshed-output"),
        ]
    )
    run_capture = capsys.readouterr()

    assert run_exit_code == 0
    assert "smoke.promoted: exact match (passed)" in run_capture.out


def test_cli_eval_run_rejects_blocking_profile_with_advisory_case(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "context.relaxed")
    _write_eval_case(
        tmp_path,
        case_id="context.relaxed",
        title="Relaxed context advisory",
        bundle_name=bundle_path.name,
        tags=["context"],
        release_contract={
            "owner": "runtime.context",
            "verification_stages": ["advisory"],
            "baseline_refresh_policy": "advisory",
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "bad-blocking-context",
                "title": "Bad blocking context profile",
                "verification_stage": "advisory",
                "tags": ["context"],
                "blocking": True,
                "budget": {
                    "allow_advisory_cases": False,
                    "promotion_policy": "Promote only deterministic commit-time cases.",
                    "demotion_policy": (
                        "Demote advisory-only cases out of blocking profiles."
                    ),
                },
            }
        ],
    )

    exit_code = main(
        [
            "eval",
            "run",
            "--profile",
            "bad-blocking-context",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 14
    assert "Budget: violated (enforced)" in captured.out
    assert (
        "profile budget disallows advisory baseline cases: context.relaxed"
        in captured.out
    )


def test_cli_eval_run_reports_budget_warning_for_non_blocking_profile(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "context.branch")
    second_bundle_path = tmp_path / "evals" / "bundles" / "context.extra.json"
    shutil.copyfile(bundle_path, second_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="context.branch",
        title="Context branch",
        bundle_name=bundle_path.name,
        tags=["context"],
        release_contract={
            "verification_stages": ["advisory"],
            "baseline_refresh_policy": "advisory",
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="context.extra",
        title="Context extra",
        bundle_name=second_bundle_path.name,
        tags=["context"],
        release_contract={
            "verification_stages": ["advisory"],
            "baseline_refresh_policy": "advisory",
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "advisory-context",
                "title": "Advisory context",
                "verification_stage": "advisory",
                "tags": ["context"],
                "blocking": False,
                "budget": {
                    "max_selected_case_count": 1,
                    "allow_advisory_cases": True,
                    "allow_unsupported_cases": True,
                    "promotion_policy": (
                        "Promote only when the case becomes deterministic "
                        "enough for a blocking stage."
                    ),
                    "demotion_policy": (
                        "Keep exploratory or noisy context cases out of "
                        "blocking profiles."
                    ),
                },
            }
        ],
    )
    output_dir = tmp_path / "advisory-budget-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "--profile",
            "advisory-context",
            "--json",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["profile_budget"]["status"] == "warning"
    assert payload["profile_budget"]["violations"][0]["code"] == "selected_case_count"


def test_cli_eval_run_enforces_blocking_profile_selected_case_budget(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    second_bundle_path = tmp_path / "evals" / "bundles" / "smoke.extra.json"
    shutil.copyfile(bundle_path, second_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke"],
        release_contract={
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="smoke.extra",
        title="Extra smoke",
        bundle_name=second_bundle_path.name,
        tags=["smoke"],
        release_contract={
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
                "budget": {
                    "max_selected_case_count": 1,
                    "allow_advisory_cases": False,
                    "allow_unsupported_cases": False,
                    "promotion_policy": (
                        "Promote only the smallest deterministic smoke checks."
                    ),
                    "demotion_policy": (
                        "Demote broad or noisy cases out of commit-time smoke."
                    ),
                },
            }
        ],
    )
    output_dir = tmp_path / "blocking-budget-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "--profile",
            "commit-smoke",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

    assert exit_code == 14
    assert "Budget: violated (enforced)" in captured.out
    assert "selected case count 2 exceeds profile budget 1" in captured.out
    assert payload["profile_budget"]["status"] == "violated"
    assert payload["profile_budget"]["violations"][0]["code"] == "selected_case_count"


def test_cli_eval_run_allows_selected_invariants_to_ignore_behavioral_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "transcript.only")
    final_state_bundle_path = tmp_path / "evals" / "bundles" / "final-state.json"
    final_state_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    final_state_payload["baseline"]["final_state"]["status"] = "completed"
    final_state_bundle_path.write_text(
        json.dumps(final_state_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    _write_eval_case(
        tmp_path,
        case_id="transcript.only",
        title="Transcript-only expectation",
        bundle_name=final_state_bundle_path.name,
        tags=["smoke"],
        expectation={
            "mode": "selected_invariants",
            "invariants": ["transcript"],
        },
    )
    output_dir = tmp_path / "selected-invariants-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "transcript.only",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "transcript.only: behavioral drift (passed)" in captured.out
    assert "Ignored mismatches: final_state drift" in captured.out
    assert (
        "Selected invariants: selected invariants matched; ignored drift was "
        "limited to final_state drift" in captured.out
    )
    assert summary["cases"][0]["replay_outcome"] == "behavioral_drift"
    assert summary["cases"][0]["passed"] is True
    assert summary["cases"][0]["ignored_mismatches"] == ["final_state drift"]
    assert summary["cases"][0]["selected_invariant_interpretation"] == (
        "selected invariants matched; ignored drift was limited to final_state drift"
    )


def test_cli_eval_run_refreshes_managed_output_dir_for_repeated_runs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    approval_bundle_path = tmp_path / "evals" / "bundles" / "approval.patch.json"
    shutil.copyfile(bundle_path, approval_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke", "tooling"],
    )
    _write_eval_case(
        tmp_path,
        case_id="approval.patch",
        title="Patch approval",
        bundle_name=approval_bundle_path.name,
        tags=["approval"],
    )
    output_dir = tmp_path / ".glassbox" / "evals" / "pre-commit"

    first_exit_code = main(
        [
            "eval",
            "run",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--refresh-output-dir",
        ]
    )

    stale_file = output_dir / "stale.json"
    stale_file.write_text("{}\n", encoding="utf-8")
    _ = capsys.readouterr()

    second_exit_code = main(
        [
            "eval",
            "run",
            "--tag",
            "smoke",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--refresh-output-dir",
        ]
    )
    captured = capsys.readouterr()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

    assert first_exit_code == 0
    assert second_exit_code == 0
    assert "Artifacts: " + str(output_dir.resolve()) in captured.out
    assert (output_dir / "smoke.readme.json").is_file()
    assert not (output_dir / "approval.patch.json").exists()
    assert not stale_file.exists()
    assert summary["selected_case_count"] == 1
    assert summary["cases"][0]["case_id"] == "smoke.readme"


def test_cli_eval_run_rejects_refresh_outside_managed_output_tree(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke"],
    )
    output_dir = tmp_path / "manual-output"

    exit_code = main(
        [
            "eval",
            "run",
            "--tag",
            "smoke",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--refresh-output-dir",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert (
        "--refresh-output-dir requires an output directory under .glassbox/evals"
        in captured.err
    )
    assert not output_dir.exists()


def test_cli_eval_report_generates_release_signoff_artifacts_for_all_pass_suite(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke_bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    release_bundle_path = tmp_path / "evals" / "bundles" / "release.flow.json"
    shutil.copyfile(smoke_bundle_path, release_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=smoke_bundle_path.name,
        tags=["smoke"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["repository_inspection"],
            "severity": "medium",
            "verification_stages": ["commit-time"],
        },
        baseline_history=[
            {
                "operation": "promote",
                "recorded_at": "2026-01-10T00:00:00Z",
                "source_session_id": "00000000-0000-0000-0000-000000000001",
                "rationale": "Initial smoke promotion",
            }
        ],
    )
    _write_eval_case(
        tmp_path,
        case_id="release.flow",
        title="Release flow",
        bundle_name=release_bundle_path.name,
        tags=["release"],
        release_contract={
            "owner": "runtime.release",
            "capabilities": ["approval_flow"],
            "severity": "high",
            "verification_stages": ["release-candidate"],
        },
        baseline_history=[
            {
                "operation": "refresh",
                "recorded_at": "2026-02-10T00:00:00Z",
                "source_session_id": "00000000-0000-0000-0000-000000000002",
                "rationale": "Refresh after contract review",
            }
        ],
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            },
            {
                "profile_id": "release-candidate",
                "title": "Release candidate",
                "verification_stage": "release-candidate",
                "tags": ["release"],
                "blocking": True,
            },
        ],
    )
    _write_eval_coverage(
        tmp_path,
        profiles=[
            {
                "capability_id": "repository_inspection",
                "title": "Repository inspection",
                "criticality": "important",
                "verification_stages": ["commit-time"],
                "expected_case_ids": ["smoke.readme"],
                "coverage_mode": "single_case",
            },
            {
                "capability_id": "approval_flow",
                "title": "Approval flow",
                "criticality": "release-critical",
                "verification_stages": ["release-candidate"],
                "expected_case_ids": ["release.flow"],
                "coverage_mode": "single_case",
            },
        ],
    )

    output_dir = tmp_path / "release-signoff-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "report",
            "commit-smoke",
            "release-candidate",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload["contract_satisfied"] is True
    assert payload["latest_baseline_case_id"] == "release.flow"
    assert payload["profiles"][0]["summary_artifact_path"] == (
        "profiles/commit-smoke/summary.json"
    )
    assert payload["profiles"][1]["summary_artifact_path"] == (
        "profiles/release-candidate/summary.json"
    )
    assert (output_dir / "release-signoff.json").is_file()
    assert (output_dir / "release-signoff.md").is_file()
    assert (output_dir / "profiles" / "commit-smoke" / "summary.json").is_file()
    assert (output_dir / "profiles" / "release-candidate" / "summary.json").is_file()


def test_cli_eval_report_surfaces_blocking_failures_and_advisory_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "release.blocking")
    blocking_bundle_path = tmp_path / "evals" / "bundles" / "release.blocking.json"
    advisory_bundle_path = tmp_path / "evals" / "bundles" / "context.relaxed.json"

    failing_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    failing_payload["baseline"]["final_state"]["status"] = "failed"
    blocking_bundle_path.write_text(
        json.dumps(failing_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    advisory_bundle_path.write_text(
        json.dumps(failing_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    _write_eval_case(
        tmp_path,
        case_id="release.blocking",
        title="Blocking release profile",
        bundle_name=blocking_bundle_path.name,
        tags=["release"],
        release_contract={
            "owner": "runtime.release",
            "capabilities": ["release_contract"],
            "severity": "critical",
            "verification_stages": ["release-candidate"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="context.relaxed",
        title="Advisory relaxed context",
        bundle_name=advisory_bundle_path.name,
        tags=["context"],
        expectation={
            "mode": "selected_invariants",
            "invariants": ["transcript"],
        },
        release_contract={
            "owner": "runtime.context",
            "capabilities": ["context_inheritance"],
            "severity": "low",
            "verification_stages": ["advisory"],
            "baseline_refresh_policy": "advisory",
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "release-candidate",
                "title": "Release candidate",
                "verification_stage": "release-candidate",
                "tags": ["release"],
                "blocking": True,
            },
            {
                "profile_id": "advisory-context",
                "title": "Advisory context",
                "verification_stage": "advisory",
                "tags": ["context"],
                "blocking": False,
            },
        ],
    )
    _write_eval_coverage(
        tmp_path,
        profiles=[
            {
                "capability_id": "release_contract",
                "title": "Release contract",
                "criticality": "release-critical",
                "verification_stages": ["release-candidate"],
                "expected_case_ids": ["release.blocking"],
                "coverage_mode": "single_case",
            },
            {
                "capability_id": "context_inheritance",
                "title": "Context inheritance",
                "criticality": "advisory",
                "verification_stages": ["advisory"],
                "expected_case_ids": ["context.relaxed"],
                "coverage_mode": "single_case",
            },
        ],
    )

    output_dir = tmp_path / "release-signoff-mixed"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "report",
            "release-candidate",
            "advisory-context",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(
        (output_dir / "release-signoff.json").read_text(encoding="utf-8")
    )

    assert exit_code == 1
    assert "Status: `failed`" in captured.out
    assert "release-candidate" in captured.out
    assert "advisory-context" in captured.out
    assert "profiles/advisory-context/context.relaxed.json" in captured.out
    assert payload["status"] == "failed"
    assert payload["advisory_drift_case_count"] == 1
    assert payload["failed_severity_totals"]["critical"] == 1
    assert [profile["status"] for profile in payload["profiles"]] == [
        "failed",
        "warning",
    ]


def test_cli_eval_report_records_skipped_profiles_and_unsupported_cases(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "context.unsupported")
    unsupported_bundle_path = (
        tmp_path / "evals" / "bundles" / "context.unsupported.json"
    )

    unsupported_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    unsupported_payload["bundle_version"] = 2
    unsupported_bundle_path.write_text(
        json.dumps(unsupported_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke"],
        release_contract={
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="context.unsupported",
        title="Unsupported advisory case",
        bundle_name=unsupported_bundle_path.name,
        tags=["context"],
        release_contract={
            "verification_stages": ["advisory"],
            "baseline_refresh_policy": "advisory",
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            },
            {
                "profile_id": "advisory-context",
                "title": "Advisory context",
                "verification_stage": "advisory",
                "tags": ["context"],
                "blocking": False,
            },
        ],
    )

    output_dir = tmp_path / "release-signoff-skipped"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "report",
            "commit-smoke",
            "advisory-context",
            "--tag",
            "context",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["unsupported_case_count"] == 1
    assert [profile["status"] for profile in payload["profiles"]] == [
        "skipped",
        "warning",
    ]
    assert payload["profiles"][0]["skip_reason"] == (
        "no eval cases selected after applying report filters"
    )
