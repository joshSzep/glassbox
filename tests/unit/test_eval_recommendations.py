"""Unit tests for replay/eval change-impact recommendations."""

import json
from pathlib import Path

from glassbox.runtime.eval_recommendations import recommend_eval_change_impact
from glassbox.runtime.eval_verification import build_eval_verification_plan


def _write_bundle(tmp_path: Path, case_id: str) -> None:
    bundle_path = tmp_path / "evals" / "bundles" / f"{case_id}.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text("{}\n", encoding="utf-8")


def _write_case(
    tmp_path: Path,
    *,
    case_id: str,
    title: str,
    owner: str,
    capabilities: list[str],
    verification_stages: list[str],
    notes: str | None = None,
    baseline_history: list[dict[str, object]] | None = None,
) -> None:
    _write_bundle(tmp_path, case_id)
    case_path = tmp_path / "evals" / "cases" / f"{case_id}.json"
    case_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "manifest_version": 1,
        "case_id": case_id,
        "title": title,
        "bundle_path": f"../bundles/{case_id}.json",
        "tags": ["smoke"],
        "release_contract": {
            "owner": owner,
            "capabilities": capabilities,
            "verification_stages": verification_stages,
        },
    }
    if notes is not None:
        payload["notes"] = notes
    if baseline_history is not None:
        payload["baseline_history"] = baseline_history
    case_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_profiles(tmp_path: Path) -> None:
    profiles_path = tmp_path / "evals" / "profiles.json"
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    profiles_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "profiles": [
                    {
                        "profile_id": "commit-smoke",
                        "title": "Commit smoke",
                        "verification_stage": "commit-time",
                        "blocking": True,
                    },
                    {
                        "profile_id": "release-candidate",
                        "title": "Release candidate",
                        "verification_stage": "release-candidate",
                        "blocking": True,
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_profiles_payload(tmp_path: Path, profiles: list[dict[str, object]]) -> None:
    profiles_path = tmp_path / "evals" / "profiles.json"
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    profiles_path.write_text(
        json.dumps({"manifest_version": 1, "profiles": profiles}, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_coverage(tmp_path: Path) -> None:
    coverage_path = tmp_path / "evals" / "coverage.json"
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "capabilities": [
                    {
                        "capability_id": "replay_portability",
                        "title": "Replay portability",
                        "criticality": "release-critical",
                        "verification_stages": ["commit-time"],
                        "expected_case_ids": ["smoke.readme"],
                    },
                    {
                        "capability_id": "context_drift_detection",
                        "title": "Context drift detection",
                        "criticality": "important",
                        "verification_stages": ["release-candidate"],
                        "expected_case_ids": ["context.artifact"],
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_impact(tmp_path: Path) -> None:
    impact_path = tmp_path / "evals" / "impact.json"
    impact_path.parent.mkdir(parents=True, exist_ok=True)
    impact_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "rules": [
                    {
                        "rule_id": "runtime-replay",
                        "title": "Replay runtime",
                        "path_globs": ["src/glassbox/runtime/replay*.py"],
                        "owners": ["runtime.replay"],
                        "capabilities": ["replay_portability"],
                    },
                    {
                        "rule_id": "runtime-context",
                        "title": "Runtime context",
                        "path_globs": [
                            "src/glassbox/runtime/context*.py",
                            "docs/runtime-context.md",
                        ],
                        "owners": ["runtime.context"],
                        "capabilities": ["context_drift_detection"],
                    },
                    {
                        "rule_id": "tool-policy-governance",
                        "title": "Repository tool policy",
                        "path_globs": [
                            "glassbox-policy.json",
                            "**/glassbox-policy.json",
                            "src/glassbox/tools/policy.py",
                            "src/glassbox/tools/policy_config.py",
                            "docs/examples/tool-policy/*.json",
                        ],
                        "owners": ["runtime.approval"],
                        "capabilities": ["approval_flow"],
                        "case_ids": ["approval.approved-patch"],
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_recommend_eval_change_impact_ignores_non_contract_case_metadata(
    tmp_path: Path,
) -> None:
    _write_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        owner="runtime.replay",
        capabilities=["replay_portability"],
        verification_stages=["commit-time"],
    )
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)

    before = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["src/glassbox/runtime/replay_execution.py"],
    )

    _write_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        owner="runtime.replay",
        capabilities=["replay_portability"],
        verification_stages=["commit-time"],
        notes="Updated reviewer note only.",
        baseline_history=[
            {
                "operation": "refresh",
                "recorded_at": "2026-04-24T00:00:00Z",
                "source_session_id": "00000000-0000-0000-0000-000000000111",
                "rationale": "Metadata-only refresh note.",
            }
        ],
    )

    after = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["src/glassbox/runtime/replay_execution.py"],
    )

    assert [case.case_id for case in before.cases] == [
        case.case_id for case in after.cases
    ]
    assert [profile.profile_id for profile in before.profiles] == [
        profile.profile_id for profile in after.profiles
    ]
    assert [reason.summary for reason in before.cases[0].reasons] == [
        reason.summary for reason in after.cases[0].reasons
    ]
    assert [reason.summary for reason in before.profiles[0].reasons] == [
        reason.summary for reason in after.profiles[0].reasons
    ]


def test_recommend_eval_change_impact_routes_context_changes_to_context_cases(
    tmp_path: Path,
) -> None:
    _write_case(
        tmp_path,
        case_id="context.artifact",
        title="Artifact-backed context",
        owner="runtime.context",
        capabilities=["context_drift_detection"],
        verification_stages=["release-candidate"],
    )
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["src/glassbox/runtime/context_builder.py"],
    )

    assert report.matched_rule_ids == ["runtime-context"]
    assert [case.case_id for case in report.cases] == ["context.artifact"]
    assert [profile.profile_id for profile in report.profiles] == ["release-candidate"]
    assert any("context.artifact" in command for command in report.suggested_commands)


def test_recommend_eval_change_impact_routes_policy_changes_to_approval_case(
    tmp_path: Path,
) -> None:
    _write_case(
        tmp_path,
        case_id="approval.approved-patch",
        title="Approved patch",
        owner="runtime.approval",
        capabilities=["approval_flow"],
        verification_stages=["advisory"],
    )
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=[
            "src/glassbox/tools/policy_config.py",
            "docs/examples/tool-policy/local-command-governance.json",
        ],
    )

    assert report.matched_rule_ids == ["tool-policy-governance"]
    assert [case.case_id for case in report.cases] == ["approval.approved-patch"]
    assert any(
        reason.rule_id == "tool-policy-governance" for reason in report.cases[0].reasons
    )
    assert any(
        "approval.approved-patch" in command for command in report.suggested_commands
    )


def test_recommend_eval_change_impact_narrows_advisory_profiles_by_case_ids(
    tmp_path: Path,
) -> None:
    _write_case(
        tmp_path,
        case_id="cancellation.cancelled-turn",
        title="Cancelled turn",
        owner="runtime.cancellation",
        capabilities=["cancellation"],
        verification_stages=["advisory"],
    )
    _write_case(
        tmp_path,
        case_id="context.artifact",
        title="Artifact context",
        owner="runtime.context",
        capabilities=["context_drift_detection"],
        verification_stages=["advisory"],
    )
    _write_profiles_payload(
        tmp_path,
        [
            {
                "profile_id": "v7-workflow-advisory",
                "title": "v7 advisory",
                "verification_stage": "advisory",
                "case_ids": ["cancellation.cancelled-turn"],
                "blocking": False,
            },
            {
                "profile_id": "advisory-context",
                "title": "Context advisory",
                "verification_stage": "advisory",
                "tags": ["context"],
                "blocking": False,
            },
        ],
    )
    _write_coverage(tmp_path)
    impact_path = tmp_path / "evals" / "impact.json"
    impact_path.parent.mkdir(parents=True, exist_ok=True)
    impact_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "rules": [
                    {
                        "rule_id": "runtime-cancellation",
                        "title": "Cancellation",
                        "path_globs": ["src/glassbox/runtime/turn_engine.py"],
                        "case_ids": ["cancellation.cancelled-turn"],
                        "capabilities": ["cancellation"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["src/glassbox/runtime/turn_engine.py"],
    )

    assert [profile.profile_id for profile in report.profiles] == [
        "v7-workflow-advisory"
    ]
    advisory_surface = next(
        surface
        for surface in report.release_surfaces
        if surface.verification_stage == "advisory"
    )
    assert advisory_surface.recommended_profile_ids == ["v7-workflow-advisory"]


def test_recommend_eval_change_impact_keeps_live_provider_canary_explicitly_skipped(
    tmp_path: Path,
) -> None:
    _write_profiles_payload(
        tmp_path,
        [
            {
                "profile_id": "live-provider-canary",
                "title": "Live provider canary",
                "verification_stage": "advisory",
                "track": "live-provider-canary",
                "blocking": False,
            }
        ],
    )
    _write_coverage(tmp_path)
    impact_path = tmp_path / "evals" / "impact.json"
    impact_path.parent.mkdir(parents=True, exist_ok=True)
    impact_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "rules": [
                    {
                        "rule_id": "provider-readiness",
                        "title": "Provider readiness",
                        "path_globs": ["docs/providers.md"],
                        "profile_ids": ["live-provider-canary"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = recommend_eval_change_impact(tmp_path, touched_paths=["docs/providers.md"])
    plan = build_eval_verification_plan(report)

    assert [profile.profile_id for profile in report.profiles] == [
        "live-provider-canary"
    ]
    assert report.suggested_commands == []
    assert plan.plan_entries == []
    assert len(plan.skipped_checks) == 1
    assert plan.skipped_checks[0].target_id == "live-provider-canary"
    assert "explicit selection" in plan.skipped_checks[0].reason
