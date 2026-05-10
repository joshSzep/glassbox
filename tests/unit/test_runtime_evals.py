"""Unit tests for replay-backed eval case schema and discovery."""

import json
from pathlib import Path

import pytest
from scripts.validate_v6_release_gate import build_gate_stages

from glassbox.runtime.evals import DEFAULT_EVAL_BUNDLES_DIR
from glassbox.runtime.evals import EvalCaseExpectation
from glassbox.runtime.evals import EvalCaseReleaseContract
from glassbox.runtime.evals import EvalProfileBudget
from glassbox.runtime.evals import EvalProfileDefinition
from glassbox.runtime.evals import discover_eval_case_files
from glassbox.runtime.evals import load_eval_case
from glassbox.runtime.evals import load_eval_profile
from glassbox.runtime.evals import load_eval_profiles
from glassbox.runtime.evals import load_eval_suite
from glassbox.runtime.evals import resolve_eval_suite_selection

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_load_eval_case_defaults_to_exact_match_expectation(tmp_path: Path) -> None:
    case_path = _write_eval_case(
        tmp_path,
        "smoke.readme",
        {
            "case_id": "smoke.readme",
            "title": "README inspection stays stable",
            "bundle_path": "../bundles/readme.json",
            "tags": ["Smoke", "tooling"],
        },
    )

    case = load_eval_case(case_path, workspace_root=tmp_path)

    assert case.case_id == "smoke.readme"
    assert case.tags == ["smoke", "tooling"]
    assert case.bundle_path == (tmp_path / DEFAULT_EVAL_BUNDLES_DIR / "readme.json")
    assert case.expectation == EvalCaseExpectation()
    assert case.release_contract == EvalCaseReleaseContract()
    assert case.expectation.selected_invariants() == (
        "transcript",
        "tool_calls",
        "approvals",
        "questions",
        "cancellations",
        "event_families",
        "final_state",
    )


def test_load_eval_case_supports_selected_invariants(tmp_path: Path) -> None:
    case_path = _write_eval_case(
        tmp_path,
        "approval.final-state",
        {
            "case_id": "approval.final-state",
            "title": "Approval flow keeps the same final state",
            "bundle_path": "../bundles/approval.json",
            "tags": ["approval"],
            "expectation": {
                "mode": "selected_invariants",
                "invariants": ["final_state", "transcript", "final_state"],
            },
        },
    )

    case = load_eval_case(case_path, workspace_root=tmp_path)

    assert case.expectation.mode == "selected_invariants"
    assert case.expectation.selected_invariants() == ("final_state", "transcript")


def test_load_eval_case_supports_release_contract_metadata(tmp_path: Path) -> None:
    case_path = _write_eval_case(
        tmp_path,
        "context.branch-inherited",
        {
            "case_id": "context.branch-inherited",
            "title": "Forked child context stays replay-stable",
            "bundle_path": "../bundles/context.branch-inherited.json",
            "release_contract": {
                "owner": "Runtime.Context",
                "capabilities": ["branching", "context_inheritance", "branching"],
                "severity": "high",
                "verification_stages": [
                    "commit-time",
                    "push-time",
                    "commit-time",
                ],
                "baseline_refresh_policy": "review_required",
            },
        },
    )

    case = load_eval_case(case_path, workspace_root=tmp_path)

    assert case.release_contract.owner == "runtime.context"
    assert case.release_contract.capabilities == [
        "branching",
        "context_inheritance",
    ]
    assert case.release_contract.severity == "high"
    assert case.release_contract.verification_stages == [
        "commit-time",
        "push-time",
    ]
    assert case.release_contract.baseline_refresh_policy == "review_required"


