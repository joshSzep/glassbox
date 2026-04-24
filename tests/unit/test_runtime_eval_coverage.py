"""Unit tests for eval capability coverage manifests and audits."""

import json
from pathlib import Path

import pytest

from glassbox.runtime.eval_coverage import EvalCoverageManifest
from glassbox.runtime.eval_coverage import audit_eval_coverage
from glassbox.runtime.eval_coverage import load_eval_coverage_manifest


def test_load_eval_coverage_manifest_supports_multi_case_capabilities(
    tmp_path: Path,
) -> None:
    _write_eval_coverage(
        tmp_path,
        [
            {
                "capability_id": "artifact_backed_context",
                "title": "Artifact-backed context",
                "criticality": "important",
                "verification_stages": ["advisory"],
                "coverage_mode": "multi_case",
                "expected_case_ids": [
                    "context.artifact",
                    "context.artifact-relaxed",
                ],
            }
        ],
    )

    manifest = load_eval_coverage_manifest(tmp_path)

    assert manifest == EvalCoverageManifest.model_validate(
        {
            "manifest_version": 1,
            "capabilities": [
                {
                    "capability_id": "artifact_backed_context",
                    "title": "Artifact-backed context",
                    "criticality": "important",
                    "verification_stages": ["advisory"],
                    "coverage_mode": "multi_case",
                    "expected_case_ids": [
                        "context.artifact",
                        "context.artifact-relaxed",
                    ],
                }
            ],
        }
    )


def test_load_eval_coverage_manifest_rejects_invalid_multi_case_definition(
    tmp_path: Path,
) -> None:
    _write_eval_coverage(
        tmp_path,
        [
            {
                "capability_id": "artifact_backed_context",
                "title": "Artifact-backed context",
                "verification_stages": ["advisory"],
                "coverage_mode": "multi_case",
                "expected_case_ids": ["context.artifact"],
            }
        ],
    )

    with pytest.raises(ValueError, match="multi_case coverage_mode"):
        load_eval_coverage_manifest(tmp_path)


def test_audit_eval_coverage_reports_gaps_unmapped_and_redundancy(
    tmp_path: Path,
) -> None:
    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        tags=["smoke"],
        capabilities=["smoke_validation", "replay_portability"],
        verification_stages=["commit-time"],
    )
    _write_eval_case(
        tmp_path,
        case_id="smoke.extra",
        tags=["smoke"],
        capabilities=["smoke_validation"],
        verification_stages=["commit-time"],
    )
    _write_eval_case(
        tmp_path,
        case_id="branching.case",
        tags=["context"],
        capabilities=["branching"],
        verification_stages=["commit-time"],
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
    _write_eval_coverage(
        tmp_path,
        [
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
                "expected_case_ids": ["branching.case"],
            },
        ],
    )

    result = audit_eval_coverage(tmp_path, profile_id="commit-smoke")

    assert result.audited_case_ids == ["smoke.extra", "smoke.readme"]
    assert result.capability_count == 2
    assert result.covered_capability_count == 1
    assert result.uncovered_capability_count == 1
    assert result.uncovered_release_critical_capability_ids == ["branching"]
    assert result.unmapped_case_ids == ["smoke.extra"]
    assert result.redundant_case_ids == ["smoke.extra"]


def test_audit_eval_coverage_rejects_unknown_expected_case_id(tmp_path: Path) -> None:
    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        tags=["smoke"],
        capabilities=["smoke_validation"],
        verification_stages=["commit-time"],
    )
    _write_eval_coverage(
        tmp_path,
        [
            {
                "capability_id": "approval_flow",
                "title": "Approval flow",
                "criticality": "release-critical",
                "verification_stages": ["release-candidate"],
                "expected_case_ids": ["missing.case"],
            }
        ],
    )

    with pytest.raises(ValueError, match="unknown eval case id"):
        audit_eval_coverage(tmp_path)


def _write_eval_case(
    workspace_root: Path,
    *,
    case_id: str,
    tags: list[str],
    capabilities: list[str],
    verification_stages: list[str],
) -> Path:
    case_path = workspace_root / "evals" / "cases" / f"{case_id}.json"
    case_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path = workspace_root / "evals" / "bundles" / f"{case_id}.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text("{}\n", encoding="utf-8")
    payload = {
        "manifest_version": 1,
        "case_id": case_id,
        "title": case_id,
        "bundle_path": f"../bundles/{case_id}.json",
        "tags": tags,
        "release_contract": {
            "capabilities": capabilities,
            "verification_stages": verification_stages,
        },
    }
    case_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
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


def _write_eval_coverage(
    workspace_root: Path,
    capabilities: list[dict[str, object]],
) -> Path:
    coverage_path = workspace_root / "evals" / "coverage.json"
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest_version": 1,
        "capabilities": capabilities,
    }
    coverage_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return coverage_path
