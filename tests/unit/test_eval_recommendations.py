"""Unit tests for replay/eval change-impact recommendations."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from glassbox.runtime.eval_recommendations import PathVerificationCommandRecipeTarget
from glassbox.runtime.eval_recommendations import PathVerificationEvalProfileTarget
from glassbox.runtime.eval_recommendations import PathVerificationImpact
from glassbox.runtime.eval_recommendations import PathVerificationProvenance
from glassbox.runtime.eval_recommendations import PathVerificationRecommendationReport
from glassbox.runtime.eval_recommendations import PathVerificationSkippedCheck
from glassbox.runtime.eval_recommendations import PathVerificationStaleEvidence
from glassbox.runtime.eval_recommendations import PathVerificationTarget
from glassbox.runtime.eval_recommendations import recommend_eval_change_impact
from glassbox.runtime.eval_verification import build_eval_verification_plan
from glassbox.runtime.eval_verification_recipes import (
    load_eval_verification_recipe_manifest,
)
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.workspace_topology import build_and_write_workspace_topology

_REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _write_recipes(tmp_path: Path, recipes: list[dict[str, object]]) -> None:
    recipes_path = tmp_path / "evals" / "recipes.json"
    recipes_path.parent.mkdir(parents=True, exist_ok=True)
    recipes_path.write_text(
        json.dumps({"manifest_version": 1, "recipes": recipes}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_path_verification_contract_serializes_evidence_classes(
    tmp_path: Path,
) -> None:
    provenance = PathVerificationProvenance(
        source="eval-impact",
        source_path="evals/impact.json",
        confidence="direct",
        freshness="fresh",
        explanation="impact rule matched the changed runtime path",
    )
    report = PathVerificationRecommendationReport(
        workspace_root=tmp_path,
        changed_paths=["src/glassbox/runtime/repository_index.py"],
        impacts=[
            PathVerificationImpact(
                path="src/glassbox/runtime/repository_index.py",
                confidence="direct",
                subsystems=["runtime.repository-intelligence"],
                release_surfaces=["commit-time"],
                why_this=["repository intelligence runtime path changed"],
                provenance=[provenance],
            )
        ],
        targets=[
            PathVerificationTarget(
                target_id="tests/unit/test_repository_index.py",
                target_kind="test-target",
                title="Repository index unit tests",
                evidence_class="deterministic-executable",
                confidence="direct",
                matched_paths=["src/glassbox/runtime/repository_index.py"],
                command="uv run pytest tests/unit/test_repository_index.py",
                verification_stage="commit-time",
                blocking=True,
                why_this="changed path belongs to the repository index runtime",
                provenance=[provenance],
            )
        ],
        command_recipes=[
            PathVerificationCommandRecipeTarget(
                target_id="repo-index-focused",
                recipe_id="repo-index-focused",
                title="Repository index focused validation",
                confidence="recipe-derived",
                matched_paths=["src/glassbox/runtime/repository_index.py"],
                command="uv run pytest tests/unit/test_repository_index.py",
                why_this="recipe matched repository index paths",
                purpose="focused repository index validation",
                risk="low",
                provenance=[provenance],
            )
        ],
        eval_profiles=[
            PathVerificationEvalProfileTarget(
                target_id="commit-smoke",
                profile_id="commit-smoke",
                title="Commit smoke",
                evidence_class="deterministic-executable",
                confidence="stage-derived",
                matched_paths=["src/glassbox/runtime/repository_index.py"],
                command="uv run glassbox eval run --profile commit-smoke --cwd .",
                verification_stage="commit-time",
                profile_track="deterministic",
                blocking=True,
                why_this="impacted case participates in commit-time verification",
                provenance=[provenance],
            )
        ],
        skipped_checks=[
            PathVerificationSkippedCheck(
                target_id="live-provider-canary",
                target_kind="live-provider-canary",
                reason="live-provider-canary",
                explanation="canary profiles require explicit operator selection",
            )
        ],
        stale_evidence=[
            PathVerificationStaleEvidence(
                evidence_id="workspace-topology",
                evidence_kind="topology",
                freshness="stale",
                affected_paths=["src/glassbox/runtime/repository_index.py"],
                reason="topology digest no longer matches the workspace",
                provenance=[provenance],
                safe_next_actions=["uv run glassbox topology build --cwd ."],
            )
        ],
        cheapest_next_command="uv run pytest tests/unit/test_repository_index.py",
    )

    payload = report.model_dump(mode="json")

    assert payload["targets"][0]["evidence_class"] == "deterministic-executable"
    assert payload["command_recipes"][0]["evidence_class"] == "advisory-command"
    assert payload["eval_profiles"][0]["profile_track"] == "deterministic"
    assert payload["skipped_checks"][0]["reason"] == "live-provider-canary"
    assert payload["stale_evidence"][0]["freshness"] == "stale"
    assert payload["impacts"][0]["provenance"][0]["source"] == "eval-impact"


def test_path_verification_contract_rejects_advisory_targets_as_deterministic() -> None:
    with pytest.raises(ValidationError, match="command-recipe"):
        PathVerificationTarget(
            target_id="docs-recipe",
            target_kind="command-recipe",
            title="Docs recipe",
            evidence_class="deterministic-executable",
            confidence="recipe-derived",
            why_this="recipes are advisory command guidance",
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
    assert report.cheapest_next_command == (
        "uv run glassbox eval run context.artifact --cwd ."
    )
    assert [group.group for group in report.reason_groups] == [
        "owner-derived-rule",
        "capability-derived-rule",
        "stage-derived-profile",
    ]


def test_recommend_eval_change_impact_distinguishes_release_profiles_from_gates(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    impact_path = tmp_path / "evals" / "impact.json"
    impact_path.parent.mkdir(parents=True, exist_ok=True)
    impact_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "rules": [
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
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=[
            "scripts/validate_v10_release_gate.py",
            "docs/v10-release-candidate.md",
            "scripts/validate_package_contents.py",
        ],
    )

    release_surface = next(
        surface
        for surface in report.release_surfaces
        if surface.verification_stage == "release-candidate"
    )

    assert report.matched_rule_ids == ["release-path-governance"]
    assert report.unmatched_paths == []
    assert [profile.profile_id for profile in report.profiles] == ["release-candidate"]
    assert report.suggested_commands == [
        "uv run glassbox eval run --profile release-candidate --cwd ."
    ]
    assert release_surface.recommended_profile_ids == ["release-candidate"]
    assert release_surface.release_gate_commands == [
        "uv run python scripts/validate_v10_release_gate.py",
        "uv run python scripts/validate_package_contents.py",
    ]
    assert any(
        "do not replace the gate" in note for note in release_surface.release_gate_notes
    )
    assert report.cheapest_next_command == (
        "uv run glassbox eval run --profile release-candidate --cwd ."
    )
    release_gate_group = next(
        group
        for group in report.reason_groups
        if group.group == "release-gate-recommendation"
    )
    assert release_gate_group.release_gate_commands == [
        "uv run python scripts/validate_v10_release_gate.py",
        "uv run python scripts/validate_package_contents.py",
    ]


def test_recommend_eval_change_impact_names_v11_release_gate() -> None:
    report = recommend_eval_change_impact(
        _REPO_ROOT,
        touched_paths=[
            "scripts/validate_v11_release_gate.py",
            "docs/v11-release-gate.md",
        ],
    )
    release_surface = next(
        surface
        for surface in report.release_surfaces
        if surface.verification_stage == "release-candidate"
    )

    assert release_surface.release_gate_commands == [
        "uv run python scripts/validate_v11_release_gate.py"
    ]
    assert "release-candidate" in release_surface.recommended_profile_ids


def test_recommend_eval_change_impact_routes_changeset_runtime_paths() -> None:
    report = recommend_eval_change_impact(
        _REPO_ROOT,
        touched_paths=["src/glassbox/runtime/changesets.py"],
    )

    assert "v13-changeset-runtime" in report.matched_rule_ids
    assert "src/glassbox/runtime/changesets.py" not in report.unmatched_paths
    assert "changeset.reviewable-lifecycle" in [
        recommendation.case_id for recommendation in report.cases
    ]
    assert "changeset-runtime" in [
        recommendation.recipe_id for recommendation in report.recipes
    ]
    assert any(
        group.group == "capability-derived-rule" for group in report.reason_groups
    )


def test_recommend_eval_change_impact_routes_review_loop_evidence_paths() -> None:
    report = recommend_eval_change_impact(
        _REPO_ROOT,
        touched_paths=[
            "src/glassbox/runtime/manual_evidence.py",
            "src/glassbox/store/sqlite_projection_review_loop.py",
        ],
    )

    assert report.matched_rule_ids == [
        "v13-changeset-runtime",
        "v13-review-loop-store",
    ]
    assert report.unmatched_paths == []
    assert "changeset.reviewable-lifecycle" in [
        recommendation.case_id for recommendation in report.cases
    ]
    assert "review-loop-evidence" in [
        recommendation.recipe_id for recommendation in report.recipes
    ]
    assert "store-schema" in [
        recommendation.recipe_id for recommendation in report.recipes
    ]


def test_recommend_eval_change_impact_routes_generated_changeset_api_types() -> None:
    report = recommend_eval_change_impact(
        _REPO_ROOT,
        touched_paths=["frontend/generated/api-types.ts"],
    )

    assert report.matched_rule_ids == ["v13-review-loop-surfaces"]
    assert report.unmatched_paths == []
    assert "changeset-surfaces" in [
        recommendation.recipe_id for recommendation in report.recipes
    ]
    assert "frontend-dashboard" in [
        recommendation.recipe_id for recommendation in report.recipes
    ]
    assert "changeset.reviewable-lifecycle" in [
        recommendation.case_id for recommendation in report.cases
    ]


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


def test_recommend_eval_change_impact_reports_long_run_surfaces(
    tmp_path: Path,
) -> None:
    _write_case(
        tmp_path,
        case_id="checkpoint.resume",
        title="Checkpoint resume",
        owner="runtime.long-run",
        capabilities=["durable_checkpoint_recovery"],
        verification_stages=["commit-time", "release-candidate"],
    )
    _write_profiles(tmp_path)
    coverage_path = tmp_path / "evals" / "coverage.json"
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "capabilities": [
                    {
                        "capability_id": "durable_checkpoint_recovery",
                        "title": "Durable checkpoint recovery",
                        "criticality": "release-critical",
                        "verification_stages": ["commit-time", "release-candidate"],
                        "expected_case_ids": ["checkpoint.resume"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    impact_path = tmp_path / "evals" / "impact.json"
    impact_path.parent.mkdir(parents=True, exist_ok=True)
    impact_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "rules": [
                    {
                        "rule_id": "v10-checkpoint-recovery",
                        "title": "Checkpoint recovery",
                        "path_globs": ["src/glassbox/runtime/checkpoints.py"],
                        "capabilities": ["durable_checkpoint_recovery"],
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
        touched_paths=["src/glassbox/runtime/checkpoints.py"],
    )

    surfaces = {surface.surface: surface for surface in report.long_run_surfaces}
    assert list(surfaces) == [
        "immediate",
        "checkpoint",
        "pre-resume",
        "pre-merge",
        "release-candidate",
    ]
    assert surfaces["immediate"].recommended_case_ids == ["checkpoint.resume"]
    assert surfaces["immediate"].recommended_profile_ids == ["commit-smoke"]
    assert surfaces["checkpoint"].impacted is True
    assert any("checkpoint" in reason for reason in surfaces["checkpoint"].reasons)
    assert surfaces["pre-resume"].impacted is True
    assert surfaces["release-candidate"].recommended_profile_ids == [
        "release-candidate"
    ]
    assert any(
        "--profile release-candidate" in command
        for command in surfaces["release-candidate"].suggested_commands
    )


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
    provider_surface = next(
        surface
        for surface in report.long_run_surfaces
        if surface.surface == "pre-resume"
    )
    assert provider_surface.impacted is True
    assert provider_surface.recommended_profile_ids == []
    assert provider_surface.suggested_commands == []


def test_recommend_eval_change_impact_marks_fallback_as_manual_policy(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["src/glassbox/runtime/unmapped.py"],
    )

    assert [profile.profile_id for profile in report.profiles] == ["commit-smoke"]
    assert report.profiles[0].confidence == "fallback"
    assert report.profiles[0].reasons[0].group == "fallback-policy"
    assert report.fallback_policy_commands == [
        "uv run glassbox eval run --profile commit-smoke --cwd ."
    ]
    assert report.cheapest_next_command == (
        "uv run glassbox eval run --profile commit-smoke --cwd ."
    )
    assert report.warnings == [
        "No confident replay or eval recommendation was found; fallback commands "
        "are manual policy guidance, not inferred evidence."
    ]
    assert [group.group for group in report.reason_groups] == ["fallback-policy"]


def test_eval_verification_recipe_manifest_validates_and_dedupes(
    tmp_path: Path,
) -> None:
    _write_recipes(
        tmp_path,
        [
            {
                "recipe_id": "frontend-dashboard",
                "title": "Frontend dashboard",
                "path_globs": ["frontend/**/*.tsx", "frontend/**/*.tsx"],
                "commands": ["pnpm --dir frontend test", "pnpm --dir frontend test"],
                "profile_ids": ["commit-smoke", "commit-smoke"],
                "case_ids": ["dashboard.action-answer", "dashboard.action-answer"],
            }
        ],
    )

    manifest = load_eval_verification_recipe_manifest(tmp_path)

    recipe = manifest.recipes[0]
    assert recipe.path_globs == ["frontend/**/*.tsx"]
    assert recipe.commands == ["pnpm --dir frontend test"]
    assert recipe.profile_ids == ["commit-smoke"]
    assert recipe.case_ids == ["dashboard.action-answer"]


def test_eval_verification_recipe_manifest_rejects_empty_commands(
    tmp_path: Path,
) -> None:
    _write_recipes(
        tmp_path,
        [
            {
                "recipe_id": "docs-only",
                "title": "Docs only",
                "path_globs": ["docs/**/*.md"],
                "commands": [],
            }
        ],
    )

    try:
        load_eval_verification_recipe_manifest(tmp_path)
    except ValueError as exc:
        assert "at least one command" in str(exc)
    else:
        raise AssertionError("expected invalid recipe manifest to fail")


def test_recommend_eval_change_impact_includes_matching_recipes(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    _write_recipes(
        tmp_path,
        [
            {
                "recipe_id": "frontend-dashboard",
                "title": "Frontend dashboard",
                "path_globs": ["frontend/**/*.tsx"],
                "commands": [
                    "pnpm --dir frontend lint",
                    "pnpm --dir frontend test",
                ],
                "profile_ids": ["commit-smoke"],
                "notes": "Run route tests when backend paths change.",
            }
        ],
    )

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["frontend/components/console/workspace-overview.tsx"],
    )

    assert [recipe.recipe_id for recipe in report.recipes] == ["frontend-dashboard"]
    assert report.recipes[0].matched_paths == [
        "frontend/components/console/workspace-overview.tsx"
    ]
    assert report.recipes[0].commands == [
        "pnpm --dir frontend lint",
        "pnpm --dir frontend test",
    ]


def test_recommend_eval_change_impact_adds_topology_component_recipes(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    _write_mixed_workspace(tmp_path)
    build_and_write_workspace_topology(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=[
            "src/demo/widget.py",
            "frontend/components/console/widget.tsx",
        ],
    )

    topology_recipes = [
        recipe for recipe in report.recipes if recipe.source == "topology"
    ]
    assert [recipe.recipe_id for recipe in topology_recipes] == [
        "topology-app-frontend",
        "topology-package-demo",
    ]
    frontend_recipe = topology_recipes[0]
    assert frontend_recipe.confidence == "topology"
    assert frontend_recipe.component_ids == ["app:frontend"]
    assert frontend_recipe.commands == [
        "pnpm --dir frontend lint",
        "pnpm --dir frontend typecheck",
        "pnpm --dir frontend test",
        "pnpm --dir frontend build",
    ]

    python_recipe = topology_recipes[1]
    assert python_recipe.component_ids == ["package:demo"]
    assert python_recipe.commands == [
        "uv run ruff check src/demo/widget.py",
        "uv run ty check src/demo/widget.py",
        "uv run pytest tests/unit/test_widget.py -q",
    ]
    assert python_recipe.limitations == []


def test_recommend_eval_change_impact_discovers_python_test_targets_from_index(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    _write_mixed_workspace(tmp_path)
    build_and_write_repository_index(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["src/demo/widget.py"],
    )

    assert [target.target_id for target in report.test_targets] == [
        "test-naming:tests/unit/test_widget.py"
    ]
    target = report.test_targets[0]
    assert target.confidence == "naming-derived"
    assert target.source == "repository-intelligence"
    assert target.freshness == "fresh"
    assert target.package_ids == ["package:demo"]
    assert target.target_paths == ["tests/unit/test_widget.py"]
    assert target.command == "uv run pytest tests/unit/test_widget.py -q"


def test_recommend_eval_change_impact_discovers_frontend_test_targets_from_index(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    _write_mixed_workspace(tmp_path)
    build_and_write_repository_index(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["frontend/components/console/widget.tsx"],
    )

    assert [target.target_id for target in report.test_targets] == [
        "test-naming:frontend/tests/widget.test.ts"
    ]
    target = report.test_targets[0]
    assert target.confidence == "naming-derived"
    assert target.source == "repository-intelligence"
    assert target.package_ids == ["app:frontend"]
    assert target.target_paths == ["frontend/tests/widget.test.ts"]
    assert target.command == "pnpm --dir frontend test -- frontend/tests/widget.test.ts"


def test_recommend_eval_change_impact_reports_docs_test_fallback(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "operator.md").write_text("# Operator\n", encoding="utf-8")
    build_and_write_repository_index(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["docs/operator.md"],
    )

    assert [target.target_id for target in report.test_targets] == [
        "test-docs:release-candidate-docs"
    ]
    assert report.test_targets[0].confidence == "fallback"
    assert report.test_targets[0].command == (
        "uv run pytest tests/unit/test_release_candidate_docs.py -q"
    )


def test_recommend_eval_change_impact_warns_for_generated_paths(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    _write_mixed_workspace(tmp_path)
    (tmp_path / "frontend" / "generated").mkdir()
    (tmp_path / "frontend" / "generated" / "api.ts").write_text(
        "export type Api = unknown;\n",
        encoding="utf-8",
    )
    build_and_write_repository_index(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["frontend/generated/api.ts"],
    )

    assert report.test_targets == []
    assert any("frontend/generated/api.ts" in warning for warning in report.warnings)
    assert any("generated" in warning for warning in report.warnings)


def test_recommend_eval_change_impact_discovers_release_script_test_by_naming(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "validate_v14_release_gate.py").write_text(
        "def main() -> int:\n    return 0\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_validate_v14_release_gate.py").write_text(
        "def test_gate() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    build_and_write_repository_index(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["scripts/validate_v14_release_gate.py"],
    )

    assert [target.target_paths for target in report.test_targets] == [
        ["tests/unit/test_validate_v14_release_gate.py"]
    ]
    assert report.test_targets[0].confidence == "naming-derived"


def test_recommend_eval_change_impact_uses_repository_intelligence_release_surface(
    tmp_path: Path,
) -> None:
    _write_profiles_payload(
        tmp_path,
        [
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "blocking": True,
                "budget": {
                    "max_selected_case_count": 3,
                    "allow_advisory_cases": False,
                },
            }
        ],
    )
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    _write_mixed_workspace(tmp_path)
    build_and_write_repository_index(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["src/demo/widget.py"],
    )

    assert [profile.profile_id for profile in report.profiles] == ["commit-smoke"]
    profile = report.profiles[0]
    assert profile.confidence == "stage-derived"
    assert profile.matched_paths == ["src/demo/widget.py"]
    assert profile.source_metadata[0].source == "repository-intelligence-snapshot"
    assert profile.source_metadata[0].source_id == "release-surface:commit-time"
    assert profile.source_metadata[0].freshness == "fresh"
    assert "Budget allows up to 3 selected cases." in profile.budget_implications
    assert profile.safe_next_commands == [
        "uv run glassbox eval run --profile commit-smoke --cwd ."
    ]
    assert [group.group for group in report.reason_groups] == [
        "repository-intelligence"
    ]
    assert report.unmatched_paths == []


def test_recommend_eval_change_impact_adds_repository_intelligence_recipes(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    _write_recipes(
        tmp_path,
        [
            {
                "recipe_id": "frontend-dashboard",
                "title": "Frontend dashboard",
                "path_globs": ["frontend/**/*.tsx"],
                "commands": ["pnpm --dir frontend test"],
            }
        ],
    )
    _write_mixed_workspace(tmp_path)
    build_and_write_repository_index(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["frontend/components/console/widget.tsx"],
    )

    repository_recipes = [
        recipe
        for recipe in report.recipes
        if recipe.source == "repository-intelligence"
    ]
    assert [recipe.recipe_id for recipe in repository_recipes] == [
        "repo-intelligence-recipe-eval-recipe-frontend-dashboard-0"
    ]
    assert repository_recipes[0].freshness == "fresh"
    assert repository_recipes[0].matched_paths == [
        "frontend/components/console/widget.tsx"
    ]
    assert repository_recipes[0].safe_next_commands == ["pnpm --dir frontend test"]


def test_recommend_eval_change_impact_marks_stale_repository_intelligence(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    _write_mixed_workspace(tmp_path)
    build_and_write_repository_index(tmp_path)
    (tmp_path / "src" / "demo" / "extra.py").write_text("VALUE = 2\n", encoding="utf-8")

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["src/demo/widget.py"],
    )

    profile = report.profiles[0]
    assert profile.source_metadata[0].freshness == "stale"
    assert any(
        "Repository intelligence snapshot is stale" in warning
        for warning in report.warnings
    )


def test_recommend_eval_change_impact_degrades_missing_test_roots(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "src" / "demo").mkdir(parents=True)
    (tmp_path / "src" / "demo" / "widget.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    build_and_write_repository_index(tmp_path)

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["src/demo/widget.py"],
    )

    assert report.test_targets == []
    assert any("no test roots" in warning for warning in report.warnings)


def test_recommend_eval_change_impact_degrades_stale_topology_guidance(
    tmp_path: Path,
) -> None:
    _write_profiles(tmp_path)
    _write_coverage(tmp_path)
    _write_impact(tmp_path)
    _write_mixed_workspace(tmp_path)
    build_and_write_workspace_topology(tmp_path)
    (tmp_path / "src" / "demo" / "extra.py").write_text("VALUE = 1\n", encoding="utf-8")

    report = recommend_eval_change_impact(
        tmp_path,
        touched_paths=["src/demo/widget.py"],
    )

    topology_recipe = next(
        recipe for recipe in report.recipes if recipe.source == "topology"
    )
    assert topology_recipe.confidence == "degraded"
    assert "Topology inputs changed" in topology_recipe.limitations[0]
    assert any("topology is stale" in warning for warning in report.warnings)


def _write_mixed_workspace(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "src" / "demo").mkdir(parents=True)
    (tmp_path / "src" / "demo" / "widget.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_widget.py").write_text(
        "def test_widget() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "package.json").write_text(
        json.dumps({"name": "frontend", "scripts": {}}),
        encoding="utf-8",
    )
    (tmp_path / "frontend" / "pnpm-lock.yaml").write_text("", encoding="utf-8")
    (tmp_path / "frontend" / "components" / "console").mkdir(parents=True)
    (tmp_path / "frontend" / "components" / "console" / "widget.tsx").write_text(
        "export function Widget() { return null; }\n",
        encoding="utf-8",
    )
    (tmp_path / "frontend" / "tests").mkdir()
    (tmp_path / "frontend" / "tests" / "widget.test.ts").write_text(
        "test('widget', () => {});\n",
        encoding="utf-8",
    )


def test_repository_recommendation_fixture_cases_stay_stable() -> None:
    fixture_path = _REPO_ROOT / "evals" / "fixtures" / "recommendation_cases.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert fixture["manifest_version"] == 1
    for case in fixture["cases"]:
        _assert_recommendation_fixture_case(case)


def _assert_recommendation_fixture_case(case: dict[str, Any]) -> None:
    report = recommend_eval_change_impact(
        _REPO_ROOT,
        touched_paths=case["touched_paths"],
    )
    release_gate_commands = [
        command
        for surface in report.release_surfaces
        for command in surface.release_gate_commands
    ]
    warning_text = "\n".join(report.warnings)

    assert _contains_all(
        [recommendation.case_id for recommendation in report.cases],
        case.get("expected_case_ids", []),
    ), case["case_id"]
    assert _contains_all(
        [recommendation.profile_id for recommendation in report.profiles],
        case.get("expected_profile_ids", []),
    ), case["case_id"]
    assert _contains_all(
        [recipe.recipe_id for recipe in report.recipes],
        case.get("expected_recipe_ids", []),
    ), case["case_id"]
    assert _contains_all(
        [group.group for group in report.reason_groups],
        case.get("expected_reason_groups", []),
    ), case["case_id"]
    assert _contains_all(
        release_gate_commands,
        case.get("expected_release_gate_commands", []),
    ), case["case_id"]
    assert _contains_all(
        report.fallback_policy_commands,
        case.get("expected_fallback_policy_commands", []),
    ), case["case_id"]
    for warning_fragment in case.get("expected_warning_fragments", []):
        assert warning_fragment in warning_text, case["case_id"]


def _contains_all(actual: list[str], expected: list[str]) -> bool:
    return all(value in actual for value in expected)