def test_load_eval_case_rejects_invalid_expectation_shape(tmp_path: Path) -> None:
    case_path = _write_eval_case(
        tmp_path,
        "invalid.expectation",
        {
            "case_id": "invalid.expectation",
            "title": "Invalid expectation",
            "bundle_path": "../bundles/invalid.json",
            "expectation": {
                "mode": "selected_invariants",
            },
        },
    )

    with pytest.raises(ValueError, match="selected_invariants expectation"):
        load_eval_case(case_path, workspace_root=tmp_path)


def test_load_eval_case_rejects_incompatible_release_contract(tmp_path: Path) -> None:
    case_path = _write_eval_case(
        tmp_path,
        "invalid.release-contract",
        {
            "case_id": "invalid.release-contract",
            "title": "Invalid release contract",
            "bundle_path": "../bundles/invalid.json",
            "release_contract": {
                "verification_stages": ["commit-time"],
                "baseline_refresh_policy": "advisory",
            },
        },
    )

    with pytest.raises(ValueError, match="advisory baseline_refresh_policy"):
        load_eval_case(case_path, workspace_root=tmp_path)


def test_load_eval_case_rejects_bundle_paths_outside_workspace(tmp_path: Path) -> None:
    case_path = _write_eval_case(
        tmp_path,
        "invalid.path",
        {
            "case_id": "invalid.path",
            "title": "Invalid path",
            "bundle_path": "../../../outside.json",
        },
        create_bundle=False,
    )

    with pytest.raises(
        ValueError,
        match="eval bundle path must stay within workspace root",
    ):
        load_eval_case(case_path, workspace_root=tmp_path)


def test_discover_eval_case_files_only_reads_eval_case_layout(tmp_path: Path) -> None:
    first_case = _write_eval_case(
        tmp_path,
        "smoke.first",
        {
            "case_id": "smoke.first",
            "title": "First",
            "bundle_path": "../../bundles/first.json",
        },
        relative_case_path=Path("smoke") / "first.json",
    )
    second_case = _write_eval_case(
        tmp_path,
        "tooling.second",
        {
            "case_id": "tooling.second",
            "title": "Second",
            "bundle_path": "../../bundles/second.json",
        },
        relative_case_path=Path("tooling") / "second.json",
    )
    bundle_only_path = tmp_path / DEFAULT_EVAL_BUNDLES_DIR / "bundle-only.json"
    bundle_only_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_only_path.write_text("{}\n", encoding="utf-8")

    discovered = discover_eval_case_files(tmp_path)

    assert discovered == [first_case.resolve(), second_case.resolve()]


def test_load_eval_suite_filters_by_tags_and_case_ids(tmp_path: Path) -> None:
    _write_eval_case(
        tmp_path,
        "smoke.readme",
        {
            "case_id": "smoke.readme",
            "title": "README smoke",
            "bundle_path": "../bundles/readme.json",
            "tags": ["smoke", "tooling"],
        },
    )
    _write_eval_case(
        tmp_path,
        "approval.patch",
        {
            "case_id": "approval.patch",
            "title": "Patch approval",
            "bundle_path": "../bundles/patch.json",
            "tags": ["approval", "tooling"],
        },
    )
    _write_eval_case(
        tmp_path,
        "provider.text-only",
        {
            "case_id": "provider.text-only",
            "title": "Text only",
            "bundle_path": "../bundles/text-only.json",
            "tags": ["provider-mode"],
        },
    )

    tooling_cases = load_eval_suite(tmp_path, tags=["tooling"])
    selected_cases = load_eval_suite(
        tmp_path,
        case_ids=["approval.patch", "smoke.readme"],
    )

    assert [case.case_id for case in tooling_cases] == [
        "approval.patch",
        "smoke.readme",
    ]
    assert [case.case_id for case in selected_cases] == [
        "approval.patch",
        "smoke.readme",
    ]


def test_load_eval_suite_rejects_unknown_case_id(tmp_path: Path) -> None:
    _write_eval_case(
        tmp_path,
        "smoke.readme",
        {
            "case_id": "smoke.readme",
            "title": "README smoke",
            "bundle_path": "../bundles/readme.json",
        },
    )

    with pytest.raises(ValueError, match="unknown eval case id"):
        load_eval_suite(tmp_path, case_ids=["missing.case"])


