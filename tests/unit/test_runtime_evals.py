"""Unit tests for replay-backed eval case schema and discovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from glassbox.runtime.evals import (
    DEFAULT_EVAL_BUNDLES_DIR,
    EvalCaseExpectation,
    discover_eval_case_files,
    load_eval_case,
    load_eval_suite,
)


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
    assert case.expectation.selected_invariants() == (
        "transcript",
        "tool_calls",
        "approvals",
        "questions",
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
