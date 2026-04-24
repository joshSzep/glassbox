"""Unit tests for replay enriched-context manifests."""

import pytest

from glassbox.runtime.replay_fingerprints import (
    build_replay_enriched_context_sources,
    fingerprint_replay_enriched_context_sources,
)
from glassbox.runtime.replay_manifests import (
    build_replay_turn_output_manifest,
    load_replay_manifest,
)


def test_enriched_context_source_fingerprint_ignores_non_semantic_ordering_noise() -> (
    None
):
    payload_a = {
        "repo_context": "Workspace: glassbox\nHigh-signal paths: README.md, src/",
        "memory_notes": [
            "[operator] Stay inside src/glassbox",
            "[inherited repo] README changed recently",
        ],
        "artifact_context": {
            "summaries": [
                {
                    "summary_kind": "pytest_failure_digest",
                    "source_tool_name": "run_tests",
                    "artifact_kind": "context_pytest_failure_digest",
                    "artifact_path": ".glassbox/sessions/a/artifacts/pytest-a.json",
                    "summary": "2 failing test(s) for tests/unit/test_a.py",
                    "target_paths": ["tests/unit/test_a.py"],
                    "keyword_filter": None,
                    "failing_tests": [
                        "tests/unit/test_a.py::test_one",
                        "tests/unit/test_a.py::test_two",
                    ],
                    "failure_count": 2,
                    "error_count": 0,
                    "timed_out": False,
                    "freshness": "fresh",
                    "inherited": False,
                }
            ],
            "additional_summary_count": 0,
        },
        "working_set": {
            "items": [
                {
                    "subject_kind": "file",
                    "subject": "src/glassbox/runtime/context_builder.py",
                    "summary": "recently targeted workspace path",
                    "reasons": ["recent tool request", "apply_patch targeted file"],
                    "signal_types": ["tool_request_path", "tool_artifact"],
                    "inherited": False,
                },
                {
                    "subject_kind": "note",
                    "subject": "[inherited repo] README changed recently",
                    "summary": "inherited runtime note",
                    "reasons": [
                        "runtime note [inherited repo] README changed recently"
                    ],
                    "signal_types": ["inherited_runtime_note"],
                    "inherited": True,
                },
                {
                    "subject_kind": "artifact",
                    "subject": ".glassbox/sessions/a/artifacts/alpha.json",
                    "summary": "recent test artifact",
                    "reasons": [
                        "context_pytest_failure_digest artifact recorded at "
                        ".glassbox/sessions/a/artifacts/alpha.json"
                    ],
                    "signal_types": ["tool_artifact"],
                    "inherited": False,
                },
            ],
            "additional_item_count": 1,
        },
    }
    payload_b = {
        "repo_context": "Workspace: glassbox\n\nHigh-signal paths: README.md, src/\n",
        "memory_notes": [
            "[inherited repo] README changed recently",
            "[operator] Stay inside src/glassbox",
        ],
        "artifact_context": {
            "summaries": [
                {
                    "summary_kind": "pytest_failure_digest",
                    "source_tool_name": "run_tests",
                    "artifact_kind": "context_pytest_failure_digest",
                    "artifact_path": ".glassbox/sessions/b/artifacts/pytest-b.json",
                    "summary": "2 failing test(s) for tests/unit/test_a.py\n",
                    "target_paths": ["tests/unit/test_a.py"],
                    "keyword_filter": None,
                    "failing_tests": [
                        "tests/unit/test_a.py::test_two",
                        "tests/unit/test_a.py::test_one",
                    ],
                    "failure_count": 2,
                    "error_count": 0,
                    "timed_out": False,
                    "freshness": "fresh",
                    "inherited": False,
                }
            ],
            "additional_summary_count": 0,
        },
        "working_set": {
            "items": [
                {
                    "subject_kind": "note",
                    "subject": "[inherited repo] README changed recently",
                    "summary": "inherited runtime note",
                    "reasons": [
                        "runtime note [inherited repo] README changed recently"
                    ],
                    "signal_types": ["inherited_runtime_note"],
                    "inherited": True,
                },
                {
                    "subject_kind": "file",
                    "subject": "src/glassbox/runtime/context_builder.py",
                    "summary": "recently targeted workspace path",
                    "reasons": ["apply_patch targeted file", "recent tool request"],
                    "signal_types": ["tool_artifact", "tool_request_path"],
                    "inherited": False,
                },
                {
                    "subject_kind": "artifact",
                    "subject": ".glassbox/sessions/b/artifacts/beta.json",
                    "summary": "recent test artifact",
                    "reasons": [
                        "context_pytest_failure_digest artifact recorded at "
                        ".glassbox/sessions/b/artifacts/beta.json"
                    ],
                    "signal_types": ["tool_artifact"],
                    "inherited": False,
                },
            ],
            "additional_item_count": 1,
        },
    }

    sources_a = build_replay_enriched_context_sources(payload_a)
    sources_b = build_replay_enriched_context_sources(payload_b)

    assert fingerprint_replay_enriched_context_sources(sources_a) == (
        fingerprint_replay_enriched_context_sources(sources_b)
    )
    assert [source.source_name for source in sources_a] == [
        "repository_context",
        "runtime_notes",
        "working_set",
        "pytest_failure_digest",
    ]
    assert [source.provenance_class for source in sources_a] == [
        "recomputed_summary",
        "persisted_session_state",
        "recomputed_summary",
        "artifact_backed_summary",
    ]
    assert sources_a[1].inherited is True
    assert sources_a[2].additional_item_count == 1
    assert sources_a[3].summary == "1 artifact-backed summary item"