def test_load_eval_profile_reads_named_repository_profile(tmp_path: Path) -> None:
    _write_eval_profiles(
        tmp_path,
        [
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            }
        ],
    )

    profile = load_eval_profile(tmp_path, profile_id="commit-smoke")

    assert profile == EvalProfileDefinition(
        profile_id="commit-smoke",
        title="Commit smoke",
        verification_stage="commit-time",
        tags=["smoke"],
        blocking=True,
    )


def test_load_eval_profile_reads_budget_metadata(tmp_path: Path) -> None:
    _write_eval_profiles(
        tmp_path,
        [
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
                "budget": {
                    "max_selected_case_count": 2,
                    "max_selected_invariant_case_count": 1,
                    "max_recorded_model_call_count": 4,
                    "max_case_artifact_bytes": 50000,
                    "allow_unsupported_cases": False,
                    "allow_advisory_cases": False,
                    "promotion_policy": (
                        "Promote only cases that stay deterministic in pre-commit."
                    ),
                    "demotion_policy": (
                        "Demote cases that need repeated baseline refreshes "
                        "or relaxed invariants."
                    ),
                },
            }
        ],
    )

    profile = load_eval_profile(tmp_path, profile_id="commit-smoke")

    assert profile.budget == EvalProfileBudget(
        max_selected_case_count=2,
        max_selected_invariant_case_count=1,
        max_recorded_model_call_count=4,
        max_case_artifact_bytes=50000,
        allow_unsupported_cases=False,
        allow_advisory_cases=False,
        promotion_policy="Promote only cases that stay deterministic in pre-commit.",
        demotion_policy=(
            "Demote cases that need repeated baseline refreshes or relaxed invariants."
        ),
    )


def test_load_eval_profile_reads_live_provider_canary_track_metadata(
    tmp_path: Path,
) -> None:
    _write_eval_profiles(
        tmp_path,
        [
            {
                "profile_id": "live-provider-canary",
                "title": "Live provider canary",
                "description": "Optional live-provider comparison scaffold.",
                "verification_stage": "advisory",
                "track": "live-provider-canary",
                "blocking": False,
                "tags": ["live-provider"],
            }
        ],
    )

    profile = load_eval_profile(tmp_path, profile_id="live-provider-canary")

    assert profile == EvalProfileDefinition(
        profile_id="live-provider-canary",
        title="Live provider canary",
        description="Optional live-provider comparison scaffold.",
        verification_stage="advisory",
        track="live-provider-canary",
        blocking=False,
        tags=["live-provider"],
    )


def test_load_eval_profiles_filters_by_track(tmp_path: Path) -> None:
    _write_eval_profiles(
        tmp_path,
        [
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
            },
        ],
    )

    profiles = load_eval_profiles(tmp_path, track="live-provider-canary")

    assert [profile.profile_id for profile in profiles] == ["live-provider-canary"]


def test_load_eval_profile_rejects_blocking_live_provider_canary_profile(
    tmp_path: Path,
) -> None:
    _write_eval_profiles(
        tmp_path,
        [
            {
                "profile_id": "bad-canary",
                "title": "Bad canary",
                "verification_stage": "advisory",
                "track": "live-provider-canary",
                "blocking": True,
            }
        ],
    )

    with pytest.raises(ValueError, match="must stay non-blocking"):
        load_eval_profile(tmp_path, profile_id="bad-canary")


