"""Unit tests for replay/eval change-impact recommendations."""

import json
from pathlib import Path

from glassbox.runtime.eval_recommendations import recommend_eval_change_impact


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
                    }
                ],
            },
            indent=2,
        )
        + "\n",
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
                    }
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
                    }
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
