"""Unit tests for handoff redaction preview helpers."""

from glassbox.runtime.handoff_redaction_preview import _redaction_marker_summary


def test_redaction_preview_detects_workspace_and_secret_markers() -> None:
    count, categories = _redaction_marker_summary(
        {
            "cwd": "<workspace-root>/project",
            "note": "OPENAI_API_KEY=<redacted>",
            "nested": ["safe", {"path": "<workspace-root>/logs/output.txt"}],
        }
    )

    assert count == 3
    assert categories == ["workspace-path", "secret-like-token"]