def test_repository_eval_profiles_align_with_v6_gate_stages() -> None:
    profiles = {
        profile.profile_id: profile for profile in load_eval_profiles(REPO_ROOT)
    }
    provider_profiles = {
        profile.profile_id: profile
        for profile in load_eval_profiles(REPO_ROOT, track="live-provider-canary")
    }
    stage_labels = {stage.label for stage in build_gate_stages()}

    assert profiles["commit-smoke"].verification_stage == "commit-time"
    assert profiles["commit-smoke"].blocking is True
    assert profiles["push-confirmation"].verification_stage == "push-time"
    assert profiles["push-confirmation"].blocking is True
    assert profiles["release-candidate"].verification_stage == "release-candidate"
    assert profiles["release-candidate"].blocking is True
    assert profiles["release-candidate"].budget is not None
    assert profiles["release-candidate"].budget.max_selected_case_count == 30
    assert profiles["release-candidate"].budget.allow_advisory_cases is False
    assert provider_profiles["live-provider-canary"].blocking is False
    assert provider_profiles["live-provider-canary"].track == "live-provider-canary"
    assert {
        "deterministic eval smoke",
        "frontend generated API freshness",
        "frontend static asset validation",
        "package contents validation",
    }.issubset(stage_labels)


def test_repository_release_candidate_profile_includes_promoted_v8_autonomy_cases() -> (
    None
):
    cases = load_eval_suite(REPO_ROOT, profile_id="release-candidate")
    case_ids = {case.case_id for case in cases}

    assert {
        "autonomy.budget-exhaustion",
        "verification.success",
        "verification.failure",
        "branch-search.candidate-comparison",
    }.issubset(case_ids)
    assert "task-plan.proposal-capture" not in case_ids
    assert "task.continuation-blocked" not in case_ids
    assert "memory.context-drift" not in case_ids
    assert "repository-index.context-drift" not in case_ids
    assert all(
        case.release_contract.baseline_refresh_policy != "advisory" for case in cases
    )


def test_repository_release_candidate_profile_includes_v10_long_run_cases() -> None:
    cases = load_eval_suite(REPO_ROOT, profile_id="release-candidate")
    case_ids = {case.case_id for case in cases}
    capabilities = {
        capability
        for case in cases
        for capability in case.release_contract.capabilities
    }

    assert {
        "long-run.recovery-boundaries",
        "context.compaction-provenance",
        "tool-attempt.partial-retry",
        "verification.stale-cockpit",
        "long-run.cockpit-summary",
    }.issubset(case_ids)
    assert {
        "incomplete_turn_recovery",
        "checkpoint_resume_recovery",
        "context_compaction_provenance",
        "stale_compaction_exclusion",
        "tool_attempt_partial_output",
        "tool_attempt_safe_retry",
        "stale_verification_warning",
        "long_run_cockpit_summary",
    }.issubset(capabilities)
    assert len(cases) >= 13


def test_repository_release_candidate_profile_includes_v11_confidence_cases() -> None:
    cases = load_eval_suite(REPO_ROOT, profile_id="release-candidate")
    case_ids = {case.case_id for case in cases}
    capabilities = {
        capability
        for case in cases
        for capability in case.release_contract.capabilities
    }

    assert {
        "recommendation.release-path",
        "context.compaction-cap-guidance",
        "checkpoint.absence-explanation",
        "knowledge.posture-summary",
        "branch-search.decision-support",
    }.issubset(case_ids)
    assert {
        "verification_recommendation_explainability",
        "compaction_range_guardrail",
        "checkpoint_absence_explanation",
        "knowledge_posture_summary",
        "branch_search_decision_support",
    }.issubset(capabilities)
    assert len(cases) >= 18


def test_repository_release_candidate_profile_includes_v12_changeset_cases() -> None:
    cases = load_eval_suite(REPO_ROOT, profile_id="release-candidate")
    case_ids = {case.case_id for case in cases}
    capabilities = {
        capability
        for case in cases
        for capability in case.release_contract.capabilities
    }

    assert {
        "changeset.reviewable-lifecycle",
        "changeset.branch-candidate-adoption",
    }.issubset(case_ids)
    assert {
        "changeset_creation",
        "change_inventory_provenance",
        "changeset_stale_verification_readiness",
        "changeset_review_brief_generation",
        "changeset_commit_readiness",
        "changeset_command_evidence",
        "changeset_branch_candidate_adoption",
    }.issubset(capabilities)
    assert len(cases) >= 20