def test_enriched_context_source_fingerprint_catches_meaningful_source_change() -> None:
    baseline_payload = {
        "repo_context": "Workspace: glassbox\nHigh-signal paths: README.md, src/",
        "memory_notes": ["[operator] Stay inside src/glassbox"],
        "artifact_context": {
            "summaries": [
                {
                    "summary_kind": "pytest_failure_digest",
                    "source_tool_name": "run_tests",
                    "artifact_kind": "context_pytest_failure_digest",
                    "artifact_path": ".glassbox/sessions/a/artifacts/pytest-a.json",
                    "summary": "1 failing test(s) for tests/unit/test_a.py",
                    "target_paths": ["tests/unit/test_a.py"],
                    "keyword_filter": None,
                    "failing_tests": ["tests/unit/test_a.py::test_one"],
                    "failure_count": 1,
                    "error_count": 0,
                    "timed_out": False,
                    "freshness": "fresh",
                    "inherited": False,
                }
            ],
            "additional_summary_count": 0,
        },
        "working_set": {
            "items": [
                {
                    "subject_kind": "file",
                    "subject": "src/glassbox/runtime/context_builder.py",
                    "summary": "recently targeted workspace path",
                    "reasons": ["apply_patch targeted file"],
                    "signal_types": ["tool_request_path"],
                    "inherited": False,
                }
            ],
            "additional_item_count": 0,
        },
    }
    changed_payload = {
        **baseline_payload,
        "artifact_context": {
            "summaries": [
                {
                    "summary_kind": "pytest_failure_digest",
                    "source_tool_name": "run_tests",
                    "artifact_kind": "context_pytest_failure_digest",
                    "artifact_path": ".glassbox/sessions/b/artifacts/pytest-b.json",
                    "summary": "2 failing test(s) for tests/unit/test_a.py",
                    "target_paths": ["tests/unit/test_a.py"],
                    "keyword_filter": None,
                    "failing_tests": [
                        "tests/unit/test_a.py::test_one",
                        "tests/unit/test_a.py::test_two",
                    ],
                    "failure_count": 2,
                    "error_count": 0,
                    "timed_out": False,
                    "freshness": "fresh",
                    "inherited": False,
                }
            ],
            "additional_summary_count": 0,
        },
        "working_set": {
            "items": [
                {
                    "subject_kind": "file",
                    "subject": "src/glassbox/runtime/replay.py",
                    "summary": "recently targeted workspace path",
                    "reasons": ["apply_patch targeted file"],
                    "signal_types": ["tool_request_path"],
                    "inherited": False,
                }
            ],
            "additional_item_count": 0,
        },
    }

    baseline_sources = build_replay_enriched_context_sources(baseline_payload)
    changed_sources = build_replay_enriched_context_sources(changed_payload)

    assert fingerprint_replay_enriched_context_sources(baseline_sources) != (
        fingerprint_replay_enriched_context_sources(changed_sources)
    )
    assert baseline_sources[-2].source_name == "working_set"
    assert baseline_sources[-2].fingerprint != changed_sources[-2].fingerprint
    assert baseline_sources[-1].source_name == "pytest_failure_digest"
    assert baseline_sources[-1].fingerprint != changed_sources[-1].fingerprint


def test_load_replay_manifest_round_trips_turn_output_manifest() -> None:
    manifest = build_replay_turn_output_manifest(
        outcome="failed",
        details={"error_message": "boom"},
    )

    loaded = load_replay_manifest(manifest.model_dump_json())

    assert loaded == manifest


def test_load_replay_manifest_rejects_unknown_artifact_kind() -> None:
    with pytest.raises(ValueError, match="unsupported replay artifact kind"):
        load_replay_manifest('{"artifact_kind": "unexpected"}')
