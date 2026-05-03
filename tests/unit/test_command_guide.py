"""Unit coverage for command-guide formatting boundaries."""

from typing import cast

from glassbox.cli.command_guide_json import command_guide_json_payload
from glassbox.cli.command_guide_render import format_command_guide
from glassbox.cli.command_guide_workflows import sections_for_workflow


def test_command_guide_renderer_preserves_terminal_contract() -> None:
    rendered = format_command_guide()

    assert rendered.startswith("Glassbox command guide")
    assert "Start Work" in rendered
    assert "glassbox readiness check --cwd ." in rendered
    assert "Review Loop" in rendered
    assert "glassbox changeset feedback status CHANGESET_ID --cwd ." in rendered
    assert "Use `glassbox command tree`" in rendered


def test_command_guide_json_preserves_payload_shape() -> None:
    payload = command_guide_json_payload()

    assert payload["schema_version"] == 1
    sections = cast(list[dict[str, object]], payload["sections"])
    first_section = sections[0]
    commands = cast(list[dict[str, str]], first_section["commands"])
    assert first_section["key"] == "start-work"
    assert commands[0] == {
        "command": "glassbox readiness check --cwd .",
        "purpose": "Check first-run workspace readiness and get next actions.",
    }


def test_command_guide_workflows_group_related_sections() -> None:
    recovery_sections = sections_for_workflow("recovery")
    review_sections = sections_for_workflow("review")

    assert [section.key for section in recovery_sections] == [
        "unblock-work",
        "long-run-recovery",
        "compaction",
        "tool-attempts",
    ]
    assert [section.key for section in review_sections] == ["review-loop"]
