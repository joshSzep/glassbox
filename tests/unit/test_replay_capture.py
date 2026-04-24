"""Unit tests for replay enriched-context manifests."""

from glassbox.runtime.replay_capture import (
    build_replay_enriched_context_sources,
    fingerprint_replay_enriched_context_sources,
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
    ]
    assert [source.provenance_class for source in sources_a] == [
        "recomputed_summary",
        "persisted_session_state",
        "recomputed_summary",
    ]
    assert sources_a[1].inherited is True
    assert sources_a[2].additional_item_count == 1


def test_enriched_context_source_fingerprint_catches_meaningful_source_change() -> None:
    baseline_payload = {
        "repo_context": "Workspace: glassbox\nHigh-signal paths: README.md, src/",
        "memory_notes": ["[operator] Stay inside src/glassbox"],
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
    assert baseline_sources[-1].source_name == "working_set"
    assert baseline_sources[-1].fingerprint != changed_sources[-1].fingerprint
