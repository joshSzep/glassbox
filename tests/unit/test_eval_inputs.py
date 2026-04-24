"""Focused tests for eval suite input loading and output shaping."""

import json
from pathlib import Path

import pytest

from glassbox.runtime.eval_inputs import load_json_file
from glassbox.runtime.eval_inputs import refresh_eval_output_dir
from glassbox.runtime.eval_inputs import resolve_eval_output_dir
from glassbox.runtime.eval_inputs import resolve_eval_suite_input
from glassbox.runtime.evals import EvalSuiteSelection


def test_resolve_eval_output_dir_uses_explicit_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "custom-output"

    resolved = resolve_eval_output_dir(tmp_path, output_dir=output_dir)

    assert resolved == output_dir.resolve()


def test_refresh_eval_output_dir_rejects_paths_outside_managed_root(
    tmp_path: Path,
) -> None:
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    with pytest.raises(
        ValueError,
        match="--refresh-output-dir requires an output directory under .glassbox/evals",
    ):
        refresh_eval_output_dir(tmp_path, output_dir=outside_dir)


def test_load_json_file_reads_object_payload(tmp_path: Path) -> None:
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps({"profile_id": "commit-smoke", "count": 2}) + "\n",
        encoding="utf-8",
    )

    assert load_json_file(payload_path) == {"profile_id": "commit-smoke", "count": 2}


def test_resolve_eval_suite_input_raises_for_empty_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "glassbox.runtime.eval_inputs.resolve_eval_suite_selection",
        lambda *_args, **_kwargs: EvalSuiteSelection(profile=None, cases=[]),
    )

    with pytest.raises(ValueError, match="no eval cases selected"):
        resolve_eval_suite_input(tmp_path)


def test_resolve_eval_suite_input_allows_empty_selection_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = EvalSuiteSelection(profile=None, cases=[])
    monkeypatch.setattr(
        "glassbox.runtime.eval_inputs.resolve_eval_suite_selection",
        lambda *_args, **_kwargs: selection,
    )

    suite_input = resolve_eval_suite_input(tmp_path, require_cases=False)

    assert suite_input.selection == selection