def test_repository_release_candidate_profile_includes_v13_review_loop_cases() -> None:
    cases = load_eval_suite(REPO_ROOT, profile_id="release-candidate")
    case_ids = {case.case_id for case in cases}
    capabilities = {
        capability
        for case in cases
        for capability in case.release_contract.capabilities
    }

    assert {
        "changeset.review-loop-lifecycle",
        "changeset.in-session-review-ux",
    }.issubset(case_ids)
    assert {
        "review_feedback_creation",
        "review_response_tracking",
        "manual_evidence_inbox",
        "review_fixup_stale_verification",
        "review_lifecycle_brief_generation",
        "handoff_readiness",
        "publication_boundary_non_claims",
        "in_session_review_entrypoints",
        "dashboard_review_quick_actions",
    }.issubset(capabilities)
    assert len(cases) >= 22


def test_repository_release_candidate_profile_includes_v14_maturity_cases() -> None:
    cases = load_eval_suite(REPO_ROOT, profile_id="release-candidate")
    case_ids = {case.case_id for case in cases}
    capabilities = {
        capability
        for case in cases
        for capability in case.release_contract.capabilities
    }

    assert {
        "changeset.lifecycle-rich-evidence",
        "changeset.response-linked-fixup-inventory",
        "changeset.skipped-advisory-evidence-posture",
    }.issubset(case_ids)
    assert {
        "review_lifecycle_rich_evidence",
        "response_linked_fixup_inventory",
        "skipped_advisory_evidence_posture",
    }.issubset(capabilities)
    assert len(cases) >= 25


def test_repository_release_candidate_profile_includes_v15_intelligence_cases() -> None:
    cases = load_eval_suite(REPO_ROOT, profile_id="release-candidate")
    case_ids = {case.case_id for case in cases}
    capabilities = {
        capability
        for case in cases
        for capability in case.release_contract.capabilities
    }

    assert {
        "repository-intelligence.snapshot-rich",
        "repository-intelligence.path-verification",
        "repository-intelligence.stale-degradation",
        "repository-intelligence.memory-command",
        "repository-intelligence.context-drift",
    }.issubset(case_ids)
    assert {
        "repository_intelligence_snapshot_generation",
        "repository_intelligence_path_verification",
        "repository_intelligence_stale_degradation",
        "repository_intelligence_memory_command_recommendation",
        "repository_intelligence_context_drift",
    }.issubset(capabilities)
    assert len(cases) == 30


def test_resolve_eval_suite_selection_applies_profile_before_extra_tag_filter(
    tmp_path: Path,
) -> None:
    _write_eval_case(
        tmp_path,
        "smoke.readme",
        {
            "case_id": "smoke.readme",
            "title": "README smoke",
            "bundle_path": "../bundles/readme.json",
            "tags": ["smoke", "tooling"],
            "release_contract": {
                "verification_stages": ["commit-time", "push-time"],
            },
        },
    )
    _write_eval_case(
        tmp_path,
        "smoke.context",
        {
            "case_id": "smoke.context",
            "title": "Context smoke",
            "bundle_path": "../bundles/context.json",
            "tags": ["smoke", "context"],
            "release_contract": {
                "verification_stages": ["commit-time"],
            },
        },
    )
    _write_eval_profiles(
        tmp_path,
        [
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            }
        ],
    )

    selection = resolve_eval_suite_selection(
        tmp_path,
        profile_id="commit-smoke",
        tags=["context"],
    )

    assert selection.profile is not None
    assert selection.profile.profile_id == "commit-smoke"
    assert [case.case_id for case in selection.cases] == ["smoke.context"]


