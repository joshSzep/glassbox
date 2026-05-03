"""Review-loop command guide section data."""

from glassbox.cli.command_guide_models import CommandGuideEntry
from glassbox.cli.command_guide_models import CommandGuideSection

REVIEW_LOOP_COMMAND_GUIDE_SECTION = CommandGuideSection(
    key="review-loop",
    title="Review Loop",
    summary=(
        "Create and continue local changeset review evidence without "
        "publishing mutations."
    ),
    entries=(
        CommandGuideEntry(
            "glassbox session chat --plain --cwd .",
            (
                "Use /review create from plain interactive mode when the "
                "TUI is unavailable."
            ),
        ),
        CommandGuideEntry(
            "glassbox changeset show CHANGESET_ID --cwd .",
            (
                "Inspect changeset evidence, feedback, verification, and "
                "safe next actions."
            ),
        ),
        CommandGuideEntry(
            "glassbox changeset verification-plan CHANGESET_ID --cwd .",
            "Preview review-loop-aware verification without running commands.",
        ),
        CommandGuideEntry(
            "glassbox changeset feedback status CHANGESET_ID --cwd .",
            ("Inspect feedback responses, stale checks, blockers, and accepted risks."),
        ),
        CommandGuideEntry(
            (
                "glassbox changeset evidence attach CHANGESET_ID "
                "--summary SUMMARY --source-label LABEL --cwd ."
            ),
            "Attach manual evidence as local evidence, not retained command proof.",
        ),
        CommandGuideEntry(
            "glassbox changeset handoff-readiness CHANGESET_ID --cwd .",
            (
                "Inspect final handoff posture without staging, committing, "
                "pushing, or opening a PR."
            ),
        ),
    ),
)

__all__ = ["REVIEW_LOOP_COMMAND_GUIDE_SECTION"]
