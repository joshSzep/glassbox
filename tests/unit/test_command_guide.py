"""Unit coverage for command-guide formatting boundaries."""

from typing import cast

from glassbox.cli.command_guide_json import command_guide_json_payload
from glassbox.cli.command_guide_render import format_command_guide
from glassbox.cli.command_guide_workflows import sections_for_workflow
from glassbox.cli.parser import build_parser


def test_command_guide_renderer_preserves_terminal_contract() -> None:
    rendered = format_command_guide()

    assert rendered.startswith("Glassbox command guide")
    assert "Start Work" in rendered
    assert "glassbox readiness check --cwd ." in rendered
    assert "glassbox repo status --cwd ." in rendered
    assert "glassbox repo refresh --cwd ." in rendered
    assert "glassbox repo path PATH --cwd ." in rendered
    assert "glassbox queue list --view action-needed --cwd ." in rendered
    assert "glassbox queue list --view maintenance --cwd ." in rendered
    assert "safe next actions and evidence references" in rendered
    assert "recovery playbooks linked to degraded maintenance cues" in rendered
    assert "glassbox session evidence-graph SESSION_ID --summary --cwd ." in rendered
    assert "Review Loop Maturity" in rendered
    assert "glassbox changeset create --from workspace-diff" in rendered
    assert "does not stage, commit, push, or open a PR" in rendered
    assert "glassbox changeset refresh CHANGESET_ID --cwd ." in rendered
    assert "glassbox changeset feedback add CHANGESET_ID" in rendered
    assert "glassbox changeset feedback status CHANGESET_ID --cwd ." in rendered
    assert "response-linked fixup inventory posture" in rendered
    assert "before recording fixup evidence" in rendered
    assert "glassbox changeset feedback fixup FEEDBACK_ID --cwd ." in rendered
    assert "glassbox changeset feedback accept-risk FEEDBACK_ID" in rendered
    assert (
        "glassbox changeset evidence-graph CHANGESET_ID --summary --cwd ." in rendered
    )
    assert "Local Handoff" in rendered
    assert (
        "glassbox handoff prepare session SESSION_ID handoff.json --cwd ." in rendered
    )
    assert "glassbox handoff inspect handoff.json --cwd ." in rendered
    assert "Legacy session export remains a supported alias" in rendered
    assert "--capture-state not_run --skip-reason REASON" in rendered
    assert "without inventing a viewport or calling it a pass" in rendered
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
    handoff_sections = sections_for_workflow("handoff")

    assert [section.key for section in recovery_sections] == [
        "unblock-work",
        "long-run-recovery",
        "compaction",
        "tool-attempts",
    ]
    assert [section.key for section in review_sections] == ["review-loop"]
    assert [section.key for section in handoff_sections] == [
        "checkpoint-inspection",
        "local-handoff",
        "review-loop",
    ]


def test_handoff_command_family_parser_covers_v17_workflow() -> None:
    parser = build_parser()

    prepare_session = parser.parse_args(
        [
            "handoff",
            "prepare",
            "session",
            "00000000-0000-0000-0000-000000000111",
            "handoff.json",
            "--intent",
            "future-self",
            "--recipient",
            "next operator",
            "--preview",
            "--cwd",
            ".",
        ]
    )
    assert prepare_session.command == "handoff"
    assert prepare_session.handoff_command == "prepare"
    assert prepare_session.handoff_prepare_source == "session"
    assert prepare_session.intent == "future-self"
    assert prepare_session.preview is True

    prepare_changeset = parser.parse_args(
        [
            "handoff",
            "prepare",
            "changeset",
            "00000000-0000-0000-0000-000000000222",
            "changeset-review.json",
            "--format",
            "json+markdown",
            "--cwd",
            ".",
        ]
    )
    assert prepare_changeset.handoff_prepare_source == "changeset"
    assert prepare_changeset.format == "json+markdown"

    inspect = parser.parse_args(
        ["handoff", "inspect", "handoff.json", "--markdown", "--cwd", "."]
    )
    assert inspect.handoff_command == "inspect"
    assert inspect.package == "handoff.json"
    assert inspect.markdown is True

    imported = parser.parse_args(["handoff", "import", "handoff.json", "--cwd", "."])
    assert imported.handoff_command == "import"
    assert imported.package == "handoff.json"