def test_load_eval_suite_rejects_case_id_outside_selected_profile(
    tmp_path: Path,
) -> None:
    _write_eval_case(
        tmp_path,
        "smoke.readme",
        {
            "case_id": "smoke.readme",
            "title": "README smoke",
            "bundle_path": "../bundles/readme.json",
            "tags": ["smoke"],
            "release_contract": {
                "verification_stages": ["commit-time"],
            },
        },
    )
    _write_eval_case(
        tmp_path,
        "approval.patch",
        {
            "case_id": "approval.patch",
            "title": "Patch approval",
            "bundle_path": "../bundles/patch.json",
            "tags": ["approval"],
            "release_contract": {
                "verification_stages": ["push-time"],
            },
        },
    )
    _write_eval_profiles(
        tmp_path,
        [
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            }
        ],
    )

    with pytest.raises(ValueError, match="does not select eval case id"):
        load_eval_suite(
            tmp_path,
            profile_id="commit-smoke",
            case_ids=["approval.patch"],
        )


def test_load_eval_suite_allows_blocking_profile_selection_with_advisory_case(
    tmp_path: Path,
) -> None:
    _write_eval_case(
        tmp_path,
        "context.relaxed",
        {
            "case_id": "context.relaxed",
            "title": "Relaxed advisory case",
            "bundle_path": "../bundles/context.json",
            "tags": ["context"],
            "release_contract": {
                "verification_stages": ["advisory"],
                "baseline_refresh_policy": "advisory",
            },
        },
    )
    _write_eval_profiles(
        tmp_path,
        [
            {
                "profile_id": "advisory-context",
                "title": "Bad blocking advisory profile",
                "verification_stage": "advisory",
                "tags": ["context"],
                "blocking": True,
            }
        ],
    )

    cases = load_eval_suite(tmp_path, profile_id="advisory-context")

    assert [case.case_id for case in cases] == ["context.relaxed"]


def test_load_eval_suite_profile_without_explicit_cases_filters_by_stage(
    tmp_path: Path,
) -> None:
    _write_eval_case(
        tmp_path,
        "context.release",
        {
            "case_id": "context.release",
            "title": "Release candidate context",
            "bundle_path": "../bundles/release.json",
            "tags": ["context"],
            "release_contract": {
                "verification_stages": ["release-candidate"],
            },
        },
    )
    _write_eval_case(
        tmp_path,
        "context.advisory",
        {
            "case_id": "context.advisory",
            "title": "Advisory context",
            "bundle_path": "../bundles/advisory.json",
            "tags": ["context"],
            "release_contract": {
                "verification_stages": ["advisory"],
                "baseline_refresh_policy": "advisory",
            },
        },
    )
    _write_eval_profiles(
        tmp_path,
        [
            {
                "profile_id": "release-candidate",
                "title": "Release candidate",
                "verification_stage": "release-candidate",
                "blocking": True,
            }
        ],
    )

    cases = load_eval_suite(tmp_path, profile_id="release-candidate")

    assert [case.case_id for case in cases] == ["context.release"]


def _write_eval_case(
    workspace_root: Path,
    case_id: str,
    payload: dict[str, object],
    *,
    relative_case_path: Path | None = None,
    create_bundle: bool = True,
) -> Path:
    if relative_case_path is None:
        relative_case_path = Path(f"{case_id}.json")

    case_path = workspace_root / "evals" / "cases" / relative_case_path
    case_path.parent.mkdir(parents=True, exist_ok=True)
    case_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if create_bundle:
        bundle_path = payload["bundle_path"]
        assert isinstance(bundle_path, str)
        resolved_bundle_path = (case_path.parent / bundle_path).resolve()
        resolved_bundle_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_bundle_path.write_text("{}\n", encoding="utf-8")

    return case_path


def _write_eval_profiles(
    workspace_root: Path,
    profiles: list[dict[str, object]],
) -> Path:
    profiles_path = workspace_root / "evals" / "profiles.json"
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest_version": 1,
        "profiles": profiles,
    }
    profiles_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return profiles_path
